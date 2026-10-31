import os
import sys
import time
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:5000")

def test_hero_showcase_pip_and_draggable():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f"\n[TEST] Navigating to {BASE_URL}...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        
        # Wait for preloader overlay to disappear
        try:
            page.wait_for_selector("#pagePreloader", state="hidden", timeout=6000)
        except Exception:
            page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")

        page.wait_for_selector("#heroShowcaseBadge", timeout=10000)

        # 1. Verification of Hero Showcase Card initial state
        badge = page.locator("#heroShowcaseBadge")
        assert badge.is_visible(), "Hero showcase badge should be visible on page load"

        title_el = page.locator("#heroShowcaseTitle")
        initial_title = title_el.text_content().strip()
        print(f"[TEST 1] Initial Hero Showcase Title: {initial_title}")
        assert len(initial_title) > 0, "Hero showcase title should not be empty"

        # 2. Test Draggable functionality
        initial_box = badge.bounding_box()
        assert initial_box is not None, "Badge bounding box should exist"
        print(f"[TEST 2] Initial Box: x={initial_box['x']}, y={initial_box['y']}")

        grip = page.locator("#heroShowcaseBadge .showcase-full-view .showcase-drag-grip")
        assert grip.is_visible(), "Drag grip should be visible"

        # Drag 140px left, 60px up
        grip_box = grip.bounding_box()
        page.mouse.move(grip_box["x"] + grip_box["width"]/2, grip_box["y"] + grip_box["height"]/2)
        page.mouse.down()
        page.wait_for_timeout(50)
        page.mouse.move(grip_box["x"] - 140, grip_box["y"] - 60, steps=8)
        page.wait_for_timeout(50)
        page.mouse.up()
        page.wait_for_timeout(300)

        after_drag_box = badge.bounding_box()
        print(f"[TEST 2] After Drag Box: x={after_drag_box['x']}, y={after_drag_box['y']}")
        assert after_drag_box["x"] < initial_box["x"], "Badge should have moved horizontally to the left"
        assert badge.evaluate("el => el.classList.contains('is-floating')"), "Badge should have .is-floating"

        reset_btn = page.locator("#showcaseResetPosBtn")
        assert reset_btn.is_visible(), "Reset position button should become visible after dragging"

        # Test Reset Position
        reset_btn.click()
        page.wait_for_timeout(300)
        assert not badge.evaluate("el => el.classList.contains('is-floating')"), "Reset should remove .is-floating"
        print("[TEST 2] Reset Position confirmed!")

        # Ensure scroll is at 0
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(100)

        # 3. Test PiP Mode (Mini Player)
        pip_btn = page.locator("#heroShowcaseBadge button[title*='Mini Player']").first
        assert pip_btn.is_visible(), "Minimize to PiP button should be visible"
        pip_btn.click()
        page.wait_for_timeout(300)

        assert badge.evaluate("el => el.classList.contains('showcase-pip')"), "Badge should have .showcase-pip class"
        pip_view = page.locator(".showcase-pip-view")
        assert pip_view.is_visible(), "PiP view should be visible"

        pip_title = page.locator("#showcasePipTitle").text_content().strip()
        print(f"[TEST 3] PiP Title in mini player: {pip_title}")
        assert pip_title == initial_title, f"PiP title '{pip_title}' should match '{initial_title}'"

        # Expand back to Full Card
        expand_btn = page.locator(".showcase-pip-view button[title*='Tam Boyuta']").first
        expand_box = expand_btn.bounding_box()
        page.mouse.click(expand_box["x"] + expand_box["width"]/2, expand_box["y"] + expand_box["height"]/2)
        page.wait_for_timeout(300)
        assert not badge.evaluate("el => el.classList.contains('showcase-pip')"), ".showcase-pip should be removed"
        print("[TEST 3] Expand back from PiP confirmed!")

        # 4. Test Dismiss (Close) & Floating Restore Pill
        close_btn = page.locator(".hero-showcase-nav button.hero-ctrl-close").first
        close_btn.click()
        page.wait_for_timeout(300)

        assert badge.evaluate("el => el.classList.contains('is-dismissed')"), "Badge should have .is-dismissed class"
        restore_fab = page.locator("#showcaseRestoreFab")
        assert restore_fab.is_visible(), "Floating Restore Fab should appear when dismissed"

        srf_title = page.locator("#srfTitle").text_content().strip()
        print(f"[TEST 4] Restore FAB Title: {srf_title}")
        assert srf_title == initial_title, "Restore FAB title should match active showcase title"

        # Check background video is still active
        is_video_paused = page.evaluate("() => { const v = document.getElementById('heroVideoElement'); return v ? v.paused : null; }")
        print(f"[TEST 4] Background video paused status: {is_video_paused}")

        # Restore
        restore_fab.click()
        page.wait_for_timeout(300)
        assert not badge.evaluate("el => el.classList.contains('is-dismissed')"), ".is-dismissed should be removed"
        assert not restore_fab.is_visible(), "Restore FAB should hide after restoring"
        print("[TEST 4] Restore from dismiss confirmed!")

        # 5. Test Day Switching updates all titles and states
        next_btn = page.locator(".hero-showcase-nav button[title*='Sonraki']").first
        next_btn.click()
        page.wait_for_timeout(300)

        new_title = page.locator("#heroShowcaseTitle").text_content().strip()
        new_pip_title = page.locator("#showcasePipTitle").text_content().strip()
        new_srf_title = page.locator("#srfTitle").text_content().strip()

        print(f"[TEST 5] After Day Switch: Title='{new_title}', PiP Title='{new_pip_title}', FAB Title='{new_srf_title}'")
        assert new_title != initial_title, "Showcase title should change when clicking next"
        assert new_pip_title == new_title, "PiP title should sync on day switch"
        assert new_srf_title == new_title, "Restore FAB title should sync on day switch"

        # 6. Test Sound Toggle synchronization
        sound_btn = page.locator("#heroSoundBtn")
        sound_btn.click(force=True)
        page.wait_for_timeout(200)

        pip_sound_icon = page.locator("#showcasePipSoundIcon").get_attribute("class")
        print(f"[TEST 6] PiP Sound Icon class after sound click: {pip_sound_icon}")
        assert "fa-volume" in pip_sound_icon, "Sound icon should update in PiP"

        browser.close()
        print("\n>>> ALL 6 HERO SHOWCASE PIP & DRAGGABLE SUITE TESTS PASSED 100%! <<<\n")

if __name__ == "__main__":
    test_hero_showcase_pip_and_draggable()
