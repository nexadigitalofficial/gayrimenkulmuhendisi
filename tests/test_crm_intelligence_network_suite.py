import pytest
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

def test_crm_intelligence_network_ui_and_logic():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        response = page.goto(f"{BASE_URL}/crm", wait_until="domcontentloaded", timeout=15000)
        assert response.status == 200, f"CRM failed to load: {response.status}"

        # Wait for #app to mount
        page.wait_for_selector("#app", timeout=10000)
        time.sleep(1)

        # 1. Simulate authentication so main CRM layout renders
        auth_state = page.evaluate("""() => {
            const app = document.querySelector('#app').__vue_app__;
            if (!app || !app._instance || !app._instance.setupState) return null;
            const state = app._instance.setupState;
            state.user = {
                uid: 'RnHhsj3K4VSWRY4cjc3Pc09JMFn2',
                email: 'yigitnarin2001@gmail.com',
                displayName: 'Yiğit Narin'
            };
            state.authLoading = false;
            return {
                userUid: state.user.uid,
                hasNetworkStats: !!state.networkStats,
                hasComputeScore: typeof state.computeContactScore === 'function'
            };
        }""")

        assert auth_state is not None, "Failed to access Vue setupState on #app"
        assert auth_state["hasNetworkStats"] is True
        assert auth_state["hasComputeScore"] is True

        time.sleep(1)

        # 2. Check that no fatal JS errors occurred
        fatal_errors = [e for e in console_errors if "ReferenceError" in e or "SyntaxError" in e or "TypeError" in e]
        assert not fatal_errors, f"Fatal JS errors on /crm: {fatal_errors}"

        # 3. Check Sidebar Item for "İstihbarat Ağı" and click it
        network_nav_button = page.locator("button:has(.fa-project-diagram)")
        assert network_nav_button.count() >= 1, "Sidebar button with .fa-project-diagram not found!"
        network_nav_button.first.click()
        time.sleep(1)

        # Verify key sections in the Network View are visible
        page.wait_for_selector("text=Kim Kimin", timeout=5000)
        page.wait_for_selector("text=Referans Merkezleri", timeout=5000)
        page.wait_for_selector("text=Takas", timeout=5000)

        # 4. Check Contacts table integration
        contacts_nav_button = page.locator(".sidebar-nav button:has(.fa-users)")
        assert contacts_nav_button.count() >= 1
        contacts_nav_button.first.click()
        time.sleep(1)

        # Check column headers
        page.wait_for_selector("text=Kategori", timeout=5000)
        page.wait_for_selector("text=Aşama", timeout=5000)
        page.wait_for_selector("text=Skor", timeout=5000)

        # Verify quick link to network view from contacts top bar
        assert page.locator("button:has(.fa-project-diagram)").count() >= 2

        # 5. Open Contact modal and check intelligence fields
        new_record_btn = page.locator("button:has(.fa-plus)")
        if new_record_btn.count():
            new_record_btn.first.click()
            time.sleep(1)

            modal = page.locator(".modal-content")
            assert modal.is_visible()
            modal_text = modal.text_content()
            assert "stihbarat" in modal_text or "Zincir" in modal_text
            assert "Takas" in modal_text
            assert "Arketip" in modal_text or "Profil" in modal_text

            close_btn = page.locator(".modal-content button:has(.fa-times)")
            if close_btn.count():
                close_btn.first.click()

        # 6. Verify CSS badges in DOM
        css_check = page.evaluate("""() => {
            const styleText = Array.from(document.querySelectorAll('style')).map(s => s.textContent).join(' ');
            return {
                hasHotBadge: styleText.includes('.badge-hot'),
                hasTreeStyles: styleText.includes('.network-tree')
            };
        }""")

        assert css_check["hasHotBadge"] is True, "CSS .badge-hot styles missing in DOM!"
        assert css_check["hasTreeStyles"] is True, "CSS .network-tree styles missing in DOM!"

        print("\n[OK] NEXA Intelligence Network test suite passed 100%!")

        browser.close()
