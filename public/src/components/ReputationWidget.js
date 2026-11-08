import { html } from "../lib.js";

export const ReputationWidget = ({ reputation }) => {
  if (!reputation) return null;

  const { stars = 3, benefits = 0, warnings = 0, feeMultiplier = 1.0 } = reputation;
  const starArray = Array.from({ length: 5 }, (_, i) => i < stars);

  return html`
    <div className="reputation-widget panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">Your Status</p>
          <h2>Campus Reputation</h2>
        </div>
      </div>
      <div className="reputation-content">
        <div className="star-display">
          ${starArray.map((isFilled, index) => html`
            <span key=${index} className=${`star ${isFilled ? "star-filled" : "star-empty"}`}>
              ${isFilled ? "★" : "☆"}
            </span>
          `)}
        </div>
        <div className="reputation-stats grid">
          <div className="metric-card">
            <span className="metric-label">Benefits</span>
            <div className="metric-value">${benefits}</div>
          </div>
          <div className="metric-card">
            <span className="metric-label">Warnings</span>
            <div className="metric-value">${warnings}</div>
          </div>
          <div className="metric-card">
            <span className="metric-label">Fee Multiplier</span>
            <div className="metric-value">${feeMultiplier}x</div>
          </div>
        </div>
      </div>
    </div>
  `;
};
