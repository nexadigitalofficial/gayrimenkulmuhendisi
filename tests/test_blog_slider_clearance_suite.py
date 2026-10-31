import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

def test_blog_slider_arrows_clearance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ══════════════════════════════════════════════════════════
        # 1. Desktop Test (1440x900)
        # ══════════════════════════════════════════════════════════
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="commit", timeout=30000)
        
        try:
            page.wait_for_selector("#pagePreloader", state="hidden", timeout=4000)
        except Exception:
            page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")
            
        page.wait_for_selector(".blog-slide", timeout=10000)
        page.evaluate("() => document.getElementById('haberlerSection').scrollIntoView()")
        page.wait_for_timeout(500)
        
        # Clear timer
        page.evaluate("() => { if (window.blogAutoInterval) clearInterval(window.blogAutoInterval); window.blogAutoInterval = null; }")
        page.wait_for_timeout(300)
        
        prev_btn = page.locator("#blogPrev")
        next_btn = page.locator("#blogNext")
        
        assert prev_btn.is_visible(), "Prev button should be visible"
        assert next_btn.is_visible(), "Next button should be visible"
        
        pb = prev_btn.bounding_box()
        nb = next_btn.bounding_box()
        
        print("\n[BLOG SLIDER ARROWS DESKTOP TEST - 1440x900]")
        print(f"  Prev Arrow Box: x={pb['x']:.1f}..{pb['x']+pb['width']:.1f}")
        print(f"  Next Arrow Box: x={nb['x']:.1f}..{nb['x']+nb['width']:.1f}")
        
        # Test 4 sequential slides
        for s in range(4):
            # Check active slide bounding box
            slide_data = page.evaluate("""(s) => {
                const slides = document.querySelectorAll('.blog-slide');
                const activeSlide = slides[s];
                const cards = activeSlide.querySelectorAll('.card');
                const c0 = cards[0].getBoundingClientRect();
                const cLast = cards[cards.length - 1].getBoundingClientRect();
                return {
                    firstX: c0.x,
                    lastRight: cLast.right
                };
            }""", s)
            
            clearance_left = slide_data["firstX"] - (pb["x"] + pb["width"])
            clearance_right = nb["x"] - slide_data["lastRight"]
            
            print(f"  Slide {s}:")
            print(f"    Left Clearance (Prev Arrow -> First Card): {clearance_left:.1f}px")
            print(f"    Right Clearance (Last Card -> Next Arrow): {clearance_right:.1f}px")
            
            assert clearance_left >= 5.0, f"Prev arrow collides on slide {s}! Clearance: {clearance_left}px"
            assert clearance_right >= 5.0, f"Next arrow collides on slide {s}! Clearance: {clearance_right}px"
            
            next_btn.click()
            page.wait_for_timeout(600) # wait for smooth slide transition
            # Freeze auto timer if restarted by click
            page.evaluate("() => { if (window.blogAutoInterval) clearInterval(window.blogAutoInterval); window.blogAutoInterval = null; }")
            
        print("  -> Desktop 1440x900: All slides tested with zero arrow collision!")
        context.close()
        
        # ══════════════════════════════════════════════════════════
        # 2. Tablet Test (1024x768)
        # ══════════════════════════════════════════════════════════
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="commit", timeout=30000)
        try:
            page.wait_for_selector("#pagePreloader", state="hidden", timeout=4000)
        except Exception:
            page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")
            
        page.wait_for_selector(".blog-slide", timeout=10000)
        page.evaluate("() => document.getElementById('haberlerSection').scrollIntoView()")
        page.wait_for_timeout(500)
        page.evaluate("() => { if (window.blogAutoInterval) clearInterval(window.blogAutoInterval); window.blogAutoInterval = null; }")
        
        pb = page.locator("#blogPrev").bounding_box()
        nb = page.locator("#blogNext").bounding_box()
        
        card_boxes = page.evaluate("""() => {
            const first = document.querySelector('.blog-slider .card').getBoundingClientRect();
            return { x: first.x, right: first.right };
        }""")
        
        clearance_left = card_boxes["x"] - (pb["x"] + pb["width"])
        print(f"\n[BLOG SLIDER ARROWS TABLET TEST - 1024x768]")
        print(f"  Prev Arrow Clearance: {clearance_left:.1f}px")
        assert clearance_left >= 5.0, f"Tablet collision! Clearance: {clearance_left}px"
        context.close()
        
        # ══════════════════════════════════════════════════════════
        # 3. Mobile Test (390x844)
        # ══════════════════════════════════════════════════════════
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(BASE_URL, wait_until="commit", timeout=30000)
        try:
            page.wait_for_selector("#pagePreloader", state="hidden", timeout=4000)
        except Exception:
            page.evaluate("() => { const p = document.getElementById('pagePreloader'); if (p) p.remove(); }")
            
        page.wait_for_selector(".blog-slide", timeout=10000)
        page.evaluate("() => document.getElementById('haberlerSection').scrollIntoView()")
        page.wait_for_timeout(500)
        page.evaluate("() => { if (window.blogAutoInterval) clearInterval(window.blogAutoInterval); window.blogAutoInterval = null; }")
        
        pb = page.locator("#blogPrev").bounding_box()
        nb = page.locator("#blogNext").bounding_box()
        
        card_boxes = page.evaluate("""() => {
            const first = document.querySelector('.blog-slider .card').getBoundingClientRect();
            return { x: first.x, right: first.right };
        }""")
        
        clearance_left = card_boxes["x"] - (pb["x"] + pb["width"])
        clearance_right = nb["x"] - card_boxes["right"]
        print(f"\n[BLOG SLIDER ARROWS MOBILE TEST - 390x844]")
        print(f"  Prev Arrow Clearance: {clearance_left:.1f}px")
        print(f"  Next Arrow Clearance: {clearance_right:.1f}px")
        assert clearance_left >= 4.0, f"Mobile left collision! Clearance: {clearance_left}px"
        assert clearance_right >= 4.0, f"Mobile right collision! Clearance: {clearance_right}px"
        context.close()
        
        browser.close()
        print("\n>>> ALL BLOG SLIDER ARROW CLEARANCE TESTS PASSED 100%! <<<")

if __name__ == "__main__":
    test_blog_slider_arrows_clearance()
