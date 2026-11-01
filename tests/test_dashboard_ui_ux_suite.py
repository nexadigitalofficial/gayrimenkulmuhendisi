import pytest
from playwright.sync_api import sync_playwright

def test_dashboard_renders_and_functions():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Navigate to /dashboard
        res = page.goto("http://127.0.0.1:5000/dashboard", wait_until="domcontentloaded", timeout=15000)
        assert res.status == 200, f"Expected 200, got {res.status}"

        page.wait_for_selector("header")

        # 1. Verify Brand and Telemetry Ribbon
        assert page.is_visible("text=NEXA")
        assert page.is_visible("text=COGNITIVE PROPTECH COMMAND CENTER")
        assert page.is_visible("text=CORE ENGINE ONLINE")
        assert page.is_visible("text=32.279 MAHALLE RADAR")

        # 2. Verify Operational Metrics HUD
        assert page.is_visible("text=TÜRKİYE LOKASYON VERİTABANI")
        assert page.is_visible("text=81 İl · 973 İlçe")
        assert page.is_visible("text=NLP & GEMINI AYRIŞTIRMA")
        assert page.is_visible("text=NEXA ORBIT™ RADAR")

        # 3. Verify Tabs are present and tab-nav has no ugly scrollbar
        tab_btns = page.locator(".tab-btn")
        assert tab_btns.count() >= 7

        # 4. Verify Dock Navigation Chevrons
        left_arrow = page.locator("#dockScrollLeft")
        right_arrow = page.locator("#dockScrollRight")
        assert left_arrow.is_visible(), "Dock scroll left chevron must be visible"
        assert right_arrow.is_visible(), "Dock scroll right chevron must be visible"

        # Verify scrollbar is zero / hidden on dockNav
        dock_scroll_style = page.evaluate("""() => {
            const el = document.getElementById('dockNav');
            const style = window.getComputedStyle(el);
            return {
                scrollbarWidth: style.scrollbarWidth,
                overflowX: style.overflowX
            };
        }""")
        assert dock_scroll_style["scrollbarWidth"] in ["none", ""], "Dock scrollbar must be 'none'"
        assert dock_scroll_style["overflowX"] in ["auto", "scroll"], "Dock must allow horizontal scrolling"

        # Click right arrow to test smooth scrolling
        initial_scroll = page.evaluate("() => document.getElementById('dockNav').scrollLeft")
        right_arrow.click()
        page.wait_for_timeout(400)
        scrolled_pos = page.evaluate("() => document.getElementById('dockNav').scrollLeft")
        print(f"Dock scroll position: initial={initial_scroll}, after arrow click={scrolled_pos}")
        assert scrolled_pos > initial_scroll, f"Clicking dock arrow must scroll right! Got: {scrolled_pos}"

        # 5. Test clicking Quick Preset Cards to populate textarea
        page.click("text=Alacaatlı 4+1 Villa")
        prompt_val = page.input_value("#crit_prompt")
        assert "Alacaatlı" in prompt_val, f"Unexpected prompt value: {prompt_val}"

        # 6. Test Tab Switching
        # Switch to Orbit Tab
        page.click("#tabBtn-orbit")
        assert page.is_visible("#pane-orbit")
        assert page.is_visible("text=NEXA ORBIT™ — OTONOM TERSİNE EMSAL")

        # Switch to Sahibinden Tab
        page.click("#tabBtn-sahibinden")
        assert page.is_visible("#pane-sahibinden")
        assert page.is_visible("text=Sahibinden Scraper Engine Settings")

        # Switch to PDF Tab
        page.click("#tabBtn-pdf")
        assert page.is_visible("#pane-pdf")
        assert page.is_visible("text=İlan URL'si → Lüks Sunum PDF")

        # Take screenshot of the new dashboard
        page.click("#tabBtn-criteria")
        screenshot_path = "C:/Users/USER/.gemini/antigravity/brain/dedfc675-1c76-4d60-a9ec-14bf967b3a5c/dashboard_futuristic_preview.png"
        page.screenshot(path=screenshot_path)
        print(f"Dashboard screenshot successfully captured: {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    test_dashboard_renders_and_functions()
    print("ALL TESTS PASSED!")
