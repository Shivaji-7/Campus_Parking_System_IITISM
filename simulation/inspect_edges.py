"""Inspect edge permissions for zero-route zones and gate edges."""
import xml.etree.ElementTree as ET

net = ET.parse('campus.net.xml').getroot()
edges = {e.get('id'): e for e in net.findall('edge')}

zero_zones = {
    'zone_main_gate': '-517026169#0',
    'zone_health_centre': '517026174',
    'zone_i2h': '-991056586#1',
    'zone_library': '-991056586#2',
    'zone_nac': '991056586#2',
    'zone_academic_complex': '-517026169#5',
}

gate_edges = {
    'gate_main': '-1031896971#0',
    'gate_ruby': '-1031143232',
    'gate_north': '-1029296863',
}

print('=== GATE EDGES ===')
for name, eid in gate_edges.items():
    e = edges.get(eid)
    if e:
        for l in e.findall('lane'):
            print(f'{name} ({eid}): type={e.get("type")} allow={l.get("allow")} disallow={l.get("disallow")} speed={l.get("speed")} width={l.get("width")} length={l.get("length")}')

print()
print('=== DESTINATION ZONE EDGES ===')
for zone, eid in zero_zones.items():
    e = edges.get(eid)
    if e:
        for l in e.findall('lane'):
            print(f'{zone} ({eid}): type={e.get("type")} allow={l.get("allow")} disallow={l.get("disallow")} speed={l.get("speed")} width={l.get("width")} length={l.get("length")}')

print()
print('=== REVERSE EDGES OF DESTINATION ZONES ===')
# Check if there is a reverse/parallel edge for these service roads  
reverse_map = {
    '-517026169#0': '517026169#0',
    '517026174': '-517026174',
    '-991056586#1': '991056586#1',
    '-991056586#2': '991056586#2',  # same edge reversed
    '991056586#2': '-991056586#2',
    '-517026169#5': '517026169#5',
}
for eid, rev_eid in reverse_map.items():
    e = edges.get(rev_eid)
    if e:
        for l in e.findall('lane'):
            print(f'Reverse of {eid} -> {rev_eid}: type={e.get("type")} allow={l.get("allow")} disallow={l.get("disallow")}')
    else:
        print(f'Reverse of {eid} -> {rev_eid}: NOT FOUND')

print()
print('=== SERVICE EDGE SAMPLE ===')
# Show a sample of highway.service edges to confirm the pattern
service_edges = [e for e in net.findall('edge') if e.get('type') == 'highway.service']
print(f'Total highway.service edges: {len(service_edges)}')
for e in service_edges[:5]:
    for l in e.findall('lane'):
        print(f'  edge {e.get("id")}: allow={l.get("allow")} speed={l.get("speed")} width={l.get("width")} length={l.get("length")}')

print()
print('=== HIGHWAY.RESIDENTIAL SAMPLE (working zones) ===')
working_edges = {'zone_sac': '991055730', 'zone_amber': '1031061562#3', 'zone_enviro': '-517026179#5'}
for zone, eid in working_edges.items():
    e = edges.get(eid)
    if e:
        for l in e.findall('lane'):
            print(f'{zone} ({eid}): type={e.get("type")} allow={l.get("allow")} speed={l.get("speed")} width={l.get("width")}')
