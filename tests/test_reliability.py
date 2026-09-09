# -*- coding: utf-8 -*-
"""
Reliability, Concurrency, Boundary & Autonomic Test Suite for NEXA Intelligence
Coldwell Banker CB VIP Ankara • Yiğit Narin
"""

import os
import sys
import json
import time
import threading
import pytest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ── 1. BOUNDARY VALUE & ZERO DIVISION STRESS TESTS ──
def test_decision_boundary_and_zero_division():
    from intelligence.decisions.engine import DecisionIntelligence

    # Test 1: Zero budget and negative budget in buying engine
    res_zero = DecisionIntelligence.evaluate_buying_conditions(budget=0, budget_tl=0)
    assert res_zero.score >= 2.5 and res_zero.score <= 9.4
    assert len(res_zero.factors) > 0

    res_neg = DecisionIntelligence.evaluate_buying_conditions(budget=-500000)
    assert res_neg.score >= 2.5 and res_neg.score <= 9.4

    # Test 2: Extreme budget (150M TL)
    res_mega = DecisionIntelligence.evaluate_buying_conditions(budget=150_000_000)
    assert res_mega.score >= 7.0
    assert "Strong" in res_mega.condition or "Moderate" in res_mega.condition

    # Test 3: Zero and negative values in selling engine
    res_sell_zero = DecisionIntelligence.evaluate_selling_conditions(approx_value=0)
    assert res_sell_zero.score >= 3.0 and res_sell_zero.score <= 9.2

    # Test 4: Zero rent and zero home price in rent-vs-buy engine (ZeroDivision check)
    res_rvb_zero = DecisionIntelligence.evaluate_rent_vs_buy(monthly_rent=0, home_price=0, cash_available=0, duration_years=0)
    assert res_rvb_zero.score >= 1.0
    assert len(res_rvb_zero.factors) > 0

    # Test 5: Extreme rent vs buy
    res_rvb_extreme = DecisionIntelligence.evaluate_rent_vs_buy(monthly_rent=250_000, home_price=50_000_000, duration_years=10)
    assert res_rvb_extreme.score >= 1.0


# ── 2. BILINGUAL CONTRACT COMPATIBILITY ──
def test_bilingual_contract_compatibility():
    from intelligence.decisions.engine import DecisionIntelligence

    # Turkish contract keys
    tr_result = DecisionIntelligence.evaluate_buying_conditions(
        budget_tl=12_000_000,
        financing_type="Nakit Peşin",
        district="Beytepe",
        purpose="Oturum"
    )

    # English contract keys
    en_result = DecisionIntelligence.evaluate_buying_conditions(
        budget=12_000_000,
        payment_method="Nakit Peşin",
        location="Beytepe",
        property_type="Oturum"
    )

    assert tr_result.score == en_result.score
    assert tr_result.condition == en_result.condition

    # Rent vs buy bilingual keys
    tr_rvb = DecisionIntelligence.evaluate_rent_vs_buy(
        rent_tl=45000,
        property_price_tl=8000000,
        cash_tl=3000000,
        years=5
    )
    en_rvb = DecisionIntelligence.evaluate_rent_vs_buy(
        monthly_rent=45000,
        home_price=8000000,
        cash_available=3000000,
        duration_years=5
    )
    assert tr_rvb.score == en_rvb.score


# ── 3. SQLITE CONCURRENCY STRESS (10 CONCURRENT THREADS) ──
def test_sqlite_multithread_concurrency_stress():
    from intelligence.db import get_db_connection, get_published_articles
    from intelligence.analytics.funnel_tracker import FunnelTracker

    errors = []

    def worker_task(thread_id):
        try:
            # 1. Read articles
            articles = get_published_articles(limit=5)
            assert isinstance(articles, list)

            # 2. Write telemetry event
            delta = FunnelTracker.track_interaction(
                event_type="decision_tool_run",
                user_id=f"test_thread_{thread_id}",
                context={"thread": thread_id, "timestamp": time.time()}
            )
            assert delta == 20

            # 3. Direct DB read
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM news_articles")
                count = cur.fetchone()[0]
                assert count >= 0
        except Exception as e:
            errors.append(f"Thread {thread_id} error: {e}")

    threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(errors) == 0, f"Concurrency errors occurred: {errors}"


# ── 4. AUTONOMIC SUPERVISOR & SELF-HEALING ──
def test_autonomic_supervisor_pulse_and_recovery():
    from intelligence.autonomic_daemon import get_supervisor

    sup = get_supervisor()
    report = sup.pulse()

    assert report["status"] in ("healthy", "degraded")
    assert report["vitality_score"] >= 80.0
    assert report["duration_ms"] < 2000.0  # Must execute fast

    # Verify db health
    db_health = report["database_health"]
    assert db_health["status"] == "ok"
    assert db_health["integrity"] == "ok"
    assert db_health["active_tables"] >= 10

    # Verify recoveries
    recoveries = report["recoveries"]
    assert recoveries["status"] == "ok"

    # Verify market sensing
    sensing = report["market_sensing"]
    assert sensing["status"] == "ok"
    assert "active_regime" in sensing


# ── 5. FLASK TEST CLIENT ENDPOINTS ──
def test_api_endpoints_via_flask_client():
    from app import app

    client = app.test_client()

    # 1. Autonomic status
    res = client.get("/api/intelligence/autonomic/status")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["ok"] is True
    assert "latest_report" in data["data"]

    # 2. Autonomic pulse
    res_pulse = client.post("/api/intelligence/autonomic/pulse")
    assert res_pulse.status_code == 200
    pulse_data = json.loads(res_pulse.data)
    assert pulse_data["ok"] is True
    assert pulse_data["data"]["vitality_score"] >= 80.0

    # 3. Buying decision endpoint
    res_buy = client.post(
        "/api/intelligence/decisions/buying",
        json={"budget_tl": 8500000, "district": "Beytepe", "financing_type": "cash"}
    )
    assert res_buy.status_code == 200
    buy_data = json.loads(res_buy.data)
    assert buy_data["ok"] is True
    assert "score" in buy_data["data"]
    assert "advisor_consultation_prompt" in buy_data["data"]

    # 4. Rent vs Buy decision endpoint
    res_rvb = client.post(
        "/api/intelligence/decisions/rent-vs-buy",
        json={"monthly_rent_tl": 40000, "property_price_tl": 7500000, "equity_tl": 3000000, "stay_horizon_years": 5}
    )
    assert res_rvb.status_code == 200
    rvb_data = json.loads(res_rvb.data)
    assert rvb_data["ok"] is True
    assert "score" in rvb_data["data"]


# ── 6. EPISTEMIC SCHEMA INTEGRITY ──
def test_epistemic_schema_integrity():
    from intelligence.analysis.ai_engine import AiIntelligenceEngine

    engine = AiIntelligenceEngine()
    title = "TCMB Haftalık Konut Fiyat Endeksi Verisi"
    content = "TCMB verilerine göre Ankara prime akslarında reel konut getirileri enflasyon karşısında pozitif seyre devam ediyor."

    result = engine._heuristic_fallback(title, content)
    assert "what_we_know" in result
    assert "what_we_infer" in result
    assert "what_we_suspect" in result
    assert "what_we_dont_know" in result
    assert "contrarian_view" in result
    assert "headline" in result["contrarian_view"]
    assert "risk_analysis" in result["contrarian_view"]
