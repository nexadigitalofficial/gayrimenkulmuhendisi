# -*- coding: utf-8 -*-
"""
Unit & Integration Tests for NEXA Real Estate Intelligence Swarm
Coldwell Banker CB VIP Ankara • Yiğit Narin
"""

import os
import json
import pytest
from datetime import datetime, timezone

from intelligence.models import RawArticle
from intelligence.swarm.swarm_models import (
    CandidateAction, VerificationStatus, MarketRegime, EvidenceItem,
    ContrarianAnalysis, ResearchTask, SignalCandidate, MarketState,
    EmergingTrend, FinalIntelligenceObject
)
from intelligence.swarm.scouts import (
    SourceScoutAgent, GovernmentDataAgent, NewsDiscoveryAgent
)
from intelligence.swarm.specialists import (
    FinanceAgent, EntityResolutionAgent, AnkaraAgent,
    InfrastructureZoningAgent, ProjectIntelligenceAgent, RentalMarketAgent
)
from intelligence.swarm.critical_thinking import (
    ContrarianAgent, TrendDetectionAgent
)
from intelligence.swarm.verification import (
    FactCheckerAgent, EvidenceGraphBuilder
)
from intelligence.swarm.synthesizer import (
    ContentSynthesizerAgent, QAGateAgent
)
from intelligence.swarm.director import IntelligenceDirector
from intelligence.market_state.engine import MarketStateEngine
from intelligence.db import (
    save_research_task, get_research_queue, save_market_state_snapshot,
    get_market_state_history, save_emerging_trend, get_active_trends,
    record_research_audit
)
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_swarm_models_and_enums():
    """Validates core data contracts and enum values."""
    assert CandidateAction.PUBLISH.value == "PUBLISH"
    assert CandidateAction.IGNORE.value == "IGNORE"
    assert CandidateAction.PRIORITY_INTELLIGENCE.value == "PRIORITY"

    assert VerificationStatus.VERIFIED.value == "VERIFIED"
    assert VerificationStatus.CONTRADICTED.value == "CONTRADICTED"

    assert MarketRegime.EXPANSION.value == "EXPANSION"
    assert MarketRegime.STABLE.value == "STABLE"
    assert MarketRegime.COOLING.value == "COOLING"

    item = EvidenceItem(
        claim="TCMB faiz oranını %45 seviyesinde sabit tuttu.",
        source_id="tcmb_official",
        source_name="TCMB Resmi Gazete"
    )
    assert item.status == VerificationStatus.VERIFIED
    assert item.authority_score >= 0.8


def test_scouts_agents():
    """Tests SourceScoutAgent and NewsDiscoveryAgent scoring logic."""
    scout = SourceScoutAgent()
    eval_res = scout.evaluate_source(source_id="tcmb", source_name="TCMB")
    assert eval_res["authority_score"] >= 0.95
    assert eval_res["tier"] == "OFFICIAL"

    gov = GovernmentDataAgent()
    benchmarks = gov.get_current_benchmarks()
    assert benchmarks["tcmb_policy_rate"] == 45.0
    assert "Beytepe" in benchmarks["prime_corridor"]

    discovery = NewsDiscoveryAgent()
    art_high = RawArticle(
        guid="art_test_high",
        source_id="tcmb_rss",
        source_name="TCMB",
        title="TCMB Faiz Kararı ve Ankara Konut Kredisi Hacmi Açıklandı",
        url="https://tcmb.gov.tr/faiz",
        summary="Faiz indirimi sinyali ve konut kredisi talebinde artış.",
        content="Resmi veriler konut sektöründe canlanmayı işaret ediyor. Beytepe ve İncek bölgesinde satışlar arttı.",
        published_at=datetime.now(timezone.utc).isoformat()
    )
    cand_high = discovery.evaluate_signal(art_high)
    assert cand_high.final_candidate_score >= 75
    assert cand_high.action in [CandidateAction.PUBLISH, CandidateAction.PRIORITY_INTELLIGENCE, CandidateAction.TRACK]


def test_specialists_agents():
    """Tests AnkaraAgent, FinanceAgent and EntityResolutionAgent."""
    resolved = EntityResolutionAgent.resolve_entities("Beytepe ve İncek lüks konut villa piyasası")
    assert resolved["primary_entity"]["neighborhood"] in ["Beytepe", "İncek"]
    assert any(w in resolved["primary_entity"]["segment"] for w in ["Rezidans", "Villa", "Konut"])

    ankara_meta = AnkaraAgent.evaluate_district("Beytepe")
    assert ankara_meta["district"] == "Beytepe"
    assert ankara_meta["depreciation_years"] > 10
    assert ankara_meta["liquidity"] == "Yüksek"

    fin_meta = FinanceAgent.analyze_financing("Kredi faiz oranları %2.80 seviyesine geriledi, peşinat avantajı oluştu.")
    assert "buyer_sentiment" in fin_meta
    assert "mortgage_cost_outlook" in fin_meta
    assert fin_meta["capital_preservation_index"] >= 80


