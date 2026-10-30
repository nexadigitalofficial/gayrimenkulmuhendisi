import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import threading
from playwright.sync_api import sync_playwright
from app import app

PORT = 5022

def start_server():
    app.run(port=PORT, debug=False, use_reloader=False)

def test_hero_dock_no_collision():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(1.2)

        print("\n=======================================================")
        print("PHASE 1: HERO VIEW (scrollY = 0) - ZERO FLOATING COLLISION")
        print("=======================================================")
        
        # Verify hero showcase badge is visible
        badge = page.locator("#heroShowcaseBadge")
        assert badge.is_visible(), "Hero showcase badge should be visible!"
        badge_box = badge.bounding_box()
        print("Hero Showcase Badge Box:", badge_box)

        # Check floating CTA at scrollY = 0
        floating_cta = page.locator("#floatingCta")
        has_is_visible = page.evaluate("() => document.getElementById('floatingCta').classList.contains('is-visible')")
        print("Floating CTA has 'is-visible' class at scrollY=0:", has_is_visible)
        assert not has_is_visible, "Floating CTA should NOT be visible on Hero view!"

        opacity = page.evaluate("() => window.getComputedStyle(document.getElementById('floatingCta')).opacity")
        pointer_events = page.evaluate("() => window.getComputedStyle(document.getElementById('floatingCta')).pointerEvents")
        print(f"Floating CTA opacity: {opacity}, pointer-events: {pointer_events}")
        assert float(opacity) == 0, f"Floating CTA opacity should be 0, got {opacity}"
        assert pointer_events == "none", f"Floating CTA pointer-events should be 'none', got {pointer_events}"

        # Verify buttons on showcase card are directly clickable without any interception
        play_btn = page.locator("#heroShowcaseBadge button:has-text('Detaylı İzle')")
        sound_btn = page.locator("#heroSoundBtn")
        project_btn = page.locator("#heroShowcaseBadge a:has-text('31 Proje')")
        
        assert play_btn.is_visible()
        assert sound_btn.is_visible()
        assert project_btn.is_visible()
        
        # Click sound button to test interactivity
        sound_btn.click()
        print("PASS: Sound button clicked with zero interception!")

        print("\n=======================================================")
        print("PHASE 2: SCROLLED VIEW (scrollY = 600) - FLOATING DOCK APPEARS")
        print("=======================================================")
        page.evaluate("() => window.scrollTo(0, 600)")
        time.sleep(0.5)

        has_is_visible_scrolled = page.evaluate("() => document.getElementById('floatingCta').classList.contains('is-visible')")
        print("Floating CTA has 'is-visible' class at scrollY=600:", has_is_visible_scrolled)
        assert has_is_visible_scrolled, "Floating CTA should become visible when scrolled past Hero!"

        opacity_scrolled = page.evaluate("() => window.getComputedStyle(document.getElementById('floatingCta')).opacity")
        print(f"Floating CTA opacity at scrollY=600: {opacity_scrolled}")
        assert float(opacity_scrolled) > 0.8, "Floating CTA should be visible!"

        # Verify all 3 dock buttons exist inside floating CTA
        map_btn = page.locator("#floatingCta #mapTrigger")
        wa_btn = page.locator("#floatingCta .float-btn.whatsapp")
        phone_btn = page.locator("#floatingCta .float-btn.phone")

        assert map_btn.is_visible(), "Map button in dock should be visible!"
        assert wa_btn.is_visible(), "WhatsApp button in dock should be visible!"
        assert phone_btn.is_visible(), "Phone button in dock should be visible!"
        print("PASS: All 3 floating dock buttons are visible and active!")

        # Test map modal opens when map button is clicked
        map_btn.click()
        time.sleep(0.3)
        modal_active = page.evaluate("() => document.getElementById('mapModal').classList.contains('active')")
        print("Map Modal active:", modal_active)
        assert modal_active, "Map modal should open on clicking mapTrigger in dock!"

        # Close map modal
        page.locator("#mapClose").click()
        time.sleep(0.3)

        print("\n=======================================================")
        print("PHASE 3: RETURN TO HERO (scrollY = 0) - CLEAN DISMISSAL")
        print("=======================================================")
        page.evaluate("() => window.scrollTo(0, 0)")
        time.sleep(0.5)

        has_is_visible_top = page.evaluate("() => document.getElementById('floatingCta').classList.contains('is-visible')")
        assert not has_is_visible_top, "Floating CTA should hide again when returning to Hero!"
        print("PASS: Floating dock cleanly dismisses when returning to Hero!")

        print("\n=======================================================")
        print("ALL HERO COLLISION & FLOATING DOCK TESTS PASSED 100%!")
        print("=======================================================")
        browser.close()

if __name__ == "__main__":
    test_hero_dock_no_collision()
