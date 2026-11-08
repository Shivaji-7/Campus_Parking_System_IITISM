"""
Part A Fix - Phase 2: Patch internal junction edges.

The junction internal edges (:node_id_idx) that lead INTO the 6 restricted zones
still have allow="pedestrian delivery bicycle". These must also be patched.

Strategy: Find ALL internal edges that are part of junctions where at least
ONE endpoint edge has been patched to allow motor vehicles.
Specifically, internal edges where:
  - The connection's source edge is now patched (allow contains 'passenger')
  - The connection's destination edge is now patched (allow contains 'passenger')

We update them to match the new permissions.
"""
import xml.etree.ElementTree as ET

NET_FILE = 'campus.net.xml'
NEW_ALLOW = 'passenger motorcycle delivery bicycle pedestrian evehicle'
OLD_ALLOW = 'pedestrian delivery bicycle'

# Target OSM IDs (same as phase 1)
TARGET_OSM_IDS = {
    '517026169', '517026174', '991056586',
    '1031143232', '1031148062', '1031148063',
    '991057338', '1031144175',
}

SKIP_OSM_IDS = {
    '517026190', '1010963507', '1010963508', '1010963509', '1010963510',
    '1031064865', '1031064866', '1031068030',
    '1031097081', '1031097082', '1031097083', '1031097084', '1031097085', '1031097086',
    '1030312998',
}

def osm_id_of_edge(edge_id):
    s = edge_id.lstrip('-')
    return s.split('#')[0]

print(f'Loading {NET_FILE} ...')
tree = ET.parse(NET_FILE)
root = tree.getroot()

edges_dict = {e.get('id'): e for e in root.findall('edge')}
connections = root.findall('connection')

# Build set of edge IDs that are now patched (allow motor vehicles)
patched_edges = set()
for e in root.findall('edge'):
    eid = e.get('id')
    osm_id = osm_id_of_edge(eid)
    etype = e.get('type')
    if etype == 'highway.service' and osm_id in TARGET_OSM_IDS and osm_id not in SKIP_OSM_IDS:
        patched_edges.add(eid)

# For each connection, if BOTH from and to are now patched (or are residential/unclassified),
# find the via (internal) edge and patch it too.
# Actually: if the internal edge's endpoint is a patched edge, patch the internal edge.

# Build mapping: internal_edge -> (from_edge, to_edge) via connections
internal_to_endpoints = {}
for c in connections:
    via = c.get('via')
    if via:
        from_edge = c.get('from')
        to_edge = c.get('to')
        if via not in internal_to_endpoints:
            internal_to_endpoints[via] = []
        internal_to_endpoints[via].append((from_edge, to_edge))

# Find internal edges to patch:
# An internal edge should allow motor vehicles if at least one of its endpoint edges
# (either from or to in the connection) is a patched edge AND the internal lane currently
# has old_allow = 'pedestrian delivery bicycle'
def allows_motor_vehicles(edge_id):
    """Check if an edge allows motor vehicles."""
    if edge_id is None:
        return False
    e = edges_dict.get(edge_id)
    if e is None:
        return False
    for l in e.findall('lane'):
        allow = l.get('allow') or ''
        disallow = l.get('disallow') or ''
        # If allow is None (means all allowed except disallow), or contains passenger
        if allow == '' or 'passenger' in allow:
            return True
    return False

changed_internal = []
for internal_id, endpoints in internal_to_endpoints.items():
    e = edges_dict.get(internal_id)
    if e is None:
        continue
    lanes = e.findall('lane')
    if not lanes:
        continue
    current_allow = lanes[0].get('allow')
    if current_allow != OLD_ALLOW:
        continue  # Already correct or different state
    
    # Check if any endpoint allows motor vehicles
    should_patch = False
    for (from_e, to_e) in endpoints:
        if allows_motor_vehicles(from_e) or allows_motor_vehicles(to_e):
            should_patch = True
            break
    
    if should_patch:
        for lane in lanes:
            lane.set('allow', NEW_ALLOW)
        changed_internal.append(internal_id)

print(f'Internal junction edges patched: {len(changed_internal)}')
print()
# Show examples
for cid in changed_internal[:20]:
    print(f'  Patched: {cid}')
if len(changed_internal) > 20:
    print(f'  ... and {len(changed_internal) - 20} more')

print()
print(f'Writing patched network back to {NET_FILE} ...')
tree.write(NET_FILE, encoding='UTF-8', xml_declaration=True)
print('Done.')

# Append to change log
import os
log_path = os.path.join('output', 'network_permission_changes.csv')
with open(log_path, 'a', encoding='utf-8') as f:
    for cid in changed_internal:
        f.write(f'{cid},(internal junction),{OLD_ALLOW},{NEW_ALLOW}\n')
print(f'Appended {len(changed_internal)} junction edge changes to {log_path}')
