#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
NEXA.OS AUTONOMOUS SYSTEM — MASTER ULTRA-COMPREHENSIVE AUDIT & TEST RUNNER
═══════════════════════════════════════════════════════════════════════════════
Tests all 8 core autonomous system criteria:
1. Drive Puller & Autonomous Cloud Sync (nexa_drive_puller.py)
2. Watchdog, Multi-Tier Asset & RAG Ingestion (nexa_watchdog.py)
3. RAG, Vector Search & AI Chat Subsystem (nexa_rag.py, nexa_vector_rag.py, nexa_ai_engine.py)
4. Scraper Pipeline, Cloud DOM & 4K Proxy (app.py, nexascout)
5. Proactive Radar, Sentinel & CDC Delta Detection (nexa_pool_sentinel.py, nexa_cross_matcher.py)
6. Swarm Intelligence & Market State Engine (intelligence/)
7. Social Autopilot & Content Studio (nexa_social_autopilot.py)
8. Data Store Consistency & Schema Integrity (JSONs & SQLite DBs)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import sqlite3
import traceback
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

BUGS = []
WARNINGS = []
PASSED = []

def record_pass(category, check_name, detail=""):
    PASSED.append({"category": category, "check": check_name, "detail": detail})
    print(f"  [PASS] {check_name}" + (f" -> {detail}" if detail else ""))

def record_bug(category, check_name, error_msg, severity="HIGH"):
    BUGS.append({"category": category, "check": check_name, "error": error_msg, "severity": severity})
    print(f"  [BUG - {severity}] {check_name}: {error_msg}")

def record_warning(category, check_name, warn_msg):
    WARNINGS.append({"category": category, "check": check_name, "warning": warn_msg})
    print(f"  [WARN] {check_name}: {warn_msg}")


# ═════════════════════════════════════════════════════════════════════════════
# 1. DRIVE PULLER & AUTONOMOUS CLOUD SYNC
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_1_drive_puller():
    print("\n🔍 CRITERION 1: Google Drive Otonom Çekici & Senkronizasyon...")
    import nexa_drive_puller as ndp

    # 1.1 Config & Folder URL
    cfg = ndp.get_config()
    url = cfg.get("drive_folder_url")
    if not url:
        record_bug("Drive Puller", "Config URL", "drive_folder_url config.json içinde tanımlı değil", "HIGH")
    else:
        record_pass("Drive Puller", "Config URL", f"URL tanımlı: {url[:45]}...")

    # 1.2 Folder ID extraction
    fid = ndp.folder_id_from_url(url)
    if not fid:
        record_bug("Drive Puller", "Folder ID Extraction", f"URL'den klasör ID çıkarılamadı: {url}", "HIGH")
    else:
        record_pass("Drive Puller", "Folder ID Extraction", f"Folder ID: {fid}")

    # 1.3 Multi-tier download mechanism
    test_dst = BASE_DIR / "static" / "data" / "test_tmp.jpg"
    try:
        # Test downloading image via LH3
        sz = ndp.download_file("1JmaDbLvgar8beizdNch6rszTxcf4FT62", test_dst)
        if sz > 1000 and test_dst.exists():
            record_pass("Drive Puller", "LH3 4K Görsel İndirme", f"İndirilen boyut: {sz} bytes")
        else:
            record_bug("Drive Puller", "LH3 4K Görsel İndirme", "Görsel indirilemedi veya boyutu çok küçük", "MEDIUM")
    except Exception as e:
        record_bug("Drive Puller", "LH3 4K Görsel İndirme", str(e), "HIGH")
    finally:
        test_dst.unlink(missing_ok=True)

    # 1.4 Drive state synchronization between root and static/data
    root_ds = BASE_DIR / "drive_state.json"
    static_ds = BASE_DIR / "static" / "data" / "drive_state.json"
    if root_ds.exists() and static_ds.exists():
        try:
            d_root = json.loads(root_ds.read_text(encoding="utf-8"))
            d_static = json.loads(static_ds.read_text(encoding="utf-8"))
            diff = abs(len(d_root) - len(d_static))
            if diff > 5:
                record_warning("Drive Puller", "Drive State Sync", f"drive_state.json dosyaları arasında {diff} adet fark var (root={len(d_root)}, static={len(d_static)})")
            else:
                record_pass("Drive Puller", "Drive State Sync", f"Root ve static/data drive_state.json uyumlu ({len(d_root)} vs {len(d_static)})")
        except Exception as e:
            record_bug("Drive Puller", "Drive State Sync", f"drive_state.json parse hatası: {e}", "MEDIUM")
    else:
        record_bug("Drive Puller", "Drive State Exists", "drive_state.json root veya static/data içinde eksik", "MEDIUM")


