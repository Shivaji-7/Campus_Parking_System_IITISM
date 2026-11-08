# Road Width, Usable Parking Space and Geometric Capacity Analysis Report
**Project**: Campus Smart Parking Management System — IIT (ISM) Dhanbad  
**Stage**: 1 — Part 2: Road Width, Usable Space and Geometric Capacity  
**Generated**: 2026-10-13 00:25:51  
**Primary Tool**: `simulation/analyze_stage1_part2.py`

---

## 1. Executive Summary

This study executes Stage 1, Part 2 of the engineering assessment for the IIT (ISM) Dhanbad smart parking system. Building on the network audit and road geometry extracted in Part 1, this study:
1. Ground-truths standard vehicle footprints against authoritative Indian Road Congress (IRC) publications (**IRC:SP:12-2015** and **IRC:SP:41**).
2. Investigates and reconciles the reported **1,505.40 m** road frontage across all 14 campus parking zones.
3. Examines carriageway cross-sections, traffic lane clearances, and fire/emergency access requirements to assess usable parking depth.
4. Calculates mathematically rigorous preliminary geometric capacities under clear layout scenarios.
5. Reconciles the dramatic discrepancies between the arbitrary database seed (140 slots), the configured SUMO simulation model (290 slots), and physical geometric reality.

### Key Headline Metrics:
- **Verified Unique Road Frontage**: **1,505.40 m** across 14 zones (confirmed zero duplicate edge IDs; however, 587.30 m represents opposing directions along the central library/NAC dual-carriageway spine).
- **Application Seed Baseline**: **140 slots** (10 slots/zone across all 14 zones, uncalibrated placeholder).
- **SUMO Simulation Baseline**: **290 slots** (total sum of `roadSideCapacity` in `campus_parking.add.xml`; previously cited as ~285).
- **Preliminary Recommended Geometric Capacity (5.5 m Parallel Car Module)**: **267 car spaces**.
- **Alternative Geometric Scenarios**:
  - Minimum Theoretical Parallel (5.0 m module, zero buffer): **294 car spaces**
  - Conservative Parallel (6.0 m module, 1.0 m buffer): **244 car spaces**
  - Theoretical Two-Wheeler Perpendicular (1.0 m curb module): **1,505 two-wheeler spaces**

---

## 2. Vehicle Design Dimensions & Authoritative Standards

In accordance with transportation engineering practice, reference vehicle envelopes and stall modules were evaluated using **IRC:SP:12-2015 (*Guidelines for Parking Facilities in Urban Areas*)** and **IRC:SP:41 (*Guidelines on Design of At-Grade Intersections in Urban Areas*)**:

### 2.1 Standard Passenger Car (Light Motor Vehicle - LMV)
- **Physical Vehicle Envelope**: Length = 4.50 m, Width = 1.80 m, Height = 1.50 m (*IRC:SP:12-2015 Clause 4.2*).
- **Standard Parking Stall Footprint**: **5.00 m length × 2.50 m width** (*IRC:SP:12-2015 Table 2*).
- **Operational Parallel Parking Module**:
  - *Minimum Legal Stall*: 5.00 m curb length × 2.50 m width. Zero maneuvering buffer.
  - *Recommended Operational Stall*: **5.50 m curb length** (5.0 m car + 0.5 m ingress/egress maneuvering clearance).
  - *Conservative/High-Turnover Stall*: **6.00 m curb length** (5.0 m car + 1.0 m buffer).
- **Perpendicular (90°) Stall Module**: 5.00 m depth × 2.50 m stall width. **Requires minimum 6.00 m drive aisle** (*IRC:SP:12-2015 Table 4*).

### 2.2 Two-Wheeler (Motorcycles / Scooters)
- **Physical Vehicle Envelope**: Length = 2.00 m, Width = 0.80 m.
- **Perpendicular Stall Footprint**: **2.00 m depth × 1.00 m curb width** (*IRC:SP:12-2015 Section 4.3*).
- **Parallel Stall Footprint**: **2.00 m curb width × 1.00 m depth**.

> [!IMPORTANT]
> The physical vehicle footprint is never equal to the required parking stall footprint. Longitudinal clearance (0.5 m to 1.0 m) is hydraulically required for parallel parking maneuvers, and transverse door-opening clearance (0.35 m to 0.70 m) is required on both sides.

