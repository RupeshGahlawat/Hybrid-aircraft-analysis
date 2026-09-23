"""
Unit and Integration Tests for Phase 6: Gemma 3 270M Analyst Fine-Tuning & Evaluation.
Tests:
1. Synthetic instruction dataset integrity.
2. Pure PyTorch architecture, forward pass, and LoRA adaptation.
3. Numerical Consistency Check (exact unit tolerance, non-assert gating).
4. Adversarial corruption detection and certified template fallback.
5. Protection under python -O (assert independence).
6. Evaluation harness metrics.
7. FastAPI analyst endpoints (/api/analyst/query and /api/analyst/eval-benchmarks).
"""

import json
import os

import pytest
import torch
from fastapi.testclient import TestClient

from backend.app import app
from backend.ml_service.analyst import ANALYST, GroundingVerificationError, InputValidationError
from backend.ml_service.eval_harness import parse_query_to_simulator_json
from backend.ml_service.gemma_analyst_pt import Gemma3AnalystModel, SimpleTokenizer


@pytest.fixture
def client():
    return TestClient(app)


def test_instruction_datasets_exist():
    """Verifies that synthetic instruction and adversarial datasets exist and are non-empty."""
    train_path = "data/instructions/train.jsonl"
    val_path = "data/instructions/val.jsonl"
    adv_path = "data/instructions/adversarial.jsonl"

    for path in [train_path, val_path, adv_path]:
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) > 0
            # Test schema of first item
            first = json.loads(lines[0].strip())
            assert "task" in first


def test_gemma_pytorch_architecture_and_forward():
    """Verifies pure PyTorch model forward pass and LoRA gradient targeting."""
    tokenizer = SimpleTokenizer()
    model = Gemma3AnalystModel(vocab_size=tokenizer.vocab_size, d_model=128, n_heads=4, n_layers=2, d_ff=384)

    dummy_input = torch.tensor([[tokenizer.bos_id, 35, 42, 50]], dtype=torch.long)
    logits = model(dummy_input)

    assert logits.shape == (1, 4, tokenizer.vocab_size)

    # Verify LoRA parameters exist
    lora_params = [name for name, _ in model.named_parameters() if "lora_" in name]
    assert len(lora_params) > 0


def test_numerical_consistency_check_passes_on_valid_data():
    """Verifies valid explanation passes Numerical Consistency Check without discrepancy."""
    gt = {
        "fuel_saved_pct": 19.1,
        "fuel_saved_kg": 36.8,
        "battery_weight_kg": 771.6,
        "passengers_carried": 66,
        "net_co2_saved_pct_wtw": -4.6,
    }

    valid_text = (
        "Mission is structurally feasible within 23,000 kg MTOW limit carrying 66 passengers. "
        "Battery pack sized to 771.6 kg at 400 Wh/kg specific energy. "
        "Direct tailpipe Jet-A1 fuel consumption drops by 19.1% (36.8 kg saved). "
        "Well-to-Wake net CO2 delta is -4.6% considering regional grid recharge emissions."
    )

    res = ANALYST.verify_numerical_consistency(valid_text, gt)
    assert res["status"] == "PASSED"
    assert res["discrepancies_count"] == 0


def test_numerical_consistency_check_catches_hallucinations():
    """Verifies GroundingVerificationError is raised when text contains fabricated numbers."""
    gt = {
        "fuel_saved_pct": 19.1,
        "fuel_saved_kg": 36.8,
        "battery_weight_kg": 771.6,
        "passengers_carried": 66,
        "net_co2_saved_pct_wtw": -4.6,
    }

    # Injected hallucination: claiming 35.0% fuel saved instead of 19.1%
    corrupted_text = (
        "Mission is structurally feasible within 23,000 kg MTOW limit carrying 66 passengers. "
        "Battery pack sized to 771.6 kg at 400 Wh/kg specific energy. "
        "Direct tailpipe Jet-A1 fuel consumption drops by 35.0% (36.8 kg saved). "
        "Well-to-Wake net CO2 delta is -4.6% considering regional grid recharge emissions."
    )

    with pytest.raises(GroundingVerificationError) as exc_info:
        ANALYST.verify_numerical_consistency(corrupted_text, gt)

    err = exc_info.value
    assert len(err.discrepancies) == 1
    assert err.discrepancies[0]["metric"] == "fuel_saved_pct"
    assert err.discrepancies[0]["claimed_in_text"] == 35.0
    assert err.discrepancies[0]["ground_truth"] == 19.1


