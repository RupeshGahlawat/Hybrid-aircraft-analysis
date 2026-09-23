import os
import sys
import json
from backend.sim_core.routes import INDIAN_REGIONAL_SECTORS, get_route_by_id
from backend.sim_core.mission_sim import MissionSimulator

os.makedirs('tests/regression_snapshots', exist_ok=True)

output_filename = sys.argv[1] if len(sys.argv) > 1 else 'phase1_correctness.json'

configs = [
    # 1. Standard nominal runs for all routes
    {'route_id': 'BLR-IXG', 'hp_fraction': 0.30, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'nominal_0.30_400'},
    {'route_id': 'BOM-PNQ', 'hp_fraction': 0.30, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'nominal_0.30_400'},
    {'route_id': 'DEL-DED', 'hp_fraction': 0.30, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'nominal_0.30_400'},
    {'route_id': 'MAA-TIR', 'hp_fraction': 0.30, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'nominal_0.30_400'},
    {'route_id': 'AMD-UDR', 'hp_fraction': 0.30, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'nominal_0.30_400'},
    
    # 2. Benchmark table specific runs
    {'route_id': 'BOM-PNQ', 'hp_fraction': 0.25, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'benchmark_table'},
    {'route_id': 'BLR-IXG', 'hp_fraction': 0.15, 'battery_wh_per_kg': 450.0, 'ambient_delta_c': 0.0, 'tag': 'benchmark_table'},
    {'route_id': 'DEL-DED', 'hp_fraction': 0.20, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'benchmark_table'},
    {'route_id': 'MAA-TIR', 'hp_fraction': 0.30, 'battery_wh_per_kg': 350.0, 'ambient_delta_c': 0.0, 'tag': 'benchmark_table'},
    {'route_id': 'AMD-UDR', 'hp_fraction': 0.20, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 0.0, 'tag': 'benchmark_table'},

    # 3. Summer temperature run (+25C offset = 40C sea level OAT)
    {'route_id': 'DEL-DED', 'hp_fraction': 0.20, 'battery_wh_per_kg': 400.0, 'ambient_delta_c': 25.0, 'tag': 'hot_summer_delhi'}
]

snapshots = {}
for cfg in configs:
    r = get_route_by_id(cfg['route_id'])
    sim = MissionSimulator(
        r,
        hp_fraction=cfg['hp_fraction'],
        battery_wh_per_kg=cfg['battery_wh_per_kg'],
        ambient_delta_c=cfg['ambient_delta_c']
    )
    res = sim.run_simulation()
    key = f"{cfg['route_id']}__{cfg['tag']}"
    snapshots[key] = {
        'route_id': cfg['route_id'],
        'tag': cfg['tag'],
        'hp_fraction': cfg['hp_fraction'],
        'battery_wh_per_kg': cfg['battery_wh_per_kg'],
        'ambient_delta_c': cfg['ambient_delta_c'],
        'summary': res['summary']
    }

output_path = os.path.join('tests', 'regression_snapshots', output_filename)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(snapshots, f, indent=2)

print(f"Successfully generated {output_path}")
for k, v in snapshots.items():
    s = v['summary']
    print(f"{k:35s}: ConvFuel={s['conventional_fuel_kg']:6.1f} kg, HybFuel={s['hybrid_fuel_kg']:6.1f} kg, FuelSave={s['fuel_saved_pct']:5.1f}%, NetCO2Save={s['net_co2_saved_pct']:5.1f}%, Pax={s['passengers_carried']}, MTOW={s['mtow_hybrid_kg']:7.1f} kg, Limit={s.get('limiting_constraint', 'NONE')}")
