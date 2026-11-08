// IIT (ISM) Dhanbad - Campus Smart Parking Map Logic
const map = L.map('map').setView([23.8155, 86.4415], 16);

// Using Esri WorldStreetMap (reliable public basemap, no API key required)
// Note: Esri tile server provides native raster tiles up to zoom level 17 for this geographic region.
// Setting maxNativeZoom: 17 ensures Leaflet automatically upscales tiles smoothly at zoom 18-19,
// preventing Esri's fallback "Map data not yet available" placeholder tiles from appearing.
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
  minZoom: 14,
  maxNativeZoom: 17,
  maxZoom: 19,
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom | IIT (ISM) Dhanbad Smart Parking'
}).addTo(map);

function selectZone(props) {
  const noSelectMsg = document.getElementById('no-select-msg');
  if (noSelectMsg) noSelectMsg.style.display = 'none';

  const zd = document.getElementById('zone-details');
  if (zd) zd.style.display = 'block';

  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val !== undefined && val !== null ? val : '';
  };

  setEl('zd-name', props.zone_name);
  setEl('zd-id', props.zone_id);
  setEl('zd-edge', props.mapped_edge_id || props.edge_id);
  setEl('zd-frontage', (props.frontage_m || props.verified_frontage_m || 0) + ' m');
  setEl('zd-4w', props.four_wheeler_capacity || props.four_wheeler_slots);
  setEl('zd-2w', props.two_wheeler_capacity || props.two_wheeler_slots);
  setEl('zd-sumo', props.sumo_roadside_capacity || props.sumo_capacity);
  setEl('zd-restrictions', props.restrictions || props.restriction_note || 'Standard Single-Side Parallel Parking.');

  const pill = document.getElementById('zd-pill');
  if (pill) {
    const status = (props.operational_status || props.corridor_status || '').toLowerCase();
    if (status.includes('restricted')) {
      pill.className = 'pill pill-red';
      pill.textContent = 'Opposing Corridor Capped (50%)';
    } else if (status.includes('conditional')) {
      pill.className = 'pill pill-amber';
      pill.textContent = 'Conditionally Suitable';
    } else {
      pill.className = 'pill pill-green';
      pill.textContent = 'Suitable For Roadside Parking';
    }
  }
}

// 1. Load Road Network
fetch('/road_network.geojson')
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status} fetching road_network.geojson`);
    return r.json();
  })
  .then(data => {
    L.geoJSON(data, {
      style: function(f) {
        return {
          color: f.properties && f.properties.is_parking_corridor ? '#38bdf8' : '#475569',
          weight: f.properties && f.properties.is_parking_corridor ? 3 : 1.5,
          opacity: f.properties && f.properties.is_parking_corridor ? 0.8 : 0.4
        };
      }
    }).addTo(map);
  })
  .catch(e => console.warn('Could not load road_network.geojson:', e));

// 2. Load Parking Frontage Lines
fetch('/parking_frontage.geojson')
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status} fetching parking_frontage.geojson`);
    return r.json();
  })
  .then(data => {
    L.geoJSON(data, {
      style: function(f) {
        const zid = (f.properties && f.properties.zone_id) || '';
        const isCorridor = zid.includes('library') || zid.includes('nac');
        return {
          color: isCorridor ? '#0284c7' : '#f59e0b',
          weight: 5,
          opacity: 0.85
        };
      },
      onEachFeature: function(f, layer) {
        layer.on('click', () => selectZone(f.properties || {}));
      }
    }).addTo(map);
  })
  .catch(e => console.warn('Could not load parking_frontage.geojson:', e));

// 3. Load Parking Zones Points
fetch('/parking_zones.geojson')
  .then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status} fetching parking_zones.geojson`);
    return r.json();
  })
  .then(data => {
    L.geoJSON(data, {
      pointToLayer: function(f, latlng) {
        return L.circleMarker(latlng, {
          radius: 9,
          fillColor: '#ef4444',
          color: '#ffffff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.95
        });
      },
      onEachFeature: function(f, layer) {
        const props = f.properties || {};
        layer.bindTooltip(
          `<strong>${props.zone_name || 'Zone'}</strong><br>Cap: ${props.total_calibrated_slots || 0} slots (${props.four_wheeler_capacity || 0} 4W, ${props.two_wheeler_capacity || 0} 2W)`,
          { direction: 'top' }
        );
        layer.on('click', () => selectZone(props));
      }
    }).addTo(map);
  })
  .catch(e => console.warn('Could not load parking_zones.geojson:', e));

// 4. Fetch Live SUMO Simulation Telemetry for Sidebar
function fetchLiveTelemetry() {
  fetch('/api/simulation/telemetry')
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(data => {
      if (!data || !data.success) return;
      const s = data.summary || {};
      const m = data.metadata || {};

      const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val !== undefined && val !== null ? val : '--';
      };

      setEl('stat-sim-active', s.globalActiveVehicles ?? 0);
      setEl('stat-sim-parked', s.totalOccupied ?? 0);
      setEl('stat-sim-entered', '+' + (s.globalCumulativeEntered ?? 0));
      setEl('stat-sim-exited', '-' + (s.globalCumulativeExited ?? 0));

      const freshEl = document.getElementById('stat-sim-freshness');
      if (freshEl) {
        if (m.isStale) {
          freshEl.textContent = 'Status: Stale (>5m)';
          freshEl.style.color = '#f59e0b';
        } else {
          freshEl.textContent = 'Status: Fresh (Live)';
          freshEl.style.color = '#10b981';
        }
      }

      const runEl = document.getElementById('stat-sim-run');
      if (runEl) {
        runEl.textContent = m.runId ? `Run: ${m.runId.slice(0, 12)}` : 'Run: Default';
      }
    })
    .catch(e => console.warn('Could not load simulation telemetry:', e));
}

fetchLiveTelemetry();
setInterval(fetchLiveTelemetry, 30000);

