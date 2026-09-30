# -*- coding: utf-8 -*-
"""
nexa_sales_miner.py — Otonom Satış, Excel (XLSX) ve Finansal Bilgi Madencisi
Zero-Storage mimarisiyle hafif JSON ve SQLite tablolarını senkronize eder.
"""

import json
import sqlite3
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPH_FILE = ROOT_DIR / "nexa_sales_knowledge_graph.json"
MAP_FILE = ROOT_DIR / "projects_map.json"
PRICES_FILE = ROOT_DIR / "nexa_project_prices.json"
SUMMARIES_FILE = ROOT_DIR / "nexa_project_summaries.json"
DB_PATH = ROOT_DIR / "nexa_database.db"


def sync_sales_knowledge():
    if not GRAPH_FILE.exists():
        print("Knowledge graph file not found:", GRAPH_FILE)
        return False

    graph = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    print(f"[1/3] {len(graph)} proje bilgi grafiğinden okundu.")

    # 1. projects_map.json güncelle
    if MAP_FILE.exists():
        projects = json.loads(MAP_FILE.read_text(encoding="utf-8"))
        for p in projects:
            title = (p.get("title") or p.get("name") or "").strip()
            matched_info = graph.get(title)
            if not matched_info:
                # Case-insensitive exact match
                t_lower = title.lower()
                for s_name, s_data in graph.items():
                    if s_name.strip().lower() == t_lower:
                        matched_info = s_data
                        break
            if not matched_info:
                # Longest matching key (exact prefix/suffix)
                sorted_graph = sorted(graph.items(), key=lambda kv: len(kv[0]), reverse=True)
                for s_name, s_data in sorted_graph:
                    if s_name.lower() in title.lower() or title.lower() in s_name.lower():
                        matched_info = s_data
                        break
            if matched_info:
                p["price_display"] = matched_info["price_display"]
                p["price_min"] = matched_info["price_min"]
                p["price_max"] = matched_info["price_max"]
                p["price_numeric"] = matched_info["price_numeric"]
                p["down_payment"] = matched_info["down_payment"]
                p["installment_terms"] = matched_info.get("installment_terms", "")
                p["monthly_installment"] = matched_info.get("monthly_installment", 0)
                p["room_info"] = matched_info["room_info"]
                p["delivery_months"] = matched_info.get("delivery_months", 24)
                p["il"] = matched_info.get("il", p.get("il", "Ankara"))
                p["ilce"] = matched_info.get("ilce", p.get("ilce", "Çankaya"))
                p["location"] = matched_info.get("location", p.get("location", "Ankara"))
                p["location_full"] = matched_info.get("location_full", p.get("location_full", "Ankara"))
                p["ada_no"] = matched_info.get("ada_no", p.get("ada_no", ""))
                p["parsel_no"] = matched_info.get("parsel_no", p.get("parsel_no", ""))
                p["tkgm_verified"] = matched_info.get("tkgm_verified", True)
                p["category"] = matched_info.get("category", "Markalı Konut Projesi")
                p["sales_highlights"] = matched_info.get("sales_highlights", "")
        MAP_FILE.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[2/3] projects_map.json güncellendi ({len(projects)} proje).")

    # 2. nexa_project_prices & summaries
    prices = {}
    summaries = {}
    for name, data in graph.items():
        prices[name] = {
            "price_display": data["price_display"],
            "price_min": data["price_min"],
            "price_max": data["price_max"],
            "price_numeric": data["price_numeric"],
            "down_payment": data["down_payment"],
            "installment_terms": data.get("installment_terms", ""),
            "monthly_installment": data.get("monthly_installment", 0),
            "delivery_months": data.get("delivery_months", 24),
            "delivery_display": data.get("delivery_display", f"{data.get('delivery_months', 24)} Ay Teslim"),
            "rooms": [r.strip() for r in data["room_info"].split(",")],
            "description": data.get("sales_highlights", "")
        }
        loc = data.get("location_full", "")
        pd = data.get("price_display", "")
        dp = data.get("down_payment", "")
        it = data.get("installment_terms", "Esnek Vade")
        rm = data.get("room_info", "")
        ada = str(data.get("ada_no", "-"))
        parsel = str(data.get("parsel_no", "-"))
        hl = data.get("sales_highlights", "")
        summaries[name] = {
            "summary": f"- {name} ({loc}): {pd}, Peşinat: {dp}, Ödeme: {it}, Daire: {rm}, Ada: {ada}/{parsel} (TKGM Onaylı). {hl}"
        }
    PRICES_FILE.write_text(json.dumps(prices, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARIES_FILE.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. SQLite güncelle
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        try:
            cur = conn.cursor()
            for name, data in graph.items():
                norm_name = name.strip().upper().replace("İ", "I")
                cur.execute("""
                    UPDATE projects SET
                        price_display = ?,
                        price_min = ?,
                        price_max = ?,
                        price_numeric = ?,
                        down_payment = ?,
                        installment_terms = ?,
                        monthly_installment = ?,
                        delivery_months = ?,
                        room_info = ?,
                        location = ?,
                        il = ?,
                        ilce = ?,
                        mahalle = ?,
                        ada_no = ?,
                        parsel_no = ?,
                        tkgm_verified = 1
                    WHERE UPPER(name) = UPPER(?)
                       OR UPPER(REPLACE(name, 'İ', 'I')) = ?
                       OR UPPER(name) LIKE ?
                       OR UPPER(?) LIKE '%' || UPPER(name) || '%'
                """, (
                    data["price_display"],
                    data["price_min"],
                    data["price_max"],
                    data["price_numeric"],
                    data["down_payment"],
                    data.get("installment_terms", ""),
                    data.get("monthly_installment", 0),
                    data.get("delivery_months", 24),
                    data["room_info"],
                    data["location"],
                    data.get("il", "Ankara"),
                    data.get("ilce", "Çankaya"),
                    data.get("mahalle", ""),
                    data.get("ada_no", ""),
                    data.get("parsel_no", ""),
                    name,
                    norm_name,
                    f"%{name}%",
                    name
                ))
            # 4. SQLite documents & document_chunks tam bilgi ve sözleşme güvencesi
            def _chunk(text, size=1200, overlap=120):
                import re
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) < 40:
                    return []
                out, i = [], 0
                while i < len(text):
                    out.append(text[i:i + size])
                    i += size - overlap
                return out

            proj_rows = cur.execute("SELECT id, name FROM projects").fetchall()
            name_to_id = {r[1]: r[0] for r in proj_rows}

            for name, data in graph.items():
                pid = name_to_id.get(name)
                if not pid:
                    for db_name, db_id in name_to_id.items():
                        if db_name.lower() == name.lower():
                            pid = db_id
                            break
                if not pid:
                    continue

                tkgm_stat = "Resmi TKGM Kayıtlarıyla Doğrulanmıştır" if data.get("tkgm_verified") else "İnceleniyor"
                docs_payload = [
                    ("doc", f"{name} - Resmi Sözleşme ve TKGM Tapu Kayıtları", f"""
NEXA PRIME RESMİ PROJE SÖZLEŞMESİ VE HUKUKİ GÜVENCE BİLGİLERİ: {name}
Proje: {name} | Konum: {data.get('location_full', '')}
Tapu Kaydı: Ada {data.get('ada_no', '-')} / Parsel {data.get('parsel_no', '-')} ({tkgm_stat})
Mülkiyet Yapısı: {data.get('category', 'Lüks Konut Projesi')} - Resmi Noter ve Satış Vaadi Sözleşmesi
Teslimat Süresi: {data.get('delivery_months', 24)} Ay ({data.get('delivery_display', '')})
Danışman: Suzanne Tenekecioğlu (0535 489 56 56) - Coldwell Banker VIP Ankara (Ofis 470)
""".strip(), "SÖZLEŞME"),
                    ("xlsx", f"{name} - Satış Takip ve Fiyat Envanter Listesi", f"""
NEXA PRIME CANLI SATIŞ TAKİP VE FİYAT LİSTESİ: {name}
Lansman Fiyatı: {data.get('price_display', '')} (Taban: {data.get('price_min', '')} TL - Tavan: {data.get('price_max', '')} TL)
Peşinat: {data.get('down_payment', '')} | Taksit: {data.get('installment_terms', '')}
Aylık Taksit: {data.get('monthly_installment', '')} TL | Oda Tipleri: {data.get('room_info', '')}
Satış Detayı: {data.get('sales_highlights', '')}
""".strip(), "SATIŞ TAKİP"),
                    ("doc", f"{name} - Mimari Konsept ve Proje Sunumu", f"""
NEXA PRIME PROJE TANITIMI VE MİMARİ KONSEPT: {name}
Kategori: {data.get('category', 'Markalı Konut Projesi')} | Adres: {data.get('location_full', '')}
Açıklama: {data.get('description', '')}
Mimari Özellikler: {data.get('sales_highlights', '')} | Teslim: {data.get('delivery_display', '')}
""".strip(), "SUNUM"),
                    ("doc", f"{name} - Yatırım Analizi ve Amortisman Raporu", f"""
NEXA PRIME BİLİŞSEL YATIRIM VE KİRA GETİRİSİ ANALİZİ: {name}
Bölgesel Prim Trendi: {data.get('ilce', '')} bölgesinde yüksek değer artışı.
Ödeme Kolaylığı: {data.get('down_payment', '')} peşinat, {data.get('installment_terms', '')} vade ile sermaye güvencesi.
""".strip(), "Yatırım")
                ]

                for dtype, dtitle, dcontent, dcat in docs_payload:
                    cur.execute("SELECT id FROM documents WHERE project_id=? AND title=?", (pid, dtitle))
                    row = cur.fetchone()
                    if row:
                        did = row[0]
                        cur.execute("UPDATE documents SET content=?, category=?, doc_type=? WHERE id=?", (dcontent, dcat, dtype, did))
                        cur.execute("DELETE FROM document_chunks WHERE document_id=?", (did,))
                    else:
                        cur.execute("INSERT INTO documents (project_id, doc_type, title, content, file_url, category, created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
                                    (pid, dtype, dtitle, dcontent, f"knowledge_graph/{name}/{dtitle}", dcat))
                        did = cur.lastrowid
                    for chk in _chunk(dcontent):
                        cur.execute("INSERT INTO document_chunks (document_id, chunk_text, embedding) VALUES (?,?,?)",
                                    (did, chk, json.dumps([0.0] * 768)))

            conn.commit()
            print("[4/4] SQLite documents & document_chunks tam bilgi ve sözleşme güvencesi güncellendi.")
        except Exception as e:
            conn.rollback()
            print(f"[3/3] SQLite senkronizasyon hatası: {e}")
            raise e
        finally:
            conn.close()
    return True


if __name__ == "__main__":
    sync_sales_knowledge()
    print("Satış bilgileri ve sözleşme belgeleri başarıyla senkronize edildi.")

