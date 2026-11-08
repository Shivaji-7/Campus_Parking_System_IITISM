"""
Check whether 517026181 (Ruby Gate spur roads) need to be enabled.
Ruby Gate incoming connections show:
  <- -517026181#2 and <- 517026181#1  

Also check OSM ways 517026171, 517026172, 517026175, 517026176, 517026189
to determine if they are needed as connector roads to campus zones.
"""
import xml.etree.ElementTree as ET
import sumolib

net = sumolib.net.readNet('campus.net.xml')
print('Network loaded.')

# Check reachability from gate_main and gate_north to all 6 zero-route zones
# after disabling service edges that are cycleways/private
gate_edges = {
    'gate_main': '-1031896971#0',
    'gate_north': '-1029296863',
    'gate_ruby': '-1031143232',
}

dest_zones = {
    'zone_main_gate': '-517026169#0',
    'zone_health_centre': '517026174',
    'zone_i2h': '-991056586#1',
    'zone_library': '-991056586#2',
    'zone_nac': '991056586#2',
    'zone_academic_complex': '-517026169#5',
}

print()
print('=== Route reachability: gate -> restricted zone ===')
for gate_name, gate_id in gate_edges.items():
    gate_edge = net.getEdge(gate_id)
    for zone_name, zone_id in dest_zones.items():
        try:
            zone_edge = net.getEdge(zone_id)
            path, cost = net.getShortestPath(gate_edge, zone_edge)
            if path is not None:
                # Show edges and their types
                edge_types = [e.getType() for e in path]
                print(f'  {gate_name} -> {zone_name}: path_len={len(path)} cost={cost:.1f}')
                # Check if any restricted types
                restricted = [e.getID() for e in path if e.getLane(0).getAllowed() == set(['pedestrian', 'delivery', 'bicycle'])]
                if restricted:
                    print(f'    BLOCKED by service edges: {restricted[:3]}...')
                else:
                    print(f'    PATH CLEAR: types={set(edge_types)}')
            else:
                print(f'  {gate_name} -> {zone_name}: NO PATH FOUND')
        except Exception as ex:
            print(f'  {gate_name} -> {zone_name}: ERROR: {ex}')
