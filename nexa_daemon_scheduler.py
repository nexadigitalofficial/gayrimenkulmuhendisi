#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
NEXA DAEMON SCHEDULER™ | 7/24 Proaktif Piyasa Gözetimi & Günlük Delta Zamanlayıcı
========================================================================================
Her gün belirlenen saatte (veya periyotta) arka planda otomatik uyanır:
  1. Takip edilen tüm portföy havuzlarını tarar.
  2. Bugünkü ve dünkü emsal fiyatlarını atomik olarak kıyaslar.
  3. FİYAT İNDİRİMLERİNİ (% indirim, -TL düşüş) ve YENİ RAKİP GİRİŞLERİNİ yakalar.
  4. NEXA AI Stratejistini devreye sokarak danışmana aksiyon tavsiyeleri üretir.
  5. Belgeler_ve_Raporlar klasörüne interaktif NEXA_GUNLUK_PAZAR_RADARI.html raporunu basar.
"""

import sys
import os
import time
import argparse
from datetime import datetime, date
from pathlib import Path

# Reconfigure stdout for Windows console UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from nexa_pool_sentinel import NexaPoolSentinel

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = Path(r"C:\Users\USER\Desktop\Belgeler_ve_Raporlar")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_html_briefing(sentinel: NexaPoolSentinel, events: list) -> Path:
    """Generates an executive-grade daily briefing HTML dashboard for the broker."""
    today_str = date.today().strftime("%d %B %Y")
    alerts = sentinel.get_alerts(limit=50)
    
    price_drops = [a for a in alerts if a.get("event_type") == "PRICE_DROP"]
    new_entries = [a for a in alerts if a.get("event_type") == "NEW_ENTRY"]
    delisted = [a for a in alerts if a.get("event_type") == "DELISTED_OR_SOLD"]

    cards_html = ""
    for a in alerts:
        event_type = a.get("event_type")
        if event_type == "PRICE_DROP":
            badge = f"<span style='background:#f43f5e; color:#fff; padding:4px 10px; border-radius:6px; font-weight:800; font-size:11px;'>🚨 %{a.get('change_pct', 0)} İNDİRİM</span>"
            border_color = "rgba(244,63,94,0.4)"
            bg_color = "linear-gradient(135deg, rgba(35,10,20,0.9), rgba(15,23,42,0.95))"
        elif event_type == "NEW_ENTRY":
            badge = "<span style='background:#06b6d4; color:#fff; padding:4px 10px; border-radius:6px; font-weight:800; font-size:11px;'>🆕 YENİ RAKİP</span>"
            border_color = "rgba(6,182,212,0.4)"
            bg_color = "linear-gradient(135deg, rgba(10,25,35,0.9), rgba(15,23,42,0.95))"
        else:
            badge = "<span style='background:#10b981; color:#fff; padding:4px 10px; border-radius:6px; font-weight:800; font-size:11px;'>🏁 SATILDI / KALKTI</span>"
            border_color = "rgba(16,185,129,0.4)"
            bg_color = "linear-gradient(135deg, rgba(10,30,20,0.9), rgba(15,23,42,0.95))"

        price_row = ""
        if a.get("old_price", 0) > 0 and a.get("new_price", 0) > 0 and event_type == "PRICE_DROP":
            price_row = f"""
            <div style="display:flex; align-items:baseline; gap:10px;">
                <span style="text-decoration:line-through; color:#94a3b8; font-size:14px;">{a['old_price']:,.0f} TL</span>
                <span style="color:#f43f5e; font-size:22px; font-weight:900;">{a['new_price']:,.0f} TL</span>
                <span style="color:#fb7185; font-size:12px; font-weight:700;">(-{a['price_diff']:,.0f} TL Düşüş)</span>
            </div>
            """
        elif a.get("new_price", 0) > 0:
            price_row = f"<span style='color:#fff; font-size:20px; font-weight:900;'>{a['new_price']:,.0f} TL</span>"

        cards_html += f"""
        <div style="background:{bg_color}; border:1px solid {border_color}; border-radius:18px; padding:22px; margin-bottom:16px; box-shadow:0 8px 24px rgba(0,0,0,0.4);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    {badge}
                    <span style="color:#d4af37; font-weight:700; font-size:12px;">📁 Havuz: {a.get('pool_title', '')}</span>
                </div>
                <span style="color:#64748b; font-size:11px; font-family:monospace;">{a.get('created_at', '')}</span>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:12px; margin-bottom:14px;">
                <div>
                    <h3 style="color:#fff; font-size:16px; font-weight:800; margin-bottom:4px;">{a.get('event_summary', '')}</h3>
                    <div style="color:#94a3b8; font-size:12px;">
                        <span>📍 {a.get('location_path', '')}</span> &bull; 
                        <span>İlan No: #{a.get('listing_id', '')}</span>
                        {f" &bull; <span style='color:#facc15; font-weight:bold;'>Bizim Fiyatımız: {a.get('our_price', 0):,.0f} TL</span>" if a.get('our_price', 0) > 0 else ""}
                    </div>
                </div>
                <div>{price_row}</div>
            </div>

            <div style="background:rgba(10,15,30,0.85); border:1px solid rgba(212,175,55,0.3); border-radius:12px; padding:14px; margin-bottom:12px;">
                <div style="color:#facc15; font-weight:800; font-size:11px; text-transform:uppercase; margin-bottom:4px;">🤖 NEXA AI Stratejik Piyasa Yorumu:</div>
                <p style="color:#e2e8f0; font-size:12.5px; line-height:1.5; margin:0;">{a.get('ai_strategic_comment', '')}</p>
            </div>

            <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#34d399; font-weight:800; font-size:11px; text-transform:uppercase;">💡 Önerilen Danışman Aksiyonu: </span>
                    <span style="color:#a7f3d0; font-size:12px; font-weight:600;">{a.get('recommended_action', '')}</span>
                </div>
                <a href="https://www.sahibinden.com/ilan/{a.get('listing_id', '')}/detay" target="_blank" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.4); text-decoration:none; padding:6px 14px; border-radius:8px; font-size:11px; font-weight:700; white-space:nowrap; margin-left:12px;">İlana Git ↗</a>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>NEXA Günlük Pazar Radarı & Fiyat İndirimi Brifingi</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ background: #030712; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 30px; }}
        .kpi-card {{ background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div style="text-align:center; margin-bottom:35px;">
            <div style="display:inline-block; padding:5px 14px; background:rgba(212,175,55,0.15); border:1px solid rgba(212,175,55,0.4); border-radius:999px; color:#d4af37; font-size:11px; font-weight:800; margin-bottom:12px;">
                ⚡ 7/24 PROAKTİF PİYASA GÖZETİMİ & DANIŞMAN RADARI
            </div>
            <h1 style="font-size:32px; font-weight:900; margin:0 0 8px 0; background:linear-gradient(135deg,#fff,#cbd5e1); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                NEXA GÜNLÜK PAZAR HAREKETİ BRİFİNGİ
            </h1>
            <p style="color:#94a3b8; font-size:13px; margin:0;">Tarih: {today_str} &bull; Otonom Takipteki Portföylerin Emsal Rekabet Raporu</p>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card" style="border-color:rgba(244,63,94,0.4); background:rgba(244,63,94,0.06);">
                <div style="color:#f43f5e; font-size:11px; font-weight:800; text-transform:uppercase;">🚨 Fiyat İndiren Rakipler</div>
                <div style="color:#fff; font-size:36px; font-weight:900; margin-top:6px;">{len(price_drops)}</div>
            </div>
            <div class="kpi-card" style="border-color:rgba(6,182,212,0.4); background:rgba(6,182,212,0.06);">
                <div style="color:#06b6d4; font-size:11px; font-weight:800; text-transform:uppercase;">🆕 Yeni Giren Emsaller</div>
                <div style="color:#fff; font-size:36px; font-weight:900; margin-top:6px;">{len(new_entries)}</div>
            </div>
            <div class="kpi-card" style="border-color:rgba(16,185,129,0.4); background:rgba(16,185,129,0.06);">
                <div style="color:#10b981; font-size:11px; font-weight:800; text-transform:uppercase;">🏁 Satılan / Kalkan İlanlar</div>
                <div style="color:#fff; font-size:36px; font-weight:900; margin-top:6px;">{len(delisted)}</div>
            </div>
        </div>

        <div>
            <h2 style="font-size:18px; font-weight:800; color:#fff; margin-bottom:16px;">Gözetim Günlüğü & Aksiyon Planı</h2>
            {cards_html}
        </div>

        <div style="text-align:center; margin-top:40px; font-size:11px; color:#64748b; font-family:'JetBrains Mono',monospace;">
            NEXA DIGITAL AUTONOMOUS PROPTECH LAB &bull; GAYRİMENKUL MÜHENDİSİ CRM v5.0
        </div>
    </div>
</body>
</html>
"""
    report_file = REPORTS_DIR / "NEXA_GUNLUK_PAZAR_RADARI.html"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    return report_file


def run_surveillance_cycle():
    """Runs one complete surveillance cycle across all registered pools."""
    print(f"\n{'='*70}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NEXA PROACTIVE SURVEILLANCE RUNNING...")
    print(f"{'='*70}")

    sentinel = NexaPoolSentinel()
    with sentinel._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, pool_search_url FROM nexa_monitored_pools WHERE is_active = 1")
        pools = [dict(r) for r in cur.fetchall()]

    print(f"  [RADAR] Toplam {len(pools)} aktif pazar havuzu gözetleniyor.")

    all_new_events = []
    for p in pools:
        pid = p["id"]
        title = p["title"]
        print(f"  -> [{pid}] {title} taranıyor...")
        events = sentinel.calculate_delta_events(pid)
        print(f"     [OK] {len(events)} yeni delta olayı yakalandı!")
        all_new_events.extend(events)

    # Generate daily briefing HTML
    report_path = generate_html_briefing(sentinel, all_new_events)
    print(f"\n[SUCCESS] Günlük Pazar Radarı Raporu oluşturuldu: {report_path}")
    print(f"Toplam tespit edilen olay sayısı: {len(all_new_events)}")
    return all_new_events


class NexaDaemonScheduler:
    """
    Autonomous 24/7 background scheduler for Nexa Proactive Surveillance.
    Manages periodic surveillance cycles, health checks, and report generation.
    """
    def __init__(self, interval_hours: int = 24):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.sentinel = NexaPoolSentinel()

    def run_once(self) -> list:
        """Executes a single cycle across all registered pools."""
        return run_surveillance_cycle()

    def generate_report(self, events: list = None) -> Path:
        """Generates the executive HTML briefing."""
        return generate_html_briefing(self.sentinel, events or [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXA Daemon Scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=86400, help="Interval in seconds (default: 86400 = 24h)")
    args = parser.parse_args()

    if args.once:
        run_surveillance_cycle()
    else:
        print("[NEXA DAEMON] Background watcher started (Press Ctrl+C to stop)...")
        while True:
            try:
                run_surveillance_cycle()
                print(f"[SLEEP] Sleeping for {args.interval} seconds until next scan...")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n[STOP] Daemon stopped by user.")
                break
            except Exception as e:
                print(f"[ERR] Daemon error: {e}")
                time.sleep(60)
