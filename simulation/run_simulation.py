import os
import sys
import time
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Robust SUMO path detection (Part D)
def detect_sumo():
    # 1. Check SUMO_HOME environment variable
    env_sumo_home = os.environ.get("SUMO_HOME")
    if env_sumo_home and os.path.exists(os.path.join(env_sumo_home, "bin", "sumo.exe")):
        return (
            os.path.join(env_sumo_home, "bin", "sumo.exe"),
            os.path.join(env_sumo_home, "bin", "sumo-gui.exe"),
            env_sumo_home
        )

    # 2. Check native installation at Program Files (x86)\SUMO
    native_path = r"C:\Program Files (x86)\SUMO"
    if os.path.exists(os.path.join(native_path, "bin", "sumo.exe")):
        return (
            os.path.join(native_path, "bin", "sumo.exe"),
            os.path.join(native_path, "bin", "sumo-gui.exe"),
            native_path
        )

    # 3. Check Python site-packages sumo fallback
    try:
        import sumo
        return (
            os.path.join(sumo.SUMO_HOME, "bin", "sumo.exe"),
            os.path.join(sumo.SUMO_HOME, "bin", "sumo-gui.exe"),
            sumo.SUMO_HOME
        )
    except Exception:
        pass

    return "sumo", "sumo-gui", None

sumo_bin, sumo_gui_bin, detected_sumo_home = detect_sumo()
if detected_sumo_home:
    os.environ["SUMO_HOME"] = detected_sumo_home
    os.environ["PATH"] = os.path.join(detected_sumo_home, "bin") + os.pathsep + os.environ.get("PATH", "")

import traci

# Optional MongoDB connection
try:
    from pymongo import MongoClient
    mongo_client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    mongo_client.server_info() # verify connection
    db = mongo_client["campus_parking"]
    mongo_available = True
    print("Connected to MongoDB at mongodb://127.0.0.1:27017/campus_parking")
except Exception as e:
    mongo_available = False
    db = None
    print(f"MongoDB not available for direct logging ({e}); will write to CSV files.")

def parse_parking_capacities(add_file):
    capacities = {}
    if os.path.exists(add_file):
        tree = ET.parse(add_file)
        root = tree.getroot()
        for p in root.findall("parkingArea"):
            p_id = p.get("id")
            # Support both roadsideCapacity and legacy roadSideCapacity
            cap_val = p.get("roadsideCapacity") or p.get("roadSideCapacity") or 10
            cap = int(cap_val)
            name = p.get("name", p_id)
            lane = p.get("lane")
            capacities[p_id] = {"capacity": cap, "name": name, "lane": lane}
    return capacities

