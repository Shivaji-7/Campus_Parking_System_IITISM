#!/usr/bin/env python3
"""
generate_geospatial_layers.py
=============================
Stage 1, Part 5 – Geospatial Layer Generation
Campus Smart Parking Management System — IIT (ISM) Dhanbad

Generates:
  1. simulation/output/parking_zones.geojson   (Point & Frontage Buffer Polygons, WGS84)
  2. simulation/output/road_network.geojson    (All normal road edges with geometry, WGS84)
  3. simulation/output/parking_frontage.geojson(Linear frontage vectors along curb, WGS84)
  4. simulation/output/signage_slot_mapping.csv(Physical signage to database slot mapping)
  5. public/map.html                           (Standalone interactive GIS Map with Leaflet & OSM)
"""

import csv
import json
import os
import xml.etree.ElementTree as ET
import sumolib

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_DIR  = BASE_DIR
OUT_DIR  = os.path.join(SIM_DIR, "output")
PUB_DIR  = os.path.join(os.path.dirname(SIM_DIR), "public")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PUB_DIR, exist_ok=True)

NET_XML       = os.path.join(SIM_DIR, "campus.net.xml")
PARK_XML      = os.path.join(SIM_DIR, "campus_parking.add.xml")
CALIB_CSV     = os.path.join(OUT_DIR, "zone_capacity_calibration.csv")
ROAD_GEOM_CSV = os.path.join(OUT_DIR, "road_geometry.csv")

OUT_ZONES_GEOJSON    = os.path.join(OUT_DIR, "parking_zones.geojson")
OUT_ROADS_GEOJSON    = os.path.join(OUT_DIR, "road_network.geojson")
OUT_FRONTAGE_GEOJSON = os.path.join(OUT_DIR, "parking_frontage.geojson")
OUT_SIGNAGE_CSV      = os.path.join(OUT_DIR, "signage_slot_mapping.csv")
OUT_MAP_HTML         = os.path.join(PUB_DIR, "map.html")

# Also save copies into public/ for web access
PUB_ZONES_GEOJSON    = os.path.join(PUB_DIR, "parking_zones.geojson")
PUB_ROADS_GEOJSON    = os.path.join(PUB_DIR, "road_network.geojson")
PUB_FRONTAGE_GEOJSON = os.path.join(PUB_DIR, "parking_frontage.geojson")


def load_calib_data():
    with open(CALIB_CSV, encoding="utf-8") as f:
        return {r["zone_id"]: r for r in csv.DictReader(f)}