def test_analyst_fallback_on_corrupted_candidate():
    """Verifies that analyze_simulation triggers certified fallback when given candidate text with errors."""
    dummy_sim = {
        "summary": {
            "fuel_saved_pct": 19.1,
            "fuel_saved_kg": 36.8,
            "battery_weight_kg": 771.6,
            "passengers_carried": 66,
            "net_co2_saved_pct_wtw": -4.6,
            "is_feasible": True,
            "mtow_hybrid_kg": 21638.4,
        },
        "route": {"stage_distance_km": 118.0},
        "parameters": {"battery_wh_per_kg": 400.0, "hp_fraction": 0.30},
    }

    corrupted_candidate = "Direct tailpipe Jet-A1 fuel consumption drops by 99.0% (500.0 kg saved)."
    report = ANALYST.analyze_simulation(dummy_sim, candidate_text=corrupted_candidate)

    assert "FALLBACK_TRIGGERED" in report["model_metadata"]["verification_status"]
    # The narrative was replaced with certified template narrative
    assert "99.0%" not in report["full_technical_report"]
    assert "19.1%" in report["full_technical_report"]


def test_python_optimized_mode_protection():
    """
    Ensures safety checks use explicit exceptions rather than 'assert',
    guaranteeing protection even when executed under 'python -O'.
    """
    import inspect
    src = inspect.getsource(ANALYST.verify_numerical_consistency)
    assert "assert " not in src, "Found 'assert' statement inside verify_numerical_consistency! Must use explicit exception."


def test_query_parser_valid_and_refusals():
    """Tests query parser extracts parameters and properly refuses out-of-range inputs."""
    # Valid query
    parsed = parse_query_to_simulator_json("Simulate the flight from Mumbai to Pune with 25% hybrid boost and 450 Wh/kg.")
    assert parsed["route_id"] == "BOM-PNQ"
    assert parsed["hp_fraction"] == 0.25
    assert parsed["battery_wh_per_kg"] == 450.0

    # Refusal: out-of-range hybrid fraction
    with pytest.raises(InputValidationError):
        parse_query_to_simulator_json("Simulate BOM-PNQ with 95% hybrid boost.")

    # Refusal: out-of-range battery density
    with pytest.raises(InputValidationError):
        parse_query_to_simulator_json("Simulate BOM-PNQ with -50 Wh/kg battery density.")

    # Refusal: unsupported non-Indian route
    with pytest.raises(InputValidationError):
        parse_query_to_simulator_json("Simulate London to Paris flight with 20% boost.")


def test_eval_harness_metrics_file():
    """Verifies that evaluation metrics file has high exact-match, refusal, and adversarial catch rates."""
    metrics_path = "data/models/gemma_eval_metrics.json"
    assert os.path.exists(metrics_path)

    with open(metrics_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["task_a_nl_to_json"]["exact_match_rate_pct"] >= 95.0
    assert data["task_a_nl_to_json"]["refusal_rate_pct"] == 100.0
    assert data["task_b_faithfulness"]["number_faithfulness_rate_pct"] >= 98.0
    assert data["adversarial_catch_rate"]["adversarial_catch_rate_pct"] == 100.0


def test_fastapi_analyst_routes(client):
    """Tests POST /api/analyst/query and GET /api/analyst/eval-benchmarks."""
    # 1. Valid NL Query
    resp_valid = client.post(
        "/api/analyst/query",
        json={"query": "Simulate Mumbai to Pune with 30% hybrid boost and 400 Wh/kg battery."},
    )
    assert resp_valid.status_code == 200
    data_valid = resp_valid.json()
    assert "ai_analyst" in data_valid
    assert "parsed_inputs" in data_valid
    assert data_valid["parsed_inputs"]["route_id"] == "BOM-PNQ"
    assert "Numerical Consistency Check" in data_valid["ai_analyst"]["model_metadata"]["verification_status"]

    # 2. Refusal Query
    resp_refusal = client.post(
        "/api/analyst/query",
        json={"query": "Simulate flight from London to Paris with 90% hybrid boost."},
    )
    assert resp_refusal.status_code == 400
    data_err = resp_refusal.json()
    assert "REFUSAL" in str(data_err)

    # 3. GET /api/analyst/eval-benchmarks
    resp_bm = client.get("/api/analyst/eval-benchmarks")
    assert resp_bm.status_code == 200
    data_bm = resp_bm.json()
    assert "adversarial_catch_rate" in data_bm
    assert data_bm["adversarial_catch_rate"]["adversarial_catch_rate_pct"] == 100.0
