# -*- coding: utf-8 -*-
"""
NexaScout Universal Portfolio Buyer Finder (CLI)
Kullanım:
    python PORTFOY_ALICI_BULUCU.py "https://www.sahibinden.com/ilan/..."
    veya parametresiz çalıştırıp ekrandan link yapıştırın.
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

try:
    from nexascout.portfolio_buyer_pipeline import run_portfolio_buyer_pipeline
except ImportError:
    from modules.portfolio_buyer_pipeline import run_portfolio_buyer_pipeline

def main():
    print("=" * 80)
    print("  🚀 NEXASCOUT OTONOM PORTFÖY ALICI BULMA MOTORU")
    print("  Tek Link ile Portföy Scrape + Analiz + Sektör Eşleştirme + 4'lü Pazarlama")
    print("=" * 80)

    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        try:
            url = input("\n🔗 İlan Linkini Giriniz (Sahibinden veya CB): ").strip()
        except EOFError:
            url = ""

    if not url:
        url = "https://www.sahibinden.com/ilan/emlak-is-yeri-satilik-kizilcasar-losante-karsisi-kose-parsel-ticari-satilik-bina-1343884633/detay/"
        print(f"[*] Link girilmedi, varsayılan portföy linki kullanılıyor:\n    {url}")

    print("\n[+] Portföy canlı olarak scrape ediliyor...")
    print("[+] Özellikler, m², ruhsat durumu ve lokasyon çözümleniyor...")

    res = run_portfolio_buyer_pipeline(url)

    if res.get("status") != "success":
        print(f"\n[!] Hata oluştu: {res.get('error')}")
        return

    analysis = res["analysis"]
    outputs = res["outputs"]

    print("\n" + "=" * 80)
    print(f"🏛️ ÇÖZÜMLENEN PORTFÖY: {analysis['title']}")
    print(f"📍 LOKASYON: {analysis['location']}")
    print(f"🏢 MÜLK SINIFI: {analysis['asset_class']} ({analysis['kapali_m2']})")
    print("=" * 80)

    print("\n🔑 TESPİT EDİLEN HAKSIZ AVANTAJLAR (ALICI KOZLARI):")
    for adv in analysis["advantages"]:
        print(f"  ✔ {adv}")

    vision = analysis.get("vision_analysis", {})
    if vision:
        print("\n🖼️ MİMARİ & GÖRSEL ANALİZ (VISION AGENT):")
        print(f"  • Genel Kondisyon: {vision.get('overall_condition', 'Bakımlı')} (Skor: {vision.get('condition_score', 8)}/10)")
        print(f"  • Ticari Uygunluk: {vision.get('commercial_suitability', 'Çok Yüksek')}")
        if vision.get("positive_visuals"):
            print(f"  • Görsel Değerler : {' • '.join(vision['positive_visuals'])}")

    print("\n🎯 EŞLEŞEN ÖNCELİKLİ ALICI SEKTÖRLERİ (PROPFIT SKORLARI):")
    for sec in analysis["matched_sectors"]:
        print(f"  • [{sec['fit_verdict']}] {sec['ad']} (PropFit: %{sec['propfit_score']})")
        print(f"    └─ Gerekçe : {sec['neden']}")
        print(f"    └─ Karar Verici: {sec.get('hedef_unvanlar', '')}")

    print("\n" + "=" * 80)
    print("📂 TÜM PAZARLAMA VE STRATEJİ DOSYALARI OLUŞTURULDU:")
    print(f"   Klasör: {res['folder_path']}")
    print(f"   • PORTFOY_YATIRIM_VE_HEDEF_ALICI_DOSYASI.docx (Resmi Word Teklif Mektubu)")
    print("   • STRATEJIK_RAPOR.md")
    print("   • MESLEKTAS_IS_BIRLIGI_DUYURUSU.txt")
    print("   • VIP_WHATSAPP_TEASER.txt")
    print("   • KURUMSAL_EPOSTA.txt")
    print("   • GORSEL_AFIS_METNI.txt")
    print("=" * 80)

    print("\n💬 1. MESLEKTAŞ WHATSAPP DUYURUSU (ÖNİZLEME):")
    print("-" * 60)
    print(outputs["meslektas_metni"][:500] + "...\n(Devamı dosyada)")
    print("-" * 60)

    print("\n[✓] Otonom Alıcı Bulma Süreci Başarıyla Tamamlandı!")

if __name__ == "__main__":
    main()
