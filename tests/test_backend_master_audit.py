# -*- coding: utf-8 -*-
"""
test_backend_master_audit.py
Coldwell Banker VIP Ankara • Yiğit Narin
Kapsamlı Uçtan Uca Backend Mimari Denetim ve Entegrasyon Test Paketi
"""

import os
import sys
import json
import glob
import time
import sqlite3
import py_compile
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================================
# 1. SYNTAX & COMPILATION TEST
# =====================================================================
def test_all_python_files_compile():
    """Tüm kök ve alt dizin Python dosyalarının sözdizimi (syntax) hatasız olduğunu doğrular."""
    py_files = list(BASE_DIR.glob("*.py")) + list(BASE_DIR.glob("intelligence/**/*.py"))
    assert len(py_files) >= 10, "Yeterli Python dosyası bulunamadı"
    
    compiled_count = 0
    for pf in py_files:
        if ".venv" in str(pf) or "env" in str(pf):
            continue
        try:
            py_compile.compile(str(pf), doraise=True)
            compiled_count += 1
        except Exception as e:
            pytest.fail(f"Python derleme hatası {pf.name}: {e}")
    assert compiled_count >= 10

# =====================================================================
# 2. DATA STORE & SCHEMA INTEGRITY
# =====================================================================
def test_json_datastores_validity():
    """Tüm kritik JSON veri depolarının geçerli ve bozulmamış olduğunu doğrular."""
    critical_jsons = [
        BASE_DIR / "projects_map.json",
        BASE_DIR / "static" / "data" / "cached_cb_listings.json",
        BASE_DIR / "static" / "data" / "portfolio_persona_intelligence.json",
        BASE_DIR / "static" / "data" / "latest_news.json",
        BASE_DIR / "static" / "data" / "market_state.json",
        BASE_DIR / "static" / "data" / "portfolio_listing_dashboards.json"
    ]
    for cj in critical_jsons:
        if cj.exists():
            with open(cj, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data is not None
                if cj.name == "projects_map.json":
                    assert len(data) >= 30, "Projeler haritasında beklenen proje sayısı eksik"
                elif cj.name == "cached_cb_listings.json":
                    assert len(data) >= 5, "Canlı CB ilanları listesi eksik"

def test_sqlite_databases_integrity():
    """Tüm SQLite veritabanlarında PRAGMA integrity_check yapar."""
    db_paths = [
        BASE_DIR / "nexa_database.db",
        BASE_DIR / "data" / "intelligence.db",
        BASE_DIR / "intelligence.db"
    ]
    checked = 0
    for dbp in db_paths:
        if dbp.exists():
            conn = sqlite3.connect(str(dbp))
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            res = cur.fetchone()
            conn.close()
            assert res is not None and res[0] == "ok", f"Veritabanı bozuk: {dbp.name}"
            checked += 1
    assert checked >= 1, "En az bir SQLite veritabanı doğrulanmalıdır"

# =====================================================================
# 3. AI PERSONA SWARM (4 AJAN) MOTORU
# =====================================================================
def test_persona_swarm_multicategory_generation():
    """Persona Swarm motorunun Konut, Ticari/Ofis, Arsa ve Villa tiplerinde eksiksiz çalıştığını doğrular."""
    from intelligence.swarm.persona_swarm import PersonaSwarmSynthesizer
    synthesizer = PersonaSwarmSynthesizer()

    test_cases = [
        {
            "title": "Cinnah Cadde Üzeri 5+1 Kiralık İş Yeri Ofis",
            "type": "Kiralık",
            "property_type": "Ofis",
            "price": "₺120.000 / ay",
            "loc": "Çankaya, Ayrancı",
            "rooms": "5+1"
        },
        {
            "title": "Kırıkkale Yahşihan Tek Tapu 7.820 m2 Satılık Arsa",
            "type": "Satılık",
            "property_type": "Arsa",
            "price": "₺9.500.000",
            "loc": "Yahşihan",
            "rooms": ""
        },
        {
            "title": "Çamlıdere Müstakil Taş Villa Doğal Yaşam",
            "type": "Satılık",
            "property_type": "Müstakil",
            "price": "₺14.000.000",
            "loc": "Çamlıdere",
            "rooms": "4+1"
        },
        {
            "title": "ANKAPORT SARAY - Mega Ticari AVM Hisseli Karma Proje",
            "type": "Satılık",
            "property_type": "Ticari",
            "price": "550.000 TL Peşin",
            "loc": "Saray, Kahramankazan",
            "rooms": "Ofis & Mağaza"
        }
    ]

    for tc in test_cases:
        intel = synthesizer.generate_intelligence(tc)
        assert intel.get("ok") is True
        assert "swarm_metadata" in intel
        assert intel["swarm_metadata"]["agents_count"] == 4
        assert len(intel["top_personas"]) >= 1
        
        # Skor aralığı kontrolü
        top_score = intel["top_personas"][0]["score"]
        assert 50 <= top_score <= 100, f"Skor mantıksız: {top_score}"

        # Dürüst danışman / anti-persona kontrolü
        anti_personas = intel.get("auditor_analysis", {}).get("anti_personas", [])
        assert len(anti_personas) >= 1, "Anti-persona (uygun olmayan kitle) eksik"
        assert "advisory_honesty_note" in intel.get("auditor_analysis", {})

# =====================================================================
# 4. NEXA SOCIAL AUTOPILOT PLANLAMA & ROTASYON
# =====================================================================
def test_social_autopilot_full_coverage_and_rotation():
    """Haftalık sosyal paylaşım planının 35 proje ve 11 ilanı %100 kapsadığını doğrular."""
    from nexa_social_autopilot import get_weekly_social_plan, synthesize_algorithmic_hook

    plan = get_weekly_social_plan()
    assert plan.get("success") is True
    assert "weekly_schedule" in plan
    assert len(plan["weekly_schedule"]) == 7

    # Gün kontrolleri
    today_found = False
    all_projects = set()
    all_listings = set()

    for day in plan["weekly_schedule"]:
        if day["is_today"]:
            today_found = True
        assert day["hero_item"] is not None, f"{day['day_name']} için hero öğe bulunamadı"
        assert "hook" in day and len(day["hook"]) > 10
        assert len(day["channels"]) >= 2
        assert len(day["format"]) > 5

        for item in day["thematic_pool"]:
            if item["type"] == "project":
                all_projects.add(item["id"])
            else:
                all_listings.add(item["id"])
            
            # Kart persona doğrulaması
            assert "top_persona" in item
            assert "persona_score" in item
            assert "anti_persona" in item
            assert "hook" in item

    assert today_found, "Bugünün planı tespit edilemedi"
    assert len(all_projects) >= 30, f"Proje havuzu eksik: {len(all_projects)}"
    assert len(all_listings) >= 10, f"İlan havuzu eksik: {len(all_listings)}"

def test_social_post_package_generation():
    """Sosyal stüdyo post paketinin 4 formatta ve persona raporuyla üretildiğini doğrular."""
    from nexa_social_autopilot import generate_social_post_package

    pkg = generate_social_post_package("prj-03", item_type="project")
    assert pkg is not None
    assert "critical_specs" in pkg
    assert "persona_report" in pkg
    assert "instagram" in pkg
    assert "reels" in pkg
    assert "linkedin" in pkg
    assert "whatsapp" in pkg

    # Instagram içeriği
    assert len(pkg["instagram"]["caption"]) > 50
    assert "#ColdwellBankerVIP" in pkg["instagram"]["hashtags"]

    # Reels senaryosu
    assert pkg["reels"]["duration_sec"] == 25
    assert len(pkg["reels"]["script_steps"]) >= 4

    # Persona raporu
    p_rep = pkg["persona_report"]
    assert len(p_rep["top_personas"]) >= 1
    assert len(p_rep["anti_personas"]) >= 1

# =====================================================================
# 5. FLASK API VE SAYFA ROUTE TESTLERİ
# =====================================================================
@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_core_html_routes(client):
    """Ana şablon sayfalarının HTTP 200 döndürdüğünü doğrular."""
    routes = ["/", "/crm", "/projeler", "/ilanlar", "/haber", "/sunum", "/admin"]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"{r} sayfası hata verdi: {resp.status_code}"

def test_social_planner_endpoints(client):
    """Sosyal planlayıcı API endpoint'lerinin doğru JSON döndürdüğünü doğrular."""
    # 1. Weekly plan
    resp = client.get("/api/crm/social-planner/weekly")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["weekly_schedule"]) == 7

    # 2. Generate post
    post_payload = {
        "item_id": "prj-03",
        "item_type": "project",
        "day_name": "Pazartesi",
        "theme": "Rasyonel / Yatırım & B2B"
    }
    resp_gen = client.post("/api/crm/social-planner/generate-post", json=post_payload)
    assert resp_gen.status_code == 200
    gen_data = resp_gen.get_json()
    assert gen_data["success"] is True
    assert "persona_report" in gen_data["data"]

