# Road Geometry Extraction Report
**Project**: Campus Smart Parking Management System — IIT (ISM) Dhanbad  
**Stage**: 1 — Part 1: Project Audit and Road Geometry Extraction  
**Generated**: 2026-10-13 00:17:53  
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
| Net offset | -441305.73,-2632026.27 |
| Conversion boundary (XY m) | 0.00,0.00,3886.93,3813.90 |
| Original boundary (lon/lat) | 86.423776,23.798453,86.461896,23.832881 |
| Projection | +proj=utm +zone=45 +ellps=WGS84 +datum=WGS84 +units=m +no_defs |
| Coordinate system | UTM Zone 45N (WGS84) |
| Total edges (all) | 8059 |
| Normal (non-internal) edges | 1773 |
| Internal junction connectors | 6286 |
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

**Key finding**: The seed file defines 14 zones with **10 slots each (= 140 total)** using a uniform fixed constant (`Array.from({ length: 10 }`). This is an arbitrary placeholder — not derived from road geometry.

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
| Normal (non-internal) edges | 1,773 |
| Total length (all normal edges) | **162,722.05 m** (162.7220 km) |
| Usable-for-parking edges | 1,739 |
| Total length (usable edges) | **156,751.13 m** (156.7511 km) |

*"Usable" excludes: `highway.trunk` roads (too fast for roadside parking) and edges with zero/missing length.*

### 3.2 Length by Road Type

| Road Type | Edge Count | Total Length (m) | Total Length (km) |
|-----------|-----------|-----------------|------------------|
| highway.primary | 37 | 6,134.01 | 6.1340 |
| highway.residential | 1426 | 119,839.14 | 119.8391 |
| highway.service | 114 | 9,836.48 | 9.8365 |
| highway.tertiary | 34 | 3,913.08 | 3.9131 |
| highway.trunk | 34 | 5,970.92 | 5.9709 |
| highway.unclassified | 128 | 17,028.42 | 17.0284 |

### 3.3 Internal Junction Connectors (Excluded from Totals)

| Metric | Value |
|--------|-------|
| Internal connector count | 6,286 |
| Total internal length | 54,153.48 m |

*(Internal connectors represent lane-change and turning movements inside junctions. They are present in `road_geometry.csv` with `is_internal=yes` for completeness.)*

---

## 4. Width and Data-Quality Status

| Category | Edge Count | Source |
|----------|-----------|--------|
| Verified (explicit width in net.xml) | 0 | campus.net.xml lane `width` attribute |
| Inferred (type-based default) | 1773 | Road type default (see table below) |
| Missing (unknown type, no default) | 0 | No source available |

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
| Mapped with high confidence | 14 |
| Mapped with medium confidence | 0 |
| Unresolved | 0 |
| **Total** | **14** |

### 5.2 Zone-by-Zone Mapping Detail

| Zone ID | Zone Name | Mapped Edge | Road Type | Edge Length (m) | Parking Range (m) | Parkable Length (m) | SUMO Capacity | Confidence |
|---------|-----------|-------------|-----------|----------------|-------------------|---------------------|--------------|------------|
| zone_main_gate | Main Gate Parking | -517026169#0 | highway.service | 90.9100 | 2.0–81.8 | 79.80 | 25 | high |
| zone_sac | SAC Parking | 991055730 | highway.residential | 101.1500 | 2.0–91.0 | 89.00 | 20 | high |
| zone_nlhc | NLHC Complex Parking | -517026168#2 | highway.residential | 103.0800 | 2.0–92.8 | 90.80 | 30 | high |
| zone_library | Central Library Parking | -991056586#2 | highway.service | 326.2100 | 2.0–293.6 | 291.60 | 25 | high |
| zone_nac | NAC Building Parking | 991056586#2 | highway.service | 330.7500 | 2.0–297.7 | 295.70 | 25 | high |
| zone_cse | CSE Department Parking | 1207647016#1 | highway.residential | 28.0100 | 2.0–25.2 | 23.20 | 15 | high |
| zone_health_centre | Health Centre Parking | 517026174 | highway.service | 73.5700 | 2.0–66.2 | 64.20 | 15 | high |
| zone_i2h | I2H Innovation Hub Parking | -991056586#1 | highway.service | 60.7100 | 2.0–54.6 | 52.60 | 20 | high |
| zone_academic_complex | Academic Complex Parking | -517026169#5 | highway.service | 132.8200 | 2.0–119.5 | 117.50 | 25 | high |
| zone_amber | Amber Hostel Parking | 1031061562#3 | highway.residential | 96.1100 | 2.0–86.5 | 84.50 | 20 | high |
| zone_aquamarine | Aquamarine Hostel Parking | 1029515471 | highway.residential | 37.3100 | 2.0–33.6 | 31.60 | 20 | high |
| zone_mechanical | Mechanical Dept Parking | -517026179#7 | highway.unclassified | 74.9700 | 2.0–67.5 | 65.50 | 15 | high |
| zone_enviro | Environmental Dept Parking | -517026179#5 | highway.unclassified | 124.8400 | 2.0–112.4 | 110.40 | 15 | high |
| zone_oat | OAT Grounds Parking | -1118600401 | highway.residential | 123.3000 | 2.0–111.0 | 109.00 | 20 | high |


> [!NOTE]
> `parkable_length_m` = `endPos − startPos` as declared in `campus_parking.add.xml`. This is the road segment reserved for parking in the simulation. It is **not** derived from road width or geometric parking-slot calculations — that is the task of Part 2.
>
> `roadSideCapacity_sumo` is the capacity declared in `campus_parking.add.xml`. It differs from the uniform 10-slots-per-zone in `seed.js`. Reconciling these two capacity sources is a task for subsequent parts.

---

## 6. Missing Data and Unresolved Questions

| Item | Status | Required for Part 2 |
|------|--------|---------------------|
| Explicit lane widths (net.xml `width` attr) | **Missing** — 0 of 1773 edges have explicit widths | Yes — needed for accurate parking-capacity calculation |
| OSM `width` tags | **Missing** — 0 of 463 OSM ways have width tags | Yes |
| OSM `lanes` tags | Partially present — 5 of 463 ways | Helpful |
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
