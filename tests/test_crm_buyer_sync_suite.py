import pytest
import requests
import time
import sqlite3
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

def test_api_portfolio_listing_buyer_sync():
    """Test backend endpoint /api/portfolio/listing/<ref_id>/buyer with UID and verify response."""
    test_ref_id = f"test_listing_{int(time.time())}"
    test_uid = "RnHhsj3K4VSWRY4cjc3Pc09JMFn2"
    buyer_payload = {
        "name": "Ahmet Yılmaz (Test Alıcı)",
        "phone": "+90 532 999 88 77",
        "offer": "14.500.000 ₺",
        "stage": "Teklif Verildi",
        "note": "Alıcı test notu: Villa ile çok ilgilendi.",
        "listing_title": "Beytepe 4+1 Özel Bahçeli Villa",
        "uid": test_uid
    }

    url = f"{BASE_URL}/api/portfolio/listing/{test_ref_id}/buyer"
    res = requests.post(url, json=buyer_payload, timeout=10)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    data = res.json()
    assert data.get("ok") is True, f"Expected ok: True, got {data}"
    assert "buyer" in data, "Expected 'buyer' in response"
    buyer = data["buyer"]
    assert buyer["name"] == buyer_payload["name"]
    assert buyer["phone"] == buyer_payload["phone"]
    assert buyer["offer"] == buyer_payload["offer"]
    assert buyer["stage"] == buyer_payload["stage"]
    assert buyer["refId"] == test_ref_id
    assert "id" in buyer and buyer["id"].startswith("b_")


def test_cinnah_7m_buyer_persisted_and_returned():
    """Verify Cinnah 7M buyer is present in all_buyers and in listing dashboard."""
    # 1. Check all_buyers
    res = requests.get(f"{BASE_URL}/api/portfolio/all_buyers", timeout=10)
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    buyers = data.get("buyers", [])
    
    cinnah_buyers = [
        b for b in buyers 
        if "cinnah" in (b.get("listingTitle", "") + b.get("name", "") + b.get("notes", "")).lower()
        and b.get("price") == 7000000
    ]
    assert len(cinnah_buyers) >= 1, "Cinnah 7M offer buyer must be in /api/portfolio/all_buyers"
    
    cb = cinnah_buyers[0]
    assert cb["category"] == "buyer"
    assert cb["role"] == "buyer"
    assert cb["price"] == 7000000
    assert "7.000.000" in cb["offer"] or "7" in cb["offer"]

    # 2. Check dashboard for Cinnah listings
    for ref_id in ["b8aee88267a9", "45e616122b56"]:
        dash_res = requests.get(f"{BASE_URL}/api/portfolio/listing/{ref_id}/dashboard", timeout=10)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data.get("ok") is True
        l_buyers = dash_data.get("data", {}).get("buyers", [])
        has_7m = any("7" in str(b.get("offer", "")) for b in l_buyers)
        assert has_7m, f"Listing {ref_id} dashboard must include 7M offer buyer"


def test_add_buyer_without_phone_succeeds():
    """Verify adding a buyer with name & offer but empty phone succeeds and persists to SQLite & JSON."""
    test_ref = "test_no_phone_persist"
    payload = {
        "name": "Mehmet Bey (Cinnah Adayı)",
        "phone": "",
        "offer": "7.200.000 ₺",
        "stage": "Pazarlık Aşamasında",
        "note": "Telefon girmeden sadece isim ve teklif ile ekleme testi.",
        "listing_title": "CİNNAHTA CADDE CEPHELİ 2+1 DAİRE"
    }

    url = f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer"
    res = requests.post(url, json=payload, timeout=10)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data.get("ok") is True
    buyer = data.get("buyer", {})
    assert buyer.get("phone") == "-"
    assert buyer.get("offer") == "7.200.000 ₺"
    b_id = buyer.get("id")

    # Verify SQLite persistence
    conn = sqlite3.connect("data/intelligence.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, offer, phone FROM portfolio_listing_buyers WHERE id = ?", (b_id,))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[1] == "Mehmet Bey (Cinnah Adayı)"
    assert row[2] == "7.200.000 ₺"


def test_crm_frontend_buyer_integration():
    """Test /crm page elements, buyer categories, filter buttons, and Vue initialization."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/crm", wait_until="domcontentloaded", timeout=15000)
        assert response.status == 200, f"Failed to load /crm: {response.status}"

        page.wait_for_selector("#app", timeout=10000)
        time.sleep(1.5)

        fatal_errors = [e for e in console_errors if "ReferenceError" in e or "SyntaxError" in e or "TypeError" in e]
        assert not fatal_errors, f"Fatal JS errors on /crm: {fatal_errors}"

        vue_state = page.evaluate("""() => {
            const appEl = document.querySelector('#app');
            return {
                title: document.title,
                hasVueApp: !!appEl,
                badgeBuyerCss: !!document.querySelector('style')?.textContent.includes('.badge-buyer'),
                badgeListingCss: !!document.querySelector('style')?.textContent.includes('.badge-listing')
            };
        }""")

        assert vue_state["hasVueApp"] is True
        assert vue_state["badgeBuyerCss"] is True
        assert vue_state["badgeListingCss"] is True

        browser.close()