---

## 3. Investigation & Reconciliation of the 1,505.40 m Frontage

A rigorous audit of `zone_road_mapping.csv`, `campus_parking.add.xml`, and `campus.net.xml` confirmed the mathematical origin and physical meaning of the reported **1,505.40 m**:

1. **How 1,505.40 m Was Derived**:
   In `campus_parking.add.xml`, each parking area specifies `startPos="2.0"` and an `endPos` that extends to approximately 88% of the edge length:
   ```
   Parkable Frontage = endPos - startPos
   Sum of Frontages = 1,505.40 m
   ```

2. **Check for Duplicate Edge IDs**:
   - Zero duplicate edge IDs exist across the 14 rows. Every zone is mapped to a distinct SUMO edge ID.
   - Zero internal junction connectors (`function="internal"`) are included.

3. **Critical Physical Geometrical Finding — Opposing Edge Pairs**:
   - `zone_library` is mapped to edge `-991056586#2` (length 326.21 m, frontage 291.60 m).
   - `zone_nac` is mapped to edge `991056586#2` (length 330.75 m, frontage 295.70 m).
   - **These two edges are opposite travel directions of the exact same physical road corridor** (OSM way `991056586`).
   - Combined, these two zones account for **587.30 m (39.0% of total campus frontage)**.
   - If this physical corridor is an undivided 2-lane road with kerbs on both sides, bilateral parallel parking may consume both shoulders. However, if it is a single undivided carriageway, parking on both sides would severely restrict moving traffic.

### Reconciled Frontage Table:
| Frontage Category | Length (m) | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **Total Reported Frontage** | **1,505.40 m** | 100.0% | Sum of all 14 `endPos - startPos` values |
| **Verified Distinct Edge Frontage** | **1,505.40 m** | 100.0% | 14 distinct SUMO edge IDs |
| **Dual-Carriageway Opposing Frontage** | **587.30 m** | 39.0% | Central spine (`zone_library` + `zone_nac`) |
| **Single-Edge Frontage (12 zones)** | **918.10 m** | 61.0% | Independent physical road links |
| **Unusable / Excluded Frontage** | **0.00 m** | 0.0% | Pre-buffered by 2.0m setback in XML |

---

## 4. Road Width & Usable Parking Space Analysis

### 4.1 Carriageway Cross-Section & Clearance Constraints
Neither `campus.net.xml` nor `iit_ism_dhanbad.osm` provides measured cross-sectional width. Applying IRC urban geometric design standards (*IRC:86-1983* and *IRC:SP:41*):
- **Single Travel Lane Width**: Minimum **3.50 m** required for passenger and emergency vehicles.
- **Fire Tender / Emergency Clearance**: Under the National Building Code (NBC) of India and IRC standards, a minimum clear passageway of **3.50 m (desirable 4.00 m)** must remain unobstructed at all times.
- **Parallel Parking Stall Depth**: **2.50 m**.
- **Required Total Carriageway Width for Roadside Parking**:
  `W_min = W_travel_lane + W_parking_bay = 3.50 m + 2.50 m = 6.00 m`

