import os
import random
import subprocess
import sumolib

def build_network_elements():
    net_path = os.path.join(os.path.dirname(__file__), "campus.net.xml")
    net = sumolib.net.readNet(net_path)
    print(f"Network loaded: {len(net.getEdges())} edges, {len(net.getNodes())} nodes")

    # 14 authentic zones on IIT (ISM) Dhanbad campus
    landmarks = [
        {"id": "zone_main_gate", "name": "Main Gate Parking", "lon": 86.4412, "lat": 23.8145, "cap": 25},
        {"id": "zone_sac", "name": "SAC Parking", "lon": 86.4385, "lat": 23.8128, "cap": 20},
        {"id": "zone_nlhc", "name": "NLHC Complex Parking", "lon": 86.4415, "lat": 23.8155, "cap": 30},
        {"id": "zone_library", "name": "Central Library Parking", "lon": 86.4420, "lat": 23.8162, "cap": 25},
        {"id": "zone_nac", "name": "NAC Building Parking", "lon": 86.4428, "lat": 23.8168, "cap": 25},
        {"id": "zone_cse", "name": "CSE Department Parking", "lon": 86.4410, "lat": 23.8172, "cap": 15},
        {"id": "zone_health_centre", "name": "Health Centre Parking", "lon": 86.4402, "lat": 23.8138, "cap": 15},
        {"id": "zone_i2h", "name": "I2H Innovation Hub Parking", "lon": 86.4435, "lat": 23.8150, "cap": 20},
        {"id": "zone_academic_complex", "name": "Academic Complex Parking", "lon": 86.4425, "lat": 23.8140, "cap": 25},
        {"id": "zone_amber", "name": "Amber Hostel Parking", "lon": 86.4430, "lat": 23.8185, "cap": 20},
        {"id": "zone_aquamarine", "name": "Aquamarine Hostel Parking", "lon": 86.4442, "lat": 23.8192, "cap": 20},
        {"id": "zone_mechanical", "name": "Mechanical Dept Parking", "lon": 86.4398, "lat": 23.8148, "cap": 15},
        {"id": "zone_enviro", "name": "Environmental Dept Parking", "lon": 86.4405, "lat": 23.8158, "cap": 15},
        {"id": "zone_oat", "name": "OAT Grounds Parking", "lon": 86.4395, "lat": 23.8122, "cap": 20},
    ]

    # Campus Entry/Exit points
    gates = [
        {"id": "gate_main", "name": "Main Gate (Saraidheela/Police Line Rd)", "lon": 86.4418, "lat": 23.8135},
        {"id": "gate_ruby", "name": "Ruby Gate (West Campus Link)", "lon": 86.4365, "lat": 23.8140},
        {"id": "gate_north", "name": "North Gate (Barwadda Connector)", "lon": 86.4450, "lat": 23.8210},
    ]

    used_edges = set()
    zone_data = []

    for lm in landmarks:
        x, y = net.convertLonLat2XY(lm["lon"], lm["lat"])
        nearby = net.getNeighboringEdges(x, y, r=300)
        nearby.sort(key=lambda item: item[1])

        selected_edge = None
        for edge, dist in nearby:
            if edge.isSpecial():
                continue
            if edge.getLength() >= 25.0 and edge.getID() not in used_edges:
                selected_edge = edge
                break

        if not selected_edge:
            for edge, dist in nearby:
                if not edge.isSpecial() and edge.getLength() >= 20.0:
                    selected_edge = edge
                    break

        if selected_edge:
            used_edges.add(selected_edge.getID())
            lane_id = f"{selected_edge.getID()}_0"
            edge_len = selected_edge.getLength()
            start_pos = 2.0
            end_pos = min(edge_len - 2.0, max(start_pos + 12.0, edge_len * 0.9))

            zone_data.append({
                "id": lm["id"],
                "name": lm["name"],
                "edge": selected_edge.getID(),
                "edge_obj": selected_edge,
                "lane": lane_id,
                "length": edge_len,
                "startPos": round(start_pos, 1),
                "endPos": round(end_pos, 1),
                "capacity": lm["cap"]
            })
            print(f"Mapped {lm['id']} -> {selected_edge.getID()} (length: {edge_len:.1f}m, cap: {lm['cap']})")

    # Locate Gate Edges
    gate_edges = []
    for g in gates:
        x, y = net.convertLonLat2XY(g["lon"], g["lat"])
        nearby = net.getNeighboringEdges(x, y, r=250)
        valid = [e for e, d in nearby if not e.isSpecial() and e.getLength() >= 20.0]
        if valid:
            gate_edges.append({"id": g["id"], "name": g["name"], "edge": valid[0].getID(), "edge_obj": valid[0]})
            print(f"Gate {g['id']} -> Edge {valid[0].getID()}")

    # 1. Create campus_parking.add.xml
    add_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<additional>']
    for z in zone_data:
        add_xml.append(
            f'    <parkingArea id="{z["id"]}" lane="{z["lane"]}" startPos="{z["startPos"]}" '
            f'endPos="{z["endPos"]}" roadSideCapacity="{z["capacity"]}" name="{z["name"]}"/>'
        )
    add_xml.append('</additional>\n')

    add_path = os.path.join(os.path.dirname(__file__), "campus_parking.add.xml")
    with open(add_path, "w", encoding="utf-8") as f:
        f.write("\n".join(add_xml))
    print(f"Saved {add_path}")

    # 2. Build Trips with valid paths and sorted departure
    trips = []
    vtypes = ["twoWheeler", "facultyCar", "studentCar", "visitorCar", "adminEV"]
    vtype_weights = [0.45, 0.20, 0.20, 0.10, 0.05]

    trip_count = 0
    # Simulate time 27000 (07:30) to 66600 (18:30)
    for _ in range(600):
        period = random.choices(["morning_peak", "midday", "evening_peak", "offpeak"], weights=[0.45, 0.20, 0.25, 0.10])[0]
        if period == "morning_peak":
            depart = random.randint(28800, 36000) # 08:00 - 10:00
        elif period == "midday":
            depart = random.randint(36000, 57600) # 10:00 - 16:00
        elif period == "evening_peak":
            depart = random.randint(57600, 64800) # 16:00 - 18:00
        else:
            depart = random.randint(27000, 28800) # 07:30 - 08:00

        vtype = random.choices(vtypes, weights=vtype_weights)[0]
        gate = random.choice(gate_edges)
        target_zone = random.choice(zone_data)

        # Check path reachability
        path, cost = net.getShortestPath(gate["edge_obj"], target_zone["edge_obj"])
        if path is not None and len(path) > 0:
            trip_count += 1
            parking_duration = random.randint(1800, 14400)
            trips.append({
                "id": f"veh_{trip_count}",
                "type": vtype,
                "depart": depart,
                "from": gate["edge"],
                "to": target_zone["edge"],
                "zone_id": target_zone["id"],
                "duration": parking_duration
            })

    # Sort trips strictly by depart time
    trips.sort(key=lambda t: t["depart"])
    print(f"Generated {len(trips)} verified reachable trips")

    trips_path = os.path.join(os.path.dirname(__file__), "campus.trips.xml")
    trips_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        '    <!-- Vehicle Types: Cars, Two-Wheelers, EVs, Visitors -->',
        '    <vType id="twoWheeler" vClass="motorcycle" length="2.2" width="0.9" maxSpeed="11.11" accel="2.6" decel="4.5" color="240,180,41"/>',
        '    <vType id="facultyCar" vClass="passenger" length="4.5" width="1.8" maxSpeed="11.11" accel="2.0" decel="4.5" color="59,130,246"/>',
        '    <vType id="studentCar" vClass="passenger" length="4.2" width="1.8" maxSpeed="11.11" accel="2.2" decel="4.5" color="14,165,233"/>',
        '    <vType id="visitorCar" vClass="passenger" length="4.8" width="1.9" maxSpeed="11.11" accel="1.8" decel="4.5" color="249,115,22"/>',
        '    <vType id="adminEV" vClass="evehicle" length="4.3" width="1.8" maxSpeed="11.11" accel="2.5" decel="4.5" color="34,197,94"/>',
        ''
    ]

    for t in trips:
        trips_xml.append(
            f'    <trip id="{t["id"]}" type="{t["type"]}" depart="{t["depart"]}" from="{t["from"]}" to="{t["to"]}">'
            f'        <stop parkingArea="{t["zone_id"]}" duration="{t["duration"]}"/>'
            f'    </trip>'
        )
    trips_xml.append('</routes>\n')

    with open(trips_path, "w", encoding="utf-8") as f:
        f.write("\n".join(trips_xml))
    print(f"Saved sorted trips to {trips_path}")

    # Now run duarouter to compile routes
    duarouter_bin = r"C:\Users\shivaji\AppData\Roaming\Python\Python313\site-packages\sumo\bin\duarouter.exe"
    routes_path = os.path.join(os.path.dirname(__file__), "campus_demand.rou.xml")
    cmd = [
        duarouter_bin,
        "-n", net_path,
        "--additional-files", add_path,
        "--route-files", trips_path,
        "-o", routes_path,
        "--ignore-errors"
    ]
    print("Running duarouter to build campus_demand.rou.xml...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("duarouter finished successfully!")
    else:
        print(f"duarouter warning/error (code {res.returncode}):", res.stderr[:300])

    return True

if __name__ == "__main__":
    build_network_elements()