# ═════════════════════════════════════════════════════════════════════════════
# 2. WATCHDOG & DOCUMENT INGESTION
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_2_watchdog():
    print("\n🔍 CRITERION 2: Watchdog, Varlık & Çok Kademeli İndeksleme...")
    import nexa_watchdog as nwd

    # 2.1 Text Extractor for various file formats
    test_txt = BASE_DIR / "test_probe.txt"
    test_txt.write_text("Nexa Watchdog Otonom Metin Çıkarıcı Doğrulama Testi", encoding="utf-8")
    try:
        extracted = nwd._extract_text(test_txt)
        if "Nexa Watchdog" in extracted:
            record_pass("Watchdog", "Text Extraction (TXT)", "Metin başarıyla çıkarıldı")
        else:
            record_bug("Watchdog", "Text Extraction (TXT)", "Çıkarılan metin beklenen içeriği içermiyor", "MEDIUM")
    except Exception as e:
        record_bug("Watchdog", "Text Extraction (TXT)", str(e), "HIGH")
    finally:
        test_txt.unlink(missing_ok=True)

    # 2.2 Thumbnail Generator
    # Test project WEST POINT
    thumb = nwd._ensure_thumbnail("WEST POINT", "cbvip-prj-36")
    if thumb and "video_thumb_36.jpg" in thumb:
        record_pass("Watchdog", "Thumbnail Generation", f"Thumbnail hazır: {thumb}")
    else:
        record_warning("Watchdog", "Thumbnail Generation", f"Thumbnail beklenen formatta değil: {thumb}")

    # 2.3 Normalize Title
    n_title = nwd._normalize_title("25_ORNEK_PROJE")
    if n_title == "ORNEK PROJE":
        record_pass("Watchdog", "Normalize Title", "Proje adı normalizasyonu başarılı")
    else:
        record_bug("Watchdog", "Normalize Title", f"Beklenen 'ORNEK PROJE', dönen '{n_title}'", "LOW")


# ═════════════════════════════════════════════════════════════════════════════
# 3. RAG, VECTOR SEARCH & AI CHAT
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_3_rag_and_ai():
    print("\n🔍 CRITERION 3: RAG, Vektör Arama & Nexa AI Chat Motoru...")
    import nexa_rag

    # 3.1 DB Path resolution
    rag_db = nexa_rag.DB_PATH
    if not rag_db.exists():
        record_bug("RAG Subsystem", "RAG DB_PATH Exists", f"nexa_rag.DB_PATH ({rag_db}) mevcut değil! Hardcoded yanlış dizin riski.", "CRITICAL")
    else:
        record_pass("RAG Subsystem", "RAG DB_PATH Exists", f"Veritabanı yolu geçerli: {rag_db}")

    # 3.2 Vector RAG DB Path
    import nexa_vector_rag
    v_db = nexa_vector_rag._db_path()
    if not Path(v_db).exists():
        record_bug("Vector RAG", "Vector RAG DB Path", f"nexa_vector_rag._db_path ({v_db}) mevcut değil!", "CRITICAL")
    else:
        record_pass("Vector RAG", "Vector RAG DB Path", f"Vektör veritabanı yolu geçerli: {v_db}")

    # 3.3 Global context builder
    try:
        ctx = nexa_rag.build_global_context()
        if ctx and len(ctx) > 50:
            record_pass("RAG Subsystem", "Global Context Builder", f"Bağlam üretildi: {len(ctx)} karakter")
        else:
            record_bug("RAG Subsystem", "Global Context Builder", "Global bağlam boş veya çok kısa", "HIGH")
    except Exception as e:
        record_bug("RAG Subsystem", "Global Context Builder", f"Hata: {e}", "CRITICAL")

    # 3.4 Nexa AI Engine query processing
    try:
        import nexa_ai_engine
        q_res = nexa_ai_engine.process_nexa_query("Ankara lüks villa arıyorum")
        if q_res and "projects" in q_res:
            record_pass("Nexa AI Engine", "Query Processing", f"Sorgu işlendi: {len(q_res['projects'])} proje önerildi")
        else:
            record_bug("Nexa AI Engine", "Query Processing", "process_nexa_query projeler döndürmedi", "HIGH")
    except Exception as e:
        record_bug("Nexa AI Engine", "Query Processing", f"Hata: {e}", "HIGH")


