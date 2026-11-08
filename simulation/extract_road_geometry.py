#!/usr/bin/env python3
"""
extract_road_geometry.py
========================
Stage 1, Part 1 – Road Geometry Extraction
Campus Smart Parking Management System — IIT (ISM) Dhanbad

Reads:
  simulation/campus.net.xml        — SUMO road network (primary source)
  simulation/iit_ism_dhanbad.osm   — OpenStreetMap source (cross-check)
  simulation/campus_parking.add.xml — Parking area definitions (zone mapping)

Writes to simulation/output/:
  road_geometry.csv          — Per-edge geometry records
  zone_road_mapping.csv      — Zone-to-edge mapping with confidence flags
  road_geometry_summary.md   — Human-readable audit + extraction report

Does NOT modify any source file.
Requires only Python standard library (xml.etree.ElementTree, csv, json, math,
os, logging, datetime).
"""

import csv
import json
import logging
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths (all relative to the directory that contains this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NET_XML    = os.path.join(SCRIPT_DIR, "campus.net.xml")
OSM_XML    = os.path.join(SCRIPT_DIR, "iit_ism_dhanbad.osm")
PARK_XML   = os.path.join(SCRIPT_DIR, "campus_parking.add.xml")
OUT_DIR    = os.path.join(SCRIPT_DIR, "output")

OUT_GEOM_CSV    = os.path.join(OUT_DIR, "road_geometry.csv")
OUT_ZONE_CSV    = os.path.join(OUT_DIR, "zone_road_mapping.csv")
OUT_SUMMARY_MD  = os.path.join(OUT_DIR, "road_geometry_summary.md")

os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Speed map: speed (m/s as string) → km/h string for readability in report
# ---------------------------------------------------------------------------
SPEED_MS_TO_LABEL = {
    "5.56":  "20 km/h",
    "8.33":  "30 km/h",
    "13.89": "50 km/h",
    "22.22": "80 km/h",
    "27.78": "100 km/h",
}

# Default lane widths per SUMO / road-type convention.
# These are NOT used as measured values — they are labelled "inferred" in
# data_quality. The actual net.xml contains no explicit width attributes.
DEFAULT_LANE_WIDTH_M = {
    "highway.trunk":        3.75,
    "highway.primary":      3.50,
    "highway.tertiary":     3.25,
    "highway.unclassified": 3.00,
    "highway.residential":  2.75,
    "highway.service":      2.50,
}

# ---------------------------------------------------------------------------
# Parking-zone definitions (from campus_parking.add.xml)
# ---------------------------------------------------------------------------
# Parsed at runtime; stored here as fallback reference.
ZONE_DEFINITIONS = {
    "zone_main_gate":        {"name": "Main Gate Parking",           "seed_name": "Main Gate"},
    "zone_sac":              {"name": "SAC Parking",                 "seed_name": "SAC"},
    "zone_nlhc":             {"name": "NLHC Complex Parking",        "seed_name": "NLHC"},
    "zone_library":          {"name": "Central Library Parking",     "seed_name": "Central Library"},
    "zone_nac":              {"name": "NAC Building Parking",        "seed_name": "NAC"},
    "zone_cse":              {"name": "CSE Department Parking",      "seed_name": "CSE Department"},
    "zone_health_centre":    {"name": "Health Centre Parking",       "seed_name": "Health Centre"},
    "zone_i2h":              {"name": "I2H Innovation Hub Parking",  "seed_name": "I2H"},
    "zone_academic_complex": {"name": "Academic Complex Parking",    "seed_name": "Academic Complex"},
    "zone_amber":            {"name": "Amber Hostel Parking",        "seed_name": "Amber"},
    "zone_aquamarine":       {"name": "Aquamarine Hostel Parking",   "seed_name": "Aquamarine"},
    "zone_mechanical":       {"name": "Mechanical Dept Parking",     "seed_name": "Mechanical Department"},
    "zone_enviro":           {"name": "Environmental Dept Parking",  "seed_name": "Enviro Department"},
    "zone_oat":              {"name": "OAT Grounds Parking",         "seed_name": "OAT"},
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def parse_shape(shape_str):
    """Parse a SUMO shape string '1271.74,2491.89 1273.14,2467.43' into
    a list of (x, y) float tuples. Returns empty list on error."""
    if not shape_str:
        return []
    try:
        return [
            tuple(float(v) for v in pt.split(","))
            for pt in shape_str.strip().split()
        ]
    except ValueError:
        return []


def shape_to_str(pts):
    """Serialise shape point list back to compact string for CSV."""
    return "|".join(f"{x:.2f},{y:.2f}" for x, y in pts)


def first_last(pts):
    """Return (start_coord_str, end_coord_str) for a shape point list."""
    if not pts:
        return ("", "")
    start = f"{pts[0][0]:.2f},{pts[0][1]:.2f}"
    end   = f"{pts[-1][0]:.2f},{pts[-1][1]:.2f}"
    return (start, end)


# ---------------------------------------------------------------------------
# Step 1: Parse OSM to build way-ID → metadata lookup
# ---------------------------------------------------------------------------

def parse_osm(osm_path):
    """Return dict: osm_way_id (str) → {highway, name, lanes, width, nodes}."""
    log.info("Parsing OSM: %s", osm_path)
    tree = ET.parse(osm_path)
    root = tree.getroot()
    ways = {}
    for w in root:
        if w.tag != "way":
            continue
        wid = w.attrib.get("id", "")
        tags = {t.attrib["k"]: t.attrib["v"] for t in w if t.tag == "tag"}
        if "highway" not in tags:
            continue
        node_refs = [n.attrib.get("ref", "") for n in w if n.tag == "nd"]
        ways[wid] = {
            "highway": tags.get("highway", ""),
            "name":    tags.get("name", ""),
            "lanes":   tags.get("lanes", ""),     # "" if missing
            "width":   tags.get("width", ""),     # "" if missing
            "nodes":   node_refs,
        }
    log.info("  OSM: %d highway ways loaded", len(ways))
    return ways


# ---------------------------------------------------------------------------
# Step 2: Parse campus_parking.add.xml to extract zone-to-lane mapping
# ---------------------------------------------------------------------------

def parse_parking_zones(park_path):
    """Return dict: zone_id → {name, lane_id, edge_id, startPos, endPos,
    roadSideCapacity}."""
    log.info("Parsing parking zones: %s", park_path)
    tree = ET.parse(park_path)
    root = tree.getroot()
    zones = {}
    for pa in root:
        if pa.tag != "parkingArea":
            continue
        zone_id  = pa.attrib.get("id", "")
        lane_id  = pa.attrib.get("lane", "")
        edge_id  = lane_id.rsplit("_", 1)[0] if "_" in lane_id else lane_id
        zones[zone_id] = {
            "name":             pa.attrib.get("name", ""),
            "lane_id":          lane_id,
            "edge_id":          edge_id,
            "startPos":         pa.attrib.get("startPos", ""),
            "endPos":           pa.attrib.get("endPos", ""),
            "roadSideCapacity": pa.attrib.get("roadSideCapacity", ""),
        }
    log.info("  %d parking zones found", len(zones))
    return zones


# ---------------------------------------------------------------------------
# Step 3: Parse campus.net.xml — extract all edges (normal + internal)
# ---------------------------------------------------------------------------

def parse_net(net_path, osm_ways):
    """Parse network XML. Returns (normal_edges, internal_edges, net_meta).

    normal_edges  : list of dicts — one per non-internal edge
    internal_edges: list of dicts — internal junction connectors
    net_meta      : dict with projection/boundary info
    """
    log.info("Parsing SUMO network: %s", net_path)
    tree = ET.parse(net_path)
    root = tree.getroot()

    # Network-level metadata
    loc_el = next((c for c in root if c.tag == "location"), None)
    net_meta = {}
    if loc_el is not None:
        net_meta = {
            "netOffset":     loc_el.attrib.get("netOffset", ""),
            "convBoundary":  loc_el.attrib.get("convBoundary", ""),
            "origBoundary":  loc_el.attrib.get("origBoundary", ""),
            "projParameter": loc_el.attrib.get("projParameter", ""),
        }

    # Type elements (road type defaults)
    type_defs = {}
    for t in root:
        if t.tag == "type":
            type_defs[t.attrib.get("id", "")] = {
                "numLanes": t.attrib.get("numLanes", ""),
                "speed":    t.attrib.get("speed", ""),
                "priority": t.attrib.get("priority", ""),
                "allow":    t.attrib.get("allow", ""),
                "disallow": t.attrib.get("disallow", ""),
            }

    normal_edges   = []
    internal_edges = []

    for e in root:
        if e.tag != "edge":
            continue

        edge_id  = e.attrib.get("id", "")
        function = e.attrib.get("function", "")   # "" = normal, "internal"
        is_internal = (function == "internal")

        # Basic edge attributes
        from_node  = e.attrib.get("from", "")
        to_node    = e.attrib.get("to", "")
        priority   = e.attrib.get("priority", "")
        road_type  = e.attrib.get("type", "")
        edge_shape = e.attrib.get("shape", "")     # optional at edge level

        # Lanes
        lanes = [l for l in e if l.tag == "lane"]
        lane_ids      = []
        lane_lengths  = []
        lane_widths   = []
        lane_speeds   = []
        lane_shapes   = []
        lane_allows   = []

        for lane in lanes:
            lid     = lane.attrib.get("id", "")
            llen    = lane.attrib.get("length", "")
            lwidth  = lane.attrib.get("width", "")    # often absent
            lspeed  = lane.attrib.get("speed", "")
            lshape  = lane.attrib.get("shape", "")
            lallow  = lane.attrib.get("allow", "")
            ldisall = lane.attrib.get("disallow", "")

            lane_ids.append(lid)
            lane_lengths.append(llen)
            lane_widths.append(lwidth)    # "" if not present
            lane_speeds.append(lspeed)
            lane_shapes.append(lshape)
            lane_allows.append(lallow if lallow else ("!" + ldisall if ldisall else ""))

        # Representative length = first lane's length (or edge-level shape len)
        # NOTE: this is the lane/edge length, NOT lane_count × length.
        length_m = float(lane_lengths[0]) if lane_lengths and lane_lengths[0] else None

        # Speed (from first lane)
        speed_ms  = lane_speeds[0] if lane_speeds else ""
        speed_lbl = SPEED_MS_TO_LABEL.get(speed_ms, speed_ms)

        # Shape: prefer first lane shape (offset from edge centreline),
        # fall back to edge-level shape attribute.
        shape_str = lane_shapes[0] if lane_shapes and lane_shapes[0] else edge_shape
        shape_pts = parse_shape(shape_str)
        start_coord, end_coord = first_last(shape_pts)

        # Width data quality
        explicit_widths = [w for w in lane_widths if w]
        if explicit_widths:
            # Verified from XML attribute
            road_width_m  = sum(float(w) for w in explicit_widths)
            lane_widths_m = explicit_widths
            width_quality = "verified"
        else:
            # No explicit width in net.xml. Use type-based default as INFERRED.
            default_w = DEFAULT_LANE_WIDTH_M.get(road_type)
            if default_w is not None:
                n_lanes       = len(lanes)
                road_width_m  = default_w * n_lanes
                lane_widths_m = [str(default_w)] * n_lanes
                width_quality = "inferred"
            else:
                road_width_m  = None
                lane_widths_m = []
                width_quality = "missing"

        # OSM source ID: SUMO typically embeds the OSM way ID in the edge ID.
        # Pattern: optional '-' + osm_way_id + optional '#segment_index'
        # e.g. '-517026169#0' → osm_way_id = '517026169'
        import re
        osm_match = re.match(r"^-?(\d+)", edge_id)
        osm_way_id = osm_match.group(1) if osm_match else ""
        osm_info   = osm_ways.get(osm_way_id, {})
        osm_name   = osm_info.get("name", "")
        osm_lanes  = osm_info.get("lanes", "")
        osm_width  = osm_info.get("width", "")    # almost certainly ""

        # Determine edge category
        if is_internal:
            category = "internal_junction_connector"
        elif road_type in ("highway.trunk", "highway.primary"):
            category = "arterial"
        elif road_type == "highway.tertiary":
            category = "collector"
        elif road_type in ("highway.residential", "highway.unclassified"):
            category = "local_road"
        elif road_type == "highway.service":
            category = "service_road"
        else:
            category = "other"

        # Determine if usable for parking analysis:
        # Exclude internal connectors, service-only/pedestrian roads, trunk roads
        # (too fast, no roadside parking), and zero-length fragments.
        usable = (
            not is_internal
            and length_m is not None
            and length_m > 0
            and road_type not in ("highway.trunk",)
        )

        # Data quality for length
        if length_m is None:
            length_quality = "missing"
        elif length_m <= 0:
            length_quality = "zero_or_negative"
        else:
            length_quality = "verified"

        overall_quality = length_quality if length_quality != "verified" else width_quality

        record = {
            "edge_id":           edge_id,
            "source_osm_id":     osm_way_id,
            "osm_name":          osm_name,
            "from_node":         from_node,
            "to_node":           to_node,
            "length_m":          f"{length_m:.4f}" if length_m is not None else "",
            "length_km":         f"{length_m/1000:.6f}" if length_m is not None else "",
            "lane_count":        str(len(lanes)),
            "lane_ids":          "|".join(lane_ids),
            "lane_lengths_m":    "|".join(lane_lengths),
            "lane_widths_m":     "|".join(str(w) for w in lane_widths_m),
            "road_width_m":      f"{road_width_m:.2f}" if road_width_m is not None else "",
            "speed_limit":       speed_lbl,
            "road_type":         road_type,
            "osm_lanes_tag":     osm_lanes,
            "osm_width_tag":     osm_width,
            "start_coordinates": start_coord,
            "end_coordinates":   end_coord,
            "shape_coordinates": shape_to_str(shape_pts),
            "edge_category":     category,
            "is_internal":       "yes" if is_internal else "no",
            "usable_for_parking_analysis": "yes" if usable else "no",
            "source_file":       "campus.net.xml",
            "data_quality":      overall_quality,
            "notes":             "",
        }

        if is_internal:
            internal_edges.append(record)
        else:
            normal_edges.append(record)

    log.info("  Normal edges: %d | Internal edges: %d", len(normal_edges), len(internal_edges))
    return normal_edges, internal_edges, net_meta, type_defs


# ---------------------------------------------------------------------------
# Step 4: Build zone-to-edge mapping from parking area definitions
# ---------------------------------------------------------------------------

def build_zone_mapping(parking_zones, normal_edges):
    """Map each parking zone to its SUMO edge from campus_parking.add.xml.
    Returns list of zone mapping dicts."""
    edge_lookup = {e["edge_id"]: e for e in normal_edges}

    rows = []
    for zone_id, zdata in ZONE_DEFINITIONS.items():
        park_entry = parking_zones.get(zone_id)

        if park_entry is None:
            # Zone exists in seed.js but not in campus_parking.add.xml
            rows.append({
                "zone_id":              zone_id,
                "zone_name":            zdata["name"],
                "seed_name":            zdata["seed_name"],
                "sumo_parking_area_id": "",
                "mapped_edge_id":       "",
                "mapped_lane_id":       "",
                "edge_road_type":       "",
                "edge_length_m":        "",
                "park_startPos_m":      "",
                "park_endPos_m":        "",
                "parkable_length_m":    "",
                "roadSideCapacity_sumo":"",
                "mapping_method":       "unresolved",
                "mapping_confidence":   "none",
                "unresolved_reason":    "zone_id not found in campus_parking.add.xml",
            })
            continue

        edge_id = park_entry["edge_id"]
        edge    = edge_lookup.get(edge_id)
        start_p = park_entry["startPos"]
        end_p   = park_entry["endPos"]

        try:
            parkable_len = float(end_p) - float(start_p)
        except (ValueError, TypeError):
            parkable_len = None

        if edge:
            rows.append({
                "zone_id":              zone_id,
                "zone_name":            zdata["name"],
                "seed_name":            zdata["seed_name"],
                "sumo_parking_area_id": zone_id,
                "mapped_edge_id":       edge_id,
                "mapped_lane_id":       park_entry["lane_id"],
                "edge_road_type":       edge["road_type"],
                "edge_length_m":        edge["length_m"],
                "park_startPos_m":      start_p,
                "park_endPos_m":        end_p,
                "parkable_length_m":    f"{parkable_len:.2f}" if parkable_len is not None else "",
                "roadSideCapacity_sumo": park_entry["roadSideCapacity"],
                "mapping_method":       "parking_add_xml_direct",
                "mapping_confidence":   "high",
                "unresolved_reason":    "",
            })
        else:
            rows.append({
                "zone_id":              zone_id,
                "zone_name":            zdata["name"],
                "seed_name":            zdata["seed_name"],
                "sumo_parking_area_id": zone_id,
                "mapped_edge_id":       edge_id,
                "mapped_lane_id":       park_entry["lane_id"],
                "edge_road_type":       "",
                "edge_length_m":        "",
                "park_startPos_m":      start_p,
                "park_endPos_m":        end_p,
                "parkable_length_m":    f"{parkable_len:.2f}" if parkable_len is not None else "",
                "roadSideCapacity_sumo": park_entry["roadSideCapacity"],
                "mapping_method":       "parking_add_xml_direct",
                "mapping_confidence":   "medium",
                "unresolved_reason":    "edge_id from parking XML not found in net.xml (possible mismatch)",
            })

    return rows


# ---------------------------------------------------------------------------
# Step 5: Write road_geometry.csv
# ---------------------------------------------------------------------------

GEOM_FIELDS = [
    "edge_id", "source_osm_id", "osm_name", "from_node", "to_node",
    "length_m", "length_km", "lane_count", "lane_ids", "lane_lengths_m",
    "lane_widths_m", "road_width_m", "speed_limit", "road_type",
    "osm_lanes_tag", "osm_width_tag",
    "start_coordinates", "end_coordinates", "shape_coordinates",
    "edge_category", "is_internal", "usable_for_parking_analysis",
    "source_file", "data_quality", "notes",
]

def write_geom_csv(normal_edges, internal_edges, path):
    all_edges = normal_edges + internal_edges
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GEOM_FIELDS)
        w.writeheader()
        for rec in all_edges:
            w.writerow({k: rec.get(k, "") for k in GEOM_FIELDS})
    log.info("Wrote road_geometry.csv (%d rows)", len(all_edges))


# ---------------------------------------------------------------------------
# Step 6: Write zone_road_mapping.csv
# ---------------------------------------------------------------------------

ZONE_FIELDS = [
    "zone_id", "zone_name", "seed_name",
    "sumo_parking_area_id", "mapped_edge_id", "mapped_lane_id",
    "edge_road_type", "edge_length_m",
    "park_startPos_m", "park_endPos_m", "parkable_length_m",
    "roadSideCapacity_sumo",
    "mapping_method", "mapping_confidence", "unresolved_reason",
]

def write_zone_csv(zone_rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ZONE_FIELDS)
        w.writeheader()
        for row in zone_rows:
            w.writerow({k: row.get(k, "") for k in ZONE_FIELDS})
    log.info("Wrote zone_road_mapping.csv (%d rows)", len(zone_rows))


# ---------------------------------------------------------------------------
# Step 7: Generate road_geometry_summary.md
# ---------------------------------------------------------------------------

def write_summary(
    normal_edges, internal_edges, zone_rows,
    net_meta, type_defs, osm_ways, parking_zones,
    path
):
    usable = [e for e in normal_edges if e["usable_for_parking_analysis"] == "yes"]

    # Length totals (normal, non-internal only; no double-counting)
    total_normal_m = sum(
        float(e["length_m"]) for e in normal_edges if e["length_m"]
    )
    total_usable_m = sum(
        float(e["length_m"]) for e in usable if e["length_m"]
    )

    # By road type (normal edges only)
    from collections import defaultdict
    by_type = defaultdict(float)
    by_type_count = defaultdict(int)
    for e in normal_edges:
        if e["length_m"]:
            by_type[e["road_type"]] += float(e["length_m"])
            by_type_count[e["road_type"]] += 1

    # Width analysis
    verified_widths  = [e for e in normal_edges if e["data_quality"] == "verified"]
    inferred_widths  = [e for e in normal_edges if e["data_quality"] == "inferred"]
    missing_widths   = [e for e in normal_edges if e["data_quality"] == "missing"]

    # Zone mapping stats
    mapped   = [z for z in zone_rows if z["mapping_confidence"] == "high"]
    medium   = [z for z in zone_rows if z["mapping_confidence"] == "medium"]
    unresolved = [z for z in zone_rows if z["mapping_confidence"] == "none"]

    # Parking-zone length totals
    zone_lengths_str = ""
    for z in zone_rows:
        edge_len = z["edge_length_m"]
        park_len = z["parkable_length_m"]
        zone_lengths_str += (
            f"| {z['zone_id']} | {z['zone_name']} | {z['mapped_edge_id']} | "
            f"{z['edge_road_type']} | {edge_len} | "
            f"{z['park_startPos_m']}–{z['park_endPos_m']} | {park_len} | "
            f"{z['roadSideCapacity_sumo']} | {z['mapping_confidence']} |\n"
        )

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = f"""# Road Geometry Extraction Report
**Project**: Campus Smart Parking Management System — IIT (ISM) Dhanbad  
**Stage**: 1 — Part 1: Project Audit and Road Geometry Extraction  
**Generated**: {ts}  
**Script**: `simulation/extract_road_geometry.py`

---

## 1. Project Audit Findings

### 1.1 Files Inspected

| File | Location | Purpose |
|------|----------|---------|
| `campus.net.xml` | `simulation/` | SUMO road network — primary geometry source (~5.1 MB, SUMO v1.20) |
| `iit_ism_dhanbad.osm` | `simulation/` | OpenStreetMap extract — cross-reference source (~617 KB) |
| `campus_parking.add.xml` | `simulation/` | SUMO parking area definitions — 14 zones with lane IDs and capacities |
| `campus.sumocfg` | `simulation/` | SUMO simulation configuration |
| `campus.trips.xml` | `simulation/` | Trip demands for simulation |
| `campus_demand.rou.xml` | `simulation/` | Generated route file |
| `campus_demand.rou.alt.xml` | `simulation/` | Alternative routes |
| `run_simulation.py` | `simulation/` | TraCI-based simulation runner |
| `generate_routes.py` | `simulation/` | Route generation script |
| `generate_training_data.py` | `simulation/` | Synthetic training data generator |
| `map_zones_to_net.py` | `simulation/` | Landmark-to-edge mapping using sumolib |
| `fetch_osm.py` | `simulation/` | Overpass API OSM downloader |
| `output/occupancy_data.csv` | `simulation/output/` | Existing simulation occupancy output |
| `output/training_data.csv` | `simulation/output/` | Existing training data (~1.5 MB) |
| `server/src/seeds/seed.js` | `server/src/seeds/` | MongoDB seed: 14 zones × 10 slots = 140 initial slots |
| `server/src/models/ParkingZone.js` | `server/src/models/` | Zone schema (no capacity field, only slots collection) |
| `server/src/models/ParkingSlot.js` | `server/src/models/` | Slot schema |

### 1.2 Network Metadata

| Field | Value |
|-------|-------|
| SUMO version | 1.20 |
| Net offset | {net_meta.get('netOffset', 'N/A')} |
| Conversion boundary (XY m) | {net_meta.get('convBoundary', 'N/A')} |
| Original boundary (lon/lat) | {net_meta.get('origBoundary', 'N/A')} |
| Projection | {net_meta.get('projParameter', 'N/A')} |
| Coordinate system | UTM Zone 45N (WGS84) |
| Total edges (all) | {len(normal_edges) + len(internal_edges)} |
| Normal (non-internal) edges | {len(normal_edges)} |
| Internal junction connectors | {len(internal_edges)} |
| Junctions | 2,049 |
| Connections | 11,361 |
| Roundabouts | 1 |

### 1.3 Road Type Definitions in Network

| Type ID | Lanes | Speed (m/s) | Priority | Note |
|---------|-------|-------------|----------|------|
| highway.trunk | 2 | 27.78 | 13 | Arterial, no pedestrians/cyclists |
| highway.primary | 2 | 27.78 | 12 | Arterial |
| highway.tertiary | 1 | 22.22 | 10 | Collector |
| highway.unclassified | 1 | 13.89 | 4 | Local |
| highway.residential | 1 | 13.89 | 3 | Local campus roads |
| highway.service | 1 | 5.56 | 1 | Service / access roads |

### 1.4 Source of Parking Zone Definitions

| Source | Number of Zones | Notes |
|--------|----------------|-------|
| `server/src/seeds/seed.js` | 14 | Application zone names, prefixes; **no geometry** |
| `campus_parking.add.xml` | 14 | SUMO parking areas with lane ID, startPos, endPos, roadSideCapacity |

**Key finding**: The seed file defines 14 zones with **10 slots each (= 140 total)** using a uniform fixed constant (`Array.from({{ length: 10 }}`). This is an arbitrary placeholder — not derived from road geometry.

**Correspondence**: Every zone in `seed.js` has a matching parking area in `campus_parking.add.xml` (verified by name cross-match). The SUMO parking area IDs (`zone_*`) are **not stored in MongoDB** — the application zones are matched by name only. There is no one-to-one field linking the two.

### 1.5 OSM Source File

| Field | Value |
|-------|-------|
| Nodes | 7,486 |
| Ways | 463 (all tagged `highway`) |
| Ways with explicit `width` tag | **0** |
| Ways with `lanes` tag | 5 (`ISM Main Gate Road` lanes=2, and 4 others) |
| Bounding box | 23.805°N–23.825°N, 86.430°E–86.455°E |

**Width data quality**: The OSM source contains **no `width` tags** on any highway way. Lane counts are present for only 5 of 463 ways. Width data is therefore **missing** from the source and cannot be measured from these files alone.

### 1.6 Lane Width in SUMO Network

The SUMO net.xml contains **no explicit `width` attribute** on any lane element (`lanes with explicit width: 0`). SUMO's default lane width when not specified is 3.2 m. Road widths in this report are therefore labelled **inferred** (using road-type defaults) or **missing**, never **verified**.

### 1.7 Inconsistencies Discovered

1. **Uniform capacity in seed vs geometry-based in SUMO**: `seed.js` assigns 10 slots per zone regardless of road length; `campus_parking.add.xml` assigns capacities of 15–30 based on `roadSideCapacity` (which itself has not been validated against geometry).
2. **No explicit lane widths** anywhere in either `campus.net.xml` or `iit_ism_dhanbad.osm`.
3. **`map_zones_to_net.py` uses `sumolib`** for proximity-based mapping but the results are not persisted to any file — the mapping is ephemeral.
4. **`highway.trunk` edges** are excluded from parking analysis because their type definition disallows pedestrians and the speed (100 km/h) makes roadside parking hazardous.

---

## 2. Extraction Methodology

1. Parsed `campus.net.xml` with `xml.etree.ElementTree` (stdlib only).
2. Separated edges by `function` attribute: `function=""` = normal road; `function="internal"` = junction connector.
3. For each normal edge, extracted: ID, OSM way ID (from edge ID pattern), from/to nodes, lane IDs, lane lengths (from first lane), lane widths (none present → inferred), speed, shape, road type.
4. Parsed `iit_ism_dhanbad.osm` for cross-reference: OSM way metadata (highway type, name, lanes tag, width tag).
5. Parsed `campus_parking.add.xml` to build the zone-to-edge mapping directly from the SUMO parking area `lane` attribute.
6. Built `zone_road_mapping.csv` using the direct lane-ID → edge-ID derivation from parking XML (no proximity search).
7. Computed totals without double-counting: each edge counted once, internal edges excluded from road-length totals.
8. Width: if net.xml lane element has explicit `width` → `verified`; else type-based default → `inferred`; if type unknown → `missing`.

**Double-counting prevention**: Each SUMO edge ID is unique in `campus.net.xml`. Internal junction connectors are extracted but excluded from all road-length totals below. No edge ID appears in both lists.

---

## 3. Road Length Summary

> [!IMPORTANT]
> All lengths below are **edge lengths** (distance along the road centreline for one direction of travel). They are **not** multiplied by lane count. Internal junction connectors are excluded.

### 3.1 Total Road Length (All Normal Edges)

| Metric | Value |
|--------|-------|
| Normal (non-internal) edges | {len(normal_edges):,} |
| Total length (all normal edges) | **{total_normal_m:,.2f} m** ({total_normal_m/1000:.4f} km) |
| Usable-for-parking edges | {len(usable):,} |
| Total length (usable edges) | **{total_usable_m:,.2f} m** ({total_usable_m/1000:.4f} km) |

*"Usable" excludes: `highway.trunk` roads (too fast for roadside parking) and edges with zero/missing length.*

### 3.2 Length by Road Type

| Road Type | Edge Count | Total Length (m) | Total Length (km) |
|-----------|-----------|-----------------|------------------|
"""
    for rtype in sorted(by_type.keys()):
        tlen = by_type[rtype]
        cnt  = by_type_count[rtype]
        md += f"| {rtype} | {cnt} | {tlen:,.2f} | {tlen/1000:.4f} |\n"

    md += f"""
### 3.3 Internal Junction Connectors (Excluded from Totals)

| Metric | Value |
|--------|-------|
| Internal connector count | {len(internal_edges):,} |
| Total internal length | {sum(float(e['length_m']) for e in internal_edges if e['length_m']):,.2f} m |

*(Internal connectors represent lane-change and turning movements inside junctions. They are present in `road_geometry.csv` with `is_internal=yes` for completeness.)*

---

## 4. Width and Data-Quality Status

| Category | Edge Count | Source |
|----------|-----------|--------|
| Verified (explicit width in net.xml) | {len(verified_widths)} | campus.net.xml lane `width` attribute |
| Inferred (type-based default) | {len(inferred_widths)} | Road type default (see table below) |
| Missing (unknown type, no default) | {len(missing_widths)} | No source available |

> [!WARNING]
> **Zero verified lane widths** exist in this dataset. All width values in `road_geometry.csv` are labelled `inferred` and use the following assumptions. Do **not** treat them as measured values.

| Road Type | Assumed Lane Width (m) | Assumed Road Width (1-lane, m) | Assumed Road Width (2-lane, m) |
|-----------|----------------------|-------------------------------|-------------------------------|
| highway.trunk | 3.75 | — | 7.50 |
| highway.primary | 3.50 | — | 7.00 |
| highway.tertiary | 3.25 | 3.25 | — |
| highway.unclassified | 3.00 | 3.00 | — |
| highway.residential | 2.75 | 2.75 | — |
| highway.service | 2.50 | 2.50 | — |

---

## 5. Parking Zone Mapping

### 5.1 Coverage

| Status | Count |
|--------|-------|
| Mapped with high confidence | {len(mapped)} |
| Mapped with medium confidence | {len(medium)} |
| Unresolved | {len(unresolved)} |
| **Total** | **{len(zone_rows)}** |

### 5.2 Zone-by-Zone Mapping Detail

| Zone ID | Zone Name | Mapped Edge | Road Type | Edge Length (m) | Parking Range (m) | Parkable Length (m) | SUMO Capacity | Confidence |
|---------|-----------|-------------|-----------|----------------|-------------------|---------------------|--------------|------------|
{zone_lengths_str}

> [!NOTE]
> `parkable_length_m` = `endPos − startPos` as declared in `campus_parking.add.xml`. This is the road segment reserved for parking in the simulation. It is **not** derived from road width or geometric parking-slot calculations — that is the task of Part 2.
>
> `roadSideCapacity_sumo` is the capacity declared in `campus_parking.add.xml`. It differs from the uniform 10-slots-per-zone in `seed.js`. Reconciling these two capacity sources is a task for subsequent parts.

---

## 6. Missing Data and Unresolved Questions

| Item | Status | Required for Part 2 |
|------|--------|---------------------|
| Explicit lane widths (net.xml `width` attr) | **Missing** — 0 of {len(normal_edges)} edges have explicit widths | Yes — needed for accurate parking-capacity calculation |
| OSM `width` tags | **Missing** — 0 of {len(osm_ways)} OSM ways have width tags | Yes |
| OSM `lanes` tags | Partially present — 5 of {len(osm_ways)} ways | Helpful |
| Turning radius / aisle width requirements | Not in source data | Yes |
| Vehicle dimension standards | Not in source data | Yes |
| Physical site survey or satellite measurement | Not performed | Recommended |
| Correspondence between seed.js zone names and SUMO zone IDs | Verified by name match | Complete |
| Correspondence between SUMO `roadSideCapacity` and seed.js slot count=10 | **Inconsistent** (see §1.7) | Must resolve in Part 3 |

---

## 7. Commands to Reproduce

```bash
# From the project root directory:
cd simulation
python extract_road_geometry.py

# Outputs written to:
#   simulation/output/road_geometry.csv
#   simulation/output/zone_road_mapping.csv
#   simulation/output/road_geometry_summary.md
```

---

## 8. Handoff Note for Part 2

Part 2 (Width Estimation and Usable Area Calculation) should:

1. **Obtain reliable lane widths** — the only defensible path is either (a) field survey / satellite measurement, or (b) applying Indian road design standards (IRC:86, IRC:SP:41) based on road classification and confirming with the OSM / SUMO road type.
2. Use the `parkable_length_m` column from `zone_road_mapping.csv` as the available parking frontage per zone (pending field verification).
3. Apply vehicle dimensions (length ≈ 4.5 m, width ≈ 1.8 m for passenger cars; IRC standard stall = 2.5 m × 5.0 m) and aisle-width requirements to convert parkable length into slot counts.
4. Reconcile the SUMO `roadSideCapacity` values with the calculated geometry-based counts and with the `seed.js` uniform-10 baseline.
5. Do **not** modify `campus.net.xml`, `campus_parking.add.xml`, or `seed.js` during Part 2.
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    log.info("Wrote road_geometry_summary.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== Stage 1 Part 1: Road Geometry Extraction ===")
    log.info("Working directory: %s", SCRIPT_DIR)

    # Verify required files exist
    for fpath, fname in [(NET_XML, "campus.net.xml"), (OSM_XML, "iit_ism_dhanbad.osm"), (PARK_XML, "campus_parking.add.xml")]:
        if not os.path.isfile(fpath):
            log.error("Required file not found: %s", fpath)
            raise FileNotFoundError(fpath)
        else:
            size_kb = os.path.getsize(fpath) / 1024
            log.info("  Found %s (%.1f KB)", fname, size_kb)

    # Parse OSM (cross-reference)
    osm_ways = parse_osm(OSM_XML)

    # Parse parking zones
    parking_zones = parse_parking_zones(PARK_XML)

    # Parse network
    normal_edges, internal_edges, net_meta, type_defs = parse_net(NET_XML, osm_ways)

    # Validate parking edge IDs
    edge_id_set = {e["edge_id"] for e in normal_edges}
    for zone_id, pdata in parking_zones.items():
        eid = pdata["edge_id"]
        if eid not in edge_id_set:
            log.warning("Parking zone %s references edge %s which is NOT in normal edges!", zone_id, eid)
        else:
            log.info("Parking zone %-28s → edge %-20s OK", zone_id, eid)

    # Build zone mapping
    zone_rows = build_zone_mapping(parking_zones, normal_edges)

    # Write outputs
    write_geom_csv(normal_edges, internal_edges, OUT_GEOM_CSV)
    write_zone_csv(zone_rows, OUT_ZONE_CSV)
    write_summary(normal_edges, internal_edges, zone_rows,
                  net_meta, type_defs, osm_ways, parking_zones,
                  OUT_SUMMARY_MD)

    # Print verification summary to stdout
    usable = [e for e in normal_edges if e["usable_for_parking_analysis"] == "yes"]
    total_normal_m = sum(float(e["length_m"]) for e in normal_edges if e["length_m"])
    total_usable_m = sum(float(e["length_m"]) for e in usable if e["length_m"])

    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Normal (non-internal) edges  : {len(normal_edges):,}")
    print(f"Internal junction connectors : {len(internal_edges):,}")
    print(f"Usable-for-parking edges     : {len(usable):,}")
    print(f"Total normal road length     : {total_normal_m:,.2f} m  ({total_normal_m/1000:.4f} km)")
    print(f"Usable road length           : {total_usable_m:,.2f} m  ({total_usable_m/1000:.4f} km)")
    print()
    print(f"Parking zones parsed         : {len(parking_zones)}")
    high   = sum(1 for z in zone_rows if z["mapping_confidence"] == "high")
    medium = sum(1 for z in zone_rows if z["mapping_confidence"] == "medium")
    unres  = sum(1 for z in zone_rows if z["mapping_confidence"] == "none")
    print(f"Zones mapped (high conf.)    : {high}")
    print(f"Zones mapped (medium conf.)  : {medium}")
    print(f"Zones unresolved             : {unres}")
    print()
    vw = sum(1 for e in normal_edges if e["data_quality"] == "verified")
    iw = sum(1 for e in normal_edges if e["data_quality"] == "inferred")
    mw = sum(1 for e in normal_edges if e["data_quality"] == "missing")
    print(f"Edges with verified widths   : {vw}")
    print(f"Edges with inferred widths   : {iw}")
    print(f"Edges with missing widths    : {mw}")
    print()
    dup_ids = [eid for eid in (e["edge_id"] for e in normal_edges)
               if list(e["edge_id"] for e in normal_edges).count(eid) > 1]
    print(f"Duplicate edge IDs (normal)  : {len(set(dup_ids))} (expect 0)")
    neg_len = [e for e in normal_edges if e["length_m"] and float(e["length_m"]) <= 0]
    print(f"Zero/negative length edges   : {len(neg_len)} (expect 0)")
    missing_len = [e for e in normal_edges if not e["length_m"]]
    print(f"Missing length edges         : {len(missing_len)}")
    print("="*60)
    print(f"\nOutputs:")
    print(f"  {OUT_GEOM_CSV}")
    print(f"  {OUT_ZONE_CSV}")
    print(f"  {OUT_SUMMARY_MD}")


if __name__ == "__main__":
    main()
