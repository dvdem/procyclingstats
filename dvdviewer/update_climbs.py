import json
import shutil

with open('stages.json', 'r', encoding='utf-8') as f:
    stages = json.load(f)

# Stage 4: Torre (index 4)
st4 = stages[4] # 04_ET4_Figueiró dos Vinhos-Torre
has_torre = any(c.get('is_finish') for c in st4['climbs'])
if not has_torre:
    st4['climbs'].append({
        'index': len(st4['climbs']) + 1,
        'summit_index': 4814,
        'elevation_gain_m': 1448.0,
        'distance_m': 24900.0,
        'avg_gradient_pct': 5.8,
        'max_ele_m': 2007.0,
        'start_ele_m': 559.0,
        'category': 'HC',
        'lat': 40.32286,
        'lon': -7.61216,
        'name': 'Alto da Torre (Meta)',
        'is_finish': True
    })

# Stage 7: Gêres (index 7)
st7 = stages[7] # 07_ET7_VieiradoMinho-Gêres
has_geres = any(c.get('is_finish') for c in st7['climbs'])
if not has_geres:
    st7['climbs'].append({
        'index': len(st7['climbs']) + 1,
        'summit_index': 5409,
        'elevation_gain_m': 201.0,
        'distance_m': 6600.0,
        'avg_gradient_pct': 3.1,
        'max_ele_m': 350.0,
        'start_ele_m': 149.0,
        'category': '3C',
        'lat': 41.727869,
        'lon': -8.162185,
        'name': 'Gêres (Meta)',
        'is_finish': True
    })

# Stage 9: Sra da Graça (index 9)
st9 = stages[9] # 09_ET9_Paredes-Mondim de Basto Sra._da_Graça
has_graca = any(c.get('is_finish') for c in st9['climbs'])
if not has_graca:
    st9['climbs'].append({
        'index': len(st9['climbs']) + 1,
        'summit_index': 4331,
        'elevation_gain_m': 767.0,
        'distance_m': 13500.0,
        'avg_gradient_pct': 5.7,
        'max_ele_m': 930.0,
        'start_ele_m': 163.0,
        'category': '1C',
        'lat': 41.4169,
        'lon': -7.91582,
        'name': 'Sra. da Graça (Meta)',
        'is_finish': True
    })

with open('stages.json', 'w', encoding='utf-8') as f:
    json.dump(stages, f, ensure_ascii=False, indent=2)

shutil.copyfile('stages.json', '../web_carreras/volta_portugal_2026/stages.json')
print('Updated stages.json successfully!')