### 4.2 Cross-Section Feasibility by Zone
| Zone ID | Zone Name | Road Type | Inferred Carriageway | Travel Lane Req. | Parking Width | Data Quality | Feasibility Assessment |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `zone_main_gate` | Main Gate Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_sac` | SAC Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |
| `zone_nlhc` | NLHC Complex Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |
| `zone_library` | Central Library Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_nac` | NAC Building Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_cse` | CSE Department Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |
| `zone_health_centre` | Health Centre Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_i2h` | I2H Innovation Hub Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_academic_complex` | Academic Complex Parking | `highway.service` | 3.75 m | 3.50 m | 0.00 m | inferred | low |
| `zone_amber` | Amber Hostel Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |
| `zone_aquamarine` | Aquamarine Hostel Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |
| `zone_mechanical` | Mechanical Dept Parking | `highway.unclassified` | 6.00 m | 3.50 m | 2.50 m | inferred | medium |
| `zone_enviro` | Environmental Dept Parking | `highway.unclassified` | 6.00 m | 3.50 m | 2.50 m | inferred | medium |
| `zone_oat` | OAT Grounds Parking | `highway.residential` | 5.50 m | 3.50 m | 2.00 m | inferred | medium |


> [!CAUTION]
> In `highway.service` zones (Main Gate, Health Centre, I2H, Academic Complex), inferred road width is 3.75 m. If vehicles park directly on the paved carriageway without an unpaved shoulder or setback, the road becomes completely blocked for through-traffic and emergency access. Parallel parking in these zones is only feasible if vehicles utilize designated unpaved road verges or dedicated setback bays.

---

## 5. Preliminary Geometric Capacity Calculations

Preliminary capacities were calculated using direct geometric division of verified frontage by standard stall modules, rounded down to whole stalls (floor(Frontage / L_stall)):

- **Scenario 1 (Recommended Operational)**: **5.50 m module** (5.0 m stall + 0.5 m ingress/egress buffer).
- **Scenario 2 (Minimum Theoretical)**: **5.00 m module** (absolute bumper-to-bumper limit).
- **Scenario 3 (Conservative Buffer)**: **6.00 m module** (1.0 m buffer for high turnover).
- **Scenario 4 (Two-Wheeler Perpendicular)**: **1.00 m curb module** (2.0 m depth into shoulder).

### Preliminary Capacity Summary Table:
| Zone ID | Zone Name | Frontage (m) | Recommended (5.5m) | Min (5.0m) | Conservative (6.0m) | 2W Perpendicular | Confidence |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `zone_main_gate` | Main Gate Parking | 79.80 | **14** | 15 | 13 | 79 | Medium |
| `zone_sac` | SAC Parking | 89.00 | **16** | 17 | 14 | 89 | Medium |
| `zone_nlhc` | NLHC Complex Parking | 90.80 | **16** | 18 | 15 | 90 | Medium |
| `zone_library` | Central Library Parking | 291.60 | **53** | 58 | 48 | 291 | Low (Opposing edge) |
| `zone_nac` | NAC Building Parking | 295.70 | **53** | 59 | 49 | 295 | Low (Opposing edge) |
| `zone_cse` | CSE Department Parking | 23.20 | **4** | 4 | 3 | 23 | Medium |
| `zone_health_centre`| Health Centre Parking | 64.20 | **11** | 12 | 10 | 64 | Medium-Low |
| `zone_i2h` | I2H Innovation Hub Parking | 52.60 | **9** | 10 | 8 | 52 | Medium-Low |
| `zone_academic_complex`| Academic Complex Parking | 117.50 | **21** | 23 | 19 | 117 | Medium-Low |
| `zone_amber` | Amber Hostel Parking | 84.50 | **15** | 16 | 14 | 84 | Medium |
| `zone_aquamarine` | Aquamarine Hostel Parking | 31.60 | **5** | 6 | 5 | 31 | Medium |
| `zone_mechanical` | Mechanical Dept Parking | 65.50 | **11** | 13 | 10 | 65 | Medium |
| `zone_enviro` | Environmental Dept Parking| 110.40 | **20** | 22 | 18 | 110 | Medium |
| `zone_oat` | OAT Grounds Parking | 109.00 | **19** | 21 | 18 | 109 | Medium |
| **CAMPUS TOTAL** | — | **1,505.40** | **267** | **294** | **244** | **1,505** | — |

---

## 6. Baseline Comparison: Seed vs. SUMO vs. Geometric Analysis

The table below reconciles the three capacity paradigms across all 14 zones:
- **Baseline A (Seed)**: 14 zones × 10 = 140 slots.
- **Baseline B (SUMO)**: Configured in `campus_parking.add.xml` = 290 slots (verified).
- **Geometric Recommended**: Derived from 5.5m module = 267 slots.

| Zone ID | Zone Name | Mapped Edge | Seed Cap | SUMO Cap | Geom. Cap (Rec) | Diff from Seed | Diff from SUMO | Confidence |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `zone_main_gate` | Main Gate Parking | `-517026169#0` | 10 | 25 | **14** | +4 | -11 | medium-low |
| `zone_sac` | SAC Parking | `991055730` | 10 | 20 | **16** | +6 | -4 | medium |
| `zone_nlhc` | NLHC Complex Parking | `-517026168#2` | 10 | 30 | **16** | +6 | -14 | medium |
| `zone_library` | Central Library Parking | `-991056586#2` | 10 | 25 | **53** | +43 | +28 | low |
| `zone_nac` | NAC Building Parking | `991056586#2` | 10 | 25 | **53** | +43 | +28 | low |
| `zone_cse` | CSE Department Parking | `1207647016#1` | 10 | 15 | **4** | -6 | -11 | medium |
| `zone_health_centre` | Health Centre Parking | `517026174` | 10 | 15 | **11** | +1 | -4 | medium-low |
| `zone_i2h` | I2H Innovation Hub Parking | `-991056586#1` | 10 | 20 | **9** | -1 | -11 | medium-low |
| `zone_academic_complex` | Academic Complex Parking | `-517026169#5` | 10 | 25 | **21** | +11 | -4 | medium-low |
| `zone_amber` | Amber Hostel Parking | `1031061562#3` | 10 | 20 | **15** | +5 | -5 | medium |
| `zone_aquamarine` | Aquamarine Hostel Parking | `1029515471` | 10 | 20 | **5** | -5 | -15 | medium |
| `zone_mechanical` | Mechanical Dept Parking | `-517026179#7` | 10 | 15 | **11** | +1 | -4 | medium |
| `zone_enviro` | Environmental Dept Parking | `-517026179#5` | 10 | 15 | **20** | +10 | +5 | medium |
| `zone_oat` | OAT Grounds Parking | `-1118600401` | 10 | 20 | **19** | +9 | -1 | medium |


