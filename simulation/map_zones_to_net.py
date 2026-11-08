import os
import sumolib

def analyze_and_map():
    net_path = os.path.join(os.path.dirname(__file__), "campus.net.xml")
    net = sumolib.net.readNet(net_path)
    print(f"Network loaded: {len(net.getEdges())} edges, {len(net.getNodes())} nodes")

    # IIT ISM Dhanbad coordinates for landmark zones:
    landmarks = {
        "zone_main_gate": ("Main Gate Parking", 86.4412, 23.8145),
        "zone_sac": ("SAC (Student Activity Centre)", 86.4385, 23.8128),
        "zone_nlhc": ("NLHC (New Lecture Hall Complex)", 86.4415, 23.8155),
        "zone_library": ("Central Library", 86.4420, 23.8162),
        "zone_nac": ("NAC (New Academic Complex)", 86.4428, 23.8168),
        "zone_cse": ("CSE Department", 86.4410, 23.8172),
        "zone_health_centre": ("Health Centre", 86.4402, 23.8138),
        "zone_i2h": ("I2H Innovation Hub", 86.4435, 23.8150),
        "zone_academic_complex": ("Heritage Academic Complex", 86.4425, 23.8140),
        "zone_amber": ("Amber Hostel", 86.4430, 23.8185),
        "zone_aquamarine": ("Aquamarine Hostel", 86.4442, 23.8192),
        "zone_mechanical": ("Mechanical Engineering Dept", 86.4398, 23.8148),
        "zone_enviro": ("Environmental Science Dept", 86.4405, 23.8158),
        "zone_oat": ("OAT (Open Air Theatre)", 86.4395, 23.8122),
        # Entry/Exit Gates
        "gate_main": ("Main Campus Gate (Saraidheela/Police Line Rd)", 86.4418, 23.8135),
        "gate_ruby": ("Ruby Gate (West Campus Entrance)", 86.4365, 23.8140),
        "gate_north": ("North Gate (Barwadda Connector)", 86.4450, 23.8210),
    }

    zone_edge_map = {}
    print("\n--- Mapping Landmarks to Real Network Edges ---")
    for zone_id, (desc, lon, lat) in landmarks.items():
        x, y = net.convertLonLat2XY(lon, lat)
        nearby = net.getNeighboringEdges(x, y, r=250)
        # Filter for edges that allow passenger or motorcycle (or general traffic)
        candidates = [e for e, d in nearby if not e.isSpecial() and (e.allows("passenger") or e.allows("motorcycle") or not e.getPermissions())]
        if not candidates:
            # Fallback to any closest non-special edge
            candidates = [e for e, d in nearby if not e.isSpecial()]

        if candidates:
            best_edge = candidates[0]
            lane_count = best_edge.getLaneNumber()
            length = best_edge.getLength()
            print(f"[{zone_id}] {desc} -> Edge {best_edge.getID()} (length: {length:.1f}m, lanes: {lane_count})")
            zone_edge_map[zone_id] = {
                "name": desc,
                "edge_id": best_edge.getID(),
                "lane_id": f"{best_edge.getID()}_0",
                "length": length,
                "x": x,
                "y": y,
                "lon": lon,
                "lat": lat
            }
        else:
            print(f"WARNING: No edge found for {zone_id} within 250m!")

    return zone_edge_map

if __name__ == "__main__":
    analyze_and_map()
