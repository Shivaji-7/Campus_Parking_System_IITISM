import os
import csv
import random
from datetime import datetime, timedelta

try:
    from pymongo import MongoClient
    mongo_client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    mongo_client.server_info()
    db = mongo_client["campus_parking"]
    mongo_available = True
    print("Connected to MongoDB for training data storage.")
except Exception as e:
    mongo_available = False
    db = None
    print(f"MongoDB not connected ({e}); saving locally to CSV.")

ZONES = [
    {"id": "zone_main_gate", "name": "Main Gate Parking", "cap": 25, "peak_factor": 1.2},
    {"id": "zone_sac", "name": "SAC Parking", "cap": 20, "peak_factor": 1.1},
    {"id": "zone_nlhc", "name": "NLHC Complex Parking", "cap": 30, "peak_factor": 1.4},
    {"id": "zone_library", "name": "Central Library Parking", "cap": 25, "peak_factor": 1.3},
    {"id": "zone_nac", "name": "NAC Building Parking", "cap": 25, "peak_factor": 1.2},
    {"id": "zone_cse", "name": "CSE Department Parking", "cap": 15, "peak_factor": 1.1},
    {"id": "zone_health_centre", "name": "Health Centre Parking", "cap": 15, "peak_factor": 0.8},
    {"id": "zone_i2h", "name": "I2H Innovation Hub Parking", "cap": 20, "peak_factor": 0.9},
    {"id": "zone_academic_complex", "name": "Academic Complex Parking", "cap": 25, "peak_factor": 1.3},
    {"id": "zone_amber", "name": "Amber Hostel Parking", "cap": 20, "peak_factor": 1.0},
    {"id": "zone_aquamarine", "name": "Aquamarine Hostel Parking", "cap": 20, "peak_factor": 1.0},
    {"id": "zone_mechanical", "name": "Mechanical Dept Parking", "cap": 15, "peak_factor": 1.1},
    {"id": "zone_enviro", "name": "Environmental Dept Parking", "cap": 15, "peak_factor": 0.9},
    {"id": "zone_oat", "name": "OAT Grounds Parking", "cap": 20, "peak_factor": 0.7},
]

def generate_data(num_days=45):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, "training_data.csv")

    start_date = datetime.now() - timedelta(days=num_days)
    records = []

    print(f"Generating {num_days} days of calibrated simulation data across {len(ZONES)} zones...")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = [
            "timestamp", "zone_id", "zone_name", "capacity",
            "occupied_slots", "available_slots", "occupancy_percentage",
            "vehicle_count", "entry_count", "exit_count",
            "traffic_density", "avg_speed_kmh",
            "hour", "day_of_week", "is_weekend", "is_peak",
            "temperature", "humidity"
        ]
        writer.writerow(header)

        for day in range(num_days):
            current_date = start_date + timedelta(days=day)
            day_of_week = current_date.weekday() # 0 = Monday, 6 = Sunday
            is_weekend = 1 if day_of_week >= 5 else 0

            for hour in range(24):
                # Peak hours: Morning rush (8-10), Afternoon lecture shift (13-14), Evening departure/sports (17-19)
                is_peak = 1 if hour in [8, 9, 10, 13, 17, 18] else 0

                # Ambient conditions for Dhanbad
                temp = round(random.uniform(18.0, 36.0), 1)
                humidity = round(random.uniform(35.0, 85.0), 1)

                # Active campus traffic volume
                if is_weekend:
                    active_vehicles = random.randint(10, 45)
                    entry_volume = random.randint(2, 12)
                    exit_volume = random.randint(2, 10)
                else:
                    if is_peak:
                        active_vehicles = random.randint(85, 220)
                        entry_volume = random.randint(25, 70)
                        exit_volume = random.randint(15, 55)
                    elif 7 <= hour <= 21:
                        active_vehicles = random.randint(40, 110)
                        entry_volume = random.randint(10, 30)
                        exit_volume = random.randint(10, 30)
                    else: # Night
                        active_vehicles = random.randint(5, 20)
                        entry_volume = random.randint(0, 5)
                        exit_volume = random.randint(0, 5)

                traffic_density = round(active_vehicles / 15.0, 2)
                # Congestion slows speed
                base_speed = 32.0 - (traffic_density * 1.5)
                avg_speed = max(10.0, round(base_speed + random.uniform(-3, 3), 1))

                timestamp_dt = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")

                for z in ZONES:
                    cap = z["cap"]
                    factor = z["peak_factor"]

                    if is_weekend:
                        base_pct = random.uniform(0.10, 0.35)
                    else:
                        if is_peak:
                            base_pct = min(0.96, random.uniform(0.65, 0.95) * factor)
                        elif 7 <= hour <= 21:
                            base_pct = min(0.85, random.uniform(0.35, 0.65) * factor)
                        else:
                            base_pct = random.uniform(0.05, 0.20)

                    # Add slight gaussian variation
                    occ_slots = int(round(cap * base_pct))
                    occ_slots = max(0, min(cap, occ_slots))
                    avail_slots = cap - occ_slots
                    occ_pct = round((occ_slots / cap) * 100.0, 1)

                    row = [
                        timestamp_str, z["id"], z["name"], cap,
                        occ_slots, avail_slots, occ_pct,
                        active_vehicles, entry_volume, exit_volume,
                        traffic_density, avg_speed,
                        hour, day_of_week, is_weekend, is_peak,
                        temp, humidity
                    ]
                    writer.writerow(row)

                    if mongo_available:
                        records.append({
                            "timestamp": timestamp_dt,
                            "zone_id": z["id"],
                            "zone_name": z["name"],
                            "capacity": cap,
                            "occupied_slots": occ_slots,
                            "available_slots": avail_slots,
                            "occupancy_percentage": occ_pct,
                            "vehicle_count": active_vehicles,
                            "entry_count": entry_volume,
                            "exit_count": exit_volume,
                            "traffic_density": traffic_density,
                            "avg_speed_kmh": avg_speed,
                            "hour": hour,
                            "day_of_week": day_of_week,
                            "is_weekend": bool(is_weekend),
                            "is_peak": bool(is_peak),
                            "temperature": temp,
                            "humidity": humidity,
                            "is_simulated": True
                        })

    print(f"Generated {num_days} days of training data to {csv_file}")

    if mongo_available and records:
        print(f"Syncing {len(records)} records to MongoDB collection 'simulated_training_data'...")
        db["simulated_training_data"].delete_many({})
        # Batch insert
        batch_size = 2000
        for i in range(0, len(records), batch_size):
            db["simulated_training_data"].insert_many(records[i:i + batch_size])
        print("MongoDB sync complete.")

if __name__ == "__main__":
    generate_data(num_days=45)
