import { html } from "../lib.js";

export const AnalyticsDashboard = ({ occupancy, predictions, reputationStats }) => {
  return html`
    <div className="analytics-section grid">
      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Real-Time</p>
            <h2>Zone Occupancy</h2>
          </div>
        </div>
        <div className="bar-chart">
          ${occupancy?.map(zone => html`
            <div className="bar-item" key=${zone.zone}>
              <div className="bar-label">
                <span>${zone.zone}</span>
                <span>${Math.round(zone.occupancyRate)}%</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style=${{ width: `${zone.occupancyRate}%` }}></div>
              </div>
            </div>
          `)}
          ${(!occupancy || occupancy.length === 0) ? html`<p className="muted">No occupancy data available.</p>` : null}
        </div>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Predictions</p>
            <h2>24-Hour Forecast</h2>
          </div>
        </div>
        <div className="prediction-chart bar-chart">
           ${predictions?.map((pred, i) => html`
            <div className="bar-item" key=${i}>
              <div className="bar-label">
                <span>${new Date(pred.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                <span>${pred.predictedOccupancy}%</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill prediction-fill" style=${{ width: `${pred.predictedOccupancy}%` }}></div>
              </div>
            </div>
          `)}
          ${(!predictions || predictions.length === 0) ? html`<p className="muted">No prediction data available.</p>` : null}
        </div>
      </div>

      <div className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Community</p>
            <h2>Reputation Stats</h2>
          </div>
        </div>
        <div className="bar-chart">
           ${reputationStats ? Object.entries(reputationStats).sort((a,b) => b[0]-a[0]).map(([stars, count]) => html`
             <div className="bar-item" key=${stars}>
               <div className="bar-label">
                 <span>${'★'.repeat(Number(stars))}${'☆'.repeat(5 - Number(stars))}</span>
                 <span>${count} users</span>
               </div>
               <div className="bar-track">
                 <div className="bar-fill" style=${{ width: `${count * 20}%`, backgroundColor: Number(stars) >= 4 ? '#2d6a4f' : Number(stars) >= 2 ? '#e9c46a' : '#e76f51' }}></div>
               </div>
             </div>
           `) : html`<p className="muted">No reputation data.</p>`}
        </div>
      </div>
    </div>
  `;
};
