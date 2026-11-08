import { html, useEffect, useMemo, useState } from "./lib.js";
import { AuthPage } from "./components/AuthPage.js";
import { DashboardShell } from "./components/common.js";
import { UserDashboard } from "./components/UserDashboard.js";
import { SecurityDashboard } from "./components/SecurityDashboard.js";
import { AdminDashboard } from "./components/AdminDashboard.js";
import { TrafficPredictionDashboard } from "./components/TrafficPredictionDashboard.js";
import { apiRequest } from "./services/api.js";
import { getPermitCodeFromText } from "./utils/format.js";
import { clearSession, loadSession, saveSession } from "./utils/session.js";

const emptyData = {
  slots: [],
  reservations: [],
  notifications: [],
  activeReservations: [],
  stats: null,
  reports: [],
  zones: [],
  adminZones: [],
  zoneUsage: [],
};

export const App = () => {
  const [session, setSession] = useState(loadSession);
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dashboardData, setDashboardData] = useState(emptyData);
  const [qrCodes, setQrCodes] = useState({});
  const [verificationResult, setVerificationResult] = useState(null);
  const [activeTab, setActiveTab] = useState("traffic-prediction");

  const resetForLogout = (message = null) => {
    clearSession();
    setSession({ token: "", user: null });
    setDashboardData(emptyData);
    setQrCodes({});
    setVerificationResult(null);
    setFeedback(message);
  };

  const handleApiError = (error) => {
    if (error.message === "Invalid token" || error.message === "Unauthorized") {
      resetForLogout({ type: "error", message: "Your session expired. Please log in again." });
      return;
    }

    setFeedback({ type: "error", message: error.message });
  };

  const refreshDashboard = async (roleOverride) => {
    const currentRole = roleOverride || session.user?.role;
    if (!session.token || !currentRole) {
      return;
    }

    setLoading(true);
    try {
      let nextData = { ...emptyData };

      if (currentRole === "user") {
        const [slotsResponse, reservationsResponse, reputationResponse] = await Promise.all([
          apiRequest("/api/parking/slots", {}, session.token),
          apiRequest("/api/parking/my-reservations", {}, session.token),
          apiRequest("/api/parking/reputation", {}, session.token).catch(() => ({})),
        ]);

        nextData = {
          ...nextData,
          slots: slotsResponse.slots,
          reservations: reservationsResponse.reservations,
          notifications: reservationsResponse.notifications,
          reputation: reputationResponse.reputation,
        };
      }

      if (currentRole === "security") {
        const [slotsResponse, zonesResponse, reservationsResponse] = await Promise.all([
          apiRequest("/api/parking/slots", {}, session.token),
          apiRequest("/api/parking/zones", {}, session.token),
          apiRequest("/api/parking/active-reservations", {}, session.token),
        ]);

        nextData = {
          ...nextData,
          slots: slotsResponse.slots,
          zones: zonesResponse.zones,
          activeReservations: reservationsResponse.reservations,
        };
      }

      if (currentRole === "admin") {
        const [
          zonesResponse,
          slotsResponse,
          statsResponse,
          reportsResponse,
          occupancyResponse,
          predictionsResponse,
          reputationStatsResponse
        ] = await Promise.all([
          apiRequest("/api/admin/zones", {}, session.token),
          apiRequest("/api/parking/slots", {}, session.token),
          apiRequest("/api/admin/statistics", {}, session.token),
          apiRequest("/api/admin/reports", {}, session.token),
          apiRequest("/api/analytics/occupancy", {}, session.token).catch(() => ({})),
          apiRequest("/api/analytics/predictions", {}, session.token).catch(() => ({})),
          apiRequest("/api/analytics/reputation-stats", {}, session.token).catch(() => ({})),
        ]);

        nextData = {
          ...nextData,
          adminZones: zonesResponse.zones,
          slots: slotsResponse.slots,
          stats: statsResponse.statistics,
          zoneUsage: statsResponse.zoneUsage,
          reports: reportsResponse.reportRows,
          analyticsData: {
            occupancy: occupancyResponse.occupancyData,
            predictions: predictionsResponse.predictions,
            reputationStats: reputationStatsResponse.reputationDistribution,
          }
        };
      }

      setDashboardData(nextData);
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session.token && session.user) {
      refreshDashboard(session.user.role);
    }
  }, [session.token, session.user?.role]);

  const metrics = useMemo(() => {
    if (!session.user) {
      return [];
    }

    if (session.user.role === "user") {
      const activeCount = dashboardData.reservations.filter(
        (item) => item.status === "active"
      ).length;

      return [
        {
          label: "Available Slots",
          value: dashboardData.slots.filter((slot) => slot.isAvailable).length,
        },
        { label: "Active Permits", value: activeCount },
        { label: "Parking History", value: dashboardData.reservations.length },
        { label: "Alerts", value: dashboardData.notifications.length },
      ];
    }

    if (session.user.role === "security") {
      return [
        { label: "Active Reservations", value: dashboardData.activeReservations.length },
        {
          label: "Available Slots",
          value: dashboardData.slots.filter((slot) => slot.isAvailable).length,
        },
        {
          label: "Occupied Slots",
          value: dashboardData.slots.filter((slot) => !slot.isAvailable).length,
        },
        { label: "Zones", value: dashboardData.zones.length },
      ];
    }

    const stats = dashboardData.stats || {
      totalZones: 0,
      totalSlots: 0,
      availableSlots: 0,
      totalReservations: 0,
    };

    return [
      { label: "Parking Zones", value: stats.totalZones },
      { label: "Total Slots", value: stats.totalSlots },
      { label: "Available Slots", value: stats.availableSlots },
      { label: "Reservations", value: stats.totalReservations },
    ];
  }, [session.user, dashboardData]);

  const authenticate = async (url, payload, successMessage) => {
    try {
      const data = await apiRequest(url, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      saveSession(data.token, data.user);
      setSession({ token: data.token, user: data.user });
      setFeedback({ type: "success", message: successMessage });
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleReserve = async (payload) => {
    try {
      await apiRequest(
        "/api/parking/reserve",
        { method: "POST", body: JSON.stringify(payload) },
        session.token
      );
      setFeedback({ type: "success", message: "Reservation created successfully." });
      await refreshDashboard("user");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleLoadQr = async (reservationId) => {
    try {
      const data = await apiRequest(
        `/api/parking/reservations/${reservationId}/qr`,
        {},
        session.token
      );
      setQrCodes((current) => ({ ...current, [reservationId]: data.qrDataUrl }));
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleVerifyPermit = async (rawValue, forwardedError = null) => {
    if (forwardedError) {
      handleApiError(forwardedError);
      throw forwardedError;
    }

    const permitCode = getPermitCodeFromText(rawValue);
    if (!permitCode) {
      const error = new Error("No permit code found in the scanned QR data.");
      handleApiError(error);
      throw error;
    }

    try {
      const data = await apiRequest(
        "/api/parking/verify-permit",
        {
          method: "POST",
          body: JSON.stringify({ permitCode }),
        },
        session.token
      );
      setVerificationResult(data);
      setFeedback({ type: "success", message: data.message });
      await refreshDashboard("security");
      return data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  };

  const handleToggleSlot = async (slotId, isAvailable) => {
    try {
      await apiRequest(
        `/api/parking/slots/${slotId}/availability`,
        {
          method: "PATCH",
          body: JSON.stringify({ isAvailable: !isAvailable }),
        },
        session.token
      );
      setFeedback({ type: "success", message: "Slot availability updated." });
      await refreshDashboard("security");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleCreateZone = async (payload) => {
    try {
      await apiRequest(
        "/api/admin/zones",
        { method: "POST", body: JSON.stringify(payload) },
        session.token
      );
      setFeedback({ type: "success", message: "Parking zone added." });
      await refreshDashboard("admin");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleCreateSlot = async (payload) => {
    try {
      await apiRequest(
        "/api/admin/slots",
        { method: "POST", body: JSON.stringify(payload) },
        session.token
      );
      setFeedback({ type: "success", message: "Parking slot added." });
      await refreshDashboard("admin");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleToggleZone = async (zoneId, isActive) => {
    try {
      await apiRequest(
        `/api/admin/zones/${zoneId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ isActive: !isActive }),
        },
        session.token
      );
      setFeedback({ type: "success", message: "Parking zone updated." });
      await refreshDashboard("admin");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleCheckout = async (reservationId) => {
    try {
      await apiRequest(
        `/api/parking/checkout/${reservationId}`,
        { method: "POST" },
        session.token
      );
      setFeedback({ type: "success", message: "Successfully checked out." });
      await refreshDashboard("user");
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleLogout = () => {
    resetForLogout(null);
  };

  if (!session.user || !session.token) {
    return html`
      ${loading ? html`<div className="loading-state">Refreshing dashboard data...</div>` : null}
      <${AuthPage}
        feedback=${feedback}
        onLogin=${(payload) =>
          authenticate("/api/auth/login", payload, "Login successful.")}
        onRegister=${(payload) =>
          authenticate("/api/auth/register", payload, "Account created successfully.")}
      />
    `;
  }

  return html`
    ${loading ? html`<div className="loading-state">Refreshing dashboard data...</div>` : null}
    <${DashboardShell}
      user=${session.user}
      feedback=${feedback}
      metrics=${metrics}
      activeTab=${activeTab}
      onTabChange=${setActiveTab}
      onLogout=${handleLogout}
    >
      ${activeTab === "traffic-prediction"
        ? html`<${TrafficPredictionDashboard} token=${session.token} />`
        : html`
            ${session.user.role === "user"
              ? html`
                  <${UserDashboard}
                    user=${session.user}
                    slots=${dashboardData.slots}
                    reservations=${dashboardData.reservations}
                    notifications=${dashboardData.notifications}
                    qrCodes=${qrCodes}
                    reputation=${dashboardData.reputation}
                    onReserve=${handleReserve}
                    onLoadQr=${handleLoadQr}
                    onCheckout=${handleCheckout}
                  />
                `
              : null}
            ${session.user.role === "security"
              ? html`
                  <${SecurityDashboard}
                    slots=${dashboardData.slots}
                    activeReservations=${dashboardData.activeReservations}
                    verificationResult=${verificationResult}
                    onVerify=${handleVerifyPermit}
                    onToggleSlot=${handleToggleSlot}
                  />
                `
              : null}
            ${session.user.role === "admin"
              ? html`
                  <${AdminDashboard}
                    adminZones=${dashboardData.adminZones}
                    zoneUsage=${dashboardData.zoneUsage}
                    reports=${dashboardData.reports}
                    analyticsData=${dashboardData.analyticsData}
                    onCreateZone=${handleCreateZone}
                    onCreateSlot=${handleCreateSlot}
                    onToggleZone=${handleToggleZone}
                  />
                `
              : null}
          `}
    </${DashboardShell}>
  `;
};
