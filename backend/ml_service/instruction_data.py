"""
Synthetic Instruction Dataset Generator for Fine-Tuning and Evaluating Gemma 3 270M Analyst.
Generates paired examples for:
Task A: Natural Language Query -> Validated Simulator JSON (with refusal on out-of-bounds inputs).
Task B: Simulation Results Dict -> Grounded Technical Narrative (only using supplied numbers).
Adversarial Set: Corrupted numerical figures to evaluate consistency check catch rates.
"""

import json
import os
import random
from typing import Any

from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.routes import INDIAN_REGIONAL_SECTORS

VALID_ROUTE_IDS = [r.route_id for r in INDIAN_REGIONAL_SECTORS]


def generate_task_a_examples(n_samples: int = 250, seed: int = 42) -> list[dict[str, Any]]:
    """Generates natural language query to validated JSON simulator inputs."""
    rng = random.Random(seed)
    examples: list[dict[str, Any]] = []

    route_templates = [
        ("Simulate the flight from {origin_city} to {dest_city} with {hp_pct}% hybrid boost and {wh} Wh/kg batteries.", False),
        ("Run feasibility analysis on {route_id} sector using {hp_pct}% electric power split and {wh} Wh/kg pack at {temp}C temperature offset.", False),
        ("Evaluate regional ATR 72 mission between {origin_city} ({origin_iata}) and {dest_city} ({dest_iata}) with {hp_pct}% hybrid ratio and {wh} Wh/kg.", False),
        ("Calculate fuel savings for {route_id} assuming {wh} Wh/kg battery technology and {hp_pct}% climb hybridization.", False),
        ("What is the payload impact on {origin_city} to {dest_city} with {hp_pct}% hybrid power and {wh} Wh/kg batteries in {temp}C summer conditions?", False),
    ]

    refusal_templates = [
        ("Simulate supersonic flight from Mumbai to London with 90% hybrid boost and 2000 Wh/kg battery.", "REFUSAL: Unsupported route and hybrid fraction 0.90 exceeds structural ceiling (0.50)"),
        ("Run mission on {route_id} with -50 Wh/kg battery density and 30% boost.", "REFUSAL: Unphysical negative battery specific energy (-50 Wh/kg)"),
        ("Evaluate flight from New York to Tokyo with 35% hybrid boost.", "REFUSAL: Unsupported non-Indian regional route"),
        ("Simulate {route_id} with 85% electric climb boost at 400 Wh/kg.", "REFUSAL: Hybridization ratio 0.85 exceeds maximum envelope (0.50)"),
        ("Run {route_id} with battery specific energy of 1200 Wh/kg and 30% boost.", "REFUSAL: Battery specific energy 1200 Wh/kg exceeds certified regional envelope (700 Wh/kg)"),
    ]

    # Valid in-distribution queries
    for _ in range(n_samples):
        route = rng.choice(INDIAN_REGIONAL_SECTORS)
        hp = round(rng.uniform(0.05, 0.40), 2)
        wh = round(rng.uniform(250.0, 550.0), 0)
        dt = round(rng.choice([0.0, 5.0, 10.0, 15.0, 20.0, 25.0]), 1)

        tmpl, _ = rng.choice(route_templates)
        query = tmpl.format(
            origin_city=route.origin.city,
            dest_city=route.destination.city,
            origin_iata=route.origin.iata,
            dest_iata=route.destination.iata,
            route_id=route.route_id,
            hp_pct=int(hp * 100),
            wh=int(wh),
            temp=int(dt),
        )

        expected_json = {
            "route_id": route.route_id,
            "hp_fraction": hp,
            "battery_wh_per_kg": wh,
            "ambient_delta_c": dt,
        }

        examples.append({
            "task": "task_a_nl_to_json",
            "query": query,
            "target": json.dumps(expected_json),
            "is_refusal": False,
            "metadata": expected_json,
        })

    # Refusal queries
    for tmpl, reason in refusal_templates:
        route = rng.choice(INDIAN_REGIONAL_SECTORS)
        query = tmpl.format(route_id=route.route_id)
        examples.append({
            "task": "task_a_nl_to_json",
            "query": query,
            "target": json.dumps({"error": "REFUSAL", "reason": reason}),
            "is_refusal": True,
            "metadata": {},
        })

    return examples