def test_contrarian_agent_and_stress_test():
    """Tests ContrarianAgent's ability to produce counter-hypotheses and downside risks."""
    contrarian = ContrarianAgent()
    analysis = contrarian.stress_test(
        title="Ankara Konut Fiyatlarında Rekor Artış Beklentisi",
        content="Faiz indirimleriyle birlikte fiyatların %50 artacağı öngörülüyor."
    )
    assert analysis.counter_hypothesis != ""
    assert len(analysis.contrary_indicators) > 0
    assert len(analysis.downside_risks) > 0
    assert 0.0 <= analysis.confidence_discount <= 0.20


def test_trend_detection_agent():
    """Tests 14-day emerging trend velocity detection."""
    agent = TrendDetectionAgent()
    items = [
        {"title": "Beytepe arsa talebinde artış", "content": "Yatırımcılar Beytepe arsa projelerine yöneliyor", "timestamp": "2026-03-01"},
        {"title": "Beytepe imar ve parsel hareketliliği", "content": "Beytepe arsa fiyatlarında prim", "timestamp": "2026-03-04"},
        {"title": "Beytepe arsa yatırımı rekor kırdı", "content": "Arsa talebi ivme kazandı", "timestamp": "2026-03-07"}
    ]
    trends = agent.detect_emerging_trends(items)
    assert len(trends) > 0
    top_trend = trends[0]
    assert "Beytepe" in top_trend.region or "Ankara" in top_trend.region
    assert top_trend.velocity >= 1.0


def test_verification_and_evidence_graph():
    """Tests claim extraction and evidence graph confidence scoring."""
    claims = FactCheckerAgent.extract_and_verify_claims(
        title="TÜİK Ankara Konut Satış Verilerini Yayımladı",
        content="TÜİK resmi bültenine göre Ankara'da satışlar yıllık %18 arttı. TCMB verileri kredili satışı doğruladı.",
        source_id="tuik_gov_tr",
        source_name="TÜİK",
        source_url="https://tuik.gov.tr"
    )
    assert len(claims) >= 1
    assert claims[0].status in [VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED]

    graph = EvidenceGraphBuilder.build_graph(claims)
    assert len(graph["evidence_nodes"]) >= 1
    assert graph["overall_authority_score"] >= 0.70


def test_qa_gate_and_zero_fill_rule():
    """Strictly validates the Zero-Fill Rule: low score (<80) or unverified must NOT be published."""
    qa = QAGateAgent()

    # Low score signal -> MUST BE REJECTED
    claims_low = [EvidenceItem(claim="Söylenti", source_id="forum", source_name="Forum", status=VerificationStatus.UNVERIFIED)]
    res_low = qa.evaluate_publication_readiness(candidate_score=62, confidence_score=0.55, claims=claims_low)
    assert res_low["is_ready_for_publish"] is False
    assert any("altında" in r for r in res_low["reasons"])

    # High score verified signal -> APPROVED FOR PUBLISH
    claims_high = [EvidenceItem(claim="TCMB Resmi Raporu", source_id="tcmb", source_name="TCMB", status=VerificationStatus.VERIFIED)]
    res_high = qa.evaluate_publication_readiness(candidate_score=88, confidence_score=0.92, claims=claims_high)
    assert res_high["is_ready_for_publish"] is True


def test_intelligence_director_and_research_queue():
    """Tests IntelligenceDirector research planning, queue creation, and synthesis."""
    director = IntelligenceDirector()

    raw_articles = [
        RawArticle(
            guid="test_art_1",
            source_id="tcmb",
            source_name="TCMB",
            title="TCMB Para Politikası Kurulu Ankara Konut Raporu",
            url="https://tcmb.gov.tr/duyuru",
            summary="Ankara konut piyasasında fiyat endeksi ve kredi hacmi açıklandı.",
            content="TCMB resmi açıklamasına göre Beytepe ve İncek bölgesinde konut fiyat endeksi dengelendi.",
            published_at=datetime.now(timezone.utc).isoformat()
        ),
        RawArticle(
            guid="test_art_2",
            source_id="generic_blog",
            source_name="Blog",
            title="Sıradan Emlak Tavsiyeleri",
            url="https://blog.com/test",
            summary="Ev alırken dikkat edilecekler.",
            content="Boya badana kontrol edilmeli.",
            published_at=datetime.now(timezone.utc).isoformat()
        )
    ]

    tasks = director.plan_daily_research(raw_articles)
    assert len(tasks) >= 1
    top_task = tasks[0]
    assert top_task.priority >= 70
    assert len(top_task.key_questions) >= 3

    swarm_result = director.execute_swarm_investigation(raw_articles)
    assert swarm_result["scanned_signals_count"] == 2
    assert "summary_statement" in swarm_result
    assert len(swarm_result["research_queue"]) >= 1


