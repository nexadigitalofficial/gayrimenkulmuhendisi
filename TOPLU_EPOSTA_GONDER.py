# -*- coding: utf-8 -*-
r"""
NexaScout - Toplu VIP E-Posta Gönderim Aracı (Masaüstü Konsol)
Coldwell Banker VIP Real - Yiğit Narin (yigit.narin@cb.com.tr)
Hedef kurumlara kuruma özel Word teklif eki (.docx) ile toplu e-posta gönderir.
"""

import os
import sys
import time
import argparse
from datetime import datetime

# UTF-8 stdout desteği
sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
PROPOSALS_DIR = os.path.join(DATA_DIR, "TEKLIF_MEKTUPLARI")
EXCEL_FILE = os.path.join(DATA_DIR, "LOSANTE_KARSISI_KURUMSAL_HEDEF_LISTE.xlsx")
TOKEN_FILE = os.path.join(CURRENT_DIR, "token.json")

try:
    from nexascout.mailer import (
        load_smtp_config,
        is_gmail_api_ready,
        load_sent_logs,
        send_bulk_proposal_emails
    )
except ImportError:
    from modules.mailer import (
        load_smtp_config,
        is_gmail_api_ready,
        load_sent_logs,
        send_bulk_proposal_emails
    )
import openpyxl

def load_leads():
    if not os.path.exists(EXCEL_FILE):
        print(f"[HATA] Excel dosyası bulunamadı: {EXCEL_FILE}")
        return []
    
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    
    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    col_map = {}
    for idx, h in enumerate(headers):
        if "kurum" in h or "işletme" in h:
            col_map["kurum_adi"] = idx
        elif "kategori" in h or "sektör" in h:
            col_map["kategori"] = idx
        elif "eposta" in h or "e-posta" in h or "email" in h:
            col_map["eposta"] = idx
        elif "telefon" in h or "gsm" in h:
            col_map["telefon"] = idx

    leads = []
    for r in rows[1:]:
        name = str(r[col_map.get("kurum_adi", 1)] or "").strip()
        if not name:
            continue
        email = str(r[col_map.get("eposta", 6)] or "").strip()
        phone = str(r[col_map.get("telefon", 5)] or "").strip()
        cat = str(r[col_map.get("kategori", 2)] or "").strip()
        leads.append({
            "kurum_adi": name,
            "ana_kategori": cat,
            "eposta": email,
            "telefon": phone
        })
    return leads

