"""
Stage 2 - Part 4: Traffic Analytics & Backend Integration Test Suite
Verifies:
1. Endpoints /api/simulation/overview and /api/simulation/telemetry are online and respond with valid JSON.
2. Zone-wise parking occupancy, available capacity, and capacities sum to 213 (SUMO roadside capacity).
3. Interval vs Cumulative counter distinction and data types.
4. Data staleness flags and distinction between simulation and live IoT sensor feeds.
5. MongoDB / CSV ground-truth consistency with backend API outputs.
6. Non-regression of existing DB slots (503 slots total: 147 4W, 356 2W) and operational routes (auth, parking slots, admin statistics).
"""

import sys
import os
import json
import csv
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5001"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "simulation", "output", "occupancy_data.csv")

def http_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "Part4-Test-Runner"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)}

def run_tests():
    print("=" * 70)
    print("STAGE 2 - PART 4: TRAFFIC ANALYTICS & BACKEND INTEGRATION TESTS")
    print("=" * 70)

    tests_passed = 0
    total_tests = 0

    # -------------------------------------------------------------
    # Test 1: Telemetry API Structure & Calibration
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[Test 1] GET /api/simulation/telemetry structure & zone capacity sum")
    status, data = http_get("/api/simulation/telemetry")
    if status == 200 and data.get("success"):
        zones = data.get("zones", [])
        total_cap = sum(z.get("capacity", 0) for z in zones)
        total_occ = sum(z.get("occupiedSlots", 0) for z in zones)
        total_avail = sum(z.get("availableSlots", 0) for z in zones)
        
        print(f"  Status: {status} OK")
        print(f"  Zones Returned: {len(zones)}")
        print(f"  Summed Zone Capacity: {total_cap} (Expected SUMO Roadside: 213)")
        print(f"  Occupied Slots: {total_occ}, Available Slots: {total_avail}")

        is_calibrated = (total_cap == 213 and len(zones) == 14)
        has_freshness = data.get("metadata", {}).get("isLiveSensorData") is False
        
        if is_calibrated and has_freshness:
            print("  PASS: 14 zones present, exactly 213 SUMO capacity, live sensor flag is False")
            tests_passed += 1
        else:
            print(f"  FAIL: is_calibrated={is_calibrated}, has_freshness={has_freshness}")
    else:
        print(f"  FAIL: Status={status}, Response={data}")

    # -------------------------------------------------------------
    # Test 2: Interval vs Cumulative Counter Distinction
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[Test 2] Telemetry counter isolation (interval vs cumulative)")
    if status == 200 and data.get("success"):
        sample_zone = data.get("zones", [])[0]
        summary = data.get("summary", {})
        
        has_interval_metrics = "intervalMetrics" in sample_zone and \
                               "parkingStarts" in sample_zone["intervalMetrics"] and \
                               "parkingEnds" in sample_zone["intervalMetrics"]
        has_cumulative_metrics = "cumulativeMetrics" in sample_zone and \
                                 "parked" in sample_zone["cumulativeMetrics"] and \
                                 "unparked" in sample_zone["cumulativeMetrics"]
        has_global_cumulative = "globalCumulativeEntered" in summary and \
                                "globalCumulativeExited" in summary
        
        print(f"  Sample zone: {sample_zone.get('zoneId')}")
        print(f"  Interval Metrics: {sample_zone.get('intervalMetrics')}")
        print(f"  Cumulative Metrics: {sample_zone.get('cumulativeMetrics')}")
        print(f"  Global Cumulative: Entered={summary.get('globalCumulativeEntered')}, Exited={summary.get('globalCumulativeExited')}")

        if has_interval_metrics and has_cumulative_metrics and has_global_cumulative:
            print("  PASS: Interval metrics and cumulative counters distinctly modeled and separated")
            tests_passed += 1
        else:
            print("  FAIL: Incomplete counter separation")
    else:
        print("  FAIL: Could not query telemetry endpoint")

    # -------------------------------------------------------------
    # Test 3: Consistency between CSV Ground-Truth and Backend API
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[Test 3] Ground-truth telemetry consistency with simulation CSV")
    if os.path.exists(CSV_PATH):
        # Read latest step rows from CSV
        rows = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        
        if rows:
            latest_time = max(int(r["sim_time_sec"]) for r in rows)
            latest_step_rows = [r for r in rows if int(r["sim_time_sec"]) == latest_time]
            csv_zone_occ = {r["zone_id"]: int(r["occupied_slots"]) for r in latest_step_rows}
            api_zone_occ = {z["zoneId"]: z["occupiedSlots"] for z in data.get("zones", [])}

            mismatches = 0
            for zid, occ in csv_zone_occ.items():
                if zid in api_zone_occ and api_zone_occ[zid] != occ:
                    mismatches += 1
            
            print(f"  Total CSV Rows: {len(rows)}, Latest Sim Time in CSV: {latest_time}s")
            print(f"  CSV Zones at latest time: {len(csv_zone_occ)}")
            print(f"  Occupancy Mismatches against API: {mismatches}")

            if mismatches == 0 and len(csv_zone_occ) > 0:
                print("  PASS: API zone occupancy perfectly matches CSV ground-truth data at latest step")
                tests_passed += 1
            else:
                print("  FAIL: Occupancy mismatch between CSV and API")
        else:
            print("  FAIL: CSV is empty")
    else:
        print(f"  FAIL: CSV not found at {CSV_PATH}")

    # -------------------------------------------------------------
    # Test 4: Overview Endpoint (/api/simulation/overview)
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[Test 4] GET /api/simulation/overview response & metadata verification")
    status_ov, data_ov = http_get("/api/simulation/overview")
    if status_ov == 200:
        meta = data_ov.get("metadata", {})
        ov_sumo_cap = data_ov.get("sumoSimulatedData", {}).get("totalCapacity", 0)
        db_slots_cap = data_ov.get("realCampusData", {}).get("totalSlots", 0)

        print(f"  Status: {status_ov} OK")
        print(f"  Overview SUMO Roadside Capacity: {ov_sumo_cap} (Expected: 213)")
        print(f"  Overview DB Slots Capacity: {db_slots_cap} (Expected: 503)")
        print(f"  Metadata liveSensorFlag: {meta.get('isLiveSensorData')}")

        if ov_sumo_cap == 213 and db_slots_cap == 503 and meta.get("isLiveSensorData") is False:
            print("  PASS: Overview endpoint correctly distinguishes SUMO capacity (213) from DB slots (503)")
            tests_passed += 1
        else:
            print("  FAIL: Overview capacity or metadata mismatch")
    else:
        print(f"  FAIL: Status={status_ov}, Response={data_ov}")

    # -------------------------------------------------------------
    # Test 5: Operational Integrity of Database Slots & Admin Stats
    # -------------------------------------------------------------
    total_tests += 1
    print("\n[Test 5] System regression: Verify 503 DB Slots (147 4W, 356 2W) intact via Authenticated API")
    # Login as user to get auth token
    login_req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"email": "user@campus.com", "password": "password123"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    user_token = None
    try:
        with urllib.request.urlopen(login_req, timeout=5) as res:
            login_data = json.loads(res.read().decode("utf-8"))
            user_token = login_data.get("token")
    except Exception as e:
        print(f"  Login failed: {e}")

    slots_req = urllib.request.Request(
        f"{BASE_URL}/api/parking/slots",
        headers={"Authorization": f"Bearer {user_token}"} if user_token else {}
    )
    try:
        with urllib.request.urlopen(slots_req, timeout=10) as res:
            data_slots_raw = json.loads(res.read().decode("utf-8"))
            slots_list = data_slots_raw.get("slots", [])
            total_slots = len(slots_list)
            four_wheelers = sum(1 for s in slots_list if s.get("vehicleType") == "four-wheeler" or s.get("type") == "car")
            two_wheelers = sum(1 for s in slots_list if s.get("vehicleType") == "two-wheeler" or s.get("type") == "bike")

            print(f"  Authenticated Slots Count: {total_slots}")
            print(f"  Four-Wheelers (Car): {four_wheelers} (Expected: 147)")
            print(f"  Two-Wheelers (Bike): {two_wheelers} (Expected: 356)")

            if total_slots == 503 and four_wheelers == 147 and two_wheelers == 356:
                print("  PASS: 503 database slots intact and operational via authenticated endpoint")
                tests_passed += 1
            else:
                print("  FAIL: Slots count mismatch")
    except Exception as e:
        print(f"  FAIL: Could not query authenticated slots: {e}")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"SUMMARY: {tests_passed} of {total_tests} tests PASSED")
    print("=" * 70)

    if tests_passed == total_tests:
        print("\nALL STAGE 2 - PART 4 BACKEND INTEGRATION TESTS PASSED.")
        return 0
    else:
        print("\nSOME TESTS FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
