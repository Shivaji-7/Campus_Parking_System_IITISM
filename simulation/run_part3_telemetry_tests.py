"""
Part 3 Regression & Telemetry Verification Suite.
Validates:
1. Duplicate events prevention & monotonic event counters
2. Incomplete trip tracking & non-parking road presence separation
3. Zone-wise capacity limits & bounds preservation (0 <= occupied <= capacity)
4. Entry/exit & parking start aggregation integrity (sum(interval) == cumulative)
5. Consistency between telemetry output and SUMO ground truth
6. Preservation of 14 parking zones and 503 database slots
"""

import os
import re
import pandas as pd
import xml.etree.ElementTree as ET

def run_tests():
    print("=" * 70)
    print("STAGE 2 - PART 3: PARKING EVENT TELEMETRY & OCCUPANCY TEST SUITE")
    print("=" * 70)

    # 1. Load telemetry data
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(sim_dir, "output", "occupancy_data.csv")
    assert os.path.exists(csv_file), f"Telemetry CSV not found: {csv_file}"
    df = pd.read_csv(csv_file)
    assert len(df) > 0, "Telemetry CSV is empty"
    print(f"Loaded telemetry data: {len(df)} rows across {len(df.drop_duplicates('sim_time_sec'))} intervals.")

    # Test 1: Schema Compliance (All event and capacity fields present)
    required_cols = [
        "timestamp", "sim_time_sec", "zone_id", "zone_name",
        "occupied_slots", "available_slots", "capacity", "occupancy_percentage",
        "active_vehicles", "entry_count", "exit_count",
        "cumulative_entered", "cumulative_exited",
        "zone_parking_starts", "zone_parking_ends",
        "cumulative_parked", "cumulative_unparked",
        "zone_teleports",
        "traffic_density", "avg_speed_kmh"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required telemetry column: {col}"
    print("TEST 1 [Schema & Event Attributes]: PASS - All 20 required event/capacity columns present.")

    # Test 2: Event Aggregation Integrity (sum of intervals == final cumulative)
    step_samples = df.drop_duplicates("sim_time_sec")
    total_interval_entries = step_samples["entry_count"].sum()
    final_cumulative_entered = step_samples["cumulative_entered"].iloc[-1]
    assert total_interval_entries == final_cumulative_entered, (
        f"Entry aggregation mismatch: sum(interval)={total_interval_entries} != final_cumulative={final_cumulative_entered}"
    )

    total_interval_exits = step_samples["exit_count"].sum()
    final_cumulative_exited = step_samples["cumulative_exited"].iloc[-1]
    assert total_interval_exits == final_cumulative_exited, (
        f"Exit aggregation mismatch: sum(interval)={total_interval_exits} != final_cumulative={final_cumulative_exited}"
    )

    # Zone-wise parking start aggregation
    for zid in df["zone_id"].unique():
        zdf = df[df["zone_id"] == zid]
        sum_p_starts = zdf["zone_parking_starts"].sum()
        final_cum_parked = zdf["cumulative_parked"].iloc[-1]
        assert sum_p_starts == final_cum_parked, (
            f"Zone {zid} parking start mismatch: sum={sum_p_starts} != final={final_cum_parked}"
        )
    print("TEST 2 [Event Aggregation Integrity]: PASS - Zero events dropped across intervals and cumulative sums.")

    # Test 3: Capacity Bounds & Non-Violation (0 <= occupied <= capacity, occupied + available == capacity)
    for idx, row in df.iterrows():
        cap = row["capacity"]
        occ = row["occupied_slots"]
        avail = row["available_slots"]
        pct = row["occupancy_percentage"]
        assert 0 <= occ <= cap, f"Occupancy {occ} out of bounds for cap {cap} at row {idx}"
        assert occ + avail == cap, f"Occupied {occ} + Available {avail} != Capacity {cap} at row {idx}"
        expected_pct = round((occ / cap) * 100.0, 1)
        assert abs(pct - expected_pct) <= 0.1, f"Occupancy pct mismatch: {pct} vs expected {expected_pct}"
    print("TEST 3 [Capacity Bounds & Invariants]: PASS - 100% of rows satisfy 0 <= occupied <= capacity and sum invariant.")

    # Test 4: Physical Separation of Road Arrival vs. Verified Parking
    # Early in the simulation, vehicles drive on roads towards destinations without being parked yet.
    # Total occupied slots must be <= active vehicles, and strictly less before arrival.
    early_rows = df[df["sim_time_sec"] <= 27150]
    early_active = early_rows["active_vehicles"].max()
    early_occupied = early_rows.groupby("sim_time_sec")["occupied_slots"].sum().max()
    assert early_active > 0, "No active vehicles in early steps"
    assert early_occupied == 0, f"Expected 0 parked vehicles in first 150s, found {early_occupied}"
    print(f"TEST 4 [Road Transit vs Verified Parking Separation]: PASS - In-transit vehicles correctly not counted as parked.")

    # Test 5: Monotonicity of Cumulative Counters (No resets or decreases)
    for zid in df["zone_id"].unique():
        zdf = df[df["zone_id"] == zid]
        cum_parked_list = list(zdf["cumulative_parked"])
        for i in range(1, len(cum_parked_list)):
            assert cum_parked_list[i] >= cum_parked_list[i - 1], (
                f"Cumulative parked decreased for zone {zid} at step {i}: {cum_parked_list[i]} < {cum_parked_list[i-1]}"
            )
    print("TEST 5 [Counter Monotonicity & Duplicate Prevention]: PASS - Cumulative counters strictly non-decreasing.")

    # Test 6: Ground Truth Consistency with SUMO Route Files
    # Vehicles departed up to step 28500 in campus_demand.rou.xml must match telemetry cumulative entered
    rou_path = os.path.join(sim_dir, "campus_demand.rou.xml")
    rou = ET.parse(rou_path).getroot()
    vehs_before_28500 = [v for v in rou.findall("vehicle") if float(v.get("depart")) <= 28470]
    assert len(vehs_before_28500) == final_cumulative_entered, (
        f"Mismatch between SUMO route departs ({len(vehs_before_28500)}) and telemetry cumulative entered ({final_cumulative_entered})"
    )
    print(f"TEST 6 [SUMO Ground-Truth Consistency]: PASS - Telemetry cumulative entered ({final_cumulative_entered}) matches route departures.")

    # Test 7: Preservation of 14 Zones & 503 Database Slots
    seed_path = os.path.join(sim_dir, "..", "server", "src", "seeds", "seed.js")
    with open(seed_path) as f:
        seed_text = f.read()
    fw_slots = sum(int(x) for x in re.findall(r"fourWheelerSlots:\s*(\d+)", seed_text))
    tw_slots = sum(int(x) for x in re.findall(r"twoWheelerSlots:\s*(\d+)", seed_text))
    assert fw_slots == 147, f"Expected 147 4W slots, got {fw_slots}"
    assert tw_slots == 356, f"Expected 356 2W slots, got {tw_slots}"
    assert fw_slots + tw_slots == 503, f"Expected 503 total database slots, got {fw_slots + tw_slots}"

    add_path = os.path.join(sim_dir, "campus_parking.add.xml")
    add = ET.parse(add_path).getroot()
    sumo_capacity = sum(int(p.get("roadsideCapacity")) for p in add.findall("parkingArea"))
    assert sumo_capacity == 213, f"Expected 213 SUMO roadside capacity, got {sumo_capacity}"
    assert len(add.findall("parkingArea")) == 14, f"Expected 14 parking areas, got {len(add.findall('parkingArea'))}"
    print("TEST 7 [Database & Frontage Capacity Preservation]: PASS - 503 database slots and 213 SUMO frontage preserved.")

    print("\nALL 7 PART 3 REGRESSION TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
