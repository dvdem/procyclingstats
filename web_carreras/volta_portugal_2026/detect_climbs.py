import xml.etree.ElementTree as ET
import math
import json
import os

GPX_NS = {'gpx': 'http://www.topografix.com/GPX/1/1'}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def parse_gpx(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        trkpts = root.findall('.//gpx:trkpt', GPX_NS)
        coords = []
        for pt in trkpts:
            lat = float(pt.get('lat'))
            lon = float(pt.get('lon'))
            ele = pt.find('gpx:ele', GPX_NS)
            ele_val = float(ele.text) if ele is not None and ele.text else None
            coords.append((lat, lon, ele_val))
        return coords
    except Exception as e:
        print(f'Error: {path}: {e}')
        return []

def smooth(arr, window):
    result = []
    for i in range(len(arr)):
        start = max(0, i - window)
        end = min(len(arr), i + window + 1)
        vals = [arr[j] for j in range(start, end) if arr[j] is not None]
        result.append(sum(vals) / len(vals) if vals else None)
    return result

def detect_summits(smooth_arr, min_prominence=30, min_separation=50):
    """Detect summits with minimum prominence and separation."""
    if not smooth_arr:
        return []
    
    peaks = []
    for i in range(2, len(smooth_arr) - 2):
        if smooth_arr[i] is None or smooth_arr[i-1] is None or smooth_arr[i+1] is None:
            continue
        if smooth_arr[i] >= smooth_arr[i-1] and smooth_arr[i] >= smooth_arr[i+1]:
            # Check prominence: how much higher is this peak than surroundings
            left_min = min(smooth_arr[max(0,i-50):i]) if smooth_arr[max(0,i-50):i] else smooth_arr[i]
            right_min = min(smooth_arr[i:min(len(smooth_arr),i+50)]) if smooth_arr[i:min(len(smooth_arr),i+50)] else smooth_arr[i]
            prominence = smooth_arr[i] - max(left_min, right_min)
            
            if prominence >= min_prominence:
                peaks.append((int(i), smooth_arr[i], prominence))
    
    # Filter by separation (keep only highest in a window)
    filtered = []
    if not peaks:
        return []
    
    peaks.sort(key=lambda x: -x[2])  # Sort by prominence descending
    
    for peak in peaks:
        idx, ele, prom = peak
        if not any(abs(idx - f[0]) < min_separation for f in filtered):
            filtered.append((idx, ele))
    
    filtered.sort(key=lambda x: x[0])  # Sort by index
    return filtered

def find_climbs(coords):
    if not coords:
        return []
    
    eles = [c[2] for c in coords]
    
    # Smooth with a moderate window
    smooth_eles = smooth(eles, window=30)
    
    # Find summits
    summits = detect_summits(smooth_eles, min_prominence=30, min_separation=100)
    
    climbs = []
    for summit_idx, summit_ele in summits:
        # Find start of climb
        start_idx = summit_idx
        for i in range(summit_idx - 1, max(summit_idx - 300, -1), -1):
            if i >= 0 and i < len(coords) and coords[i][2] is not None:
                ele = coords[i][2]
                prev_ele = coords[max(0, i-1)][2] if max(0, i-1) < len(coords) and coords[max(0, i-1)][2] is not None else ele
                if ele <= summit_ele - 60 and prev_ele > ele:
                    start_idx = i
                    break
                start_idx = i
        
        # Find end of climb
        end_idx = summit_idx
        for i in range(summit_idx + 1, min(summit_idx + 300, len(coords))):
            if i < len(coords) and coords[i][2] is not None:
                ele = coords[i][2]
                nxt_ele = coords[min(len(coords)-1, i+1)][2] if min(len(coords)-1, i+1) < len(coords) and coords[min(len(coords)-1, i+1)][2] is not None else ele
                if ele <= summit_ele - 60 and nxt_ele < ele:
                    end_idx = i
                    break
                end_idx = i
        
        climb_coords = [c for c in coords[max(0, start_idx):min(len(coords), end_idx+1)] if c[2] is not None]
        if len(climb_coords) < 3:
            continue
        
        climb_start_ele = climb_coords[0][2]
        actual_gain = 0.0
        for i in range(1, len(climb_coords)):
            diff = climb_coords[i][2] - climb_coords[i-1][2]
            if diff > 0:
                actual_gain += diff
        
        dist = 0.0
        for i in range(1, len(climb_coords)):
            dist += haversine(climb_coords[i-1][0], climb_coords[i-1][1], climb_coords[i][0], climb_coords[i][1])
        dist *= 1000
        
        avg_gradient = (actual_gain / dist * 100) if dist > 0 else 0
        
        if actual_gain < 50 or dist < 400:
            continue
        
        category = categorize(actual_gain, dist, avg_gradient)
        
        summit_coord = coords[summit_idx] if summit_idx < len(coords) else None
        if summit_coord is None or summit_coord[2] is None:
            summit_coord = coords[min(len(coords)-1, summit_idx)]
        
        if summit_coord is None or summit_coord[2] is None:
            continue
        
        climbs.append({
            'index': len(climbs) + 1,
            'summit_index': int(summit_idx),
            'elevation_gain_m': float(round(actual_gain, 0)),
            'distance_m': float(round(dist, 0)),
            'avg_gradient_pct': float(round(avg_gradient, 1)),
            'max_ele_m': float(round(summit_coord[2], 0)),
            'start_ele_m': float(round(climb_start_ele, 0)),
            'category': category,
            'lat': round(summit_coord[0], 6),
            'lon': round(summit_coord[1], 6)
        })
    
    # Remove overlapping climbs (keep the ones with highest gain)
    seen = set()
    unique_climbs = []
    climbs.sort(key=lambda x: x['summit_index'])
    
    for climb in climbs:
        if climb['summit_index'] not in seen:
            seen.add(climb['summit_index'])
            unique_climbs.append(climb)
    
    return unique_climbs

def categorize(gain, dist_m, gradient):
    gain = round(gain, 0)
    dist = dist_m / 1000.0
    if gain >= 700 and dist >= 10: return 'HC'
    if gain >= 500 and dist >= 8 and gradient >= 5.5: return 'HC'
    if gain >= 400 and dist >= 8: return '1C'
    if gain >= 300 and dist >= 6 and gradient >= 4.5: return '1C'
    if gain >= 250 and dist >= 5: return '2C'
    if gain >= 200 and dist >= 4 and gradient >= 4: return '2C'
    if gain >= 150 and dist >= 3.5: return '3C'
    if gain >= 120 and dist >= 2.5 and gradient >= 3.5: return '3C'
    if gain >= 80 and dist >= 2: return '4C'
    if gain >= 60 and dist >= 1.5 and gradient >= 3: return '4C'
    if gain >= 50 and dist >= 5: return '4C'
    return 'Spec'

def calc_stats(coords):
    if not coords:
        return 0, 0, None, None
    gain = 0.0
    max_ele = None
    min_ele = None
    for i, (lat, lon, ele) in enumerate(coords):
        if ele is not None:
            if max_ele is None or ele > max_ele: max_ele = ele
            if min_ele is None or ele < min_ele: min_ele = ele
            if i > 0 and coords[i-1][2] is not None:
                diff = ele - coords[i-1][2]
                if diff > 0: gain += diff
    dist = 0.0
    for i in range(1, len(coords)):
        dist += haversine(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
    return dist, gain, max_ele, min_ele

gpx_dir = r'C:\Users\echav\OneDrive\Documentos\GitHub\procyclingstats\web_carreras\volta_portugal_2026\gpx'

all_climbs = {}

for f in sorted(os.listdir(gpx_dir)):
    if not f.endswith('.gpx'):
        continue
    if 'RETORNO' in f.upper():
        continue
    path = os.path.join(gpx_dir, f)
    coords = parse_gpx(path)
    
    dist, gain, max_ele, min_ele = calc_stats(coords)
    
    summits = detect_summits(smooth([c[2] for c in coords], 30), min_prominence=30, min_separation=100)
    
    climbs = find_climbs(coords)
    all_climbs[f] = climbs
    
    print(f'=== {f} ({len(coords)} pts) ===')
    print(f'  Stats: {dist:.1f}km, +{gain:.0f}m, max={max_ele:.0f}m, min={min_ele:.0f}m')
    print(f'  Raw summits (prom>=30m): {len(summits)}')
    if not climbs:
        print('  Climbs: No significant climbs detected')
    else:
        for c in climbs:
            cat = c['category']
            g = c['elevation_gain_m']
            d = c['distance_m']
            a = c['avg_gradient_pct']
            m = c['max_ele_m']
            print(f'  {cat}: +{g:.0f}m, {d:.0f}m, avg {a:.1f}% @ {m:.0f}m')
    print()

output_path = os.path.join(os.path.dirname(gpx_dir), 'climbs.json')
with open(output_path, 'w', encoding='utf-8') as fout:
    json.dump(all_climbs, fout, ensure_ascii=False, indent=2)
print(f'\nClimbs data saved to {output_path}')

print('\n=== VERIFICATION SUMMARY ===')
for f in sorted(os.listdir(gpx_dir)):
    if not f.endswith('.gpx') or 'RETORNO' in f.upper():
        continue
    path = os.path.join(gpx_dir, f)
    coords = parse_gpx(path)
    dist, gain, max_ele, min_ele = calc_stats(coords)
    category_counts = {}
    if f in all_climbs:
        for c in all_climbs[f]:
            category_counts[c['category']] = category_counts.get(c['category'], 0) + 1
    climbs_text = ', '.join([f"{k}:{v}" for k,v in sorted(category_counts.items())]) if category_counts else '0'
    print(f'{f}: {dist:.1f}km, +{gain:.0f}m, {climbs_text}')
