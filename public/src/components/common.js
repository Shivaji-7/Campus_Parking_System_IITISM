import { html } from "../lib.js";

export const roleHeadline = {
  user: "Student and Staff Parking Dashboard",
  security: "Security Operations Dashboard",
  admin: "Administration Dashboard",
};

export const FeedbackBanner = ({ feedback }) =>
  feedback
    ? html`<div className=${`feedback ${feedback.type}`}>${feedback.message}</div>`
    : null;

export const StatusChip = ({ variant = "", children }) =>
  html`<span className=${`chip ${variant}`.trim()}>${children}</span>`;

export const MetricGrid = ({ metrics = [] }) => html`
  <section className="metrics">
    ${metrics.map(
      (metric) => html`
        <article className="metric-card" key=${metric.label}>
          <div className="metric-label">${metric.label}</div>
          <div className="metric-value">${metric.value}</div>
        </article>
      `
    )}
  </section>
`;

export const DashboardShell = ({ user, feedback, metrics, onLogout, activeTab = "main", onTabChange, children }) => html`
  <section className="dashboard-header">
    <div className="dashboard-title">
      <p className="eyebrow">${user.role}</p>
      <h2>${roleHeadline[user.role]}</h2>
      <p className="muted">Signed in as ${user.name} (${user.email}) • IIT (ISM) Dhanbad</p>
    </div>
    <div style=${{ display: "flex", gap: "10px", alignItems: "center" }}>
      <button className="btn btn-danger" onClick=${onLogout}>Logout</button>
    </div>
  </section>

  <!-- Section Switcher Tabs -->
  <nav className="tab-navigation" style=${{ 
    display: "flex", 
    gap: "12px", 
    margin: "18px 0 24px", 
    borderBottom: "2px solid rgba(25, 55, 40, 0.12)", 
    paddingBottom: "12px",
    flexWrap: "wrap"
  }}>
    <button 
      className=${`btn ${activeTab === "main" ? "btn-primary" : "btn-ghost"}`}
      onClick=${() => onTabChange && onTabChange("main")}
      style=${{ fontSize: "0.95rem", padding: "10px 18px" }}
    >
      📋 Campus Operations (${user.role.toUpperCase()})
    </button>
    <button 
      className=${`btn ${activeTab === "traffic-prediction" ? "btn-primary" : "btn-secondary"}`}
      onClick=${() => onTabChange && onTabChange("traffic-prediction")}
      style=${{ 
        fontSize: "0.95rem", 
        padding: "10px 18px", 
        display: "flex", 
        alignItems: "center", 
        gap: "8px" 
      }}
    >
      🚗 Traffic & Parking Prediction
      <span className="chip" style=${{ 
        background: activeTab === "traffic-prediction" ? "#fff" : "#1f7a54", 
        color: activeTab === "traffic-prediction" ? "#1f7a54" : "#fff", 
        padding: "2px 8px", 
        fontSize: "0.75rem",
        fontWeight: "bold"
      }}>SUMO + ML</span>
    </button>
    <a 
      href="/map.html" 
      target="_blank"
      className="btn btn-secondary"
      style=${{ 
        fontSize: "0.95rem", 
        padding: "10px 18px", 
        display: "flex", 
        alignItems: "center", 
        gap: "8px",
        textDecoration: "none"
      }}
    >
      🗺️ Campus GIS Map
      <span className="chip" style=${{ 
        background: "#0284c7", 
        color: "#fff", 
        padding: "2px 8px", 
        fontSize: "0.75rem",
        fontWeight: "bold"
      }}>GeoJSON</span>
    </a>
  </nav>

  <${FeedbackBanner} feedback=${feedback} />
  ${activeTab === "main" ? html`<${MetricGrid} metrics=${metrics} />` : null}
  ${children}
`;
