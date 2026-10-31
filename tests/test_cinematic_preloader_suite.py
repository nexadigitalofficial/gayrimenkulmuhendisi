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
        print("TEST 1: DESKTOP (1366x768) - Full Luxury Signature Preloader")
        print("=======================================================")
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        page.goto(f"http://127.0.0.1:{PORT}/")

        # 1. Preloader existence & structure
        loader = page.locator("#pagePreloader")
        assert loader.is_visible(), "Page preloader should be immediately visible on cold load!"

        # Rings & Avatar
        outer_ring = page.locator(".preloader-outer-ring")
        inner_ring = page.locator(".preloader-inner-ring")
        avatar = page.locator(".preloader-avatar")
        avatar_status = page.locator(".preloader-avatar-status")
        assert outer_ring.is_visible(), "Outer rotating ring not visible!"
        assert inner_ring.is_visible(), "Inner rotating ring not visible!"
        assert avatar.is_visible(), "Avatar image not visible!"
        assert avatar_status.is_visible(), "Avatar live status dot not visible!"

        # Brand Identity
        badge = page.locator(".preloader-badge")
        title = page.locator(".preloader-title")
        subtitle = page.locator(".preloader-subtitle")
        assert badge.is_visible(), "CB VIP badge not visible!"
        assert title.is_visible(), "Preloader title (Yiğit Narin) not visible!"
        assert subtitle.is_visible(), "Preloader subtitle not visible!"

        # Progress elements
        fill = page.locator("#preloaderFill")
        pct = page.locator("#preloaderPercent")
        status_el = page.locator("#preloaderStatus")
        compliance = page.locator(".preloader-compliance")
        assert fill.is_visible(), "Progress fill not visible!"
        assert pct.is_visible(), "Progress percent not visible!"
        assert status_el.is_visible(), "Status text not visible!"
        assert compliance.is_visible(), "Compliance text not visible!"

        skip_btn = page.locator("#preloaderSkipBtn")
        assert skip_btn.is_visible(), "Skip micro-pill button not visible!"

        # Wait for progression and check live counter update
        time.sleep(1.0)
        pct_text = page.locator("#preloaderPercent").inner_text()
        print("Progress mid-flight:", pct_text)
        assert "%" in pct_text, "Percent text missing %"

        # Wait for complete reveal
        page.wait_for_selector("#pagePreloader.revealed", state="attached", timeout=6000)
        print("PASS: Preloader received .revealed class on completion!")

        # Verify exit & unmounting
        time.sleep(1.0)
        assert not loader.is_visible(), "Preloader should be hidden after unmounting!"
        print("PASS: Preloader successfully unmounted after completion!")

        print("\n=======================================================")
        print("TEST 2: FAST-PASS (Session Seen Hash Navigation)")
        print("=======================================================")
        ctx_fp = browser.new_context(viewport={"width": 1366, "height": 768})
        page_fp = ctx_fp.new_page()
        page_fp.add_init_script("sessionStorage.setItem('nexa_preloader_seen', '1');")
        page_fp.goto(f"http://127.0.0.1:{PORT}/#portfolio")
        time.sleep(0.3)
        is_fast_pass = page_fp.evaluate("() => document.documentElement.classList.contains('nexa-fast-pass')")
        print("Fast-Pass class on <html>:", is_fast_pass)
        assert is_fast_pass, "Returning in-session hash visit should have .nexa-fast-pass on <html>!"
        loader_fp = page_fp.locator("#pagePreloader")
        assert not loader_fp.is_visible(), "Preloader should be instantly bypassed on fast-pass visit!"
        print("PASS: Fast-Pass works seamlessly for in-session navigation!")
        page_fp.close()

        print("\n=======================================================")
        print("TEST 3: SKIP BUTTON INTERACTION")
        print("=======================================================")
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
        print("ALL SIGNATURE LUXURY PRELOADER TESTS PASSED 100%!")
        print("=======================================================")

def test_cinematic_preloader_suite():
    run_suite()

if __name__ == "__main__":
    run_suite()