def generate_signage_mapping_csv(calib_dict):
    fields = [
        "zone_id", "zone_name", "prefix", "vehicle_class",
        "slot_id_range", "database_count", "signage_label_format",
        "physical_signage_verification_status", "outstanding_manual_action"
    ]
    rows = []
    for zid, c in calib_dict.items():
        # Derive prefix from zone_id
        pfx_map = {
            "zone_main_gate": "MG", "zone_sac": "SAC", "zone_nlhc": "NLHC",
            "zone_library": "CL", "zone_nac": "NAC", "zone_cse": "CSE",
            "zone_health_centre": "HC", "zone_i2h": "I2H",
            "zone_academic_complex": "AC", "zone_amber": "AMB",
            "zone_aquamarine": "AQM", "zone_mechanical": "ME",
            "zone_enviro": "ENV", "zone_oat": "OAT"
        }
        pfx = pfx_map.get(zid, "ZN")
        c_4w = int(c["proposed_calibrated_car_slots"])
        c_2w = int(c["proposed_calibrated_2w_slots"])

        rows.append({
            "zone_id": zid,
            "zone_name": c["zone_name"],
            "prefix": pfx,
            "vehicle_class": "four-wheeler",
            "slot_id_range": f"{pfx}-4W-01 to {pfx}-4W-{c_4w:02d}",
            "database_count": c_4w,
            "signage_label_format": f"IIT ISM {pfx} CAR BAY #01-{c_4w:02d}",
            "physical_signage_verification_status": "requires_on_site_verification",
            "outstanding_manual_action": "Paint yellow bay markings (5.0m x 2.5m) and install pole sign."
        })

        rows.append({
            "zone_id": zid,
            "zone_name": c["zone_name"],
            "prefix": pfx,
            "vehicle_class": "two-wheeler",
            "slot_id_range": f"{pfx}-2W-01 to {pfx}-2W-{c_2w:02d}",
            "database_count": c_2w,
            "signage_label_format": f"IIT ISM {pfx} 2W BAY #01-{c_2w:02d}",
            "physical_signage_verification_status": "requires_on_site_verification",
            "outstanding_manual_action": "Mark white chevron/curb stalls (2.0m x 1.0m) with dedicated two-wheeler sign."
        })

    with open(OUT_SIGNAGE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {OUT_SIGNAGE_CSV} ({len(rows)} rows)")


def generate_geojson_layers():
    print("Loading SUMO network via sumolib...")
    net = sumolib.net.readNet(NET_XML)
    calib = load_calib_data()

    # Parse campus_parking.add.xml
    park_tree = ET.parse(PARK_XML)
    parking_areas = {pa.attrib["id"]: pa.attrib for pa in park_tree.getroot()}

    # -----------------------------------------------------------------------
    # 1. PARKING ZONES GEOJSON (Points & buffer footprints)
    # -----------------------------------------------------------------------
    zone_features = []
    frontage_features = []

    for zid, pa_attr in parking_areas.items():
        c_info = calib.get(zid, {})
        lane_id = pa_attr["lane"]
        edge_id = lane_id.rsplit("_", 1)[0]
        start_p = float(pa_attr.get("startPos", 2.0))
        end_p   = float(pa_attr.get("endPos", 80.0))
        sumo_cap= int(pa_attr.get("roadSideCapacity", 0))

        lane = net.getLane(lane_id)
        lane_shape = lane.getShape()  # list of (x, y) in net coordinates
        
        # Convert entire lane shape to (lon, lat)
        wgs_lane_coords = [list(net.convertXY2LonLat(x, y)) for x, y in lane_shape]

        # Calculate midpoint in WGS84
        mid_idx = len(lane_shape) // 2
        mid_x, mid_y = lane_shape[mid_idx]
        mid_lon, mid_lat = net.convertXY2LonLat(mid_x, mid_y)

        # Usable frontage line: slice lane geometry approximately between startPos and endPos
        # For visualization, we include the exact lane polyline segment
        frontage_coords = wgs_lane_coords

        c_4w = int(c_info.get("proposed_calibrated_car_slots", sumo_cap))
        c_2w = int(c_info.get("proposed_calibrated_2w_slots", 0))
        tot_slots = c_4w + c_2w
        frontage_m = float(c_info.get("frontage_m", end_p - start_p))

        # Zone Point Feature
        zone_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [mid_lon, mid_lat]
            },
            "properties": {
                "zone_id": zid,
                "zone_name": pa_attr.get("name", zid),
                "mapped_edge_id": edge_id,
                "host_lane_id": lane_id,
                "road_type": c_info.get("road_type", "residential"),
                "frontage_m": frontage_m,
                "total_calibrated_slots": tot_slots,
                "four_wheeler_capacity": c_4w,
                "two_wheeler_capacity": c_2w,
                "sumo_roadside_capacity": sumo_cap,
                "parking_classification": "roadside_parallel_curb",
                "confidence": c_info.get("confidence_level", "medium"),
                "operational_status": c_info.get("operational_corridor_status", "suitable_for_parking"),
                "restrictions": c_info.get("corridor_constraint_remedy", "None"),
                "source": "IIT ISM SUMO Network & Stage 1 Calibration"
            }
        })

        # Frontage Line Feature
        frontage_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": frontage_coords
            },
            "properties": {
                "zone_id": zid,
                "zone_name": pa_attr.get("name", zid),
                "edge_id": edge_id,
                "lane_id": lane_id,
                "verified_frontage_m": frontage_m,
                "start_pos_m": start_p,
                "end_pos_m": end_p,
                "sumo_capacity": sumo_cap,
                "four_wheeler_slots": c_4w,
                "two_wheeler_slots": c_2w,
                "corridor_status": c_info.get("operational_corridor_status", "suitable_for_parking"),
                "restriction_note": c_info.get("corridor_constraint_remedy", "")
            }
        })

    zones_fc = {
        "type": "FeatureCollection",
        "name": "IIT_ISM_Calibrated_Parking_Zones",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": zone_features
    }

    frontage_fc = {
        "type": "FeatureCollection",
        "name": "IIT_ISM_Parking_Frontage_Lines",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": frontage_features
    }

    with open(OUT_ZONES_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(zones_fc, f, indent=2)
    with open(PUB_ZONES_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(zones_fc, f, indent=2)
    print(f"Wrote {OUT_ZONES_GEOJSON} ({len(zone_features)} zones)")

    with open(OUT_FRONTAGE_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(frontage_fc, f, indent=2)
    with open(PUB_FRONTAGE_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(frontage_fc, f, indent=2)
    print(f"Wrote {OUT_FRONTAGE_GEOJSON} ({len(frontage_features)} frontage lines)")

    # -----------------------------------------------------------------------
    # 2. ROAD NETWORK GEOJSON (Normal edges)
    # -----------------------------------------------------------------------
    print("Exporting road network edges to GeoJSON...")
    road_features = []
    all_edges = net.getEdges()
    parking_edge_ids = {pa.attrib["lane"].rsplit("_", 1)[0] for pa in park_tree.getroot()}

    for edge in all_edges:
        if edge.isSpecial():  # skip internal connectors
            continue
        
        eid = edge.getID()
        lanes = edge.getLanes()
        if not lanes:
            continue
        
        shape = lanes[0].getShape()
        if len(shape) < 2:
            continue

        wgs_coords = [list(net.convertXY2LonLat(x, y)) for x, y in shape]
        rtype = edge.getType()
        is_parking = eid in parking_edge_ids

        road_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": wgs_coords
            },
            "properties": {
                "edge_id": eid,
                "road_type": rtype,
                "lane_count": edge.getLaneNumber(),
                "length_m": round(edge.getLength(), 2),
                "speed_limit_mps": edge.getSpeed(),
                "is_parking_corridor": is_parking,
                "data_quality": "inferred_width"
            }
        })

    roads_fc = {
        "type": "FeatureCollection",
        "name": "IIT_ISM_Campus_Road_Network",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": road_features
    }

    with open(OUT_ROADS_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(roads_fc, f)
    with open(PUB_ROADS_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(roads_fc, f)
    print(f"Wrote {OUT_ROADS_GEOJSON} ({len(road_features)} normal road edges)")


def generate_interactive_map_html():
    """Generates a high-performance Leaflet-based campus map dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IIT (ISM) Dhanbad — Campus Smart Parking Map</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', -apple-system, sans-serif; background: #0f172a; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; }
    header { background: #1e293b; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
    h1 { font-size: 1.15rem; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
    .badge { background: #0284c7; color: #fff; font-size: 0.72rem; padding: 3px 8px; border-radius: 9999px; font-weight: 600; }
    .main-container { display: flex; flex: 1; position: relative; overflow: hidden; }
    #map { flex: 1; height: 100%; background: #0b1120; }
    .sidebar { width: 380px; background: #1e293b; border-left: 1px solid #334155; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
    .card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; }
    .card h3 { font-size: 0.88rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .stat-box { background: #1e293b; padding: 10px; border-radius: 6px; text-align: center; border: 1px solid #334155; }
    .stat-val { font-size: 1.35rem; font-weight: 700; color: #38bdf8; }
    .stat-lbl { font-size: 0.72rem; color: #94a3b8; margin-top: 2px; }
    .legend-item { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; margin-top: 6px; }
    .legend-color { width: 14px; height: 14px; border-radius: 3px; }
    .zone-detail-title { font-size: 1.1rem; font-weight: 700; color: #f8fafc; margin-bottom: 4px; }
    .pill { display: inline-block; padding: 2px 8px; font-size: 0.72rem; border-radius: 4px; font-weight: 600; margin-bottom: 8px; }
    .pill-green { background: #065f46; color: #6ee7b7; }
    .pill-amber { background: #78350f; color: #fde68a; }
    .pill-red { background: #881337; color: #fecdd3; }
    .nav-btn { display: inline-block; text-decoration: none; background: #38bdf8; color: #0f172a; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <h1><span>Campus Smart Parking Management</span> <span class="badge">IIT (ISM) Dhanbad</span></h1>
    <div>
      <a href="/" class="nav-btn">Return to App Dashboard</a>
    </div>
  </header>

  <div class="main-container">
    <div id="map"></div>
    <div class="sidebar">
      <div class="card">
        <h3>Campus Capacity Overview</h3>
        <div class="stat-grid">
          <div class="stat-box">
            <div class="stat-val" id="stat-total-slots">503</div>
            <div class="stat-lbl">Total Seed Slots</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="stat-sumo-cap">213</div>
            <div class="stat-lbl">SUMO Car Capacity</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="stat-4w">147</div>
            <div class="stat-lbl">Four-Wheeler (70%)</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="stat-2w">356</div>
            <div class="stat-lbl">Two-Wheeler (30%)</div>
          </div>
        </div>
      </div>

      <div class="card" id="selected-zone-card">
        <h3>Selected Zone Inspector</h3>
        <p style="font-size: 0.82rem; color: #94a3b8;" id="no-select-msg">Click any marker or frontage line on the campus map to view its geometric details and slot breakdown.</p>
        <div id="zone-details" style="display: none;">
          <div class="zone-detail-title" id="zd-name">Central Library</div>
          <div id="zd-pill"></div>
          <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px;">Zone ID: <code id="zd-id" style="color: #38bdf8;">zone_library</code></p>
          <div style="font-size: 0.82rem; line-height: 1.5; margin-bottom: 8px;">
            <div><strong>Host Edge:</strong> <span id="zd-edge"></span></div>
            <div><strong>Frontage Length:</strong> <span id="zd-frontage"></span></div>
            <div><strong>4W Car Slots:</strong> <span id="zd-4w" style="color: #38bdf8; font-weight: 600;"></span></div>
            <div><strong>2W Bike Slots:</strong> <span id="zd-2w" style="color: #facc15; font-weight: 600;"></span></div>
            <div><strong>SUMO Car Cap:</strong> <span id="zd-sumo"></span></div>
          </div>
          <div style="background: #1e293b; padding: 8px; border-radius: 4px; font-size: 0.75rem; border: 1px solid #334155;">
            <strong>Corridor Policy:</strong>
            <p id="zd-restrictions" style="color: #cbd5e1; margin-top: 2px;"></p>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Map Legend & Layers</h3>
        <div class="legend-item"><div class="legend-color" style="background: #ef4444;"></div> Calibrated Parking Zone Marker</div>
        <div class="legend-item"><div class="legend-color" style="background: #f59e0b;"></div> Parking Frontage Corridor Line</div>
        <div class="legend-item"><div class="legend-color" style="background: #0284c7;"></div> Opposing Corridor Bottleneck (Library/NAC)</div>
        <div class="legend-item"><div class="legend-color" style="background: #475569;"></div> Campus Road Network (SUMO XML)</div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([23.8155, 86.4415], 16);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors | IIT (ISM) Dhanbad Smart Parking'
    }).addTo(map);

    function selectZone(props) {
      document.getElementById('no-select-msg').style.display = 'none';
      const zd = document.getElementById('zone-details');
      zd.style.display = 'block';

      document.getElementById('zd-name').textContent = props.zone_name;
      document.getElementById('zd-id').textContent = props.zone_id;
      document.getElementById('zd-edge').textContent = props.mapped_edge_id || props.edge_id;
      document.getElementById('zd-frontage').textContent = (props.frontage_m || props.verified_frontage_m) + ' m';
      document.getElementById('zd-4w').textContent = props.four_wheeler_capacity || props.four_wheeler_slots;
      document.getElementById('zd-2w').textContent = props.two_wheeler_capacity || props.two_wheeler_slots;
      document.getElementById('zd-sumo').textContent = props.sumo_roadside_capacity || props.sumo_capacity;
      document.getElementById('zd-restrictions').textContent = props.restrictions || props.restriction_note || 'Standard Single-Side Parallel Parking.';

      const pill = document.getElementById('zd-pill');
      const status = props.operational_status || props.corridor_status || '';
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

    // Load Road Network
    fetch('road_network.geojson')
      .then(r => r.json())
      .then(data => {
        L.geoJSON(data, {
          style: function(f) {
            return {
              color: f.properties.is_parking_corridor ? '#38bdf8' : '#475569',
              weight: f.properties.is_parking_corridor ? 3 : 1.5,
              opacity: f.properties.is_parking_corridor ? 0.8 : 0.4
            };
          }
        }).addTo(map);
      })
      .catch(e => console.warn('Could not load road_network.geojson:', e));

    // Load Parking Frontage Lines
    fetch('parking_frontage.geojson')
      .then(r => r.json())
      .then(data => {
        L.geoJSON(data, {
          style: function(f) {
            const isCorridor = f.properties.zone_id.includes('library') || f.properties.zone_id.includes('nac');
            return {
              color: isCorridor ? '#0284c7' : '#f59e0b',
              weight: 5,
              opacity: 0.85
            };
          },
          onEachFeature: function(f, layer) {
            layer.on('click', () => selectZone(f.properties));
          }
        }).addTo(map);
      })
      .catch(e => console.warn('Could not load parking_frontage.geojson:', e));

    // Load Parking Zones Points
    fetch('parking_zones.geojson')
      .then(r => r.json())
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
            layer.bindTooltip(`<strong>${f.properties.zone_name}</strong><br>Cap: ${f.properties.total_calibrated_slots} slots (${f.properties.four_wheeler_capacity} 4W, ${f.properties.two_wheeler_capacity} 2W)`, { direction: 'top' });
            layer.on('click', () => selectZone(f.properties));
          }
        }).addTo(map);
      })
      .catch(e => console.warn('Could not load parking_zones.geojson:', e));
  </script>
</body>
</html>
"""
    with open(OUT_MAP_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Wrote interactive map page to {OUT_MAP_HTML}")


def main():
    print("=== Stage 1 Part 5: Geospatial Layer Generation ===")
    calib_dict = load_calib_data()
    generate_signage_mapping_csv(calib_dict)
    generate_geojson_layers()
    generate_interactive_map_html()
    print("=== Geospatial Layer Generation Complete ===")


if __name__ == "__main__":
    main()
