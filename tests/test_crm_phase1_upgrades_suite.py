import time
import pytest
import requests
import sqlite3
from playwright.sync_api import sync_playwright
from crm_excel_export import _parse_currency

BASE_URL = "http://127.0.0.1:5000"

def test_currency_shorthand_parsing():
    """Verify smart currency parser correctly scales shorthand notations (BUG-09 fix)."""
    assert _parse_currency("14.5M") == 14500000
    assert _parse_currency("14,5 Milyon") == 14500000
    assert _parse_currency("28.75M") == 28750000
    assert _parse_currency("500k") == 500000
    assert _parse_currency("750 bin") == 750000
    assert _parse_currency("7.000.000 ₺") == 7000000
    assert _parse_currency(12000000) == 12000000
    assert _parse_currency("") == 0
    assert _parse_currency(None) == 0


def test_buyer_delete_and_update_dual_persistence():
    """Verify buyer delete and update APIs persist across both SQLite and JSON dashboards (BUG-01, BUG-02 fix)."""
    test_ref = "test_phase1_listing"
    # 1. Create buyer
    create_res = requests.post(f"{BASE_URL}/api/portfolio/listing/{test_ref}/buyer", json={
        "name": "Burak Çetin (Faz 1 Test Alıcısı)",
        "phone": "+90 535 000 11 22",
        "offer": "18.500.000 ₺",
        "stage": "Teklif Verildi",
        "note": "Faz 1 silme ve güncelleme testi.",
        "listing_title": "Çayyolu Test Villası"
    }, timeout=10)
    assert create_res.status_code == 200
    b_data = create_res.json()["buyer"]
    bid = b_data["id"]

    # 2. Update buyer
    update_res = requests.post(f"{BASE_URL}/api/portfolio/buyer/{bid}/update", json={
        "name": "Burak Çetin (Güncellendi)",
        "phone": "+90 535 000 99 99",
        "offer": "19.000.000 ₺",
        "stage": "Pazarlık Aşamasında",
        "note": "Yeni teklif 19M olarak güncellendi."
    }, timeout=10)
    assert update_res.status_code == 200
    assert update_res.json().get("ok") is True

    # Verify SQLite update
    with sqlite3.connect("data/intelligence.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, phone, offer, stage FROM portfolio_listing_buyers WHERE id = ?", (bid,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "Burak Çetin (Güncellendi)"
        assert row[1] == "+90 535 000 99 99"
        assert row[2] == "19.000.000 ₺"

    # 3. Delete buyer
    del_res = requests.delete(f"{BASE_URL}/api/portfolio/buyer/{bid}", timeout=10)
    assert del_res.status_code == 200
    assert del_res.json().get("ok") is True

    # Verify SQLite deletion
    with sqlite3.connect("data/intelligence.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM portfolio_listing_buyers WHERE id = ?", (bid,))
        row = cur.fetchone()
        assert row is None, "Deleted buyer must not exist in SQLite"

    # Verify all_buyers does not return deleted buyer
    all_res = requests.get(f"{BASE_URL}/api/portfolio/all_buyers", timeout=10)
    assert all_res.status_code == 200
    buyers = all_res.json().get("buyers", [])
    assert not any(b["id"] == bid for b in buyers), "Deleted buyer must not exist in all_buyers"


def test_buyer_stage_harmonization_kanban_visibility():
    """Verify offer buyers are mapped to 'negotiation' so they render in the Vue Kanban board (BUG-03 fix)."""
    res = requests.get(f"{BASE_URL}/api/portfolio/all_buyers", timeout=10)
    assert res.status_code == 200
    buyers = res.json().get("buyers", [])
    cinnah_buyers = [b for b in buyers if "cinnah" in (b.get("listingTitle", "") + b.get("name", "")).lower() and b.get("price") == 7000000]
    assert len(cinnah_buyers) >= 1
    cb = cinnah_buyers[0]
    # In Vue buyerStages, 'Teklif' column has id 'negotiation'
    assert cb["stage"] == "negotiation", f"Offer buyer must have stage 'negotiation' for Kanban visibility, got: {cb['stage']}"


def test_crm_playwright_phase1_features():
    """Verify SATICI tab, WebTapu checklist, CB Commission calculator and zero 'NaN gün' in Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.goto(f"{BASE_URL}/crm?demo=1", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("#app", timeout=10000)

        # Switch to pipeline view first
        page.locator("button.sidebar-item:has(i.fa-columns)").first.click()
        page.wait_for_timeout(600)

        # 1. Verify SATICI pipeline button exists and click it
        seller_tab = page.locator(".overflow-x-auto button:has-text('SATICI')").first
        assert seller_tab.count() > 0, "SATICI pipeline tab must exist in pipelineCategories"

        seller_tab.click()
        page.wait_for_timeout(600)
        kanban_cols = page.locator(".kanban-column")
        assert kanban_cols.count() >= 5, "SATICI pipeline should render stages (İlk Temas, Değerleme, Sözleşme, vb.)"

        # 2. Switch back to ALICI tab and verify buyers with offers appear in Kanban
        buyer_tab = page.locator(".overflow-x-auto button:has-text('ALICI')").first
        buyer_tab.click()
        page.wait_for_timeout(600)
        # Check text on cards does not have "NaN gün"
        body_text = page.locator(".kanban-board").inner_text()
        assert "NaN gün" not in body_text, "Kanban board cards must not contain 'NaN gün'"

        # 3. Open lead panel with an actual contact from contacts pool
        page.evaluate("""() => {
            const app = window.__crmApp;
            if (app) {
                if (!app.contacts || app.contacts.length === 0) {
                    app.contacts = [{ id: 'c_test_01', name: 'Ahmet Yılmaz', category: 'buyer', price: 15000000 }];
                }
                const c = app.contacts[0];
                app.openLeadPanel(c);
            }
        }""")
        page.wait_for_timeout(800)

        webtapu_btn = page.locator("button:has-text('Tapu & Kapanış')")
        komisyon_btn = page.locator("button:has-text('Komisyon')")
        assert webtapu_btn.count() > 0, "Tapu & Kapanış tab must exist in panel"
        assert komisyon_btn.count() > 0, "Komisyon tab must exist in panel"

        # Click Tapu & Kapanış tab and verify 10-step checklist renders
        webtapu_btn.click()
        page.wait_for_timeout(400)
        assert page.locator("text=Coldwell Banker CB VIP — 10 Adımlı Tapu & Kapanış").count() > 0

        # Click Komisyon tab and verify split calculator renders
        komisyon_btn.click()
        page.wait_for_timeout(400)
        assert page.locator("text=Coldwell Banker CB VIP Komisyon & Hakediş Modeli").count() > 0

        browser.close()