def test_persona_intelligence_api(client):
    """Persona istihbarat API'sinin hem ilan hem proje için çalıştığını doğrular."""
    # Proje sorgusu
    resp_p = client.get("/api/portfolio/persona-intelligence?title=ANKAPORT+-+SARAY")
    assert resp_p.status_code == 200
    data_p = resp_p.get_json()
    assert data_p["ok"] is True
    assert len(data_p["data"]["top_personas"]) >= 1

    # İlan sorgusu
    resp_l = client.get("/api/portfolio/persona-intelligence?title=Cinnah+Cadde+Üzerinde")
    assert resp_l.status_code == 200
    data_l = resp_l.get_json()
    assert data_l["ok"] is True

def test_api_robustness_on_malformed_input(client):
    """Hatalı ve eksik girişlerde API'nin çökmeden (graceful fallback) yanıt verdiğini doğrular."""
    # Boş post isteği
    resp = client.post("/api/crm/social-planner/generate-post", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True  # Güvenli varsayılan mülk döndürür

    # Olmayan id ile persona sorgusu
    resp_missing = client.get("/api/portfolio/persona-intelligence?title=BILINMEYEN_MULK_XYZ_999")
    assert resp_missing.status_code == 200
    data_m = resp_missing.get_json()
    assert data_m["ok"] is True
    assert len(data_m["data"]["top_personas"]) >= 1