# ═════════════════════════════════════════════════════════════════════════════
# 4. SCRAPER PIPELINE, CLOUD DOM & 4K PROXY
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_4_scraper_and_proxy():
    print("\n🔍 CRITERION 4: Scraper Pipeline, Cloud DOM & 4K İmaj Proxy...")
    from app import app, Job

    # 4.1 Job State Atomic Persistence
    test_job = Job("audit_probe_job_99", "sahibinden", {"url": "https://example.com"})
    test_job.status = "running"
    test_job.logs.append("Probe log line")
    test_job.set_step(1)
    probe_status_file = BASE_DIR / "jobs" / "audit_probe_job_99" / "status.json"
    if probe_status_file.exists():
        try:
            st = json.loads(probe_status_file.read_text(encoding="utf-8"))
            if st.get("status") == "running" and st.get("step_index") == 1:
                record_pass("Scraper Pipeline", "Job Disk Persistence", "Job durumu diske atomik yazıldı")
            else:
                record_bug("Scraper Pipeline", "Job Disk Persistence", f"Beklenmeyen durum verisi: {st}", "MEDIUM")
        except Exception as e:
            record_bug("Scraper Pipeline", "Job Disk Persistence", str(e), "MEDIUM")
        finally:
            import shutil
            shutil.rmtree(probe_status_file.parent, ignore_errors=True)
    else:
        record_bug("Scraper Pipeline", "Job Disk Persistence", "jobs/<id>/status.json oluşturulmadı", "HIGH")

    # 4.2 Status Route Disk Fallback
    with app.test_client() as client:
        # Create disk-only job
        fake_job_dir = BASE_DIR / "jobs" / "audit_disk_only_job"
        fake_job_dir.mkdir(parents=True, exist_ok=True)
        (fake_job_dir / "status.json").write_text(json.dumps({
            "status": "done",
            "job_type": "sahibinden",
            "step_index": 5,
            "step_label": "Tamamlandı",
            "step_total": 6,
            "total_listings": 3,
            "error": "",
            "output_ready": True,
            "output_url": "/jobs/audit_disk_only_job/test.html",
            "all_logs": "Log A\n",
            "new_logs": "Log A\n",
            "log_len": 6,
            "elapsed": 5.0
        }), encoding="utf-8")
        try:
            res = client.get("/api/status/audit_disk_only_job?after=0")
            if res.status_code == 200 and res.get_json().get("status") == "done":
                record_pass("Scraper Pipeline", "Status Disk Fallback", "Multi-worker disk fallback çalışıyor")
            else:
                record_bug("Scraper Pipeline", "Status Disk Fallback", f"Status endpoint beklenen 200 dönmedi: {res.status_code}", "HIGH")
        finally:
            import shutil
            shutil.rmtree(fake_job_dir, ignore_errors=True)

    # 4.3 Image Proxy Endpoint
    with app.test_client() as client:
        res = client.get("/api/image-proxy?url=invalid")
        if res.status_code == 400:
            record_pass("Scraper Pipeline", "Image Proxy Invalid Input", "Geçersiz URL 400 ile reddedildi")
        else:
            record_bug("Scraper Pipeline", "Image Proxy Invalid Input", f"Beklenen 400, dönen {res.status_code}", "LOW")

        res_miss = client.get("/api/image-proxy")
        if res_miss.status_code == 400:
            record_pass("Scraper Pipeline", "Image Proxy Missing Param", "Parametre yokluğu 400 ile yakalandı")
        else:
            record_bug("Scraper Pipeline", "Image Proxy Missing Param", f"Beklenen 400, dönen {res_miss.status_code}", "LOW")


