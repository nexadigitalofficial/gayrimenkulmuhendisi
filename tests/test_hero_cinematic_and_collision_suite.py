import os
import time
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:5000")

def test_hero_collision_overflow_and_cinematic_scroll():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ══════════════════════════════════════════════════════════
        # TEST 1: NO COLLISION ON DESKTOP (1440x900 & 1366x768)
        # ══════════════════════════════════════════════════════════
        for width, height in [(1440, 900), (1366, 768)]:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)

            # Wait for preloader to clear
            try:
                page.wait_for_selector("#pagePreloader", state="hidden", timeout=5000)
            except Exception:
                page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")

            page.wait_for_selector("#heroShowcaseBadge", timeout=10000)
            page.wait_for_selector(".hero-trust-strip", timeout=10000)
            page.wait_for_timeout(400)

            trust_strip = page.locator(".hero-trust-strip")
            showcase_badge = page.locator("#heroShowcaseBadge")

            t_box = trust_strip.bounding_box()
            s_box = showcase_badge.bounding_box()

            print(f"\n[COLLISION TEST - {width}x{height}]")
            print(f"  Trust Strip Box: x={t_box['x']:.1f}, width={t_box['width']:.1f}, right={t_box['x'] + t_box['width']:.1f}")
            print(f"  Showcase Badge Box: x={s_box['x']:.1f}, width={s_box['width']:.1f}, right={s_box['x'] + s_box['width']:.1f}")

            # Check horizontal clearance (trust strip must end before showcase starts)
            clearance = s_box['x'] - (t_box['x'] + t_box['width'])
            print(f"  Clearance distance: {clearance:.1f}px")
            assert clearance > 15, f"Clearance between trust strip and showcase should be > 15px, got {clearance}px"

            # Check vertical clearance between VIP Zeka Island and Advisor Pill
            island = page.locator("#nxaIslandNav")
            advisor_pill = page.locator(".hero-advisor-pill")
            if island.is_visible() and advisor_pill.is_visible():
                i_box = island.bounding_box()
                p_box = advisor_pill.bounding_box()
                top_clearance = p_box['y'] - (i_box['y'] + i_box['height'])
                print(f"  VIP Island -> Advisor Pill vertical clearance: {top_clearance:.1f}px")
                assert top_clearance > 20, f"Advisor pill must have at least 20px clearance below Island, got {top_clearance}px"

            context.close()

        # ══════════════════════════════════════════════════════════
        # TEST 2: CLOSE BUTTON OVERFLOW TEST (WHEN PLAYING/DRAGGING)
        # ══════════════════════════════════════════════════════════
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("#pagePreloader", state="hidden", timeout=5000)
        except Exception:
            page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")

        page.wait_for_selector("#heroShowcaseBadge")
        badge = page.locator("#heroShowcaseBadge")
        grip = page.locator("#heroShowcaseBadge .showcase-drag-grip").first
        grip_box = grip.bounding_box()

        # Drag showcase to trigger reset button visibility
        page.mouse.move(grip_box["x"] + 5, grip_box["y"] + 5)
        page.mouse.down()
        page.wait_for_timeout(50)
        page.mouse.move(grip_box["x"] - 120, grip_box["y"] - 50, steps=8)
        page.wait_for_timeout(50)
        page.mouse.up()
        page.wait_for_timeout(300)

        reset_btn = page.locator("#showcaseResetPosBtn")
        assert reset_btn.is_visible(), "Reset position button should be visible after dragging"

        close_btn = page.locator(".hero-showcase-nav button.hero-ctrl-close").first
        assert close_btn.is_visible(), "Close button should be visible"

        badge_box = badge.bounding_box()
        close_box = close_btn.bounding_box()

        badge_right = badge_box["x"] + badge_box["width"]
        close_right = close_box["x"] + close_box["width"]
        inner_margin = badge_right - close_right

        print(f"\n[OVERFLOW TEST]")
        print(f"  Badge Right Edge: {badge_right:.1f}px")
        print(f"  Close Button Right Edge: {close_right:.1f}px")
        print(f"  Inner Margin (Safety Padding): {inner_margin:.1f}px")

        assert close_right <= badge_right, f"Close button overflows outside badge by {close_right - badge_right}px!"
        assert inner_margin >= 5, f"Close button should have at least 5px inner margin, got {inner_margin}px"
        print("  -> Close button is safely inside the card without any overflow!")

        # ══════════════════════════════════════════════════════════
        # TEST 3: CINEMATIC SCROLL IMMERSION TEST
        # ══════════════════════════════════════════════════════════
        # At top: hero content and showcase are visible
        content_opacity_initial = page.evaluate("() => window.getComputedStyle(document.querySelector('.hero-content')).opacity")
        showcase_opacity_initial = page.evaluate("() => window.getComputedStyle(document.getElementById('heroShowcaseBadge')).opacity")
        island_opacity_initial = page.evaluate("() => window.getComputedStyle(document.getElementById('nxaIslandNav')).opacity")

        print(f"\n[CINEMATIC SCROLL TEST - Initial at top]")
        print(f"  Hero Content Opacity: {content_opacity_initial}")
        print(f"  Showcase Opacity: {showcase_opacity_initial}")
        print(f"  VIP Island Opacity: {island_opacity_initial}")

        assert float(content_opacity_initial) > 0.8, "Hero content should be visible initially"
        assert float(showcase_opacity_initial) > 0.8, "Showcase badge should be visible initially"
        assert float(island_opacity_initial) > 0.8, "VIP Island should be visible initially"

        # Scroll down 60px
        page.evaluate("() => window.scrollTo(0, 95)")
        page.wait_for_timeout(600)  # wait for animation transition

        has_cinematic_mode = page.evaluate("() => document.body.classList.contains('hero-cinematic-mode')")
        assert has_cinematic_mode, "document.body should have .hero-cinematic-mode after scrolling down"

        content_opacity_scrolled = page.evaluate("() => window.getComputedStyle(document.querySelector('.hero-content')).opacity")
        showcase_opacity_scrolled = page.evaluate("() => window.getComputedStyle(document.getElementById('heroShowcaseBadge')).opacity")
        island_opacity_scrolled = page.evaluate("() => window.getComputedStyle(document.getElementById('nxaIslandNav')).opacity")

        print(f"[CINEMATIC SCROLL TEST - After scroll down 95px]")
        print(f"  Hero Content Opacity: {content_opacity_scrolled}")
        print(f"  Showcase Opacity: {showcase_opacity_scrolled}")
        print(f"  VIP Island Opacity (Should stay 1): {island_opacity_scrolled}")

        assert float(content_opacity_scrolled) < 0.05, "Hero content should fade out completely (opacity 0)"
        assert float(showcase_opacity_scrolled) < 0.05, "Showcase badge should fade out completely (opacity 0)"
        assert float(island_opacity_scrolled) >= 0.9, "VIP Zeka Menüsü island must remain visible!"

        # Scroll back to top
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(600)  # wait for animation transition

        has_cinematic_mode_restored = page.evaluate("() => document.body.classList.contains('hero-cinematic-mode')")
        assert not has_cinematic_mode_restored, "hero-cinematic-mode should be removed when scrolling back to top"

        content_opacity_restored = page.evaluate("() => window.getComputedStyle(document.querySelector('.hero-content')).opacity")
        showcase_opacity_restored = page.evaluate("() => window.getComputedStyle(document.getElementById('heroShowcaseBadge')).opacity")

        print(f"[CINEMATIC SCROLL TEST - After scrolling back to top]")
        print(f"  Hero Content Opacity: {content_opacity_restored}")
        print(f"  Showcase Opacity: {showcase_opacity_restored}")

        assert float(content_opacity_restored) > 0.8, "Hero content should be restored when scrolling to top"
        assert float(showcase_opacity_restored) > 0.8, "Showcase badge should be restored when scrolling to top"

        browser.close()
        print("\n>>> ALL TESTS PASSED: NO COLLISION, NO BUTTON OVERFLOW, CINEMATIC SCROLL IMMERSION 100% VERIFIED! <<<\n")

if __name__ == "__main__":
    test_hero_collision_overflow_and_cinematic_scroll()
