# Campus Smart Parking Management System
## IIT (ISM) Dhanbad Campus & Surrounding Dhanbad Road Network

A full-stack, production-quality smart parking management platform integrating real-time campus parking operations with **Eclipse SUMO microscopic traffic simulation** and **Scikit-learn machine learning occupancy prediction models**.

---

### Project Architecture Flow

```
IIT (ISM) / Dhanbad Road Network (OSM 1,773 Edges, 758 Junctions)
                        ↓
            SUMO Traffic Simulation (TraCI)
                        ↓
         Vehicle & Parking Data (Telemetry & Logging)
                        ↓
             MongoDB / Data Processing
                        ↓
            ML Regressor Pipeline (Gradient Boosting & Random Forest)
                        ↓
             Parking Occupancy Prediction (with Confidence Bounds)
                        ↓
              Node.js + Express API (/api/simulation)
                        ↓
        Web Dashboard ("Traffic & Parking Prediction")
```

---

### Strict Academic Data Distinction

The system clearly differentiates between three modalities of data:

| Modality | Badge Indicator | Data Source & Mechanism | Verification Standard |
| :--- | :--- | :--- | :--- |
| **Real Campus Data** | 🟢 `REAL CAMPUS DATA` | Operational MongoDB collections (Slots, Users, QR permits) | Live physical slots & gate check-ins |
| **SUMO Simulated Data** | 🔵 `SUMO SIMULATION DATA` | Microscopic TraCI simulation on authentic OpenStreetMap network | Physics-based vehicle movement & parking |
| **ML Predicted Data** | 🟣 `ML PREDICTED DATA` | Scikit-learn Gradient Boosting & Random Forest regressors | Hold-out test set evaluated (MAE ±1.26 slots) |

---

## Key Features

### Feature 1 — SUMO Road Network
- Authentic OpenStreetMap network representing **IIT (ISM) Dhanbad campus** (23.814° N, 86.441° E) and surrounding Dhanbad arterial roads (Saraidheela Road, Police Line Road, Housing Colony Road, Luby Circular Road).
- **1,773 edges** and **758 junctions** compiled via `netconvert` with UTM zone 45 projection.
- Modeled Entry/Exit checkpoints:
  - **Main Gate** (Saraidheela / Police Line Rd)
  - **Ruby Gate** (West Campus Link)
  - **North Gate** (Barwadda Connector)
- Includes 14 authentic campus parking facilities with calibrated operational capacities:
  1. `zone_main_gate`: Main Gate Parking (Cap: 14 roadside car bays | 33 multimodal slots: 10 4W, 23 2W)
  2. `zone_sac`: SAC Parking (Cap: 16 roadside car bays | 37 multimodal slots: 11 4W, 26 2W)
  3. `zone_nlhc`: NLHC Complex Parking (Cap: 16 roadside car bays | 38 multimodal slots: 11 4W, 27 2W)
  4. `zone_library`: Central Library Parking (Cap: 26 roadside car bays | 61 multimodal slots: 18 4W, 43 2W) [Capped 50% for corridor]
  5. `zone_nac`: NAC Building Parking (Cap: 26 roadside car bays | 62 multimodal slots: 18 4W, 44 2W) [Capped 50% for corridor]
  6. `zone_cse`: CSE Department Parking (Cap: 4 roadside car bays | 8 multimodal slots: 2 4W, 6 2W)
  7. `zone_health_centre`: Health Centre Parking (Cap: 11 roadside car bays | 27 multimodal slots: 8 4W, 19 2W)
  8. `zone_i2h`: I2H Innovation Hub Parking (Cap: 9 roadside car bays | 21 multimodal slots: 6 4W, 15 2W)
  9. `zone_academic_complex`: Academic Complex Parking (Cap: 21 roadside car bays | 49 multimodal slots: 14 4W, 35 2W)
  10. `zone_amber`: Amber Hostel Parking (Cap: 15 roadside car bays | 35 multimodal slots: 10 4W, 25 2W)
  11. `zone_aquamarine`: Aquamarine Hostel Parking (Cap: 5 roadside car bays | 13 multimodal slots: 4 4W, 9 2W)
  12. `zone_mechanical`: Mechanical Dept Parking (Cap: 11 roadside car bays | 27 multimodal slots: 8 4W, 19 2W)
  13. `zone_enviro`: Environmental Dept Parking (Cap: 20 roadside car bays | 47 multimodal slots: 14 4W, 33 2W)
  14. `zone_oat`: OAT Grounds Parking (Cap: 19 roadside car bays | 45 multimodal slots: 13 4W, 32 2W)
  - **Total Campus Application Database**: **503 Slots** (147 four-wheelers, 356 two-wheelers)
  - **Total SUMO Roadside Car Capacity**: **213 Car Bays** (operational traffic-calibrated)