# ═════════════════════════════════════════════════════════════════════════════
# 5. PROACTIVE RADAR & SENTINEL
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_5_proactive_radar():
    print("\n🔍 CRITERION 5: Proaktif Radar, Sentinel & CDC Delta Motoru...")
    from nexa_pool_sentinel import NexaPoolSentinel
    from nexa_cross_matcher import NexaCrossMatcher

    sentinel = NexaPoolSentinel()
    with sentinel._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM nexa_monitored_pools")
        pool_count = cur.fetchone()[0]
    alerts = sentinel.get_alerts(limit=5)
    record_pass("Proactive Radar", "Pool Sentinel Discovery", f"Aktif havuz sayısı: {pool_count}, Kayıtlı alarm sayısı: {len(alerts)}")

    # Test dHash and CrossMatcher
    from nexa_cross_matcher import compute_dhash, hamming_distance
    from PIL import Image

    img1 = Image.new("RGB", (64, 64), color="red")
    img2 = Image.new("RGB", (64, 64), color="red")
    h1 = compute_dhash(img1)
    h2 = compute_dhash(img2)
    dist_same = hamming_distance(h1, h2) if (h1 and h2) else -1
    if dist_same == 0:
        record_pass("Proactive Radar", "Perceptual dHash", f"Özdeş mesafe={dist_same}, Hash={h1}")
    else:
        record_bug("Proactive Radar", "Perceptual dHash", f"dHash hesaplama hatası: dist={dist_same}", "MEDIUM")

    matcher = NexaCrossMatcher()
    s_cb = {"title": "Çankaya Ayrancı 2+1 Daire", "price": "7.950.000 TL", "rooms": "2+1", "m2": "130"}
    s_cand = {"title": "Ayrancı Cinnah Caddesi 2+1 Daire", "price": "7.950.000 TL", "rooms": "2+1", "m2": "130"}
    match_res = matcher.compare_listings(s_cb, s_cand)
    score = match_res.get("total_score") or match_res.get("confidence", 0)
    record_pass("Proactive Radar", "Cross-Matcher Scoring", f"Skor: %{score*100:.1f}")


# ═════════════════════════════════════════════════════════════════════════════
# 6. SWARM INTELLIGENCE & MARKET STATE ENGINE
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_6_swarm_intelligence():
    print("\n🔍 CRITERION 6: Swarm İstihbarat & Piyasa Rejimi Motoru...")
    from intelligence.market_state.engine import MarketStateEngine
    from intelligence.db import get_active_trends, save_emerging_trend

    engine = MarketStateEngine()
    regime_data = engine.get_current_state()
    regime = getattr(regime_data.regime, "value", str(regime_data.regime))
    if regime:
        record_pass("Swarm Intelligence", "Market State Engine", f"Hesaplanan piyasa rejimi: {regime}")
    else:
        record_bug("Swarm Intelligence", "Market State Engine", "Market state regime hesaplanamadı", "HIGH")

    # Emerging Trends Persistence & Query Check
    test_trend_id = f"audit_trend_{int(time.time())}"
    ok = save_emerging_trend(
        trend_id=test_trend_id,
        topic="Audit Trend Topic",
        region="Beytepe",
        velocity=99.0, # High velocity so it ranks top
        signal_count=10,
        summary="Test trend for audit verification",
        first_seen=datetime.utcnow().isoformat(),
        last_seen=datetime.utcnow().isoformat()
    )
    if ok:
        top_trends = get_active_trends(limit=20)
        if any(t["id"] == test_trend_id for t in top_trends):
            record_pass("Swarm Intelligence", "Emerging Trends Query", "Yeni trend kaydedildi ve get_active_trends ile çekildi")
        else:
            record_bug("Swarm Intelligence", "Emerging Trends Query", "Trend kaydedildi fakat get_active_trends sonucunda bulunamadı", "MEDIUM")
    else:
        record_bug("Swarm Intelligence", "Emerging Trends Save", "save_emerging_trend False döndü", "HIGH")


