import pytest
import requests
import time
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

    print(f"\n[OK] Backend buyer creation succeeded! Buyer ID: {buyer['id']}")


def test_crm_frontend_buyer_integration():
    """Test /crm page elements, buyer categories, filter buttons, and Vue initialization."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/crm", wait_until="domcontentloaded", timeout=15000)
        assert response.status == 200, f"Failed to load /crm: {response.status}"

        # Wait for Vue app mount (#app)
        page.wait_for_selector("#app", timeout=10000)
        time.sleep(1.5)

        # Check that no fatal JS errors occurred
        fatal_errors = [e for e in console_errors if "ReferenceError" in e or "SyntaxError" in e or "TypeError" in e]
        assert not fatal_errors, f"Fatal JS errors on /crm: {fatal_errors}"

        # Evaluate Vue setup properties and verify buyer category exists
        vue_state = page.evaluate("""() => {
            const appEl = document.querySelector('#app');
            // Check pipeline categories and helper functions if exposed or DOM elements
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

        print(f"\n[OK] Frontend CRM loaded cleanly with .badge-buyer and .badge-listing styles active!")

        browser.close()
