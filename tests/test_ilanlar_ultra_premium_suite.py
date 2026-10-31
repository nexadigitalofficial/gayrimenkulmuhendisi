import sys
import time
from playwright.sync_api import sync_playwright

def run_suite():
    print("=======================================================")
    print("TEST SUITE: ILANLAR ULTRA PREMIUM SUITE")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ----------------------------------------------------
        # TEST 1: Desktop Load & Stat Verification
        # ----------------------------------------------------
        print("\n--- TEST 1: Desktop Load & Statistics ---")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:5000/ilanlar", wait_until="networkidle")
        page.wait_for_selector(".lc", timeout=8000)

        cards = page.locator(".lc")
        card_count = cards.count()
        print(f"PASS: Found {card_count} listing cards on page 1")
        assert card_count > 0, "No listing cards found!"

        # Check stats
        stat_total = page.locator("#statTotal").inner_text()
        stat_satilik = page.locator("#statSatilik").inner_text()
        stat_kiralik = page.locator("#statKiralik").inner_text()
        print(f"Stats loaded: Total={stat_total}, Satilik={stat_satilik}, Kiralik={stat_kiralik}")
        assert int(stat_total) >= 16, f"Expected at least 16 listings, got {stat_total}"

        # ----------------------------------------------------
        # TEST 2: Instant Smart Search in Hero
        # ----------------------------------------------------
        print("\n--- TEST 2: Instant Smart Search in Hero ---")
        search_input = page.locator("#heroSearchInput")
        search_input.fill("Gölbaşı")
        page.wait_for_timeout(500)

        filtered_count = page.locator(".lc").count()
        print(f"PASS: After searching 'Gölbaşı', displayed cards: {filtered_count}")
        assert filtered_count > 0 and filtered_count < card_count, "Search filter did not reduce card count!"

        # Clear search
        page.locator("#heroSearchClear").click()
        page.wait_for_timeout(500)
        reset_count = page.locator(".lc").count()
        print(f"PASS: After clearing search, displayed cards: {reset_count}")
        assert reset_count == card_count, "Clearing search did not reset cards!"

        # ----------------------------------------------------
        # TEST 3: Quick District Chip Filtering
        # ----------------------------------------------------
        print("\n--- TEST 3: Quick District Chip Filtering ---")
        cankaya_pill = page.locator(".district-pill[data-district='Çankaya']")
        cankaya_pill.click()
        page.wait_for_timeout(500)

        cankaya_cards = page.locator(".lc").count()
        print(f"PASS: After selecting 'Çankaya' chip, displayed cards: {cankaya_cards}")
        assert cankaya_cards > 0, "Çankaya district returned no cards!"

        # Reset via Tümü
        page.locator(".district-pill[data-district='']").click()
        page.wait_for_timeout(500)
        assert page.locator(".lc").count() == card_count, "Resetting district failed!"

        # ----------------------------------------------------
        # TEST 4: Type Pill (Kiralık vs Satılık)
        # ----------------------------------------------------
        print("\n--- TEST 4: Type Pill (Kiralık) ---")
        kiralik_pill = page.locator(".type-pill[data-type='Kiralık']")
        kiralik_pill.click()
        page.wait_for_timeout(500)

        kiralik_count = page.locator(".lc").count()
        print(f"PASS: 'Kiralık' listings count: {kiralik_count}")
        assert kiralik_count == int(stat_kiralik), f"Expected {stat_kiralik} kiralık, got {kiralik_count}"

        # Reset via Tümü
        page.locator(".type-pill[data-type='']").click()
        page.wait_for_timeout(500)

        # ----------------------------------------------------
        # TEST 5: Favorite Heart Toggle & Persistence
        # ----------------------------------------------------
        print("\n--- TEST 5: Favorite Heart Toggle ---")
        first_fav = page.locator(".lc .lc-fav").first
        first_fav.click()
        page.wait_for_timeout(300)
        assert "active" in first_fav.get_attribute("class"), "Favorite button did not become active!"
        print("PASS: Favorite heart active toggle verified!")

        # ----------------------------------------------------
        # TEST 6: AI Swarm Persona Modal Open & Close
        # ----------------------------------------------------
        print("\n--- TEST 6: AI Swarm Persona Modal ---")
        first_persona_btn = page.locator(".lc .nxc-persona-btn").first
        first_persona_btn.click()
        page.wait_for_selector("#nxp-persona-overlay", timeout=5000)
        page.wait_for_timeout(600)

        overlay_display = page.evaluate("() => window.getComputedStyle(document.getElementById('nxp-persona-overlay')).display")
        assert overlay_display != "none", "Persona overlay did not open!"
        print("PASS: AI Persona Intelligence modal opened successfully!")

        # Close persona modal
        page.locator(".nxp-p-close-btn").click()
        page.wait_for_timeout(400)
        overlay_display_after = page.evaluate("() => window.getComputedStyle(document.getElementById('nxp-persona-overlay')).display")
        assert overlay_display_after == "none", "Persona overlay did not close!"
        print("PASS: AI Persona modal closed cleanly!")

        # ----------------------------------------------------
        # TEST 7: Mobile Viewport & Responsiveness
        # ----------------------------------------------------
        print("\n--- TEST 7: Mobile Viewport (390x844) ---")
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile.goto("http://127.0.0.1:5000/ilanlar", wait_until="networkidle")
        mobile.wait_for_selector(".lc", timeout=8000)

        # Verify no horizontal scroll / overflow
        scroll_width = mobile.evaluate("() => document.documentElement.scrollWidth")
        client_width = mobile.evaluate("() => document.documentElement.clientWidth")
        print(f"Mobile widths: scrollWidth={scroll_width}, clientWidth={client_width}")
        assert scroll_width <= client_width + 1, f"Horizontal overflow detected on mobile: {scroll_width} > {client_width}"
        print("PASS: Zero horizontal overflow on mobile verified!")

        browser.close()

    print("\n=======================================================")
    print("ALL ILANLAR ULTRA PREMIUM TESTS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    run_suite()
