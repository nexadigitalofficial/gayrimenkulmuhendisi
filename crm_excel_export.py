"""
COLDWELL BANKER CB VIP ANKARA — NEXA.OS CRM
Kurumsal ve Kategorize Edilmiş Excel (XLSX) Dışa Aktarma & Yedekleme Motoru

Bu modül, CRM'deki tüm müşteri, alıcı, satıcı, FSBO, ilan alıcıları ve web leadlerini
profesyonel yönetici seviyesinde, çok sekmeli ve stilize edilmiş bir Excel (.xlsx) çalışma
kitabına dönüştürür.
"""

import io
import re
import os
import json
import sqlite3
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ── KURUMSAL RENK PALETİ ──────────────────────────────────────────
NAVY_HEADER = "0F172A"       # Midnight Navy (#0F172A)
CB_GOLD = "D4AF37"           # Coldwell Banker Altın (#D4AF37)
PURPLE_HEADER = "312E81"     # Indigo/Purple (#312E81)
EMERALD_HEADER = "064E3B"    # Forest/Emerald (#064E3B)
CYAN_HEADER = "0E7490"       # Deep Cyan (#0E7490)
SUBTLE_BORDER = "CBD5E1"     # Slate 300 (#CBD5E1)
ZEBRA_LIGHT_NAVY = "F8FAFC"  # Slate 50
ZEBRA_LIGHT_PURPLE = "FAF5FF"# Purple 50
ZEBRA_LIGHT_EMERALD = "F0FDF4"# Emerald 50
ZEBRA_LIGHT_CYAN = "ECFEFF"  # Cyan 50
CARD_BG = "F1F5F9"           # Slate 100


