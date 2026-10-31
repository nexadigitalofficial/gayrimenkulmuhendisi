import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import threading
from playwright.sync_api import sync_playwright
from app import app

PORT = 5012

def start_server():
    app.run(port=PORT, debug=False, use_reloader=False)

def run_suite():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        print("\n=======================================================")
        print("TEST 1: DESKTOP (1366x768) - Full Cinematic Preloader & Telemetry")
        print("=======================================================")
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        page.goto(f"http://127.0.0.1:{PORT}/")

        # 1. Preloader existence & structure
        loader = page.locator("#pagePreloader")
        assert loader.is_visible(), "Page preloader should be immediately visible on cold load!"

        shutter_top = page.locator(".nxa-shutter-top")
        shutter_bottom = page.locator(".nxa-shutter-bottom")
        assert shutter_top.is_visible(), "Top velvet shutter not visible!"
        assert shutter_bottom.is_visible(), "Bottom velvet shutter not visible!"

        skip_btn = page.locator("#preloaderSkipBtn")
        assert skip_btn.is_visible(), "Skip micro-pill button not visible!"

        # 3D Gimbal & Monogram SVG
        gimbal = page.locator(".preloader-gimbal-rig")
        assert gimbal.is_visible(), "3D Gimbal rig not visible!"
        svg = page.locator(".luxury-compass-svg")
        assert svg.is_visible(), "Luxury compass SVG not visible!"

        # Telemetry HUD Grid Cards
        hud_grid = page.locator("#hudTelemetryGrid")
        assert hud_grid.is_visible(), "HUD Telemetry Grid not visible!"
        cards = page.locator(".hud-card")
        assert cards.count() == 4, f"Expected 4 HUD cards, found {cards.count()}"

        lat_el = page.locator("#hudLatVal")
        assert lat_el.is_visible(), "Latitude telemetry element not visible!"

        # Wait for progression and check live counter update
        time.sleep(1.2)
        pct_text = page.locator("#preloaderPercent").inner_text()
        print("Progress mid-flight:", pct_text)
        assert "%" in pct_text, "Percent text missing %"

        # Wait for complete reveal
        page.wait_for_selector("#pagePreloader.revealed", state="attached", timeout=6000)
        print("PASS: Preloader received .revealed class on completion!")

        # Verify shutters parted
        time.sleep(1.3)
        assert not loader.is_visible(), "Preloader should be hidden after unmounting!"
        print("PASS: Preloader successfully unmounted after shutter split!")

        print("\n=======================================================")
        print("TEST 2: FAST-PASS (Session Storage Return Visit)")
        print("=======================================================")
        # Navigate to another internal URL or refresh within the same session
        page.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(0.3)
        # Should be bypassed immediately via fast-pass
        is_fast_pass = page.evaluate("() => document.documentElement.classList.contains('nexa-fast-pass')")
        print("Fast-Pass class on <html>:", is_fast_pass)
        assert is_fast_pass, "Returning session should have .nexa-fast-pass on <html>!"
        assert not loader.is_visible(), "Preloader should be instantly bypassed on return visit!"
        print("PASS: Turbo Fast-Pass works seamlessly for returning VIP visits!")

        print("\n=======================================================")
        print("TEST 3: SKIP BUTTON INTERACTION")
        print("=======================================================")
        # Fresh context without session storage
        ctx_skip = browser.new_context(viewport={"width": 1366, "height": 768})
        page_skip = ctx_skip.new_page()
        page_skip.goto(f"http://127.0.0.1:{PORT}/")

        btn = page_skip.locator("#preloaderSkipBtn")
        assert btn.is_visible(), "Skip button should be visible"
        btn.click()
        time.sleep(0.5)

        is_rev = page_skip.evaluate("() => document.getElementById('pagePreloader').classList.contains('revealed')")
        assert is_rev, "Preloader should be revealed immediately on skip button click!"
        print("PASS: Skip button successfully dismisses preloader!")
        page_skip.close()

        print("\n=======================================================")
        print("TEST 4: ESCAPE KEY DISMISSAL")
        print("=======================================================")
        ctx_esc = browser.new_context(viewport={"width": 1366, "height": 768})
        page_esc = ctx_esc.new_page()
        page_esc.goto(f"http://127.0.0.1:{PORT}/")

        page_esc.keyboard.press("Escape")
        time.sleep(0.5)

        is_rev_esc = page_esc.evaluate("() => document.getElementById('pagePreloader').classList.contains('revealed')")
        assert is_rev_esc, "Preloader should be revealed on Escape key press!"
        print("PASS: Escape key dismisses preloader!")
        page_esc.close()

        print("\n=======================================================")
        print("TEST 5: MOBILE (360x800) ERGONOMICS & ZERO OVERFLOW")
        print("=======================================================")
        ctx_mob = browser.new_context(viewport={"width": 360, "height": 800})
        page_mob = ctx_mob.new_page()
        page_mob.goto(f"http://127.0.0.1:{PORT}/")

        mob_content = page_mob.locator(".preloader-content")
        box = mob_content.bounding_box()
        print("Mobile Preloader Content Box:", box)
        assert box["width"] <= 360, f"Content overflows mobile width: {box['width']}"
        assert box["x"] >= 0, "Content shifted into negative X space!"

        # Verify Skip button within mobile bounds
        mob_skip = page_mob.locator("#preloaderSkipBtn").bounding_box()
        print("Mobile Skip Button Box:", mob_skip)
        assert mob_skip["x"] + mob_skip["width"] <= 360, "Skip button overflows mobile screen!"

        # Let it complete on mobile
        page_mob.wait_for_selector("#pagePreloader.revealed", state="attached", timeout=6000)
        print("PASS: Mobile preloader completed smoothly!")

        page_mob.close()
        browser.close()

        print("\n=======================================================")
        print("ALL CINEMATIC PRELOADER TESTS PASSED 100%!")
        print("=======================================================")

def test_cinematic_preloader_suite():
    run_suite()

if __name__ == "__main__":
    run_suite()
