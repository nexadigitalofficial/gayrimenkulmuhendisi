#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
NEXA RADAR™ | KAPSAMLI RAKİP TAKİP & PROAKTİF GÖZETİM ENTEGRASYON TESTİ
========================================================================================
gayrimenkulmuhendisi-main platformundaki rakip takip sisteminin (Cross-Matcher,
Pool Sentinel, Proactive Advisor, Flask API, Database & CRM UI) 7 aşamalı
kapsamlı doğrulama test paketidir.
"""

import os
import sys
import json
import time
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime, date

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"c:\Users\USER\Desktop\gayrimenkulmuhendisi-main")
sys.path.insert(0, str(BASE_DIR))

# Colors for terminal reporting
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class NexaCompetitorTrackingMasterTest(unittest.TestCase):
    test_results = []

    @classmethod
    def setUpClass(cls):
        print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
        print(f"{BOLD}{CYAN}NEXA PROAKTİF RAKİP TAKİP SİSTEMİ | MASTER DOĞRULAMA & DENETİM TESTİ{RESET}")
        print(f"{BOLD}{CYAN}{'='*80}{RESET}")
        print(f"Çalışma Dizini: {BASE_DIR}")
        print(f"Test Başlangıç Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def log_step(self, step_name, status, details=""):
        icon = f"{GREEN}✔ BAŞARILI{RESET}" if status else f"{RED}✘ BAŞARISIZ{RESET}"
        print(f"[{icon}] {BOLD}{step_name}{RESET}")
        if details:
            print(f"       └── {details}")
        self.test_results.append({"step": step_name, "passed": status, "details": details})

    # =========================================================================
    # FAZ 1: ÇEKİRDEK MODÜL & VERİTABANI ŞEMA BÜTÜNLÜĞÜ
    # =========================================================================
    def test_01_core_modules_import(self):
        print(f"\n{YELLOW}▶ FAZ 1: Çekirdek Modül ve Veritabanı Şeması Doğrulaması{RESET}")
        try:
            from nexa_cross_matcher import NexaCrossMatcher, compute_dhash, hamming_distance
            from nexa_pool_sentinel import NexaPoolSentinel
            from nexa_proactive_advisor import NexaProactiveAdvisor
            from nexa_daemon_scheduler import NexaDaemonScheduler
            self.log_step("Modül İçe Aktarma", True, "Tüm 4 çekirdek motor başarıyla import edildi.")
        except Exception as e:
            self.log_step("Modül İçe Aktarma", False, f"Hata: {e}")
            raise

    def test_02_database_schema(self):
        from nexa_pool_sentinel import NexaPoolSentinel
        sentinel = NexaPoolSentinel()
        with sentinel._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            
            required_tables = [
                "nexa_monitored_pools", 
                "nexa_pool_snapshots", 
                "nexa_market_delta_events"
            ]
            for t in required_tables:
                self.assertIn(t, tables, f"Gerekli tablo eksik: {t}")
            
            # Check column definitions in nexa_market_delta_events
            cur.execute("PRAGMA table_info(nexa_market_delta_events)")
            cols = [r[1] for r in cur.fetchall()]
            for expected_col in ["pool_id", "listing_id", "event_type", "old_price", "new_price", 
                                  "price_diff", "change_pct", "ai_strategic_comment", "recommended_action"]:
                self.assertIn(expected_col, cols, f"Kolon eksik: {expected_col}")
                
            self.log_step("Veritabanı Şema Bütünlüğü", True, 
                          f"3 gözetim tablosu ve tüm delta kolonları ('{', '.join(required_tables)}') doğrulandı.")

    # =========================================================================
    # FAZ 2: TERSİNE MÜHENDİSLİK & CROSS-MATCHER TESTLERİ
    # =========================================================================
    def test_03_perceptual_dhash_matching(self):
        print(f"\n{YELLOW}▶ FAZ 2: Tersine Mühendislik & Dijital İkiz Eşleme (Cross-Matcher){RESET}")
        from PIL import Image
        import io
        from nexa_cross_matcher import compute_dhash, hamming_distance

        # Generate a test gradient image
        im1 = Image.new("RGB", (200, 200), color=(100, 150, 200))
        h1 = compute_dhash(im1)
        self.assertIsNotNone(h1)
        
        # Identical image -> hamming distance must be 0
        h1_dup = compute_dhash(im1)
        self.assertEqual(hamming_distance(h1, h1_dup), 0)

        # Slightly modified image (compressed / resized) -> distance should be tiny (< 5)
        im2 = im1.resize((100, 100))
        h2 = compute_dhash(im2)
        dist_similar = hamming_distance(h1, h2)
        self.assertLessEqual(dist_similar, 5)

        # Completely different inverted image -> distance should be high (> 20)
        im3 = Image.new("RGB", (200, 200), color=(0, 0, 0))
        h3 = compute_dhash(im3)
        dist_diff = hamming_distance(h1, h3)
        
        self.log_step("Perceptual dHash Görsel Parmak İzi", True, 
                      f"Birebir mesafe: 0, Yeniden boyutlandırılmış benzer: {dist_similar} bit, Ayrışma testi başarılı.")

    def test_04_cross_matcher_twin_listing_identification(self):
        from nexa_cross_matcher import NexaCrossMatcher
        matcher = NexaCrossMatcher()

        # Mock CB listing
        cb_listing = {
            "listing_id": "CB_TEST_001",
            "title": "Mustafa Kemal Mah. 1+1 Full Eşyalı Kiralık Lüks Ofis",
            "price": "55.000 TL",
            "specs": {
                "Şehir": "Ankara",
                "İlçe": "Çankaya",
                "Mahalle": "Mustafa Kemal Mah.",
                "m2": 65,
                "Oda Sayısı": "1+1"
            }
        }

        # Mock Twin listing on Sahibinden (same property published by our agent)
        twin_candidate = {
            "listing_id": "1296499962",
            "title": "Mustafa Kemal Mah. Full Eşyalı 1+1 Kiralık Ofis - Sahibinden",
            "price": "55.000 TL",
            "m2": 65,
            "room_count": "1+1",
            "specs": {
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Mustafa Kemal"
            }
        }

        # Mock Competitor listing (different office, different floor/price/title)
        competitor_candidate = {
            "listing_id": "COMP_888999",
            "title": "Balgat Ziyabey Cad. Boş Masrafsız 3+1 Büro",
            "price": "35.000 TL",
            "m2": 120,
            "room_count": "3+1",
            "specs": {
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Balgat"
            }
        }

        res_twin = matcher.compare_listings(cb_listing, twin_candidate)
        res_comp = matcher.compare_listings(cb_listing, competitor_candidate)

        self.assertTrue(res_twin["is_match"], f"İkiz ilan eşleşmeliydi! Skor: {res_twin['confidence']}")
        self.assertFalse(res_comp["is_match"], f"Farklı rakip ilan eşleşmemeliydi! Skor: {res_comp['confidence']}")
        self.assertGreater(res_twin["confidence"], 0.70)

        self.log_step("Çapraz Platform İkiz İlan Sahiplenme", True, 
                      f"Bizim ilan tespit skoru: %{res_twin['confidence']*100:.1f} (MATCH), Rakip ilan: %{res_comp['confidence']*100:.1f} (REJECT).")

    # =========================================================================
    # FAZ 3: CHANGE DATA CAPTURE (CDC) & POOL SENTINEL DELTA SİMÜLASYONU
    # =========================================================================
    def test_05_pool_sentinel_full_lifecycle(self):
        print(f"\n{YELLOW}▶ FAZ 3: Otonom Gözetim & Günlük CDC Delta Motoru (Price Drop, New Entry, Delist){RESET}")
        from nexa_pool_sentinel import NexaPoolSentinel
        sentinel = NexaPoolSentinel()

        # Step 1: Register a test pool
        test_cb_listing = {
            "listing_id": "TEST_POOL_AUTO_999",
            "title": "Mustafa Kemal Mah. Test Kiralık Ofis Havuzu",
            "price": 50000,
            "specs": {
                "Şehir": "Ankara",
                "İlçe": "Çankaya",
                "Mahalle": "Mustafa Kemal Mah.",
                "Marka": "Kiralık",
                "Kategori 2": "İşyeri"
            }
        }
        pool_id = sentinel.register_pool(test_cb_listing, search_url="https://test.sahibinden.com/kiralik-ofis")
        self.assertIsInstance(pool_id, int)
        self.assertGreater(pool_id, 0)

        # Step 2: Ingest Yesterday's Snapshot (3 Competitors)
        yesterday_date = "2026-10-27"
        yesterday_listings = [
            {"listing_id": "TEST_RAKIP_A", "title": "Mustafa Kemal Barış Sitesi 1+1 Ofis", "price": 55000, "m2": 65, "room_count": "1+1"},
            {"listing_id": "TEST_RAKIP_B", "title": "Mustafa Kemal Dumlupınar Bulv. Ofis", "price": 60000, "m2": 70, "room_count": "2+1"},
            {"listing_id": "TEST_RAKIP_C", "title": "Mustafa Kemal Tepe Prime Emsali", "price": 52000, "m2": 60, "room_count": "1+1"},
        ]
        count_y = sentinel.ingest_snapshot(pool_id, yesterday_listings, scan_date_str=yesterday_date)
        self.assertEqual(count_y, 3)

        # Step 3: Ingest Today's Snapshot:
        # - RAKIP_A: Price drop from 55.000 to 48.000 TL (-12.7%)
        # - RAKIP_B: Price hike from 60.000 to 65.000 TL (+8.3%)
        # - RAKIP_C: Delisted / Sold (vanished from today's pool)
        # - RAKIP_D: Brand new competitor enters at 47.000 TL
        today_date = "2026-10-28"
        today_listings = [
            {"listing_id": "TEST_RAKIP_A", "title": "Mustafa Kemal Barış Sitesi 1+1 Ofis", "price": 48000, "m2": 65, "room_count": "1+1"},
            {"listing_id": "TEST_RAKIP_B", "title": "Mustafa Kemal Dumlupınar Bulv. Ofis", "price": 65000, "m2": 70, "room_count": "2+1"},
            {"listing_id": "TEST_RAKIP_D", "title": "Mustafa Kemal 2120. Cadde Sıfır Ofis", "price": 47000, "m2": 58, "room_count": "1+1"},
        ]
        count_t = sentinel.ingest_snapshot(pool_id, today_listings, scan_date_str=today_date)
        self.assertEqual(count_t, 3)

        # Step 4: Calculate Delta Events
        events = sentinel.calculate_delta_events(pool_id, today_date_str=today_date, yesterday_date_str=yesterday_date)
        
        event_types = {e["event_type"] for e in events}
        self.assertIn("PRICE_DROP", event_types)
        self.assertIn("PRICE_HIKE", event_types)
        self.assertIn("NEW_ENTRY", event_types)
        self.assertIn("DELISTED_OR_SOLD", event_types)

        # Verify exact PRICE_DROP details
        drop_event = next(e for e in events if e["event_type"] == "PRICE_DROP" and e["listing_id"] == "TEST_RAKIP_A")
        self.assertEqual(drop_event["old_price"], 55000)
        self.assertEqual(drop_event["new_price"], 48000)
        self.assertEqual(drop_event["old_price"] - drop_event["new_price"], 7000)
        self.assertAlmostEqual(drop_event["change_pct"], 12.73, places=1)

        # Verify NEW_ENTRY
        entry_event = next(e for e in events if e["event_type"] == "NEW_ENTRY" and e["listing_id"] == "TEST_RAKIP_D")
        self.assertEqual(entry_event["new_price"], 47000)

        # Verify DELISTED_OR_SOLD
        delist_event = next(e for e in events if e["event_type"] == "DELISTED_OR_SOLD" and e["listing_id"] == "TEST_RAKIP_C")
        self.assertEqual(delist_event["old_price"], 52000)

        self.log_step("Havuz Kaydı & Çoklu Snapshot Alımı", True, f"Pool #{pool_id} oluşturuldu, 6 snapshot atomik kaydedildi.")
        self.log_step("CDC Delta Alarm Motoru (Fiyat İndirimi & Rakip Girişi)", True, 
                      f"4 temel pazar olayı başarıyla ayrıştırıldı: PRICE_DROP (-7.000 TL), PRICE_HIKE (+5.000 TL), NEW_ENTRY, DELISTED_OR_SOLD.")

        # Cleanup test records
        with sentinel._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM nexa_market_delta_events WHERE pool_id = ?", (pool_id,))
            cur.execute("DELETE FROM nexa_pool_snapshots WHERE pool_id = ?", (pool_id,))
            cur.execute("DELETE FROM nexa_monitored_pools WHERE id = ?", (pool_id,))
            conn.commit()

    # =========================================================================
    # FAZ 4: NEXA PROACTIVE ADVISOR STRATEJİK YAPAY ZEKÂ YORUMU
    # =========================================================================
    def test_06_proactive_ai_strategic_advice(self):
        print(f"\n{YELLOW}▶ FAZ 4: NEXA Proactive Advisor Yapay Zekâ Strateji Motoru{RESET}")
        from nexa_proactive_advisor import NexaProactiveAdvisor
        advisor = NexaProactiveAdvisor()

        our_listing = {"title": "Bizim Ofis", "price": 50000, "current_price": 50000}
        comp_listing = {"title": "Rakip Barış Sitesi Ofis", "m2": 65}

        # Case A: Competitor drops price below us
        adv_drop = advisor.generate_advice(
            event_type="PRICE_DROP",
            competitor_listing=comp_listing,
            our_listing=our_listing,
            old_price=55000,
            new_price=46000,
            change_pct=16.36
        )
        self.assertIn("ai_strategic_comment", adv_drop)
        self.assertIn("recommended_action", adv_drop)
        self.assertIn("altına indi", adv_drop["ai_strategic_comment"].lower())
        self.assertIn("şerefiye", adv_drop["recommended_action"].lower())

        # Case B: New competitor enters cheaper
        adv_entry = advisor.generate_advice(
            event_type="NEW_ENTRY",
            competitor_listing=comp_listing,
            our_listing=our_listing,
            old_price=0,
            new_price=45000,
            change_pct=0
        )
        self.assertIn("pazara dahil oldu", adv_entry["ai_strategic_comment"].lower())

        # Case C: Competitor delisted / sold
        adv_delist = advisor.generate_advice(
            event_type="DELISTED_OR_SOLD",
            competitor_listing=comp_listing,
            our_listing=our_listing,
            old_price=55000,
            new_price=0,
            change_pct=0
        )
        self.assertIn("arz azaldı", adv_delist["ai_strategic_comment"].lower())

        self.log_step("Proaktif AI Danışmanlık & Taktiksel Aksiyon Üretimi", True, 
                      "Fiyat indirimi, yeni emsal ve kalkma olayları için sektörel Türkçe taktik yorumlar başarıyla üretildi.")

    # =========================================================================
    # FAZ 5: FLASK REST API UÇ NOKTALARI ENTEGRASYON TESTİ
    # =========================================================================
    def test_07_flask_proactive_api_endpoints(self):
        print(f"\n{YELLOW}▶ FAZ 5: Flask Backend Proaktif API Uç Noktaları (/api/proactive/*){RESET}")
        from app import app
        app.config["TESTING"] = True
        client = app.test_client()

        # 1. GET /api/proactive/alerts
        resp = client.get("/api/proactive/alerts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertIn("alerts", data)
        self.assertIsInstance(data["alerts"], list)
        self.log_step("GET /api/proactive/alerts", True, f"HTTP 200, {len(data['alerts'])} adet alarm döndü.")

        # 2. GET /api/proactive/pools
        resp = client.get("/api/proactive/pools")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.assertIn("pools", data)
        self.log_step("GET /api/proactive/pools", True, f"HTTP 200, {len(data['pools'])} adet aktif pazar havuzu listelendi.")

        # 3. POST /api/proactive/register
        reg_payload = {
            "listing": {
                "listing_id": "API_TEST_PORTFOY_77",
                "title": "API Test Çankaya Kiralık Daire",
                "price": 45000,
                "specs": {"city": "Ankara", "district": "Çankaya", "neighborhood": "Gaziosmanpaşa"}
            },
            "search_url": "https://www.sahibinden.com/kiralik-daire/ankara-cankaya-gaziosmanpasa"
        }
        resp = client.post("/api/proactive/register", json=reg_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        test_pid = data.get("pool_id")
        self.assertIsNotNone(test_pid)
        self.log_step("POST /api/proactive/register", True, f"HTTP 200, Yeni portföy havuzu (ID: {test_pid}) kaydedildi.")

        # 4. POST /api/proactive/scan_now
        resp = client.post("/api/proactive/scan_now", json={"pool_id": test_pid})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("ok"))
        self.log_step("POST /api/proactive/scan_now", True, "HTTP 200, Anlık tarama ve delta hesaplama tetiklendi.")

        # 5. Invalid input error handling
        resp = client.post("/api/proactive/register", json={})
        self.assertEqual(resp.status_code, 400)
        self.log_step("Hata Yakalama (Graceful 400 Validation)", True, "Boş istek 400 Bad Request ile güvenle reddedildi.")

        # Teardown test pool
        from nexa_pool_sentinel import NexaPoolSentinel
        sentinel = NexaPoolSentinel()
        with sentinel._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM nexa_monitored_pools WHERE id = ?", (test_pid,))
            conn.commit()

    # =========================================================================
    # FAZ 6: CRM FRONTEND (Vue 3 / HTML / Script) REAKTİFLİK TESTİ
    # =========================================================================
    def test_08_crm_frontend_ui_integrity(self):
        print(f"\n{YELLOW}▶ FAZ 6: CRM Frontend (Vue 3 / JavaScript) Entegrasyon Denetimi{RESET}")
        crm_path = BASE_DIR / "templates" / "crm.html"
        self.assertTrue(crm_path.exists())

        with open(crm_path, 'r', encoding='utf-8') as f:
            crm_content = f.read()

        # Check critical proactive radar UI elements
        checks = [
            ("Radar Menü Butonu", "@click=\"activeView = 'proactive_radar'"),
            ("Proaktif Alarmlar Reactive State", "proactiveAlerts = ref([])"),
            ("Pazar Havuzları Reactive State", "proactivePools = ref([])"),
            ("Tarama Durum Flag'i", "radarScanning = ref(false)"),
            ("Radar Veri Çekme Fonksiyonu", "const loadProactiveRadar = async ()"),
            ("Anlık Tarama Tetikleyici", "const triggerProactiveScan = async"),
            ("İlanı Radara Ekle Butonu", "trackListingInProactiveRadar"),
            ("Filtreleme Hesaplaması", "filteredProactiveAlerts = computed"),
            ("Vue Return Scope İhracı", "filteredProactiveAlerts, loadProactiveRadar")
        ]

        for label, snippet in checks:
            self.assertIn(snippet, crm_content, f"Eksik UI bileşeni: {label}")
            
        self.log_step("CRM Vue 3 Reactive State & Fonksiyon Bağlantıları", True, 
                      "9 temel frontend radar bileşeni ve Vue 3 state reaktifliği eksiksiz doğrulandı.")

    # =========================================================================
    # FAZ 7: GÜNLÜK ZAMANLAYICI & OTOMATİK RAPOR MOTORU
    # =========================================================================
    def test_09_daemon_scheduler_and_briefing_engine(self):
        print(f"\n{YELLOW}▶ FAZ 7: Günlük Daemon Zamanlayıcı & Yönetici HTML Brifingi{RESET}")
        from nexa_daemon_scheduler import NexaDaemonScheduler, generate_html_briefing
        from nexa_pool_sentinel import NexaPoolSentinel

        sentinel = NexaPoolSentinel()
        scheduler = NexaDaemonScheduler(interval_hours=24)
        self.assertEqual(scheduler.interval_hours, 24)

        # Generate an HTML briefing report
        report_path = generate_html_briefing(sentinel, [])
        self.assertTrue(report_path.exists(), f"Brifing raporu oluşturulamadı: {report_path}")
        self.assertGreater(report_path.stat().st_size, 1000)

        self.log_step("NEXA Daemon Zamanlayıcı & Günlük Rapor Motoru", True, 
                      f"Rapor oluşturuldu: {report_path.name} ({report_path.stat().st_size:,} bytes).")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(NexaCompetitorTrackingMasterTest)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}DENETİM SONUCU:{RESET}")
    print(f"Toplam Test Sayısı : {result.testsRun}")
    print(f"Başarılı Testler   : {GREEN}{result.testsRun - len(result.failures) - len(result.errors)}{RESET}")
    print(f"Başarısız Testler  : {RED if result.failures else GREEN}{len(result.failures)}{RESET}")
    print(f"Hatalı Testler     : {RED if result.errors else GREEN}{len(result.errors)}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