def _clean_str(val, default=""):
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _parse_currency(val):
    """Metin içindeki para tutarını temiz bir tamsayıya dönüştürür."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    digits = re.sub(r'[^0-9]', '', s)
    return int(digits) if digits else 0


def _style_header_cell(cell, fill_hex, font_color="FFFFFF", font_size=11, bold=True, align="left"):
    cell.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
    cell.font = Font(name="Segoe UI", size=font_size, bold=bold, color=font_color)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    thin = Side(border_style="thin", color=SUBTLE_BORDER)
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)


def _safe_cell_val(val):
    if val is None:
        return ""
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            val = val.replace(tzinfo=None)
        return val.strftime("%d.%m.%Y %H:%M")
    if hasattr(val, 'strftime'):
        return val.strftime("%d.%m.%Y")
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return val

def _format_date_val(val):
    if not val:
        return "-"
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            val = val.replace(tzinfo=None)
        return val.strftime("%d.%m.%Y %H:%M")
    if hasattr(val, 'strftime'):
        return val.strftime("%d.%m.%Y")
    s = str(val).strip()
    try:
        if "T" in s:
            clean_s = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_s)
            return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        pass
    return s if s else "-"

def _style_data_cell(cell, fill_hex=None, font_color="000000", font_size=10, bold=False, align="left", num_format=None):
    cell.value = _safe_cell_val(cell.value)
    if fill_hex:
        cell.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
    cell.font = Font(name="Segoe UI", size=font_size, bold=bold, color=font_color)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    thin = Side(border_style="thin", color=SUBTLE_BORDER)
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    if num_format:
        cell.number_format = num_format


def _autofit_columns(ws, min_width=12, max_width=65, padding=3):
    """Sütun genişliklerini içeriğe göre hesaplar ve otomatik ayarlar."""
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val = cell.value
            if val is not None:
                lines = str(val).split("\n")
                line_max = max(len(l) for l in lines)
                if line_max > max_len:
                    max_len = line_max
        adjusted_width = max(max_len + padding, min_width)
        adjusted_width = min(adjusted_width, max_width)
        ws.column_dimensions[col_letter].width = adjusted_width


def _collect_master_data(provided_contacts=None, provided_leads=None, db_admin=None):
    """
    Tüm kaynaklardan (Frontend payload, Firestore Admin, SQLite, JSON)
    müşteri ve alıcı kayıtlarını toplar ve tekilleştirir.
    """
    contacts_map = {}

    # 1. Frontend tarafından gönderilen canlı bellek kayıtları
    if provided_contacts and isinstance(provided_contacts, list):
        for c in provided_contacts:
            cid = c.get("id") or f"c_{len(contacts_map)+1}"
            contacts_map[cid] = dict(c)

    # 2. SQLite veritabanındaki portföy alıcıları
    try:
        db_path = os.path.join("data", "intelligence.db")
        if os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_listing_buyers';")
                if cur.fetchone():
                    cur.execute("SELECT * FROM portfolio_listing_buyers")
                    for row in cur.fetchall():
                        r = dict(row)
                        bid = r.get("id")
                        if bid and bid not in contacts_map:
                            contacts_map[bid] = {
                                "id": bid,
                                "name": r.get("name") or "İlan Alıcısı",
                                "phone": r.get("phone") or "-",
                                "email": r.get("email") or "-",
                                "category": "buyer",
                                "role": "buyer",
                                "type": "buyer",
                                "stage": r.get("stage") or "Yeni Talep",
                                "stageName": r.get("stage") or "Yeni Talep",
                                "price": _parse_currency(r.get("offer")),
                                "offer": r.get("offer") or "",
                                "source": "listing",
                                "source_label": "İlan Alıcısı",
                                "listingRef": r.get("refId") or "",
                                "listingTitle": r.get("listingTitle") or "Portföy İlanı",
                                "notes": f"📌 İlan: {r.get('listingTitle')}\nTeklif: {r.get('offer')}\nNot: {r.get('note')}",
                                "createdAt": r.get("createdAt") or datetime.now().strftime("%d.%m.%Y %H:%M")
                            }
    except Exception as e:
        print(f"⚠️ SQLite contacts read error: {e}")

    # 3. JSON dosyasındaki portföy alıcıları
    try:
        json_path = os.path.join("static", "data", "portfolio_listing_dashboards.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                dash_data = json.load(f)
            for ref_id, item in dash_data.items():
                for b in item.get("buyers", []):
                    bid = b.get("id")
                    if bid and bid not in contacts_map:
                        contacts_map[bid] = {
                            "id": bid,
                            "name": b.get("name") or "İlan Alıcısı",
                            "phone": b.get("phone") or "-",
                            "email": b.get("email") or "-",
                            "category": "buyer",
                            "role": "buyer",
                            "type": "buyer",
                            "stage": b.get("stage") or "Yeni Talep",
                            "stageName": b.get("stage") or "Yeni Talep",
                            "price": _parse_currency(b.get("offer")),
                            "offer": b.get("offer") or "",
                            "source": "listing",
                            "source_label": "İlan Alıcısı",
                            "listingRef": b.get("refId") or ref_id,
                            "listingTitle": b.get("listingTitle") or "Portföy İlanı",
                            "notes": f"📌 İlan: {b.get('listingTitle')}\nTeklif: {b.get('offer')}\nNot: {b.get('note')}",
                            "createdAt": b.get("createdAt") or datetime.now().strftime("%d.%m.%Y %H:%M")
                        }
    except Exception as e:
        print(f"⚠️ JSON dashboards read error: {e}")

    # 4. Firestore Admin (Eğer canlıda/yerelde initialize edilmişse ve contacts_map azsa)
    if len(contacts_map) < 50 and db_admin:
        try:
            admin_uids = ['RnHhsj3K4VSWRY4cjc3Pc09JMFn2', 'GP3Eiiz0cvPgibGnXPoNElCeWzW2', 'N24DQxhNQHVYGHoX9bBi52mINYi1']
            for u in admin_uids:
                docs = db_admin.collection("users").document(u).collection("contacts").stream()
                for doc in docs:
                    did = doc.id
                    if did not in contacts_map:
                        d = doc.to_dict()
                        d["id"] = did
                        contacts_map[did] = d
        except Exception as fe:
            print(f"⚠️ Firestore Admin stream error: {fe}")

    # 5. Web Leadleri
    web_leads = []
    if provided_leads and isinstance(provided_leads, list):
        web_leads = provided_leads
    elif db_admin:
        try:
            docs = db_admin.collection("leads").order_by("createdAt", direction="DESCENDING").limit(200).stream()
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                web_leads.append(d)
        except Exception as le:
            print(f"⚠️ Firestore leads stream error: {le}")

    return list(contacts_map.values()), web_leads


def generate_crm_excel_backup(contacts=None, web_leads=None, db_admin=None) -> bytes:
    """
    CRM'deki tüm müşteri ve alıcı verilerini içeren tam teşekküllü,
    5 sekmeli, kurumsal biçimlendirilmiş bir XLSX çalışma kitabı üretir.
    """
    all_contacts, leads_list = _collect_master_data(contacts, web_leads, db_admin)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ── VERİ GRUPLAMA VE ANALİZ ─────────────────────────────────────
    buyers_list = []
    sellers_list = []
    fsbo_list = []
    other_list = []

    total_offer_volume = 0
    total_seller_volume = 0

    category_counts = {}
    stage_counts = {}
    source_counts = {}

    for c in all_contacts:
        cat = str(c.get("category") or c.get("type") or "client").lower()
        role = str(c.get("role") or "").lower()
        stage_name = str(c.get("stageName") or c.get("stage") or "Yeni Talep")
        source = str(c.get("source_label") or c.get("source") or "Doğrudan")

        price = _parse_currency(c.get("price") or c.get("offer"))
        c["_clean_price"] = price

        category_counts[cat] = category_counts.get(cat, 0) + 1
        stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1

        is_seller = cat in ["seller", "satici", "satıcı"] or role == "seller" or c.get("type") == "seller"
        is_fsbo = cat in ["fsbo"]
        is_buyer = (
            cat in ["buyer", "alici", "alıcı"] or
            role == "buyer" or
            c.get("type") == "buyer" or
            bool(c.get("listingRef")) or
            (bool(c.get("offer")) and not is_seller and not is_fsbo)
        )

        if is_seller:
            sellers_list.append(c)
            total_seller_volume += price
        elif is_fsbo:
            fsbo_list.append(c)
            sellers_list.append(c)
            total_seller_volume += price
        elif is_buyer:
            buyers_list.append(c)
            total_offer_volume += price
        else:
            other_list.append(c)

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    # ════════════════════════════════════════════════════════════════
    # SEKME 1: 📊 KONSOLİDE YÖNETİCİ ÖZETİ (EXECUTIVE OVERVIEW)
    # ════════════════════════════════════════════════════════════════
    ws_summary = wb.create_sheet(title="📊 Özet & İstatistikler")
    ws_summary.sheet_properties.tabColor = CB_GOLD
    ws_summary.views.sheetView[0].showGridLines = True

    # 1. Başlık Banner
    ws_summary.merge_cells("A1:G1")
    top_cell = ws_summary["A1"]
    top_cell.value = "COLDWELL BANKER CB VIP ANKARA — NEXA.OS CRM MASTER YEDEKLEME VE MÜŞTERİ PORTFÖY RAPORU"
    _style_header_cell(top_cell, NAVY_HEADER, font_color="FFFFFF", font_size=13, bold=True, align="center")
    ws_summary.row_dimensions[1].height = 36

    # 2. Alt Bilgi Bandı (Altın Şerit)
    ws_summary.merge_cells("A2:G2")
    sub_cell = ws_summary["A2"]
    sub_cell.value = f"Gayrimenkul Mühendisi: Yiğit Narin  |  Coldwell Banker CB VIP (Yetki: 0600470 / 0602339)  |  Yedekleme Tarihi: {now_str}  |  Sistem: NEXA.OS PropTech v5.2"
    _style_header_cell(sub_cell, CB_GOLD, font_color="000000", font_size=10, bold=True, align="center")
    ws_summary.row_dimensions[2].height = 24

    ws_summary.row_dimensions[3].height = 12

    # 3. KPI Metrik Kartları
    kpis = [
        ("TOPLAM MÜŞTERİ HAVUZU", f"{len(all_contacts):,} Kayıt", "0F172A", "A", "B"),
        ("ALICI & TEKLİF ADAYLARI", f"{len(buyers_list):,} Alıcı", "312E81", "C", "D"),
        ("SATICI & FSBO PORTFÖYÜ", f"{len(sellers_list):,} Portföy", "064E3B", "E", "F"),
        ("DİJİTAL WEB LEADLERİ", f"{len(leads_list):,} Lead", "0E7490", "G", "G"),
    ]
    for label, val, color, c1, c2 in kpis:
        if c1 != c2:
            ws_summary.merge_cells(f"{c1}4:{c2}4")
            ws_summary.merge_cells(f"{c1}5:{c2}5")
        l_cell = ws_summary[f"{c1}4"]
        v_cell = ws_summary[f"{c1}5"]
        l_cell.value = label
        v_cell.value = val
        _style_header_cell(l_cell, color, font_color="E2E8F0", font_size=9, bold=True, align="center")
        _style_header_cell(v_cell, CARD_BG, font_color=color, font_size=14, bold=True, align="center")

    ws_summary.row_dimensions[4].height = 18
    ws_summary.row_dimensions[5].height = 28
    ws_summary.row_dimensions[6].height = 14

    # 4. Finansal Hacim Özeti
    ws_summary.merge_cells("A7:G7")
    fin_header = ws_summary["A7"]
    fin_header.value = "💰 PORTFÖY VE MÜZAKERE FİNANSAL HACİM ÖZETİ"
    _style_header_cell(fin_header, "1E293B", font_color=CB_GOLD, font_size=11, bold=True, align="left")
    ws_summary.row_dimensions[7].height = 24

    ws_summary.merge_cells("A8:C8")
    ws_summary.merge_cells("D8:G8")
    ws_summary["A8"].value = "Müzakeredeki Alıcı Teklif Hacmi"
    ws_summary["D8"].value = total_offer_volume
    _style_data_cell(ws_summary["A8"], ZEBRA_LIGHT_NAVY, bold=True)
    _style_data_cell(ws_summary["D8"], "FFFFFF", bold=True, align="right", num_format='#,##0 "₺"')

    ws_summary.merge_cells("A9:C9")
    ws_summary.merge_cells("D9:G9")
    ws_summary["A9"].value = "Kayıtlı Portföy & Satıcı Talep Hacmi"
    ws_summary["D9"].value = total_seller_volume
    _style_data_cell(ws_summary["A9"], ZEBRA_LIGHT_NAVY, bold=True)
    _style_data_cell(ws_summary["D9"], "FFFFFF", bold=True, align="right", num_format='#,##0 "₺"')

    ws_summary.row_dimensions[8].height = 20
    ws_summary.row_dimensions[9].height = 20
    ws_summary.row_dimensions[10].height = 14

    # 5. Kategori Dağılımı Tablosu
    ws_summary.merge_cells("A11:C11")
    cat_header = ws_summary["A11"]
    cat_header.value = "Kategori Dağılımı"
    _style_header_cell(cat_header, NAVY_HEADER, font_color="FFFFFF", font_size=10, bold=True)

    ws_summary.merge_cells("D11:E11")
    ws_summary["D11"].value = "Kişi Sayısı"
    _style_header_cell(ws_summary["D11"], NAVY_HEADER, font_color="FFFFFF", font_size=10, bold=True, align="center")

    ws_summary.merge_cells("F11:G11")
    ws_summary["F11"].value = "Yüzdelik Pay"
    _style_header_cell(ws_summary["F11"], NAVY_HEADER, font_color="FFFFFF", font_size=10, bold=True, align="center")
    ws_summary.row_dimensions[11].height = 22

    row_idx = 12
    total_cnt = max(len(all_contacts), 1)
    for cat_name, cnt in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        ws_summary.merge_cells(f"A{row_idx}:C{row_idx}")
        ws_summary.merge_cells(f"D{row_idx}:E{row_idx}")
        ws_summary.merge_cells(f"F{row_idx}:G{row_idx}")

        lbl = cat_name.capitalize()
        if cat_name in ["buyer", "alici"]: lbl = "Alıcı / Teklif Veren"
        elif cat_name in ["seller", "satici"]: lbl = "Satıcı / Mülk Sahibi"
        elif cat_name in ["fsbo"]: lbl = "FSBO (Sahibinden Satılık)"
        elif cat_name in ["client"]: lbl = "Müşteri / Danışan"
        elif cat_name in ["investor"]: lbl = "Yatırımcı"

        ws_summary[f"A{row_idx}"].value = lbl
        ws_summary[f"D{row_idx}"].value = cnt
        ws_summary[f"F{row_idx}"].value = f"%{(cnt / total_cnt) * 100:.1f}"

        bg = ZEBRA_LIGHT_NAVY if row_idx % 2 == 0 else "FFFFFF"
        _style_data_cell(ws_summary[f"A{row_idx}"], bg)
        _style_data_cell(ws_summary[f"D{row_idx}"], bg, align="center", bold=True)
        _style_data_cell(ws_summary[f"F{row_idx}"], bg, align="center")
        ws_summary.row_dimensions[row_idx].height = 19
        row_idx += 1

    row_idx += 1
    # Güvenlik ve KVKK Notu
    ws_summary.merge_cells(f"A{row_idx}:G{row_idx}")
    notice = ws_summary[f"A{row_idx}"]
    notice.value = "🔒 GÜVENLİK & VERİ POLİTİKASI: Bu Excel çalışma kitabı Coldwell Banker CB VIP kurumsal müşteri ve ticari istihbarat verilerini içermektedir. Üçüncü şahıslarla paylaşılamaz. Tüm hakları saklıdır."
    _style_header_cell(notice, "334155", font_color="CBD5E1", font_size=8, bold=False, align="center")
    ws_summary.row_dimensions[row_idx].height = 20

    _autofit_columns(ws_summary)


    # ════════════════════════════════════════════════════════════════
    # SEKME 2: 🎯 ALICILAR VE TEKLİF HAVUZU (BUYERS & OFFERS MATRIX)
    # ════════════════════════════════════════════════════════════════
    ws_buyers = wb.create_sheet(title="🎯 Alıcılar & Teklifler")
    ws_buyers.sheet_properties.tabColor = PURPLE_HEADER
    ws_buyers.views.sheetView[0].showGridLines = True
    ws_buyers.freeze_panes = "A2"

    buyer_headers = [
        "Sıra", "ID", "Alıcı Adı Soyadı", "Telefon", "E-Posta", "Teklif / Bütçe (₺)", "Aşama / Pipeline",
        "İlgili Portföy / İlan Başlığı", "İlan Ref No", "Alıcı Tipi", "Isı / Öncelik",
        "Kaynak", "Görüşme ve Müzakere Notları", "Kayıt Tarihi"
    ]
    for col_idx, h in enumerate(buyer_headers, start=1):
        cell = ws_buyers.cell(row=1, column=col_idx, value=h)
        _style_header_cell(cell, PURPLE_HEADER, font_color="FFFFFF", font_size=10, bold=True, align="center")
    ws_buyers.row_dimensions[1].height = 28

    for b_idx, b in enumerate(buyers_list, start=1):
        row_num = b_idx + 1
        bg = ZEBRA_LIGHT_PURPLE if b_idx % 2 == 0 else "FFFFFF"

        price_val = b.get("_clean_price") or _parse_currency(b.get("offer") or b.get("price"))

        row_vals = [
            (b_idx, "center", False, None),
            (b.get("id", "-"), "center", False, "@"),
            (b.get("name") or "İlan Alıcısı", "left", True, None),
            (b.get("phone") or "-", "center", False, "@"),
            (b.get("email") or "-", "center", False, None),
            (price_val, "right", True, '#,##0 "₺"'),
            (b.get("stageName") or b.get("stage") or "Yeni Talep", "center", False, None),
            (b.get("listingTitle") or b.get("title") or "Portföy İlanı", "left", False, None),
            (b.get("listingRef") or b.get("refId") or "-", "center", False, "@"),
            (b.get("role") or b.get("type") or "Alıcı", "center", False, None),
            (b.get("heat") or "🔥 Sıcak", "center", False, None),
            (b.get("source_label") or b.get("source") or "İlan Alıcısı", "center", False, None),
            (b.get("notes") or b.get("note") or "-", "left", False, None),
            (_format_date_val(b.get("createdAt")), "center", False, None)
        ]

        for col_idx, (v, align, bold, num_fmt) in enumerate(row_vals, start=1):
            c_cell = ws_buyers.cell(row=row_num, column=col_idx, value=v)
            _style_data_cell(c_cell, bg, align=align, bold=bold, num_format=num_fmt)

        ws_buyers.row_dimensions[row_num].height = 22

    ws_buyers.auto_filter.ref = f"A1:{get_column_letter(len(buyer_headers))}{max(len(buyers_list)+1, 2)}"
    _autofit_columns(ws_buyers)


    # ════════════════════════════════════════════════════════════════
    # SEKME 3: 🏢 SATICILAR VE PORTFÖYLER (SELLERS & FSBO)
    # ════════════════════════════════════════════════════════════════
    ws_sellers = wb.create_sheet(title="🏢 Satıcılar & Portföyler")
    ws_sellers.sheet_properties.tabColor = EMERALD_HEADER
    ws_sellers.views.sheetView[0].showGridLines = True
    ws_sellers.freeze_panes = "A2"

    seller_headers = [
        "Sıra", "ID", "Mülk Sahibi Adı Soyadı", "Telefon", "E-Posta", "Mülk / Portföy Tanımı",
        "İstenen Fiyat (₺)", "Lokasyon / Bölge", "Kategori", "Pipeline Aşaması",
        "Takas İhtimali", "Takas Beklentisi", "Görüşme Notları", "Kayıt Tarihi"
    ]
    for col_idx, h in enumerate(seller_headers, start=1):
        cell = ws_sellers.cell(row=1, column=col_idx, value=h)
        _style_header_cell(cell, EMERALD_HEADER, font_color="FFFFFF", font_size=10, bold=True, align="center")
    ws_sellers.row_dimensions[1].height = 28

    for s_idx, s in enumerate(sellers_list, start=1):
        row_num = s_idx + 1
        bg = ZEBRA_LIGHT_EMERALD if s_idx % 2 == 0 else "FFFFFF"

        price_val = s.get("_clean_price") or _parse_currency(s.get("price"))

        row_vals = [
            (s_idx, "center", False, None),
            (s.get("id", "-"), "center", False, "@"),
            (s.get("name") or "Mülk Sahibi", "left", True, None),
            (s.get("phone") or "-", "center", False, "@"),
            (s.get("email") or "-", "center", False, None),
            (s.get("title") or s.get("listingTitle") or s.get("notes", "-")[:45], "left", False, None),
            (price_val, "right", True, '#,##0 "₺"'),
            (s.get("district") or s.get("location") or "Çankaya, Ankara", "left", False, None),
            ("FSBO Satılık" if s.get("category") == "fsbo" else "Satıcı / Mülk Sahibi", "center", False, None),
            (s.get("stageName") or s.get("stage") or "İlk Temas", "center", False, None),
            ("EVET (Takas Var)" if s.get("hasExchange") else "Hayır", "center", bool(s.get("hasExchange")), None),
            (s.get("exchangeNotes") or "-", "left", False, None),
            (s.get("notes") or "-", "left", False, None),
            (_format_date_val(s.get("createdAt")), "center", False, None)
        ]

        for col_idx, (v, align, bold, num_fmt) in enumerate(row_vals, start=1):
            c_cell = ws_sellers.cell(row=row_num, column=col_idx, value=v)
            _style_data_cell(c_cell, bg, align=align, bold=bold, num_format=num_fmt)

        ws_sellers.row_dimensions[row_num].height = 22

    ws_sellers.auto_filter.ref = f"A1:{get_column_letter(len(seller_headers))}{max(len(sellers_list)+1, 2)}"
    _autofit_columns(ws_sellers)


    # ════════════════════════════════════════════════════════════════
    # SEKME 4: 👥 TÜM KİŞİLER VERİTABANI (MASTER CONTACTS POOL)
    # ════════════════════════════════════════════════════════════════
    ws_master = wb.create_sheet(title="👥 Tüm Kişiler Veritabanı")
    ws_master.sheet_properties.tabColor = NAVY_HEADER
    ws_master.views.sheetView[0].showGridLines = True
    ws_master.freeze_panes = "A2"

    master_headers = [
        "Sıra", "ID", "Kategori", "Adı Soyadı", "Telefon", "E-Posta", "Fiyat / Bütçe (₺)",
        "Süreç Aşaması", "İlişkili İlan / Portföy", "Bölge / Lokasyon", "Müşteri Skoru",
        "Isı", "Kaynak", "Takas", "Görüşme Notları", "Kayıt Tarihi"
    ]
    for col_idx, h in enumerate(master_headers, start=1):
        cell = ws_master.cell(row=1, column=col_idx, value=h)
        _style_header_cell(cell, NAVY_HEADER, font_color=CB_GOLD, font_size=10, bold=True, align="center")
    ws_master.row_dimensions[1].height = 28

    for m_idx, m in enumerate(all_contacts, start=1):
        row_num = m_idx + 1
        bg = ZEBRA_LIGHT_NAVY if m_idx % 2 == 0 else "FFFFFF"

        price_val = m.get("_clean_price") or _parse_currency(m.get("price") or m.get("offer"))
        cat_raw = str(m.get("category") or m.get("type") or "Diğer")

        row_vals = [
            (m_idx, "center", False, None),
            (m.get("id", "-"), "center", False, "@"),
            (cat_raw.upper(), "center", True, None),
            (m.get("name") or "İsimsiz Kayıt", "left", True, None),
            (m.get("phone") or "-", "center", False, "@"),
            (m.get("email") or "-", "center", False, None),
            (price_val, "right", True, '#,##0 "₺"'),
            (m.get("stageName") or m.get("stage") or "Yeni", "center", False, None),
            (m.get("listingTitle") or m.get("title") or "-", "left", False, None),
            (m.get("district") or m.get("location") or "-", "left", False, None),
            (m.get("score") or 75, "center", False, None),
            (m.get("heat") or "Normal", "center", False, None),
            (m.get("source_label") or m.get("source") or "Doğrudan", "center", False, None),
            ("VAR" if m.get("hasExchange") else "YOK", "center", False, None),
            (m.get("notes") or "-", "left", False, None),
            (_format_date_val(m.get("createdAt")), "center", False, None)
        ]

        for col_idx, (v, align, bold, num_fmt) in enumerate(row_vals, start=1):
            c_cell = ws_master.cell(row=row_num, column=col_idx, value=v)
            _style_data_cell(c_cell, bg, align=align, bold=bold, num_format=num_fmt)

        ws_master.row_dimensions[row_num].height = 20

    ws_master.auto_filter.ref = f"A1:{get_column_letter(len(master_headers))}{max(len(all_contacts)+1, 2)}"
    _autofit_columns(ws_master)


    # ════════════════════════════════════════════════════════════════
    # SEKME 5: 🛰️ DİJİTAL WEB LEADLERİ (INBOUND LEADS)
    # ════════════════════════════════════════════════════════════════
    ws_leads = wb.create_sheet(title="🛰️ Web Leadleri")
    ws_leads.sheet_properties.tabColor = CYAN_HEADER
    ws_leads.views.sheetView[0].showGridLines = True
    ws_leads.freeze_panes = "A2"

    lead_headers = [
        "Sıra", "ID", "Gönderen Adı", "Telefon", "E-Posta",
        "İlgilenilen Mülk / Konu", "Kategori", "Aşama / Durum", "Mesaj / Not", "Tarih"
    ]
    for col_idx, h in enumerate(lead_headers, start=1):
        cell = ws_leads.cell(row=1, column=col_idx, value=h)
        _style_header_cell(cell, CYAN_HEADER, font_color="FFFFFF", font_size=10, bold=True, align="center")
    ws_leads.row_dimensions[1].height = 28

    for l_idx, lead in enumerate(leads_list, start=1):
        row_num = l_idx + 1
        bg = ZEBRA_LIGHT_CYAN if l_idx % 2 == 0 else "FFFFFF"

        row_vals = [
            (l_idx, "center", False, None),
            (lead.get("id", "-"), "center", False, "@"),
            (lead.get("name") or "İsimsiz Lead", "left", True, None),
            (lead.get("phone") or "-", "center", False, "@"),
            (lead.get("email") or "-", "center", False, None),
            (lead.get("property_title") or lead.get("title") or lead.get("subject") or "Genel Web Talebi", "left", False, None),
            (lead.get("category") or "Web", "center", False, None),
            (lead.get("status") or lead.get("stage") or "Yeni", "center", False, None),
            (lead.get("message") or lead.get("notes") or "-", "left", False, None),
            (_format_date_val(lead.get("createdAt")), "center", False, None)
        ]

        for col_idx, (v, align, bold, num_fmt) in enumerate(row_vals, start=1):
            c_cell = ws_leads.cell(row=row_num, column=col_idx, value=v)
            _style_data_cell(c_cell, bg, align=align, bold=bold, num_format=num_fmt)

        ws_leads.row_dimensions[row_num].height = 20

    ws_leads.auto_filter.ref = f"A1:{get_column_letter(len(lead_headers))}{max(len(leads_list)+1, 2)}"
    _autofit_columns(ws_leads)

    # ── DOSYAYI BELLEKTE BYTE DİZİSİNE DÖKME ──────────────────────────
    output_stream = io.BytesIO()
    wb.save(output_stream)
    output_stream.seek(0)
    return output_stream.getvalue()
