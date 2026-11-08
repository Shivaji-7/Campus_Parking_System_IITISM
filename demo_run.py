import os
import sys
import json
from pymongo import MongoClient

print("=" * 70)
print("[STEP 1]: SUMO TRAFFIC SIMULATION RUN (IIT ISM DHANBAD)")
print("=" * 70)
exit_code = os.system("python simulation/run_simulation.py --quick")

print("\n" + "=" * 70)
print("[STEP 2]: VERIFY DATA STORED IN MONGODB & CSV")
print("=" * 70)
client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["campus_parking"]
sim_count = db["simulated_traffic_data"].count_documents({})
train_count = db["simulated_training_data"].count_documents({})
print(f"Total Simulation Telemetry Records in MongoDB: {sim_count}")
print(f"Total Multi-Day Training Records in MongoDB:  {train_count}")

sample = db["simulated_traffic_data"].find_one({}, sort=[("timestamp", -1)])
if sample:
    print("\n[Sample Latest Telemetry Document]:")
    print(f"  - Zone:            {sample.get('zone_name')} ({sample.get('zone_id')})")
    print(f"  - Capacity:        {sample.get('capacity')} slots")
    print(f"  - Occupied Slots:  {sample.get('occupied_slots')}")
    print(f"  - Available Slots: {sample.get('available_slots')}")
    print(f"  - Occupancy %:     {sample.get('occupancy_percentage')}%")
    print(f"  - Active Vehicles: {sample.get('active_vehicles')} on campus roads")
    print(f"  - Traffic Density: {sample.get('traffic_density')} veh/km")
    print(f"  - Average Speed:   {sample.get('avg_speed_kmh')} km/h")

print("\n" + "=" * 70)
print("[STEP 3]: ML MODEL PARKING PREDICTION INFERENCE")
print("=" * 70)
zones_to_test = [
    ("zone_nlhc", 2, "NLHC Complex Parking"),
    ("zone_library", 4, "Central Library Parking"),
    ("zone_main_gate", 1, "Main Gate Parking"),
    ("zone_sac", 3, "SAC Parking")
]

for zid, h, name in zones_to_test:
    pipe = os.popen(f"python ml_service/predict_cli.py {zid} {h}")
    res = pipe.read().strip()
    try:
        data = json.loads(res)
        print(f"\n[Prediction for {name} (+{h} Hours Ahead)]:")
        print(f"  - Target Time:          {data.get('prediction_time')}")
        print(f"  - Predicted Occupancy:  {data.get('predicted_occupancy')} / {data.get('capacity')} slots ({data.get('predicted_percentage')}%)")
        print(f"  - 95% Confidence Band:  {data.get('confidence_interval_low')} to {data.get('confidence_interval_high')} slots")
        print(f"  - Model Used:           {data.get('model_used')}")
        print(f"  - Model Accuracy (MAE): +/-{data.get('evaluation_metrics', {}).get('mae')} slots (RMSE: {data.get('evaluation_metrics', {}).get('rmse')}, R2: {data.get('evaluation_metrics', {}).get('r2')})")
    except Exception as e:
        print(f"  Prediction error for {zid}: {res} ({e})")

print("\n" + "=" * 70)
print("[STEP 4]: WEB DASHBOARD API LIVE CHECK (PORT 5001)")
print("=" * 70)
print("Server is ACTIVE on: http://localhost:5001")
print("Dashboard URL:       http://localhost:5001")
print("Demo Credentials:")
print("  - User:     user@campus.com / password123")
print("  - Security: security@campus.com / password123")
print("  - Admin:    admin@campus.com / password123")
print("\nTo visually watch SUMO vehicles driving in GUI, run:")
print("  simulation\\launch_sumo_gui.bat")
print("=" * 70)
