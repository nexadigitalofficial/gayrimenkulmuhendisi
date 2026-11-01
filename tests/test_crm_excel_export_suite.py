import io
import time
import pytest
import requests
import openpyxl
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

def test_crm_excel_export_get_endpoint():
    """Verify GET /api/crm/export/xlsx generates a valid 5-sheet styled workbook with Coldwell Banker CB VIP metadata."""
    url = f"{BASE_URL}/api/crm/export/xlsx"
    res = requests.get(url, timeout=15)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers.get("Content-Type", "")
    content_disp = res.headers.get("Content-Disposition", "")
    assert "attachment" in content_disp
    assert "NEXA_CRM_Musteri_Yedek_" in content_disp
    assert content_disp.endswith(".xlsx") or ".xlsx" in content_disp

    # Parse with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
    sheet_names = wb.sheetnames
    expected_sheets = [
        "📊 Özet & İstatistikler",
        "🎯 Alıcılar & Teklifler",
        "🏢 Satıcılar & Portföyler",
        "👥 Tüm Kişiler Veritabanı",
        "🛰️ Web Leadleri"
    ]
    for expected in expected_sheets:
        assert expected in sheet_names, f"Expected sheet '{expected}' in workbook. Found: {sheet_names}"

    # Verify Summary Sheet
    summary_ws = wb["📊 Özet & İstatistikler"]
    a1_val = str(summary_ws["A1"].value or "").upper()
    a2_val = str(summary_ws["A2"].value or "").upper()
    assert "COLDWELL BANKER" in a1_val
    assert "YIĞIT NARIN" in a2_val or "YİĞİT NARİN" in a2_val or "NARIN" in a2_val

    # Verify Buyers Sheet has records
    buyers_ws = wb["🎯 Alıcılar & Teklifler"]
    buyer_rows = list(buyers_ws.iter_rows(values_only=True))
    assert len(buyer_rows) >= 5, "Buyers sheet should have header rows and data"
    buyer_text = " ".join([str(cell) for row in buyer_rows for cell in row if cell is not None]).lower()
    assert "alıcı" in buyer_text or "teklif" in buyer_text or "cinnah" in buyer_text


def test_crm_excel_export_post_endpoint():
    """Verify POST /api/crm/export/xlsx handles custom frontend state payload."""
    url = f"{BASE_URL}/api/crm/export/xlsx"
    custom_contacts = [
        {
            "id": "c_test_01",
            "name": "Zeynep Kaya (Lüks Konut Alıcısı)",
            "phone": "+90 532 111 22 33",
            "email": "zeynep@example.com",
            "category": "buyer",
            "role": "buyer",
            "status": "active",
            "pipelineStage": "Pazarlık",
            "price": 28500000,
            "offer": "28.500.000 ₺",
            "notes": "İncek bölgesinde 5+1 villa arıyor.",
            "source": "Tavsiye",
            "tags": ["Lüks", "Nakit Hazır"],
            "listingTitle": "İncek Loft Özel Villa"
        },
        {
            "id": "c_test_02",
            "name": "Murat Arslan (Mülk Sahibi)",
            "phone": "+90 533 444 55 66",
            "email": "murat@example.com",
            "category": "seller",
            "role": "seller",
            "status": "warm",
            "pipelineStage": "Portföy Alındı",
            "price": 42000000,
            "notes": "Çayyolu ticari plaza katı.",
            "source": "FSBO",
            "tags": ["Ticari", "Tek Yetkili"],
            "listingTitle": "Çayyolu Prestij Plaza"
        }
    ]

    res = requests.post(url, json={"contacts": custom_contacts}, timeout=15)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    wb = openpyxl.load_workbook(io.BytesIO(res.content), data_only=True)
    all_ws = wb["👥 Tüm Kişiler Veritabanı"]
    all_rows = list(all_ws.iter_rows(values_only=True))
    all_text = " ".join([str(cell) for row in all_rows for cell in row if cell is not None])
    assert "Zeynep Kaya" in all_text
    assert "Murat Arslan" in all_text

    buyers_ws = wb["🎯 Alıcılar & Teklifler"]
    b_text = " ".join([str(cell) for row in buyers_ws.iter_rows(values_only=True) for cell in row if cell is not None])
    assert "Zeynep Kaya" in b_text

    sellers_ws = wb["🏢 Satıcılar & Portföyler"]
    s_text = " ".join([str(cell) for row in sellers_ws.iter_rows(values_only=True) for cell in row if cell is not None])
    assert "Murat Arslan" in s_text


def test_crm_ui_excel_export_buttons_playwright():
    """Verify CRM page renders the Excel Export buttons and initiates file download cleanly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Listen for console errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        # Load demo mode to pass authentication gate
        page.goto(f"{BASE_URL}/crm?demo=1", wait_until="domcontentloaded", timeout=15000)

        # 1. Verify Header Excel button exists and is visible
        page.wait_for_selector("#btn-excel-export-header", timeout=10000)
        btn_header_excel = page.locator("#btn-excel-export-header")
        assert btn_header_excel.count() > 0, "Header Excel button #btn-excel-export-header must exist"
        btn_text = btn_header_excel.inner_text()
        assert "Excel" in btn_text

        # 2. Trigger download event by clicking header export button
        with page.expect_download(timeout=15000) as download_info:
            btn_header_excel.click()
        download = download_info.value
        filename = download.suggested_filename
        assert filename.startswith("NEXA_CRM_Musteri_Yedek_")
        assert filename.endswith(".xlsx")

        # 3. Switch to contacts view via sidebar and verify toolbar export button
        page.locator("button.sidebar-item:has(i.fa-users)").first.click()
        page.wait_for_selector("#btn-excel-export-toolbar", timeout=5000)
        btn_toolbar_excel = page.locator("#btn-excel-export-toolbar")
        assert btn_toolbar_excel.count() > 0
        assert "Excel" in btn_toolbar_excel.inner_text()

        # 4. Verify dropdown menu item
        page.locator("button:has(i.fa-ellipsis-v)").first.click()
        page.wait_for_selector("#btn-excel-export-dropdown", timeout=5000)
        dropdown_btn = page.locator("#btn-excel-export-dropdown")
        assert dropdown_btn.count() > 0
        assert "Excel" in dropdown_btn.inner_text()

        browser.close()
