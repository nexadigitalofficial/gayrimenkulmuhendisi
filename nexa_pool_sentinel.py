#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
NEXA POOL SENTINEL™ | Otonom Pazar Havuzu Gözetimi & Günlük CDC Delta Motoru
========================================================================================
Pazar havuzlarını sürekli takip eden, dünkü ve bugünkü snapshot'ları atomik olarak
karşılaştırıp FİYAT İNDİRİMLERİNİ, YENİ RAKİP GİRİŞLERİNİ ve KALKAN İLANLARI
anında yakalayan, yapay zekâ stratejisiyle CRM sistemine alarm basan nöbetçi motor.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Reconfigure stdout for Windows console UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from nexa_cross_matcher import NexaCrossMatcher, extract_numeric_price
from nexa_proactive_advisor import NexaProactiveAdvisor

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "intelligence.db"


class NexaPoolSentinel:
    """
    Central Surveillance & Change Data Capture (CDC) Sentinel.
    Maintains daily snapshots of competitive pools and produces actionable alarms.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        if not self.db_path.exists():
            # Fallback path if in another folder
            alt_path = Path(r"c:\Users\USER\Desktop\gayrimenkulmuhendisi-main\data\intelligence.db")
            if alt_path.exists():
                self.db_path = alt_path
        self.matcher = NexaCrossMatcher()
        self.advisor = NexaProactiveAdvisor()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # 1. POOL REGISTRATION (Havuz Kaydı & Sahiplenme)
    # =========================================================================
    def register_pool(
        self,
        cb_listing: dict,
        search_url: Optional[str] = None
    ) -> int:
        """
        Registers a Coldwell Banker (or CRM) listing as a monitored market pool.
        Constructs the search URL if missing, returns pool_id.
        """
        cb_id = str(cb_listing.get("listing_id") or cb_listing.get("ilan_no") or "").strip()
        title = cb_listing.get("title") or cb_listing.get("baslik") or f"Portföy #{cb_id}"
        price = extract_numeric_price(cb_listing.get("price") or cb_listing.get("fiyat"))
        
        specs = cb_listing.get("specs", {})
        city = specs.get("Şehir") or specs.get("city") or "Ankara"
        district = specs.get("İlçe") or specs.get("district") or "Çankaya"
        neigh = specs.get("Mahalle") or specs.get("neighborhood") or specs.get("Mahalle (detay)") or ""
        
        kat2 = specs.get("Kategori 2") or "Konut"
        marka = specs.get("Marka") or "Satılık"
        category_slug = f"{marka.lower()}-{kat2.lower()}".replace(" ", "-")

        # If search URL is not explicitly given, construct a standard Sahibinden search URL
        if not search_url:
            from nexa_reverse_cma_engine import NexaOrbitReverseCMA
            orbit = NexaOrbitReverseCMA()
            search_url, _ = orbit.reverse_engineer_search_url(cb_listing)

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO nexa_monitored_pools 
                (cb_listing_id, sahibinden_listing_id, title, category_slug, location_path, 
                 city, district, neighborhood, current_price, pool_search_url, is_active, last_scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(cb_listing_id) DO UPDATE SET
                    current_price=excluded.current_price,
                    pool_search_url=excluded.pool_search_url,
                    last_scanned_at=CURRENT_TIMESTAMP
            """, (cb_id, cb_id, title, category_slug, f"{city}/{district}/{neigh}",
                  city, district, neigh, price, search_url))
            conn.commit()
            
            cur.execute("SELECT id FROM nexa_monitored_pools WHERE cb_listing_id = ?", (cb_id,))
            pool_id = cur.fetchone()[0]
            return pool_id

    # =========================================================================
    # 2. INGEST POOL SNAPSHOT (Günlük Anlık Görüntü Kaydı)
    # =========================================================================
    def ingest_snapshot(
        self,
        pool_id: int,
        listings: List[dict],
        scan_date_str: Optional[str] = None
    ) -> int:
        """
        Saves a snapshot of listings for the given pool_id on scan_date.
        Identifies our own listing in the pool.
        """
        target_date = scan_date_str or date.today().isoformat()
        
        # Get monitored pool info to match our own listing
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM nexa_monitored_pools WHERE id = ?", (pool_id,))
            pool_row = cur.fetchone()
            if not pool_row:
                raise ValueError(f"Pool #{pool_id} bulunamadı!")
            cb_listing = dict(pool_row)

            # Delete any previous snapshot for the same date to allow idempotency
            cur.execute("DELETE FROM nexa_pool_snapshots WHERE pool_id = ? AND scan_date = ?", (pool_id, target_date))

            inserted_count = 0
            for item in listings:
                lid = str(item.get("listing_id") or item.get("id") or "").strip()
                title = item.get("title") or item.get("baslik") or f"İlan #{lid}"
                price = extract_numeric_price(item.get("price") or item.get("fiyat"))
                m2 = item.get("m2_gross") or item.get("m2") or 0
                room = item.get("room_count") or item.get("oda") or ""
                floor = item.get("floor") or item.get("kat") or ""
                age = item.get("building_age") or item.get("yas") or ""
                detail_url = item.get("detail_url") or item.get("url") or f"https://www.sahibinden.com/ilan/{lid}/detay"
                
                # Check if this item is our twin listing
                match_res = self.matcher.compare_listings(cb_listing, item)
                is_ours = 1 if match_res["is_match"] else 0

                cur.execute("""
                    INSERT INTO nexa_pool_snapshots 
                    (pool_id, listing_id, title, price, m2_gross, room_count, floor, building_age,
                     detail_url, is_our_listing, scan_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (pool_id, lid, title, price, m2, room, floor, age, detail_url, is_ours, target_date))
                inserted_count += 1

            conn.commit()
            return inserted_count

    # =========================================================================
    # 3. CDC DELTA CALCULATION & ALARM GENERATION (Fiyat İndirimi & Değişim Yakalama)
    # =========================================================================
    def calculate_delta_events(
        self,
        pool_id: int,
        today_date_str: Optional[str] = None,
        yesterday_date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Compares today's snapshot against yesterday's snapshot for a pool.
        Generates PRICE_DROP, PRICE_HIKE, NEW_ENTRY, DELISTED_OR_SOLD alarms.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # Fetch pool info
            cur.execute("SELECT * FROM nexa_monitored_pools WHERE id = ?", (pool_id,))
            pool_info = dict(cur.fetchone())

            # Find the two most recent scan dates if not explicitly provided
            if not today_date_str or not yesterday_date_str:
                cur.execute("""
                    SELECT DISTINCT scan_date FROM nexa_pool_snapshots 
                    WHERE pool_id = ? ORDER BY scan_date DESC LIMIT 2
                """, (pool_id,))
                dates = [row[0] for row in cur.fetchall()]
                if len(dates) < 2:
                    # Only 1 snapshot exists, cannot calculate delta yet
                    return []
                today_date_str = dates[0]
                yesterday_date_str = dates[1]

            # Fetch yesterday's listings: {listing_id: dict}
            cur.execute("SELECT * FROM nexa_pool_snapshots WHERE pool_id = ? AND scan_date = ?", (pool_id, yesterday_date_str))
            yesterday_items = {row["listing_id"]: dict(row) for row in cur.fetchall()}

            # Fetch today's listings: {listing_id: dict}
            cur.execute("SELECT * FROM nexa_pool_snapshots WHERE pool_id = ? AND scan_date = ?", (pool_id, today_date_str))
            today_items = {row["listing_id"]: dict(row) for row in cur.fetchall()}

            # Identify our listing info
            our_listing = next((v for v in today_items.values() if v.get("is_our_listing")), None) or pool_info

            events_created = []

            # 1. Check for Price Changes & Existing Listings
            for lid, today_item in today_items.items():
                if lid in yesterday_items:
                    old_price = yesterday_items[lid]["price"]
                    new_price = today_item["price"]

                    if old_price > 0 and new_price > 0 and old_price != new_price:
                        price_diff = old_price - new_price
                        change_pct = round(abs(price_diff) / old_price * 100, 2)

                        if new_price < old_price:
                            event_type = "PRICE_DROP"
                            summary = f"🚨 FİYAT İNDİRİMİ: {today_item['title']} fiyatını {old_price:,.0f} TL'den {new_price:,.0f} TL'ye düşürdü (%{change_pct:.1f} İNDİRİM)"
                        else:
                            event_type = "PRICE_HIKE"
                            summary = f"📈 FİYAT ARTIŞI: {today_item['title']} fiyatını {old_price:,.0f} TL'den {new_price:,.0f} TL'ye artırdı (+%{change_pct:.1f})"

                        advice = self.advisor.generate_advice(
                            event_type=event_type,
                            competitor_listing=today_item,
                            our_listing=our_listing,
                            old_price=old_price,
                            new_price=new_price,
                            change_pct=change_pct
                        )

                        cur.execute("""
                            INSERT INTO nexa_market_delta_events 
                            (pool_id, listing_id, event_type, old_price, new_price, price_diff, change_pct,
                             event_summary, ai_strategic_comment, recommended_action, is_our_listing, is_read)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """, (pool_id, lid, event_type, old_price, new_price, price_diff, change_pct,
                              summary, advice["ai_strategic_comment"], advice["recommended_action"],
                              today_item.get("is_our_listing", 0)))
                        
                        events_created.append({
                            "event_type": event_type,
                            "listing_id": lid,
                            "summary": summary,
                            "old_price": old_price,
                            "new_price": new_price,
                            "change_pct": change_pct,
                            "ai_comment": advice["ai_strategic_comment"],
                            "recommended_action": advice["recommended_action"]
                        })

                else:
                    # 2. Check for NEW COMPETITOR ENTRY
                    event_type = "NEW_ENTRY"
                    summary = f"🆕 YENİ RAKİP İLAN: {today_item['title']} ({today_item['price']:,.0f} TL) pazara girdi."
                    advice = self.advisor.generate_advice(
                        event_type=event_type,
                        competitor_listing=today_item,
                        our_listing=our_listing,
                        old_price=0,
                        new_price=today_item["price"],
                        change_pct=0
                    )
                    cur.execute("""
                        INSERT INTO nexa_market_delta_events 
                        (pool_id, listing_id, event_type, old_price, new_price, price_diff, change_pct,
                         event_summary, ai_strategic_comment, recommended_action, is_our_listing, is_read)
                        VALUES (?, ?, ?, 0, ?, 0, 0, ?, ?, ?, ?, 0)
                    """, (pool_id, lid, event_type, today_item["price"],
                          summary, advice["ai_strategic_comment"], advice["recommended_action"],
                          today_item.get("is_our_listing", 0)))

                    events_created.append({
                        "event_type": event_type,
                        "listing_id": lid,
                        "summary": summary,
                        "new_price": today_item["price"],
                        "ai_comment": advice["ai_strategic_comment"],
                        "recommended_action": advice["recommended_action"]
                    })

            # 3. Check for DELISTED OR SOLD (In yesterday's list, but missing today)
            for lid, yesterday_item in yesterday_items.items():
                if lid not in today_items:
                    event_type = "DELISTED_OR_SOLD"
                    summary = f"🏁 RAKİP İLAN KALKTI / SATILDI: {yesterday_item['title']} ({yesterday_item['price']:,.0f} TL) yayından kaldırıldı."
                    advice = self.advisor.generate_advice(
                        event_type=event_type,
                        competitor_listing=yesterday_item,
                        our_listing=our_listing,
                        old_price=yesterday_item["price"],
                        new_price=0,
                        change_pct=0
                    )
                    cur.execute("""
                        INSERT INTO nexa_market_delta_events 
                        (pool_id, listing_id, event_type, old_price, new_price, price_diff, change_pct,
                         event_summary, ai_strategic_comment, recommended_action, is_our_listing, is_read)
                        VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, 0)
                    """, (pool_id, lid, event_type, yesterday_item["price"],
                          summary, advice["ai_strategic_comment"], advice["recommended_action"],
                          yesterday_item.get("is_our_listing", 0)))

                    events_created.append({
                        "event_type": event_type,
                        "listing_id": lid,
                        "summary": summary,
                        "old_price": yesterday_item["price"],
                        "ai_comment": advice["ai_strategic_comment"],
                        "recommended_action": advice["recommended_action"]
                    })

            conn.commit()
            return events_created

    # =========================================================================
    # 4. QUERY ACTIVE ALERTS FOR CRM UI (Alarmları Listeleme)
    # =========================================================================
    def get_alerts(self, pool_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns proactive market delta alarms for CRM consumption."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if pool_id:
                cur.execute("""
                    SELECT e.*, p.title as pool_title, p.category_slug, p.location_path, p.current_price as our_price,
                           p.pool_search_url, p.store_name
                    FROM nexa_market_delta_events e
                    JOIN nexa_monitored_pools p ON e.pool_id = p.id
                    WHERE e.pool_id = ?
                    ORDER BY e.created_at DESC LIMIT ?
                """, (pool_id, limit))
            else:
                cur.execute("""
                    SELECT e.*, p.title as pool_title, p.category_slug, p.location_path, p.current_price as our_price,
                           p.pool_search_url, p.store_name
                    FROM nexa_market_delta_events e
                    JOIN nexa_monitored_pools p ON e.pool_id = p.id
                    ORDER BY e.created_at DESC LIMIT ?
                """, (limit,))
            return [dict(r) for r in cur.fetchall()]


if __name__ == "__main__":
    print("[NEXA POOL SENTINEL] Testing registration, simulation & CDC delta detection...")
    sentinel = NexaPoolSentinel()

    # 1. Register a test pool
    test_cb = {
        "listing_id": "1345396672",
        "title": "Kavaklıdere'de Satılık Daire | Merkezi Konum",
        "price": "7.500.000 ₺",
        "specs": {
            "Şehir": "Ankara",
            "İlçe": "Çankaya",
            "Mahalle": "Kavaklıdere",
            "Kategori 2": "Konut",
            "Marka": "Satılık"
        }
    }
    pool_id = sentinel.register_pool(test_cb, search_url="https://www.sahibinden.com/satilik-daire/ankara-cankaya-kavaklidere")
    print(f"Registered Pool ID: {pool_id}")

    # 2. Simulate Yesterday's Snapshot
    yesterday_data = [
        {"listing_id": "1345396672", "title": "Kavaklıdere Satılık Daire (Bizim Portföy)", "price": 7500000},
        {"listing_id": "999001", "title": "Kavaklıdere Tunalı 3+1 Daire (Rakip A)", "price": 8200000},
        {"listing_id": "999002", "title": "Kavaklıdere Esat Cad. 2+1 (Rakip B)", "price": 6800000},
        {"listing_id": "999003", "title": "Kavaklıdere Kuğulu Park Yakını (Rakip C)", "price": 9500000}
    ]
    sentinel.ingest_snapshot(pool_id, yesterday_data, scan_date_str="2026-10-26")

    # 3. Simulate Today's Snapshot:
    #   - Rakip A dropped price from 8.2M -> 7.1M (PRICE DROP!)
    #   - Rakip C delisted / sold (DELISTED_OR_SOLD!)
    #   - Rakip D entered the market at 7.4M (NEW_ENTRY!)
    today_data = [
        {"listing_id": "1345396672", "title": "Kavaklıdere Satılık Daire (Bizim Portföy)", "price": 7500000},
        {"listing_id": "999001", "title": "Kavaklıdere Tunalı 3+1 Daire (Rakip A)", "price": 7100000}, # dropped!
        {"listing_id": "999002", "title": "Kavaklıdere Esat Cad. 2+1 (Rakip B)", "price": 6800000},
        {"listing_id": "999004", "title": "Kavaklıdere Bestekar 3+1 (Rakip D)", "price": 7400000}  # new entry!
    ]
    sentinel.ingest_snapshot(pool_id, today_data, scan_date_str="2026-10-27")

    # 4. Compute Delta & Alarms
    alarms = sentinel.calculate_delta_events(pool_id, today_date_str="2026-10-27", yesterday_date_str="2026-10-26")
    print(f"\n[OK] Delta Calculated! Total Generated Alarms: {len(alarms)}")
    for a in alarms:
        print(f"\n[{a['event_type']}] {a['summary']}")
        print(f"  🤖 AI Yorumu: {a['ai_comment']}")
        print(f"  💡 Aksiyon: {a['recommended_action']}")
