import { html } from "../lib.js";
import { formatDate } from "../utils/format.js";
import { StatusChip } from "./common.js";
import { ReputationWidget } from "./ReputationWidget.js";

export const UserDashboard = ({
  user,
  slots,
  reservations,
  notifications,
  qrCodes,
  reputation,
  onReserve,
  onLoadQr,
  onCheckout,
}) => {
  const reserveSlot = async (event, slotId) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    const hours = Math.max(0, Number(payload.durationHours || 0));
    const minutes = Math.max(0, Number(payload.durationMinutes || 0));
    const normalizedHours = hours + Math.floor(minutes / 60);
    const normalizedMinutes = minutes % 60;

    payload.durationHours = String(normalizedHours);
    payload.durationMinutes = String(normalizedMinutes);
    await onReserve({ ...payload, slotId });
  };

  return html`
    <${ReputationWidget} reputation=${reputation} />
    <section className="grid main-grid">
      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Reserve</p>
            <h2>Available Parking Slots</h2>
          </div>
        </div>
        <div className="slot-list">
          ${slots.map(
            (slot) => html`
              <article className="slot-card" key=${slot._id}>
                <div className="between">
                  <strong>${slot.slotNumber}</strong>
                  <${StatusChip} variant=${slot.isAvailable ? "available" : "occupied"}>
                    ${slot.isAvailable ? "Available" : "Occupied"}
                  </${StatusChip}>
                </div>
                <p className="muted">${slot.zone?.name || "Zone"} • ${slot.zone?.location || ""}</p>
                <div className="chip-row">
                  <${StatusChip}>${slot.vehicleType}</${StatusChip}>
                </div>
                <form className="form-grid" onSubmit=${(event) => reserveSlot(event, slot._id)}>
                  <label>
                    <span>Vehicle Number</span>
                    <input name="vehicleNumber" defaultValue=${user.vehicleNumber || ""} />
                  </label>
                  <label>
                    <span>Duration</span>
                    <div className="duration-inputs">
                      <input
                        name="durationHours"
                        type="number"
                        min="0"
                        max="12"
                        defaultValue="2"
                        inputMode="numeric"
                      />
                      <span className="duration-separator">hr</span>
                      <input
                        name="durationMinutes"
                        type="number"
                        min="0"
                        max="59"
                        defaultValue="0"
                        step="5"
                        inputMode="numeric"
                      />
                      <span className="duration-separator">min</span>
                    </div>
                  </label>
                  <button className="btn btn-primary" type="submit" disabled=${!slot.isAvailable}>
                    Reserve Slot
                  </button>
                </form>
              </article>
            `
          )}
        </div>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">History</p>
            <h2>My Reservations</h2>
          </div>
        </div>
        ${notifications.length
          ? html`
              <div className="cards">
                ${notifications.map(
                  (item) => html`
                    <div className="notification" key=${item.reservationId}>
                      <strong>Expiry Alert</strong>
                      <p>${item.message}</p>
                      <p className="subtle">Expires at ${formatDate(item.expiresAt)}</p>
                    </div>
                  `
                )}
              </div>
            `
          : html`<p className="muted">No active expiry notifications right now.</p>`}

        <div className="reservation-list">
          ${reservations.map(
            (reservation) => html`
              <article className="reservation-card" key=${reservation._id}>
                <div className="between">
                  <div>
                    <strong>${reservation.zone?.name || "Zone"} / ${reservation.slot?.slotNumber || ""}</strong>
                    <p className="muted">${reservation.permitCode}</p>
                  </div>
                  <${StatusChip} variant=${reservation.status}>${reservation.status}</${StatusChip}>
                </div>
                <p>Vehicle: ${reservation.vehicleNumber}</p>
                <p className="subtle">
                  From ${formatDate(reservation.startsAt)} to ${formatDate(reservation.expiresAt)}
                </p>
                <button className="btn btn-ghost" onClick=${() => onLoadQr(reservation._id)}>
                  View QR Permit
                </button>
                ${reservation.status === "active"
                  ? html`
                      <button 
                        className="btn btn-secondary checkout-btn" 
                        onClick=${() => onCheckout(reservation._id)}
                      >
                        Check Out
                      </button>
                    `
                  : null}
                ${qrCodes[reservation._id]
                  ? html`
                      <img
                        className="qr-image"
                        src=${qrCodes[reservation._id]}
                        alt="QR permit"
                      />
                    `
                  : null}
              </article>
            `
          )}
        </div>
      </div>
    </section>
  `;
};
