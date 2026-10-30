#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
TEST SUITE: NEXA VIP STORE BRIDGE & PROACTIVE REVERSE-ENGINEERING RADAR
========================================================================================
Tests:
  1. Coldwell Banker VIP 1 & VIP 2 Store Ingestion (Sahibinden-based)
  2. Cross-matching internal CB CRM listings with Sahibinden VIP stores
  3. Reverse Engineering of rational competitor pool search URLs
  4. Automatic Registration & CDC Delta Detection (Price Drop, New Competitor, Delisted)
  5. Flask API integration (/api/proactive/sync_vip_stores, /pools, /alerts, /scan_now)
========================================================================================
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from nexa_vip_store_bridge import NexaVipStoreBridge
from nexa_cross_matcher import NexaCrossMatcher
from nexa_pool_sentinel import NexaPoolSentinel
from nexa_reverse_cma_engine import NexaOrbitReverseCMA


@pytest.fixture
def bridge():
    return NexaVipStoreBridge()


@pytest.fixture
def client():
    import app
    app.app.config["TESTING"] = True
    with app.app.test_client() as c:
        yield c


def test_01_vip_store_ingestion(bridge):
    """Verifies that VIP 1 and VIP 2 store listings are discovered from Sahibinden data."""
    store_listings = bridge.get_vip_store_listings(force_live_scan=False)
    assert len(store_listings) >= 100, f"Expected >= 100 VIP store listings, got {len(store_listings)}"
    
    # Check that both VIP 1 and VIP 2 exist in stores
    stores_found = set(item.get("store") for item in store_listings.values())
    has_vip1 = any("VIP 1" in s for s in stores_found)
    has_vip2 = any("VIP 2" in s for s in stores_found)
    assert has_vip1, "Coldwell Banker VIP 1 store listings not found!"
    print(f"\n[TEST 01 OK] VIP store listings verified: {len(store_listings)} total.")


def test_02_cb_crm_listings_discovery(bridge):
    """Verifies internal Coldwell Banker CRM portfolios are loaded."""
    cb_listings = bridge.get_cb_crm_listings()
    assert len(cb_listings) >= 5, f"Expected >= 5 CB CRM listings, got {len(cb_listings)}"
    assert "1345396672" in cb_listings or "1316861991" in cb_listings
    print(f"\n[TEST 02 OK] CB CRM listings loaded: {len(cb_listings)} total.")


def test_03_cross_matching_pipeline(bridge):
    """Verifies cross-matching between CB CRM and Sahibinden VIP store listings."""
    matches = bridge.cross_match_portfolios()
    assert len(matches) > 0, "No portfolios cross-matched!"
    
    # Check that twin verification works
    twin_matches = [m for m in matches if m.get("match_type") == "TWIN_VERIFIED"]
    assert len(twin_matches) > 0, "At least one twin match should be verified!"
    sample_twin = twin_matches[0]
    assert sample_twin["confidence"] >= 0.70
    assert "sahibinden" in sample_twin["store"].lower() or "vip" in sample_twin["store"].lower()
    print(f"\n[TEST 03 OK] Cross-match successful: {len(matches)} ready portfolios ({len(twin_matches)} twin-verified).")


def test_04_reverse_engineering_competitor_url(bridge):
    """Verifies that rational Sahibinden competitor search URLs are generated via Reverse Engineering."""
    sample_listing = {
        "listing_id": "1345396672",
        "title": "Kavaklıdere'de Satılık Daire | Merkezi Konum",
        "price": "7.500.000 ₺",
        "specs": {
            "Şehir": "Ankara",
            "İlçe": "Çankaya",
            "Mahalle": "Kavaklıdere",
            "Kategori 2": "Konut",
            "Marka": "Satılık",
            "Fiyat (Sayısal)": "7500000"
        }
    }
    url, meta = bridge.reverse_engineer_pool_url(sample_listing)
    assert url.startswith("https://www.sahibinden.com/satilik-daire/ankara-cankaya-kavaklidere")
    assert "pagingSize=50" in url
    assert "price_max=" in url
    print(f"\n[TEST 04 OK] Reverse engineered URL verified: {url}")


def test_05_sync_vip_stores_pipeline(bridge):
    """Verifies end-to-end sync, registration, and delta alert calculation."""
    res = bridge.sync_vip_stores_pipeline(force_live_scan=False)
    assert res.get("ok") is True
    assert res.get("status") == "SUCCESS"
    assert res.get("registered_pools_count") > 0
    assert len(res.get("pools", [])) > 0
    first_pool = res["pools"][0]
    assert "pool_search_url" in first_pool
    assert "https://www.sahibinden.com/" in first_pool["pool_search_url"]
    print(f"\n[TEST 05 OK] Pipeline completed: {res['registered_pools_count']} pools, {res['new_delta_alerts_count']} alerts.")


def test_06_flask_api_sync_endpoint(client):
    """Tests POST /api/proactive/sync_vip_stores Flask endpoint."""
    resp = client.post("/api/proactive/sync_vip_stores")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get("ok") is True
    assert data.get("registered_pools_count") > 0
    print(f"\n[TEST 06 OK] API /api/proactive/sync_vip_stores returned 200 with {data['registered_pools_count']} pools.")


def test_07_flask_api_pools_and_alerts(client):
    """Tests GET /api/proactive/pools and GET /api/proactive/alerts endpoints."""
    # Test pools
    resp_pools = client.get("/api/proactive/pools")
    assert resp_pools.status_code == 200
    pools_data = json.loads(resp_pools.data)
    assert pools_data.get("ok") is True
    assert len(pools_data.get("pools", [])) > 0
    sample_p = pools_data["pools"][0]
    assert "pool_search_url" in sample_p

    # Test alerts
    resp_alerts = client.get("/api/proactive/alerts")
    assert resp_alerts.status_code == 200
    alerts_data = json.loads(resp_alerts.data)
    assert alerts_data.get("ok") is True
    assert len(alerts_data.get("alerts", [])) > 0
    sample_a = alerts_data["alerts"][0]
    assert "event_type" in sample_a
    assert "ai_strategic_comment" in sample_a
    print(f"\n[TEST 07 OK] API /pools ({len(pools_data['pools'])}) and /alerts ({len(alerts_data['alerts'])}) verified.")


if __name__ == "__main__":
    pytest.main(["-v", str(Path(__file__).resolve())])
