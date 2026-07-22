import json
from detect_climbs import parse_gpx, calc_stats, find_climbs, categorize
import os

gpx_dir = r'C:\Users\echav\OneDrive\Documentos\GitHub\procyclingstats\web_carreras\volta_portugal_2026\gpx'

# Load existing stages.json
stages_path = os.path.join(os.path.dirname(gpx_dir), 'stages.json')
stages = json.load(open(stages_path, encoding='utf-8'))
stages_by_filename = {s['filename']: s for s in stages}

for f in sorted(os.listdir(gpx_dir)):
    if not f.endswith('.gpx') or 'RETORNO' in f.upper():
        continue
    path = os.path.join(gpx_dir, f)
    coords = parse_gpx(path)
    dist, gain, max_ele, min_ele = calc_stats(coords)
    climbs = find_climbs(coords)
    
    print(f'=== {f} ===')
    print(f'  {dist:.1f}km, +{gain:.0f}m')
    print(f'  Climbs: {len(climbs)}')
    for c in climbs:
        cat = c['category']
        g = c['elevation_gain_m']
        d = c['distance_m']
        a = c['avg_gradient_pct']
        m = c['max_ele_m']
        print(f'    {cat}: +{g:.0f}m, {d:.0f}m, avg {a:.1f}% @ {m:.0f}m')
    print()
    
    if f in stages_by_filename:
        stages_by_filename[f]['climbs'] = climbs

# Update stages.json with climbs
with open(stages_path, 'w', encoding='utf-8') as f:
    json.dump(stages, f, ensure_ascii=False, indent=2)
print('stages.json updated with climbs data')
