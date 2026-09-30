#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions CI Sync Orchestrator
Sıra: CB Sync → Data Import → Self-Healing → AI Summaries
Hata yakalama + loglama + exit code yönetimi ile.
"""

import sys
import os
import traceback
import logging
import time
from datetime import datetime

# Proje kök dizinini path'e ekle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ci_sync")


def run_step(name: str, func, *args, **kwargs) -> tuple[bool, str]:
    """Tek bir adımı çalıştır, hata yakala, süre ölç."""
    log.info("▶ %s başlıyor...", name)
    t0 = time.time()
    try:
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            if result.get("errors") and len(result["errors"]) > 0 and result.get("upserted", 0) == 0 and result.get("fetched", 0) > 0:
                dt = time.time() - t0
                log.error("✗ %s KISMİ/TAM HATA (%.1fs): %s", name, dt, result["errors"])
                return False, f"{name} FAILED: {result['errors'][:2]}"
            if "health_score" in result and result["health_score"] < 60:
                dt = time.time() - t0
                log.error("✗ %s KRİTİK SAĞLIK SKORU: %%%d", name, result["health_score"])
                return False, f"{name} LOW HEALTH SCORE: {result['health_score']}%"
        dt = time.time() - t0
        log.info("✓ %s tamam (%.1fs)", name, dt)
        return True, f"{name} OK ({dt:.1f}s)"
    except Exception as e:
        dt = time.time() - t0
        log.error("✗ %s HATA (%.1fs): %s", name, dt, e)
        log.debug(traceback.format_exc())
        return False, f"{name} FAILED: {e}"


def sync_site_html_embedded():
    import json
    import re
    site_path = os.path.join(BASE_DIR, "templates", "site.html")
    if not os.path.exists(site_path):
        site_path = os.path.join(BASE_DIR, "site.html")
    pm_path = os.path.join(BASE_DIR, "projects_map.json")
    port_path = os.path.join(BASE_DIR, "nexa_portfolio_data.json")

    if not (os.path.exists(site_path) and os.path.exists(pm_path)):
        return {"updated": 0, "msg": "files missing"}

    with open(pm_path, "r", encoding="utf-8") as f:
        pm_data = json.load(f)
    projects = pm_data.get("projects", []) if isinstance(pm_data, dict) else pm_data

    listings = []
    if os.path.exists(port_path):
        with open(port_path, "r", encoding="utf-8") as f:
            port_data = json.load(f)
        for idx, p in enumerate(port_data, 1):
            title = p.get("title") or p.get("name")
            if not title:
                continue
            price_val = p.get("price_numeric") or p.get("price") or 0
            price_disp = p.get("price_display") or (f"{price_val:,} TL".replace(",", ".") if price_val else "Fiyat Sorunuz")
            listings.append({
                "id": p.get("id") or f"cbvip-port-{idx}",
                "title": title,
                "type": p.get("type") or ("Kiralık" if "kiralık" in title.lower() else "Satılık"),
                "listing_type": p.get("listing_type") or ("Kiralık" if "kiralık" in title.lower() else "Satılık"),
                "price_display": str(price_disp).replace("₺", "TL"),
                "price": price_val,
                "location": p.get("location") or f"{p.get('ilce', 'Çankaya')}, {p.get('il', 'Ankara')}",
                "il": p.get("il") or "Ankara",
                "ilce": p.get("ilce") or "Çankaya",
                "mahalle": p.get("mahalle") or "",
                "room_info": p.get("room_info") or p.get("rooms") or "Daire",
                "property_category": p.get("property_category") or p.get("category") or "Portföy",
                "thumbnail": p.get("thumbnail") or f"/static/img/video_thumbs/video_thumb_{idx}.jpg",
                "link": p.get("link") or f"/portfolio/{idx}"
            })

    with open(site_path, "r", encoding="utf-8") as f:
        content = f.read()

    p_json = json.dumps(projects, ensure_ascii=False, indent=2)
    l_json = json.dumps(listings, ensure_ascii=False, indent=2)

    content = re.sub(r"const EMBEDDED_PROJECTS = \[.*?\];\n", f"const EMBEDDED_PROJECTS = {p_json};\n", content, flags=re.DOTALL)
    content = re.sub(r"const EMBEDDED_LISTINGS = \[.*?\];\n", f"const EMBEDDED_LISTINGS = {l_json};\n", content, flags=re.DOTALL)

    with open(site_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"updated": 1, "projects": len(projects), "listings": len(listings)}


def main():
    log.info("=" * 60)
    log.info("CI SYNC BAŞLADI — %s", datetime.utcnow().isoformat())
    log.info("=" * 60)

    results = []
    any_failed = False

    # 1. CB.com.tr Senkronizasyonu
    try:
        from scripts.nexa_cb_sync import sync_once
        ok, msg = run_step("CB Sync", sync_once, verbose=True)
    except ImportError:
        ok, msg = False, "CB Sync modülü bulunamadı (scripts/nexa_cb_sync.py)"
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # 2. Sales & Financial Miner (Kanonik Bilgi Grafiği ve Fiyatları İşle)
    try:
        from scripts.nexa_sales_miner import sync_sales_knowledge
        ok, msg = run_step("Sales Miner", sync_sales_knowledge)
    except ImportError:
        ok, msg = False, "Sales Miner modülü bulunamadı (scripts/nexa_sales_miner.py)"
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # 3. Data Importer (DB → JSON fiyat/oda çıkarma)
    try:
        import nexa_data_importer
        ok, msg = run_step("Data Importer", nexa_data_importer.main)
    except ImportError:
        ok, msg = False, "Data Importer modülü bulunamadı (nexa_data_importer.py)"
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # 4. Self-Healing (DB şema + kanonik veri + RAG + NLP)
    try:
        import nexa_self_healing
        ok, msg = run_step("Self-Healing", nexa_self_healing.run_full_self_healing_cycle)
    except ImportError:
        ok, msg = False, "Self-Healing modülü bulunamadı (nexa_self_healing.py)"
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # 5. AI Summaries (Gemini ile proje özetleri)
    try:
        import nexa_rag
        ok, msg = run_step("AI Summaries", nexa_rag.generate_all_project_summaries)
    except ImportError:
        ok, msg = False, "RAG modülü bulunamadı (nexa_rag.py)"
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # 6. Frontend Static Hydration (site.html EMBEDDED_PROJECTS & EMBEDDED_LISTINGS güncellemesi)
    ok, msg = run_step("Frontend Hydration", sync_site_html_embedded)
    results.append((ok, msg))
    if not ok:
        any_failed = True

    # Özet
    log.info("=" * 60)
    log.info("CI SYNC ÖZET")
    log.info("=" * 60)
    for ok, msg in results:
        status = "✓" if ok else "✗"
        log.info("  %s %s", status, msg)

    log.info("=" * 60)

    if any_failed:
        log.error("CI SYNC KISMİ BAŞARISIZ — exit code 1")
        sys.exit(1)

    log.info("CI SYNC TAM BAŞARILI — exit code 0")
    sys.exit(0)


if __name__ == "__main__":
    main()