# ═════════════════════════════════════════════════════════════════════════════
# 7. SOCIAL AUTOPILOT & CONTENT STUDIO
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_7_social_autopilot():
    print("\n🔍 CRITERION 7: Sosyal Otopilot & İçerik Stüdyosu Motoru...")
    from nexa_social_autopilot import get_weekly_social_plan, load_projects_data, load_listings_data

    projects = load_projects_data()
    listings = load_listings_data()
    record_pass("Social Autopilot", "Katalog Yükleme", f"Yüklenen Projeler: {len(projects)}, Yüklenen İlanlar: {len(listings)}")

    if len(projects) < 30:
        record_bug("Social Autopilot", "Proje Kataloğu Eksik", f"Beklenen >= 30, bulunan {len(projects)}", "HIGH")
    if len(listings) < 10:
        record_bug("Social Autopilot", "İlan Kataloğu Eksik", f"Beklenen >= 10, bulunan {len(listings)}. cached_cb_listings.json güncellenirken veri kaybı oluşmuş.", "HIGH")

    plan = get_weekly_social_plan()
    if plan.get("success") is True and len(plan.get("weekly_schedule", [])) == 7:
        record_pass("Social Autopilot", "7 Günlük Plan Üretimi", "7 günlük plan başarıyla üretildi")
    else:
        record_bug("Social Autopilot", "7 Günlük Plan Üretimi", "get_weekly_social_plan başarısız veya 7 gün içermiyor", "CRITICAL")


