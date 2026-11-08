"""
Diagnose why still no routes to 6 zones.
Look at what edges immediately precede the restricted dest zones
and whether there are junction connection elements blocking crossing.

duarouter says: "No connection between edge '-1031896971#0' and edge '-517026169#0' found"
But sumolib finds a path. The difference: sumolib doesn't check permissions,
duarouter does. The junctions themselves (in <connection> elements) also 
have a "tl" permission requirement, but most importantly the JUNCTION EDGES
(internal ":cluster_..." edges) inherit permissions from their endpoint lanes.

Let us check the actual junction edges between working residential streets 
and the patched service streets.
"""
import xml.etree.ElementTree as ET

net = ET.parse('campus.net.xml').getroot()
edges_dict = {e.get('id'): e for e in net.findall('edge')}
connections = net.findall('connection')

# Key question: what are the junction/internal edges connecting residential to service?
# From the connectivity output:
# -517026169#0 has incoming: from=-517026169#1 (service), from=1085560803 (unclassified), from=517026169#0 (service)
# But what does the vehicle type-specific routing see?

# Let's check if internal junction edges (:cluster_...) have permissions
# These are key — they are created from the junction nodes

# Find internal edges (start with ':')
internal_edges = [e for e in net.findall('edge') if e.get('id', '').startswith(':')]
print(f'Total internal (junction) edges: {len(internal_edges)}')

# Check the ones that connect into our restricted zones
# From connectivity output for -517026169#0:
#   from=:5046281246_2, :5046281246_9, :5046281246_3, :5046281246_7

problem_internals = [':5046281246_2', ':5046281246_9', ':5046281246_3', ':5046281246_7',
                     ':5046281250_1', ':5046281250_6', ':5046281250_11', ':5046281250_12',
                     ':9504677030_0', ':9504677030_4', ':9504677030_8',
                     ':9504677030_2', ':9504677030_3', ':9504677030_7',
                     ':5046281262_0', ':5046281262_4', ':5046281262_8']

print()
print('=== Internal junction edges leading INTO restricted zones ===')
for pid in problem_internals:
    e = edges_dict.get(pid)
    if e is not None:
        for l in e.findall('lane'):
            print(f'{pid}: allow={l.get("allow")} disallow={l.get("disallow")}')
    else:
        print(f'{pid}: NOT FOUND')

# Also check connections table: what are the "from" edges for the junction edges
print()
print('=== What edges lead INTO the junction for node 5046281246 (main_gate area)? ===')
for c in connections:
    if c.get('to') == '-517026169#0':
        from_id = c.get('from')
        e = edges_dict.get(from_id)
        etype = e.get('type') if e is not None else 'unknown'
        lane = e.findall('lane')[0] if e is not None else None
        allow = lane.get('allow') if lane is not None else 'unknown'
        print(f'  from={from_id} type={etype} allow={allow}')

print()
print('=== Connections from nearest residential edges ===')
# 1085560803 is unclassified and connects to -517026169#0
# What connects to 1085560803?
for c in connections:
    if c.get('to') == '1085560803' or c.get('from') == '1085560803':
        e = edges_dict.get(c.get('from') or c.get('to'))
        etype = e.get('type') if e is not None else 'unknown'
        print(f'  {c.get("from")} -> {c.get("to")} ({etype})')