def test_market_state_engine():
    """Tests dynamic macro market indices and regime transitions."""
    engine = MarketStateEngine()
    state = engine.get_current_state()
    assert 0.0 <= state.demand <= 100.0
    assert 0.0 <= state.supply <= 100.0
    assert 0.0 <= state.price_pressure <= 100.0
    assert isinstance(state.regime, MarketRegime)

    # Test regime heuristics
    assert engine.detect_regime(demand=85.0, supply=45.0, credit=60.0, rental=75.0, price_pressure=80.0) == MarketRegime.EXPANSION
    assert engine.detect_regime(demand=35.0, supply=40.0, credit=30.0, rental=50.0, price_pressure=40.0) == MarketRegime.STRESS
    assert engine.detect_regime(demand=50.0, supply=70.0, credit=50.0, rental=50.0, price_pressure=50.0) == MarketRegime.COOLING

    # Test district metrics
    beytepe_meta = engine.get_district_metrics("Beytepe")
    assert beytepe_meta["demand"] > 80.0
    assert beytepe_meta["m2_average_try"] > 60000.0


def test_swarm_database_helpers():
    """Tests SQLite persistence helpers for Swarm tables."""
    # 1. Research queue
    ok_q = save_research_task(
        task_id="test_task_001",
        priority=88,
        topic="Beytepe Villa Trendi",
        region="Beytepe",
        status="ACTIVE",
        payload={"notes": "Önemli piyasa sinyali"}
    )
    assert ok_q is True
    queue = get_research_queue(limit=10)
    assert any(t["task_id"] == "test_task_001" for t in queue)

    # 2. Market state history
    ok_state = save_market_state_snapshot({
        "demand": 78.5,
        "supply": 52.0,
        "credit": 64.0,
        "rental": 76.0,
        "price_pressure": 71.0,
        "investment_appetite": 82.0,
        "regime": "EXPANSION",
        "last_updated": datetime.now(timezone.utc).isoformat()
    })
    assert ok_state is True
    history = get_market_state_history(limit=5)
    assert len(history) > 0
    assert history[0]["regime"] == "EXPANSION"

    # 3. Emerging trends
    ok_trend = save_emerging_trend(
        trend_id="trend_test_001",
        topic="İncek Müstakil Parsel Talebi",
        region="İncek",
        velocity=1.85,
        signal_count=4,
        summary="İncek bölgesinde arsa talebinde haftalık %40 artış",
        first_seen="2026-03-01T00:00:00Z",
        last_seen="2026-03-07T00:00:00Z"
    )
    assert ok_trend is True
    trends = get_active_trends(limit=5)
    assert any(t["id"] == "trend_test_001" for t in trends)

    # 4. Research audit
    ok_audit = record_research_audit(
        research_id="audit_run_test_001",
        agents_used=["NewsDiscoveryAgent", "ContrarianAgent", "FactCheckerAgent"],
        scores={"score": 85},
        result={"verdict": "Verified"}
    )
    assert ok_audit is True


