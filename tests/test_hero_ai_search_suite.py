import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import threading
from playwright.sync_api import sync_playwright
from app import app

PORT = 5011

def start_server():
    app.run(port=PORT, debug=False, use_reloader=False)

def run_suite():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        print("\n=======================================================")
        print("TEST 1: DESKTOP (1366x768) - Quick Chip Search")
        print("=======================================================")
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(1.2)

        # 1. Check Hero AI Search box existence
        search_box = page.locator("#heroAiSearchBox")
        assert search_box.is_visible(), "Hero AI Search Box is not visible!"

        query_input = page.locator("#heroAiQueryInput")
        assert query_input.is_visible(), "Hero AI Query Input is not visible!"

        search_btn = page.locator("#heroAiSearchBtn")
        assert search_btn.is_visible(), "Hero AI Search button is not visible!"

        chips = page.locator(".hero-quick-chips button.quick-chip")
        assert chips.count() == 4, f"Expected 4 quick chips, found {chips.count()}"

        # 2. Click the 'Beytepe & Çayyolu' chip
        print("Clicking 'Beytepe & Çayyolu' quick chip...")
        chips.nth(1).click()

        # Modal should open
        modal_overlay = page.locator("#heroAiModalOverlay")
        page.wait_for_selector("#heroAiModalOverlay", state="visible", timeout=5000)
        assert modal_overlay.is_visible(), "Hero AI Modal Overlay did not open after chip click!"
        print("PASS: Modal overlay opened!")

        # Wait for loading to finish and results to appear
        page.wait_for_selector("#heroAiResultContent", state="visible", timeout=10000)
        print("PASS: AI Result content visible!")

        res_text = page.locator("#heroAiResText").inner_text()
        print("Result text snippet:", res_text[:100].strip())
        assert len(res_text) > 20, "AI response text is too short or empty!"

        prj_cards = page.locator("#heroAiPrjGrid .ai-prj-card")
        cards_count = prj_cards.count()
        print(f"Matched Projects count: {cards_count}")
        assert cards_count >= 1, "Expected at least 1 matched project card!"

        # Verify first card content
        first_card = prj_cards.first
        title = first_card.locator(".ai-prj-title").inner_text()
        print("First Card Title:", title)
        assert len(title) > 0, "Card title is empty!"

        wa_btn = first_card.locator("a[href*='wa.me']")
        assert wa_btn.is_visible(), "WhatsApp CTA button is missing from project card!"

        # 3. Close modal via close button
        print("Closing modal via close button...")
        page.locator(".hero-ai-close-btn").click()
        time.sleep(0.4)
        assert not modal_overlay.is_visible(), "Modal did not close via close button!"
        print("PASS: Modal closed cleanly via close button!")

        print("\n=======================================================")
        print("TEST 2: DESKTOP (1366x768) - Custom Query & Enter Key")
        print("=======================================================")
        # Fill custom query
        query_input.fill("2M altı, Beytepe villa")
        query_input.press("Enter")

        page.wait_for_selector("#heroAiModalOverlay", state="visible", timeout=5000)
        assert modal_overlay.is_visible(), "Modal did not open on Enter key press!"
        page.wait_for_selector("#heroAiResultContent", state="visible", timeout=10000)
        print("PASS: Custom query results loaded!")

        # Close via Escape key
        print("Pressing Escape key to close...")
        page.keyboard.press("Escape")
        time.sleep(0.4)
        assert not modal_overlay.is_visible(), "Modal did not close on Escape key!"
        print("PASS: Modal closed on Escape key!")

        print("\n=======================================================")
        print("TEST 3: MOBILE (390x844) - Mobile Responsiveness & Touch")
        print("=======================================================")
        page_mobile = browser.new_page(viewport={"width": 390, "height": 844})
        page_mobile.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(1.2)

        mob_chips = page_mobile.locator(".hero-quick-chips button.quick-chip")
        mob_chips.first.click()

        mob_overlay = page_mobile.locator("#heroAiModalOverlay")
        page_mobile.wait_for_selector("#heroAiModalOverlay", state="visible", timeout=5000)
        assert mob_overlay.is_visible(), "Mobile modal did not open!"

        page_mobile.wait_for_selector("#heroAiResultContent", state="visible", timeout=10000)
        print("PASS: Mobile AI search results loaded!")

        # Verify modal fits mobile viewport width
        modal_box = page_mobile.locator(".hero-ai-modal").bounding_box()
        print("Mobile Modal Box:", modal_box)
        assert modal_box["width"] <= 390, f"Modal overflows mobile screen: {modal_box['width']}"

        # Close via backdrop click (clicking outside modal box)
        page_mobile.locator("#heroAiModalOverlay").click(position={"x": 5, "y": 5})
        time.sleep(0.4)
        assert not mob_overlay.is_visible(), "Mobile modal did not close on backdrop click!"
        print("PASS: Mobile modal closed on backdrop tap!")

        page_mobile.close()
        browser.close()

        print("\n=======================================================")
        print("ALL HERO AI SEARCH TESTS PASSED 100%!")
        print("=======================================================")

def test_hero_ai_search_suite():
    run_suite()

if __name__ == "__main__":
    run_suite()