def generate_task_b_examples(n_samples: int = 150, seed: int = 42) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Generates simulation results to grounded explanation, plus adversarial corrupted pairs.
    """
    rng = random.Random(seed)
    grounded_examples: list[dict[str, Any]] = []
    adversarial_examples: list[dict[str, Any]] = []

    for _ in range(n_samples):
        route = rng.choice(INDIAN_REGIONAL_SECTORS)
        hp = round(rng.uniform(0.10, 0.35), 2)
        wh = round(rng.choice([300.0, 350.0, 400.0, 450.0, 500.0]), 1)
        dt = round(rng.choice([0.0, 10.0, 20.0]), 1)

        sim = MissionSimulator(route, hp_fraction=hp, battery_wh_per_kg=wh, ambient_delta_c=dt, physics_mode="phase2")
        res = sim.run_simulation()
        s = res["summary"]

        pax = s["passengers_carried"]
        fuel_pct = s["fuel_saved_pct"]
        fuel_kg = s["fuel_saved_kg"]
        batt_wt = s["battery_weight_kg"]
        net_co2 = s["net_co2_saved_pct_wtw"]
        mtow = s["mtow_hybrid_kg"]
        is_feas = s["is_feasible"]

        # Faithful grounded explanation
        bullets = []
        if is_feas:
            bullets.append(f"Mission is structurally feasible within 23,000 kg MTOW limit carrying {pax} passengers.")
        else:
            bullets.append(f"Mission exceeds structural ceiling requiring shedding to {pax} passengers.")

        bullets.append(f"Battery pack sized to {batt_wt:.1f} kg at {wh:.0f} Wh/kg specific energy.")
        bullets.append(f"Direct tailpipe Jet-A1 fuel consumption drops by {fuel_pct:.1f}% ({fuel_kg:.1f} kg saved).")
        bullets.append(f"Well-to-Wake net CO2 delta is {net_co2:.1f}% considering regional grid recharge emissions.")

        narrative = " ".join(bullets)

        input_data = {
            "route_id": route.route_id,
            "stage_distance_km": route.stage_distance_km,
            "hp_fraction": hp,
            "battery_wh_per_kg": wh,
            "ambient_delta_c": dt,
            "passengers_carried": pax,
            "battery_weight_kg": round(batt_wt, 1),
            "fuel_saved_pct": round(fuel_pct, 1),
            "fuel_saved_kg": round(fuel_kg, 1),
            "net_co2_saved_pct_wtw": round(net_co2, 1),
            "mtow_hybrid_kg": round(mtow, 1),
            "is_feasible": is_feas,
        }

        grounded_examples.append({
            "task": "task_b_results_to_explanation",
            "input_data": input_data,
            "target": narrative,
            "is_adversarial": False,
        })

        # Generate adversarial example with intentionally corrupted numbers
        corrupted_fuel_pct = round(fuel_pct + rng.choice([15.0, 25.0, -10.0]), 1)
        corrupted_batt_wt = round(batt_wt * rng.choice([0.4, 1.8]), 1)
        corrupted_bullets = [
            f"Mission is structurally feasible within 23,000 kg MTOW limit carrying {pax} passengers.",
            f"Battery pack sized to {corrupted_batt_wt:.1f} kg at {wh:.0f} Wh/kg specific energy.",
            f"Direct tailpipe Jet-A1 fuel consumption drops by {corrupted_fuel_pct:.1f}% ({fuel_kg:.1f} kg saved).",
            f"Well-to-Wake net CO2 delta is {net_co2:.1f}% considering regional grid recharge emissions.",
        ]
        adversarial_narrative = " ".join(corrupted_bullets)

        adversarial_examples.append({
            "task": "task_b_results_to_explanation",
            "input_data": input_data,
            "corrupted_target": adversarial_narrative,
            "corrupted_fields": {
                "fuel_saved_pct": {"true": round(fuel_pct, 1), "injected": corrupted_fuel_pct},
                "battery_weight_kg": {"true": round(batt_wt, 1), "injected": corrupted_batt_wt},
            },
            "is_adversarial": True,
        })

    return grounded_examples, adversarial_examples


def build_and_save_instruction_dataset(output_dir: str = "data/instructions") -> dict[str, int]:
    """Builds and serializes instruction tuning and adversarial benchmark datasets."""
    os.makedirs(output_dir, exist_ok=True)

    task_a_all = generate_task_a_examples(n_samples=300, seed=42)
    task_b_all, adv_all = generate_task_b_examples(n_samples=200, seed=42)

    # 80/20 train/validation split
    n_a_train = int(len(task_a_all) * 0.8)
    n_b_train = int(len(task_b_all) * 0.8)

    train_set = task_a_all[:n_a_train] + task_b_all[:n_b_train]
    val_set = task_a_all[n_a_train:] + task_b_all[n_b_train:]

    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")
    adv_path = os.path.join(output_dir, "adversarial.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_set:
            f.write(json.dumps(item) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_set:
            f.write(json.dumps(item) + "\n")

    with open(adv_path, "w", encoding="utf-8") as f:
        for item in adv_all:
            f.write(json.dumps(item) + "\n")

    return {
        "train_samples": len(train_set),
        "val_samples": len(val_set),
        "adversarial_samples": len(adv_all),
    }


if __name__ == "__main__":
    stats = build_and_save_instruction_dataset()
    print("Dataset generation complete:", stats)
