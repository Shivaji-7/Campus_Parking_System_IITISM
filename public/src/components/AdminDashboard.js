import { html } from "../lib.js";
import { StatusChip } from "./common.js";
import { AnalyticsDashboard } from "./AnalyticsDashboard.js";

export const AdminDashboard = ({
  adminZones,
  zoneUsage,
  reports,
  analyticsData,
  onCreateZone,
  onCreateSlot,
  onToggleZone,
}) => {
  const submitZone = async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    await onCreateZone(payload);
    event.currentTarget.reset();
  };

  const submitSlot = async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    await onCreateSlot(payload);
    event.currentTarget.reset();
  };

  return html`
    <${AnalyticsDashboard}
      occupancy=${analyticsData?.occupancy}
      predictions=${analyticsData?.predictions}
      reputationStats=${analyticsData?.reputationStats}
    />
    <section className="grid main-grid">
      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Management</p>
            <h2>Create Parking Zone</h2>
          </div>
        </div>
        <form className="form-grid" onSubmit=${submitZone}>
          <label><span>Zone Name</span><input name="name" required /></label>
          <label><span>Location</span><input name="location" required /></label>
          <label><span>Description</span><textarea name="description"></textarea></label>
          <button className="btn btn-primary" type="submit">Add Zone</button>
        </form>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Inventory</p>
            <h2>Create Parking Slot</h2>
          </div>
        </div>
        <form className="form-grid" onSubmit=${submitSlot}>
          <label><span>Slot Number</span><input name="slotNumber" required /></label>
          <label>
            <span>Zone</span>
            <select name="zone" required>
              <option value="">Select a zone</option>
              ${adminZones.map(
                (zone) => html`
                  <option value=${zone._id} key=${zone._id}>${zone.name} - ${zone.location}</option>
                `
              )}
            </select>
          </label>
          <label>
            <span>Vehicle Type</span>
            <select name="vehicleType" defaultValue="four-wheeler">
              <option value="four-wheeler">Four Wheeler</option>
              <option value="two-wheeler">Two Wheeler</option>
              <option value="visitor">Visitor</option>
              <option value="ev">EV</option>
            </select>
          </label>
          <label><span>Notes</span><input name="notes" /></label>
          <button className="btn btn-secondary" type="submit">Add Slot</button>
        </form>
      </div>
    </section>

    <section className="grid main-grid">
      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Zones</p>
            <h2>Manage Parking Zones</h2>
          </div>
        </div>
        <div className="reservation-list">
          ${adminZones.map(
            (zone) => html`
              <article className="reservation-card" key=${zone._id}>
                <div className="between">
                  <div>
                    <strong>${zone.name}</strong>
                    <p className="muted">${zone.location}</p>
                  </div>
                  <${StatusChip} variant=${zone.isActive ? "available" : "expired"}>
                    ${zone.isActive ? "Active" : "Inactive"}
                  </${StatusChip}>
                </div>
                <p className="subtle">${zone.description || "No description provided."}</p>
                <button className="btn btn-ghost" onClick=${() => onToggleZone(zone._id, zone.isActive)}>
                  Mark as ${zone.isActive ? "Inactive" : "Active"}
                </button>
              </article>
            `
          )}
        </div>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Statistics</p>
            <h2>Usage Overview</h2>
          </div>
        </div>
        <div className="zone-usage">
          ${zoneUsage.map(
            (zone) => html`
              <article className="reservation-card" key=${zone.zoneName}>
                <div className="between">
                  <strong>${zone.zoneName || "Unknown Zone"}</strong>
                  <${StatusChip} variant="active">${zone.reservations} reservations</${StatusChip}>
                </div>
              </article>
            `
          )}
        </div>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Reports</p>
            <h2>Reservation Report</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Zone</th>
                <th>Slot</th>
                <th>Status</th>
                <th>Permit</th>
              </tr>
            </thead>
            <tbody>
              ${reports.map(
                (report, index) => html`
                  <tr key=${`${report.permitCode}-${index}`}>
                    <td>${report.user}</td>
                    <td>${report.zone}</td>
                    <td>${report.slot}</td>
                    <td>${report.status}</td>
                    <td>${report.permitCode}</td>
                  </tr>
                `
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  `;
};