### Key Discrepancy Findings:
1. **The 140-Slot Seed Baseline is Arbitrary**:
   The application's `seed.js` uniformly created 10 slots per zone regardless of whether the road was 23 metres long (`zone_cse`) or nearly 300 metres long (`zone_nac`).
2. **SUMO Baseline (290 slots) is an Uncalibrated Approximation**:
   - On short edges (`zone_cse` at 23.2 m and `zone_aquamarine` at 31.6 m), SUMO assigned 15 and 20 slots. This requires a vehicle stall length of **1.55 m** — physical impossibility for passenger cars.
   - On long edges (`zone_library` and `zone_nac` at ~295 m), SUMO capped slots at 25 each (spacing of **11.8 m/slot**), severely underutilizing available frontage.
   - Ironically, because SUMO's over-allocations on short edges canceled out its under-allocations on long edges, SUMO's aggregate total (290) landed close to the theoretical 5.0m maximum (294) and recommended capacity (267). However, its zone-by-zone distribution is physically distorted.

---

## 7. Deliverables Created

The following machine-readable and technical files were generated in `simulation/output/`:
1. `vehicle_design_assumptions.csv`: Authoritative vehicle envelopes and stall modules referencing IRC:SP:12-2015.
2. `zone_usable_width.csv`: Detailed cross-sectional width requirements, traffic lane clearances, and feasibility assessments per zone.
3. `zone_geometric_capacity_preliminary.csv`: Zone-by-zone geometric capacities across 4 layout scenarios.
4. `capacity_baseline_comparison.csv`: Direct multi-factor comparison between Seed, SUMO, and Geometric capacities.
5. `stage1_part2_report.md`: This comprehensive engineering audit report.
6. `analyze_stage1_part2.py`: The underlying calculation and data generation engine.

---

## 8. Handoff Note for Stage 1, Part 3

Stage 1, Part 3 (*Capacity Calibration and Layout Refinement*) must now address:
1. **Field Ground-Truthing & Satellite Cross-Verification**: Verify physical road widths, kerbs, and driveways along the 14 links to confirm where shoulder parking is physically possible.
2. **Opposing Carriageway Conflict Resolution**: Resolve whether `zone_library` and `zone_nac` share a single road bed or have a physical median dividing them.
3. **Vehicle Mix Allocation**: Establish the modal split between four-wheelers and two-wheelers. Allocating even 20% of frontage to two-wheelers will dramatically increase total vehicle capacity.
4. **Capacity Calibration Proposal**: Formulate a proposal to replace the arbitrary 10-slot seed with calibrated, geometrically grounded capacities in both the database seed and SUMO simulation.