def main():
    parser = argparse.ArgumentParser(description="Toplu VIP E-Posta Gönderim Aracı")
    parser.add_argument("--yes", "-y", action="store_true", help="Onay sormadan doğrudan başlat")
    parser.add_argument("--force", "-f", action="store_true", help="Daha önce gönderilenlere de tekrar gönder")
    parser.add_argument("--delay", type=float, default=2.5, help="İki e-posta arası güvenlik beklemesi (saniye)")
    args = parser.parse_args()

    print("=" * 75)
    print(" NEXASCOUT — TOPLU VIP E-POSTA VE WORD TEKLİF GÖNDERİM MOTORU")
    print(" Yetkili Danışman: Yiğit Narin | yigit.narin@cb.com.tr | 0532 451 40 08")
    print("=" * 75)

    # 1. Kimlik ve Yetkilendirme Denetimi
    cfg = load_smtp_config()
    gmail_ready = is_gmail_api_ready()
    smtp_ready = bool(cfg.get("smtp_password"))

    if not (gmail_ready or smtp_ready):
        print("\n[KRİTİK UYARI] E-Posta gönderim altyapısı henüz yetkilendirilmemiş!")
        print("---------------------------------------------------------------------------")
        print("1. Google Workspace (Gmail API) ile güvenli gönderim için:")
        print("   -> 'GOOGLE_GMAIL_BAGLA.bat' dosyasını çalıştırıp hesabınızı onaylayınız.")
        print("2. Klasik SMTP ile gönderim için:")
        print("   -> 'PANEL_BASLAT.bat' üzerinden paneli açıp SMTP şifrenizi kaydediniz.")
        print("---------------------------------------------------------------------------\n")
        sys.exit(1)

    provider_name = "Resmi Google Workspace (Gmail API)" if gmail_ready else "Kurumsal SMTP"
    print(f"\n[+] Aktif Gönderim Kanalı : {provider_name}")
    print(f"[+] Gönderen E-Posta       : {cfg.get('sender_email', 'yigit.narin@cb.com.tr')}")
    print(f"[+] Teklif Dosyaları Yolu : {PROPOSALS_DIR}")

    # 2. Kurum Veritabanı Analizi
    leads = load_leads()
    if not leads:
        print("[HATA] Hedef kurum listesi boş!")
        sys.exit(1)

    valid_leads = [l for l in leads if l.get("eposta") and l.get("eposta") != "N/A" and "@" in l.get("eposta")]
    missing_leads = [l for l in leads if not (l.get("eposta") and l.get("eposta") != "N/A" and "@" in l.get("eposta"))]
    sent_logs = load_sent_logs()
    already_sent = [l for l in valid_leads if l.get("kurum_adi") in sent_logs and "SUCCESS" in sent_logs[l.get("kurum_adi")].get("status", "")]

    to_be_sent = len(valid_leads) if args.force else (len(valid_leads) - len(already_sent))

    print("\n[VERİTABANI VE İLETİŞİM DURUMU]")
    print(f" -> Toplam Kurum Sayısı          : {len(leads)}")
    print(f" -> E-Postası Doğrulanan Kurum   : {len(valid_leads)}")
    print(f" -> E-Postası Olmayan (Atlanacak): {len(missing_leads)}")
    print(f" -> Daha Önce Gönderilmiş Kurum  : {len(already_sent)}")
    print(f" -> Bu Turda Gönderilecek Hedef  : {to_be_sent}")
    print(f" -> Güvenlik Aralığı (Anti-Spam) : {args.delay} saniye")
    est_duration = round((to_be_sent * args.delay) / 60, 1)
    print(f" -> Tahmini Toplam Süre          : ~{est_duration} dakika\n")

    if to_be_sent <= 0:
        print("[BİLGİ] Gönderilecek yeni kurum bulunmamaktadır (Tüm kurumlara zaten gönderilmiş).")
        print("Tekrar göndermek isterseniz '--force' parametresini kullanabilirsiniz.")
        sys.exit(0)

    # 3. Kullanıcı Onayı
    if not args.yes:
        confirm = input(f"[?] {to_be_sent} kuruma kişiselleştirilmiş Word teklif eki (.docx) ile e-posta gönderilsin mi? (E/H): ").strip().upper()
        if confirm not in ["E", "EVET", "Y", "YES"]:
            print("[İPTAL] Gönderim işlemi kullanıcı tarafından iptal edildi.")
            sys.exit(0)

    print("\n" + "=" * 75)
    print(" GÖNDERİM BAŞLATILDI — LÜTFEN PENCEREYİ KAPATMAYINIZ")
    print("=" * 75 + "\n")

    def progress_callback(current, total, name, status, msg):
        now_str = datetime.now().strftime("%H:%M:%S")
        if status == "SUCCESS":
            icon = "[✓ BAŞARILI]"
        elif status == "FAILED":
            icon = "[✗ HATA]    "
        else:
            icon = "[ℹ ATLANDI] "
        print(f"[{now_str}] ({current:02d}/{total:02d}) {icon} {name[:32]:<32} -> {msg}")

    results = send_bulk_proposal_emails(
        leads=leads,
        proposals_dir=PROPOSALS_DIR,
        delay_sec=args.delay,
        skip_already_sent=not args.force,
        status_callback=progress_callback
    )

    print("\n" + "=" * 75)
    print(" TOPLU GÖNDERİM ÖZETİ")
    print("=" * 75)
    print(f" [+] Başarıyla Gönderilen : {results['sent']}")
    print(f" [-] Başarısız / Hatalı   : {results['failed']}")
    print(f" [o] Atlanan (Geçersiz/Sent): {results['skipped']}")
    print(f" [>] Kayıt Dosyası         : {os.path.join(DATA_DIR, 'SENT_EMAILS_LOG.json')}")
    print("=" * 75 + "\n")
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