def run(use_gui=False, max_steps=None, sample_interval=30, seed=42):
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_file = os.path.join(sim_dir, "campus.sumocfg")
    add_file = os.path.join(sim_dir, "campus_parking.add.xml")
    output_dir = os.path.join(sim_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, "occupancy_data.csv")

    capacities = parse_parking_capacities(add_file)
    print(f"Loaded {len(capacities)} parking zones from configuration.")

    # Lane to Zone lookup map
    lane_to_zone = {}
    for zid, zinfo in capacities.items():
        if zinfo.get("lane"):
            lane_to_zone[zinfo["lane"]] = zid

    # Run identifier for tracking simulation runs across telemetry
    run_id = f"sim_run_{int(time.time())}"

    executable = sumo_gui_bin if use_gui else sumo_bin
    sumo_cmd = [
        executable,
        "-c", cfg_file,
        "--start", "true",
        "--quit-on-end", "true"
    ]
    if seed is not None:
        sumo_cmd.extend(["--seed", str(seed)])

    print(f"Starting SUMO simulation using: {executable} (seed={seed}, run_id={run_id})")
    traci.start(sumo_cmd)

    # Initialize status in MongoDB
    if mongo_available:
        db["simulation_status"].update_one(
            {"_id": "current_status"},
            {"$set": {
                "status": "RUNNING",
                "mode": "GUI" if use_gui else "HEADLESS",
                "startedAt": datetime.now(),
                "simulationScenario": "IIT (ISM) Dhanbad Campus & Dhanbad Area",
                "totalZones": len(capacities),
                "runId": run_id,
                "seed": seed
            }},
            upsert=True
        )

    records = []
    base_date = datetime.now().replace(hour=7, minute=30, second=0, microsecond=0)
    
    # Global trip counters
    cumulative_entered = 0
    cumulative_exited = 0
    interval_entered = 0
    interval_exited = 0
    
    # Global teleport counter
    cumulative_teleported = 0
    interval_teleported = 0
    
    # Zone-wise event accumulators
    interval_parking_starts = {zid: 0 for zid in capacities}
    interval_parking_ends = {zid: 0 for zid in capacities}
    cumulative_parked = {zid: 0 for zid in capacities}
    cumulative_unparked = {zid: 0 for zid in capacities}
    zone_teleports = {zid: 0 for zid in capacities}

    # Tracking map to associate vehicles with the zone they parked in
    # vid -> zone_id (ensures unparking events are mapped exactly to the origin zone)
    veh_parking_zone = {}

    step_count = 0

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "sim_time_sec", "zone_id", "zone_name",
            "occupied_slots", "available_slots", "capacity", "occupancy_percentage",
            "active_vehicles", "entry_count", "exit_count",
            "cumulative_entered", "cumulative_exited",
            "zone_parking_starts", "zone_parking_ends",
            "cumulative_parked", "cumulative_unparked",
            "zone_teleports",
            "traffic_density", "avg_speed_kmh"
        ])

        def sample_and_flush_telemetry(sim_time):
            nonlocal interval_entered, interval_exited, interval_teleported
            sim_clock = base_date + timedelta(seconds=max(0, sim_time - 27000))
            timestamp_str = sim_clock.strftime("%Y-%m-%d %H:%M:%S")

            # Vehicle counts and telemetry
            active_veh_ids = traci.vehicle.getIDList()
            active_count = len(active_veh_ids)

            # Calculate average speed in km/h
            if active_count > 0:
                speeds = [traci.vehicle.getSpeed(v) for v in active_veh_ids]
                avg_speed = (sum(speeds) / len(speeds)) * 3.6  # m/s to km/h
            else:
                avg_speed = 0.0

            # Network density estimation (vehicles per km across campus roads)
            traffic_density = round(active_count / 15.0, 2)

            # Iterate zones to capture verified occupancy and event metrics
            current_zone_summaries = []
            for zone_id, zinfo in capacities.items():
                try:
                    veh_count = traci.parkingarea.getVehicleCount(zone_id)
                except Exception:
                    veh_count = 0

                cap = zinfo["capacity"]
                avail = max(0, cap - veh_count)
                occ_pct = round((veh_count / cap) * 100.0, 1)

                p_starts = interval_parking_starts[zone_id]
                p_ends = interval_parking_ends[zone_id]
                tot_parked = cumulative_parked[zone_id]
                tot_unparked = cumulative_unparked[zone_id]
                z_teleports = zone_teleports[zone_id]

                # Complete schema record matching 20 columns
                row = [
                    timestamp_str, int(sim_time), zone_id, zinfo["name"],
                    veh_count, avail, cap, occ_pct,
                    active_count, interval_entered, interval_exited,
                    cumulative_entered, cumulative_exited,
                    p_starts, p_ends,
                    tot_parked, tot_unparked,
                    z_teleports,
                    traffic_density, round(avg_speed, 1)
                ]
                writer.writerow(row)

                mongo_doc = {
                    "timestamp": sim_clock,
                    "sim_time_sec": int(sim_time),
                    "zone_id": zone_id,
                    "zone_name": zinfo["name"],
                    "occupied_slots": veh_count,
                    "available_slots": avail,
                    "capacity": cap,
                    "occupancy_percentage": occ_pct,
                    "active_vehicles": active_count,
                    "entry_count": interval_entered,
                    "exit_count": interval_exited,
                    "cumulative_entered": cumulative_entered,
                    "cumulative_exited": cumulative_exited,
                    "zone_parking_starts": p_starts,
                    "zone_parking_ends": p_ends,
                    "cumulative_parked": tot_parked,
                    "cumulative_unparked": tot_unparked,
                    "zone_teleports": z_teleports,
                    "traffic_density": traffic_density,
                    "avg_speed_kmh": round(avg_speed, 1),
                    "run_id": run_id,
                    "is_simulated": True
                }
                records.append(mongo_doc)
                current_zone_summaries.append({
                    "zone_id": zone_id,
                    "name": zinfo["name"],
                    "occupied": veh_count,
                    "available": avail,
                    "capacity": cap,
                    "occupancyRate": occ_pct,
                    "parkingStarts": p_starts,
                    "parkingEnds": p_ends,
                    "totalParked": tot_parked,
                    "totalUnparked": tot_unparked
                })

                # Reset per-interval zone parking event counters
                interval_parking_starts[zone_id] = 0
                interval_parking_ends[zone_id] = 0

            # Reset global interval counters after recording all zones
            interval_entered = 0
            interval_exited = 0
            interval_teleported = 0

            # Flush batch to MongoDB periodically
            if mongo_available and len(records) >= 100:
                db["simulated_traffic_data"].insert_many(records)
                records.clear()

            # Update live simulation status
            if mongo_available:
                db["simulation_status"].update_one(
                    {"_id": "current_status"},
                    {"$set": {
                        "status": "RUNNING",
                        "currentSimTime": timestamp_str,
                        "sim_time_sec": int(sim_time),
                        "active_vehicles": active_count,
                        "total_entered": cumulative_entered,
                        "total_exited": cumulative_exited,
                        "total_teleported": cumulative_teleported,
                        "traffic_density": traffic_density,
                        "avg_speed_kmh": round(avg_speed, 1),
                        "zone_summaries": current_zone_summaries,
                        "runId": run_id,
                        "lastUpdated": datetime.now()
                    }},
                    upsert=True
                )

        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                sim_time = traci.simulation.getTime()
                step_count += 1

                # 1. Global entry / exit (departure into network, complete trip arrival)
                step_departed_ids = traci.simulation.getDepartedIDList()
                step_arrived_ids = traci.simulation.getArrivedIDList()
                step_departed = len(step_departed_ids)
                step_arrived = len(step_arrived_ids)

                cumulative_entered += step_departed
                cumulative_exited += step_arrived
                interval_entered += step_departed
                interval_exited += step_arrived

                # Clean arrived vehicles from tracking dictionary
                for avid in step_arrived_ids:
                    veh_parking_zone.pop(avid, None)

                # 2. Teleports (vehicles vaporized or relocated due to jam/overflow)
                step_starting_teleports = traci.simulation.getStartingTeleportIDList()
                if step_starting_teleports:
                    cumulative_teleported += len(step_starting_teleports)
                    interval_teleported += len(step_starting_teleports)
                    for vid in step_starting_teleports:
                        try:
                            lane_id = traci.vehicle.getLaneID(vid)
                            zid = lane_to_zone.get(lane_id)
                            if zid:
                                zone_teleports[zid] += 1
                        except Exception:
                            pass

                # 3. Verified Parking Events: parking start and parking end
                step_parking_starts = traci.simulation.getParkingStartingVehiclesIDList()
                step_parking_ends = traci.simulation.getParkingEndingVehiclesIDList()

                if step_parking_starts:
                    for vid in step_parking_starts:
                        target_zone = None
                        for zid in capacities:
                            try:
                                if vid in traci.parkingarea.getVehicleIDs(zid):
                                    target_zone = zid
                                    break
                            except Exception:
                                pass

                        if not target_zone:
                            try:
                                stops = traci.vehicle.getStops(vid)
                                if stops and len(stops) > 0:
                                    target_zone = stops[0].stoppingPlaceID
                            except Exception:
                                pass

                        if target_zone and target_zone in capacities:
                            veh_parking_zone[vid] = target_zone
                            interval_parking_starts[target_zone] += 1
                            cumulative_parked[target_zone] += 1

                if step_parking_ends:
                    for vid in step_parking_ends:
                        # 1. Look up from exact parking start tracking
                        target_zone = veh_parking_zone.pop(vid, None)
                        # 2. Fallback to current vehicle lane if not tracked
                        if not target_zone:
                            try:
                                lane_id = traci.vehicle.getLaneID(vid)
                                target_zone = lane_to_zone.get(lane_id)
                            except Exception:
                                pass

                        if target_zone and target_zone in capacities:
                            interval_parking_ends[target_zone] += 1
                            cumulative_unparked[target_zone] += 1

                if max_steps and step_count >= max_steps:
                    print(f"Reached max requested steps: {max_steps}")
                    break

                # Telemetry Sampling Interval
                if step_count % sample_interval == 0:
                    sample_and_flush_telemetry(sim_time)

            # Ensure final state is sampled if there were steps since last interval
            if step_count % sample_interval != 0:
                sample_and_flush_telemetry(traci.simulation.getTime())

        except KeyboardInterrupt:
            print("\nSimulation interrupted by user.")
        finally:
            traci.close()

    # Flush remaining mongo records
    if mongo_available and len(records) > 0:
        db["simulated_traffic_data"].insert_many(records)

    # Finalize status
    if mongo_available:
        db["simulation_status"].update_one(
            {"_id": "current_status"},
            {"$set": {
                "status": "COMPLETED",
                "completedAt": datetime.now(),
                "totalSteps": step_count,
                "totalEntered": cumulative_entered,
                "totalExited": cumulative_exited,
                "totalTeleported": cumulative_teleported,
                "runId": run_id,
                "outputFile": "output/occupancy_data.csv"
            }},
            upsert=True
        )

    print(f"\nSimulation finished! Total steps: {step_count}.")
    print(f"Cumulative Entered: {cumulative_entered}, Exited: {cumulative_exited}, Teleported: {cumulative_teleported}")
    print(f"Total Verified Parked Across Zones: {sum(cumulative_parked.values())}")
    print(f"Data logged to {csv_file}")
    if mongo_available:
        print("Logged simulation telemetry to MongoDB database 'campus_parking' -> 'simulated_traffic_data'")

if __name__ == "__main__":
    use_gui = "--gui" in sys.argv
    max_steps = 1500 if "--quick" in sys.argv else None
    seed = 42
    if "--seed" in sys.argv:
        try:
            s_idx = sys.argv.index("--seed") + 1
            seed = int(sys.argv[s_idx])
        except Exception:
            seed = 42
    run(use_gui=use_gui, max_steps=max_steps, seed=seed)