### Feature 2 — SUMO Traffic Simulation
- Realistic multi-class vehicular composition:
  - **Two-Wheelers** (`vClass="motorcycle"`)
  - **Faculty & Staff Cars** (`vClass="passenger"`)
  - **Student Cars** (`vClass="passenger"`)
  - **Visitor Cars** (`vClass="passenger"`)
  - **Campus Administrative EVs** (`vClass="evehicle"`)
- Time-varying demand curves:
  - Morning rush (08:00–10:30 AM)
  - Mid-day lecture & dining shift (11:00 AM–02:00 PM)
  - Evening departure & sports peak (04:30–06:30 PM)
  - Off-peak night hours
- Visual GUI execution: launch `simulation/launch_sumo_gui.bat` to visually watch vehicles moving through campus roads and entering parking areas.

### Feature 3 — Data Generation & Telemetry Logging
- Comprehensive telemetry tracking during simulation:
  - `timestamp`
  - `vehicle_count` (active campus vehicles)
  - `entry_count` (inflow volume)
  - `exit_count` (outflow volume)
  - `traffic_density` (veh/km)
  - `avg_speed_kmh`
  - `occupied_slots`, `available_slots`, `occupancy_percentage`
- Dual persistence:
  - Structured CSV: `simulation/output/occupancy_data.csv` and `simulation/output/training_data.csv`
  - Document Database: MongoDB collections `simulated_traffic_data`, `simulated_training_data`, and `simulation_status`.

### Feature 4 — ML Parking Occupancy Prediction
- Trained on 15,120 calibrated simulation records across 14 zones and 45 days.
- Ensemble Regressor Pipeline:
  - **Gradient Boosting Regressor**: Short-term horizon ($\le 4$ hours)
  - **Random Forest Regressor**: Long-term horizon ($> 4$ hours)
- Empirical Hold-Out Test Set Evaluation ($N=3,024$ test samples):
  - **Mean Absolute Error (MAE):** **1.263 slots**
  - **Root Mean Squared Error (RMSE):** **1.584**
  - **Coefficient of Determination ($R^2$):** **0.9427**
  - **Occupancy Percentage Model:** MAE = 6.11%, RMSE = 7.42%, $R^2 = 0.9281$
- Feature Set: `zone_id`, `capacity`, `vehicle_count`, `entry_count`, `exit_count`, `traffic_density`, `avg_speed_kmh`, `hour`, `day_of_week`, `is_weekend`, `is_peak`, `temperature`, `humidity`.
- Outputs 95% confidence intervals $[CI_{low}, CI_{high}]$ based on empirical MAE.

### Feature 5 — Website Dashboard: "Traffic & Parking Prediction"
- Dedicated dashboard view accessible to all users via top navigation tab:
  1. **Current / Simulated Occupancy Metric**: Live gauge and slot breakdown.
  2. **Available & Occupied Slots Counter**: Real-time counter across all 14 zones.
  3. **Traffic Density & Speed Indicators**: Vehicles/km and flow condition badge.
  4. **Interactive Zone Forecast Predictor**: Select zone and prediction horizon (1–24 hours) to receive instant ML forecast with confidence intervals.
  5. **Parking Occupancy Time-Series Graph**: Visual hourly occupancy percentage trends.
  6. **Traffic & Vehicle Flow Graph**: Visual breakdown of active vehicles, inflow, and outflow.
  7. **SUMO Simulation Status**: Status badge (READY / RUNNING / COMPLETED), scenario description, and one-click simulation trigger.
  8. **14 Campus Parking Zones Grid**: Detailed status cards for each zone with clickable instant forecast lookup.
  9. **Academic Integrity Table**: Explicit side-by-side comparison of Real vs Simulated vs Predicted data.

### Feature 6 — Geospatial GIS Map: "Campus GIS Map"
- Dedicated interactive GIS map accessible via top navigation tab or directly at `http://localhost:5001/map.html`.
- Powered by Leaflet.js and authentic OpenStreetMap cartography.
- Geospatial Layer Suite:
  - **`parking_zones.geojson`**: 14 calibrated zone point centroids with full slot quotas, road types, and restriction metadata.
  - **`road_network.geojson`**: 1,773 normal campus road edges extracted from `campus.net.xml` and projected into standard WGS84 (`EPSG:4326`).
  - **`parking_frontage.geojson`**: 14 physical curb frontage polylines highlighting parallel parking bays and corridor bottlenecks.