def test_swarm_api_endpoints(client):
    """Tests the Swarm REST API routes in app.py."""
    # 1. Swarm Status
    res_status = client.get("/api/intelligence/swarm/status")
    assert res_status.status_code == 200
    data_status = res_status.get_json()
    assert data_status["ok"] is True
    assert "active_swarm_agents" in data_status
    assert data_status["zero_fill_threshold"] == 80
    assert "swarm_summary" in data_status

    # 2. Swarm Market State
    res_ms = client.get("/api/intelligence/swarm/market-state")
    assert res_ms.status_code == 200
    data_ms = res_ms.get_json()
    assert data_ms["ok"] is True
    assert "demand" in data_ms["market_state"]
    assert "regime" in data_ms["market_state"]
    assert "Beytepe" in data_ms["market_state"]["regional_indices"]

    # 3. Swarm Trends
    res_tr = client.get("/api/intelligence/swarm/trends")
    assert res_tr.status_code == 200
    data_tr = res_tr.get_json()
    assert data_tr["ok"] is True
    assert isinstance(data_tr["trends"], list)

    # 4. Swarm Investigate (On-demand)
    res_inv = client.post("/api/intelligence/swarm/investigate", json={
        "topic": "Beytepe Lüks Konut Fiyat Dinamikleri",
        "region": "Beytepe",
        "content": "Beytepe bölgesinde yeni villa projeleri satışa çıktı, TCMB faiz kararı sonrası alıcı ilgisi arttı."
    })
    assert res_inv.status_code == 200
    data_inv = res_inv.get_json()
    assert data_inv["ok"] is True
    assert "epistemology" in data_inv
    assert "what_we_know" in data_inv["epistemology"]
    assert "what_we_infer" in data_inv["epistemology"]
    assert "what_we_suspect" in data_inv["epistemology"]
    assert "what_we_dont_know" in data_inv["epistemology"]
    assert "contrarian_analysis" in data_inv
    assert "counter_hypothesis" in data_inv["contrarian_analysis"]
    assert "specialist_context" in data_inv
    assert data_inv["advisor"]["name"] == "Yiğit Narin"


def test_article_epistemology_persistence_and_sync(client):
    """Tests that Swarm epistemological fields are saved, loaded, and synced across DB, API, and JSON."""
    from intelligence.models import IntelligenceArticle, ContentStatus, ImpactScore, RegionEntity, TopicEntity
    from intelligence.db import save_article, get_article_by_slug_or_id, get_published_articles
    import json
    from pathlib import Path

    art = IntelligenceArticle(
        id="art_test_epistemic_01",
        slug="test-epistemic-beytepe-analizi",
        title="Beytepe Ultra-Lüks Villa Talebi ve Fiyat Trendleri Analizi",
        summary="Beytepe bölgesinde lüks konut talebinde artış gözlemlenmektedir.",
        content="Beytepe bölgesinde yeni müstakil projeler geliştiriciler tarafından satışa çıkarıldı...",
        image_url="https://images.unsplash.com/photo-1600607687939-ce8a6c25118c",
        category="Konut",
        read_time="3 dk",
        status=ContentStatus.PUBLISHED,
        what_we_know="TCMB ve tapu kayıtlarına göre Beytepe'de m² birim fiyatı 88.000 TL seviyesindedir.",
        what_we_infer="Arz kısıtı ve yüksek arsa maliyeti birim fiyatları yukarı yönlü desteklemektedir.",
        what_we_suspect="Kurumsal yatırımcıların yılın ikinci yarısında toplu blok alımları gerçekleştirebileceği izlenmektedir.",
        what_we_dont_know="Yeni imar aksının resmi altyapı teslim takvimi henüz belediyece açıklanmamıştır.",
        contrarian_view={
          "counter_hypothesis": "Mevduat faizlerinin yüksekliği likiditeyi geciktirebilir.",
          "verdict": "Piyasa etkisi teyit edildi ancak risk marjı dikkate alınmalıdır."
        },
        why_this_news={
          "importance_score": 92,
          "evidence_score": 95,
          "market_impact_score": 88,
          "regional_relevance_score": 96,
          "selection_reason": "Ankara Prime Lokasyon"
        },
        locations=[RegionEntity(name="Beytepe")],
        topics=[TopicEntity(name="Konut")]
    )

    # 1. Save and retrieve
    saved = save_article(art)
    assert saved is True

    loaded = get_article_by_slug_or_id("test-epistemic-beytepe-analizi")
    assert loaded is not None
    assert loaded.what_we_know == art.what_we_know
    assert loaded.what_we_infer == art.what_we_infer
    assert loaded.what_we_suspect == art.what_we_suspect
    assert loaded.what_we_dont_know == art.what_we_dont_know
    assert loaded.contrarian_view.get("counter_hypothesis") == "Mevduat faizlerinin yüksekliği likiditeyi geciktirebilir."
    assert loaded.why_this_news.get("importance_score") == 92

    # 2. Check /api/blog/posts
    res_blog = client.get("/api/blog/posts")
    assert res_blog.status_code == 200
    blog_data = res_blog.get_json()
    assert blog_data["ok"] is True
    assert len(blog_data["data"]) > 0
    matched = next((p for p in blog_data["data"] if p.get("slug") == "test-epistemic-beytepe-analizi"), None)
    assert matched is not None
    assert matched.get("what_we_know") == art.what_we_know

    # 3. Check /api/intelligence/feed
    res_feed = client.get("/api/intelligence/feed")
    assert res_feed.status_code == 200
    feed_data = res_feed.get_json()
    assert feed_data["ok"] is True
    assert len(feed_data["data"]) > 0
