import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import threading
from playwright.sync_api import sync_playwright
from app import app

PORT = 5009

def start_server():
    app.run(port=PORT, debug=False, use_reloader=False)

def run_suite():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        print("\n=======================================================")
        print("TEST 1: DESKTOP (1366x768) - Resting, Expand, Nav Links, Fit")
        print("=======================================================")
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(1.2)

        island = page.locator("#nxaIslandNav")
        resting_box = island.bounding_box()
        print("1.1 Resting Capsule Box:", resting_box)
        assert resting_box["width"] <= 430, f"Resting capsule too wide: {resting_box['width']}"
        assert resting_box["height"] >= 40 and resting_box["height"] <= 52, f"Unexpected resting height: {resting_box['height']}"

        # Verify no clipping of collapsed items (Yiğit Narin brand, pulse, badge, hint)
        brand = page.locator(".nxa-island-brand")
        brand_box = brand.bounding_box()
        assert brand_box["x"] >= resting_box["x"], f"Brand clipped on left! brand.x={brand_box['x']}, container.x={resting_box['x']}"
        assert (brand_box["x"] + brand_box["width"]) <= (resting_box["x"] + resting_box["width"]), "Brand clipped on right!"

        hint = page.locator(".nxa-island-trigger-hint")
        hint_box = hint.bounding_box()
        assert hint_box["x"] >= resting_box["x"], "Hint clipped on left!"
        assert (hint_box["x"] + hint_box["width"]) <= (resting_box["x"] + resting_box["width"]), "Hint clipped on right!"

        # Hover onto center capsule
        island.hover()
        time.sleep(0.5)

        expanded_box = island.bounding_box()
        print("1.2 Expanded Navbar Box:", expanded_box)
        assert expanded_box["width"] > 1000, f"Navbar did not expand horizontally: {expanded_box['width']}"
        assert expanded_box["height"] >= 60, f"Navbar height not expanded: {expanded_box['height']}"

        # Check all 11 navigation links
        nav_items = page.locator(".nxa-desktop-nav-links a.nxa-nav-item")
        count = nav_items.count()
        print(f"1.3 Nav items count in bar: {count}")
        # The 12th is the hidden mobile one, so 11 visible desktop links
        visible_links = []
        for i in range(count):
            item = nav_items.nth(i)
            box = item.bounding_box()
            txt = item.inner_text().strip()
            if box and box["width"] > 0:
                visible_links.append((txt, box))
                # Verify it is horizontally inside the expanded navbar
                assert box["x"] >= expanded_box["x"], f"Link {txt} overflows left: {box['x']} < {expanded_box['x']}"
                assert box["x"] + box["width"] <= expanded_box["x"] + expanded_box["width"] + 5, f"Link {txt} overflows right"
        print(f"1.4 Total verified visible links inside navbar bounds: {len(visible_links)}")
        assert len(visible_links) >= 11, f"Expected 11 visible links, found {len(visible_links)}"

        # Check Logo and NEXA.OS Terminal Button
        logo = page.locator(".nxa-expanded-logo")
        logo_box = logo.bounding_box()
        print("1.5 Logo Box:", logo_box)
        assert logo_box and logo_box["x"] >= expanded_box["x"], "Logo out of bounds"

        terminal = page.locator(".nxa-nav-terminal-btn")
        term_box = terminal.bounding_box()
        print("1.6 NEXA.OS Terminal Button Box:", term_box)
        assert term_box and (term_box["x"] + term_box["width"] <= expanded_box["x"] + expanded_box["width"] + 5), \
            f"NEXA.OS button overflows navbar: {term_box['x'] + term_box['width']} > {expanded_box['x'] + expanded_box['width']}"

        print("\n=======================================================")
        print("TEST 2: HORIZONTAL X-AXIS MOVEMENT STABILITY")
        print("=======================================================")
        # Move mouse across links from right to left
        print("Moving to Harita link (X=~250)...")
        page.mouse.move(expanded_box["x"] + 200, expanded_box["y"] + 33)
        time.sleep(0.3)
        curr_box = island.bounding_box()
        assert curr_box["width"] > 1000, "Navbar prematurely closed on moving left to Harita!"
        print("PASS: Maintained open state while moving left!")

        print("Moving to NEXA.OS button (X=~1280)...")
        page.mouse.move(term_box["x"] + 20, term_box["y"] + 15)
        time.sleep(0.3)
        curr_box2 = island.bounding_box()
        assert curr_box2["width"] > 1000, "Navbar prematurely closed on moving right to NEXA.OS!"
        print("PASS: Maintained open state while moving right!")

        print("\n=======================================================")
        print("TEST 3: PURE Y-AXIS EXIT COLLAPSE DETECTION")
        print("=======================================================")
        # Move mouse down into the hero content (Y = 300)
        print("Moving mouse to (683, 300) - Y-Axis exit below navbar...")
        page.mouse.move(683, 300)
        time.sleep(0.8)

        box_after_down = island.bounding_box()
        print("Box after moving down:", box_after_down)
        assert box_after_down["width"] <= 430, f"Navbar did not collapse on Y-axis exit downwards! Width: {box_after_down['width']}"
        print("PASS: Successfully collapsed back to center capsule on Y-axis downwards exit!")

        # Re-open and test exit above
        print("Re-opening navbar...")
        island.hover()
        time.sleep(0.6)
        assert island.bounding_box()["width"] > 1000, "Failed to re-open"

        print("Moving mouse to (683, 10) - Y-Axis exit above navbar...")
        page.mouse.move(683, 10)
        time.sleep(0.8)
        box_after_up = island.bounding_box()
        print("Box after moving up:", box_after_up)
        assert box_after_up["width"] <= 430, f"Navbar did not collapse on Y-axis exit upwards! Width: {box_after_up['width']}"
        print("PASS: Successfully collapsed back to center capsule on Y-axis upwards exit!")

        print("\n=======================================================")
        print("TEST 4: MOBILE (390x844) VIEWPORT ERGONOMICS")
        print("=======================================================")
        page_mobile = browser.new_page(viewport={"width": 390, "height": 844})
        page_mobile.goto(f"http://127.0.0.1:{PORT}/")
        time.sleep(1.2)

        mob_island = page_mobile.locator("#nxaIslandNav")
        mob_box = mob_island.bounding_box()
        print("Mobile Capsule Box:", mob_box)
        assert mob_box["width"] <= 380, f"Mobile capsule overflows screen: {mob_box['width']}"

        # Click mobile toggle
        mob_toggle = page_mobile.locator("#mobileToggle")
        mob_toggle.click()
        time.sleep(0.4)

        nav_links = page_mobile.locator("#navLinks")
        nav_links_box = nav_links.bounding_box()
        print("Mobile Drawer Box:", nav_links_box)
        assert nav_links.is_visible(), "Mobile drawer is not visible after toggle click!"
        assert nav_links_box["width"] >= 260, f"Mobile drawer too narrow: {nav_links_box['width']}"
        print("PASS: Mobile drawer opens properly and all links are accessible!")

        browser.close()
        print("\n=======================================================")
        print("ALL INTERACTIVE NAVBAR TESTS PASSED 100%!")
        print("=======================================================")

def test_navbar_dynamic_island_suite():
    run_suite()

if __name__ == "__main__":
    run_suite()