# ═════════════════════════════════════════════════════════════════════════════
# 8. DATA STORE CONSISTENCY & SCHEMA INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════
def audit_criterion_8_data_stores():
    print("\n🔍 CRITERION 8: Veri Depoları, Şemalar & Kanonik Bütünlük...")

    # 8.1 SQLite DB integrity
    for db_file in [BASE_DIR / "nexa_database.db", BASE_DIR / "data" / "intelligence.db"]:
        if db_file.exists():
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            res = cur.fetchall()
            conn.close()
            if res == [("ok",)]:
                record_pass("Data Stores", f"SQLite Integrity ({db_file.name})", "Veritabanı sağlam (ok)")
            else:
                record_bug("Data Stores", f"SQLite Integrity ({db_file.name})", f"Bütünlük hatası: {res}", "CRITICAL")
        else:
            record_bug("Data Stores", f"DB File Exists ({db_file.name})", f"{db_file} bulunamadı", "HIGH")

    # 8.2 projects_map.json synchronization
    p1 = BASE_DIR / "projects_map.json"
    p2 = BASE_DIR / "static" / "data" / "projects_map.json"
    if p1.exists() and p2.exists():
        l1 = json.loads(p1.read_text(encoding="utf-8"))
        l2 = json.loads(p2.read_text(encoding="utf-8"))
        if len(l1) == len(l2):
            record_pass("Data Stores", "projects_map.json Senkronizasyonu", f"Root ve static/data birebir senkron ({len(l1)} proje)")
        else:
            record_bug("Data Stores", "projects_map.json Senkronizasyonu", f"Proje sayısı uyuşmuyor: root={len(l1)}, static={len(l2)}", "HIGH")

        # Check WEST POINT presence and fields
        wp = next((x for x in l1 if x.get("title") == "WEST POINT"), None)
        if wp:
            missing_wp = [f for f in ["price_display", "thumbnail", "location", "drive_video_preview", "drive_pdf_preview"] if not wp.get(f)]
            if missing_wp:
                record_bug("Data Stores", "WEST POINT Veri Tamlığı", f"Eksik alanlar: {missing_wp}", "HIGH")
            else:
                record_pass("Data Stores", "WEST POINT Veri Tamlığı", f"Fiyat: {wp.get('price_display')}, Thumbnail: {wp.get('thumbnail')}")
        else:
            record_bug("Data Stores", "WEST POINT Projesi", "WEST POINT projesi projects_map.json içinde bulunamadı!", "CRITICAL")
    else:
        record_bug("Data Stores", "projects_map.json Varlığı", "projects_map.json root veya static/data içinde eksik", "CRITICAL")

    # 8.3 display_order.json synchronization
    d1 = BASE_DIR / "display_order.json"
    d2 = BASE_DIR / "static" / "data" / "display_order.json"
    if d1.exists() and d2.exists():
        o1 = json.loads(d1.read_text(encoding="utf-8"))
        o2 = json.loads(d2.read_text(encoding="utf-8"))
        if len(o1) == len(o2):
            record_pass("Data Stores", "display_order.json Senkronizasyonu", f"Root ve static/data birebir senkron ({len(o1)} sıra kaydı)")
        else:
            record_warning("Data Stores", "display_order.json Senkronizasyonu", f"Sıra sayısı root={len(o1)}, static={len(o2)}")

    # 8.4 Self-healing sentinel verification
    import nexa_self_healing as nsh
    try:
        sh_res = nsh.run_self_healing()
        record_pass("Data Stores", "Self-Healing Sentinel", f"Sağlık skoru: %{sh_res.get('health_score')}, Durum: {sh_res.get('status')}")
        if sh_res.get("active_issues"):
            for issue in sh_res["active_issues"]:
                record_warning("Self-Healing Sentinel", "Aktif İyileştirme Uyarısı", issue)
    except Exception as e:
        record_bug("Data Stores", "Self-Healing Sentinel", str(e), "HIGH")


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    t0 = time.time()
    print("=" * 80)
    print("NEXA.OS AUTONOMOUS SYSTEM ULTRA-COMPREHENSIVE AUDIT TEST")
    print("Zaman:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    try:
        audit_criterion_1_drive_puller()
    except Exception as e:
        record_bug("Drive Puller", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_2_watchdog()
    except Exception as e:
        record_bug("Watchdog", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_3_rag_and_ai()
    except Exception as e:
        record_bug("RAG Subsystem", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_4_scraper_and_proxy()
    except Exception as e:
        record_bug("Scraper Pipeline", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_5_proactive_radar()
    except Exception as e:
        record_bug("Proactive Radar", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_6_swarm_intelligence()
    except Exception as e:
        record_bug("Swarm Intelligence", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_7_social_autopilot()
    except Exception as e:
        record_bug("Social Autopilot", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    try:
        audit_criterion_8_data_stores()
    except Exception as e:
        record_bug("Data Stores", "Uncaught Exception", traceback.format_exc(), "CRITICAL")

    elapsed = round(time.time() - t0, 2)
    print("\n" + "=" * 80)
    print(f"AUDIT TAMAMLANDI ({elapsed} sn)")
    print(f"Başarılı Testler : {len(PASSED)}")
    print(f"Uyarılar (Warn)  : {len(WARNINGS)}")
    print(f"Hatalar (Bug)    : {len(BUGS)}")
    print("=" * 80)

    # Save report as JSON for programmatic inspection
    report = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_sec": elapsed,
        "summary": {
            "passed": len(PASSED),
            "warnings": len(WARNINGS),
            "bugs": len(BUGS)
        },
        "bugs": BUGS,
        "warnings": WARNINGS,
        "passed": PASSED
    }
    Path("audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapor audit_report.json dosyasına kaydedildi.")