- Interactive features: Click any zone marker or road frontage line to inspect live 4W/2W capacity breakdowns, host road edge IDs, and corridor traffic regulations.

---

## Demonstration & Quick Start

### 1. Start the Web Platform
```bash
# In project root
node server/src/index.js
```
Open your browser at `http://localhost:5001`.

### 2. Demo Login Credentials (Local Development & Testing Only)
> **Note:** The credentials listed below are mock accounts pre-seeded in `server/src/seeds/seed.js` strictly for local testing, grading, and academic demonstration. They do not grant access to any real production environment.

- **Administrator (Demo):** `admin@campus.com` / `password123`
- **Security Officer (Demo):** `security@campus.com` / `password123`
- **Student/Staff User (Demo):** `user@campus.com` / `password123`

### 3. Access the Prediction Module
Click on the **"🚗 Traffic & Parking Prediction [SUMO + ML]"** tab in the dashboard navigation.

### 4. Run SUMO Microscopic Simulation
- From Web UI: Click **"▶ Run SUMO Simulation"** in the action bar.
- From Command Line (Headless):
  ```bash
  python simulation/run_simulation.py --quick
  ```
- Visual GUI Mode:
  ```bash
  # Double-click or run from command prompt:
  simulation\launch_sumo_gui.bat
  ```
  In SUMO GUI, click the green Play button and adjust the delay slider (e.g. 50–100ms) to visually watch vehicles moving through the IIT (ISM) Dhanbad road network.

### 5. Retrain ML Models (Optional)
```bash
# 1. Regenerate 45 days of simulation training data
python simulation/generate_training_data.py

# 2. Train Gradient Boosting and Random Forest models
python ml_service/train_model.py
```

---

## Project Structure

```text
Campus_Parking_System/
├── public/                                # Single-Page Web Frontend (ESM + React 18)
│   ├── index.html
│   ├── styles.css
│   └── src/
│       ├── App.js                         # Main application container & tab router
│       ├── components/
│       │   ├── TrafficPredictionDashboard.js # Feature 5: Traffic & Parking Prediction
│       │   ├── AdminDashboard.js          # Admin zone/slot management
│       │   ├── SecurityDashboard.js       # Gate permit scanning via QR
│       │   ├── UserDashboard.js           # Commuter reservation & passbook
│       │   └── common.js                  # Shared UI components & DashboardShell
│       └── services/api.js                # API request wrapper
│
├── simulation/                            # Features 1, 2, 3: SUMO Road Network & Simulation
│   ├── iit_ism_dhanbad.osm                # Authentic OpenStreetMap extract
│   ├── campus.net.xml                     # Compiled road network (1,773 edges, 758 nodes)
│   ├── campus_parking.add.xml             # 14 parking areas with calibrated positions
│   ├── campus.trips.xml                   # Multi-class vehicle trips (cars, 2W, EVs)
│   ├── campus_demand.rou.xml              # Duarouter compiled vehicle routes
│   ├── campus.sumocfg                     # SUMO simulation configuration
│   ├── gui-settings.cfg                   # Viewport & visual display settings
│   ├── launch_sumo_gui.bat                # Windows batch launcher for SUMO GUI
│   ├── run_simulation.py                  # TraCI simulation runner with MongoDB logging
│   └── generate_training_data.py          # 45-day calibrated time-series data generator
│
├── ml_service/                            # Feature 4: ML Occupancy Prediction Pipeline
│   ├── train_model.py                     # Pipeline trainer (GB + RF) with hold-out evaluation
│   ├── app.py                             # FastAPI prediction microservice
│   ├── predict_cli.py                     # Node-resilient CLI predictor
│   └── models/
│       ├── model_metrics.json             # Empirical test metrics (MAE: 1.263, R²: 0.9427)
│       ├── short_term_model.pkl           # Gradient Boosting model pipeline
│       └── long_term_model.pkl            # Random Forest model pipeline
│
└── server/                                # Backend Express REST API
    └── src/
        ├── index.js                       # Express server entry point
        ├── controllers/
        │   ├── simulationController.js    # Simulation & prediction controller
        │   ├── parkingController.js
        │   └── authController.js
        ├── routes/
        │   ├── simulationRoutes.js        # /api/simulation endpoints
        │   ├── parkingRoutes.js
        │   └── authRoutes.js
        └── models/
            ├── SimulatedTraffic.js        # Mongoose schema for simulation telemetry
            ├── ParkingSlot.js
            └── Reservation.js
```
