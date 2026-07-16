# 🚀 HIZLI BAŞLANGIÇ (5 DAKİKA)

## 1️⃣ Hazırlık (30 saniye)

```bash
# Python kontrol et
python --version

# Dependencies kur
pip install -r requirements.txt
```

## 2️⃣ Çalıştır

### SEÇENEK A: Sadece Scraping

```bash
python a.py
```

✅ Çıktı: `scraper_output/listings_*.json` (587 ilan)  
⏱️ Süre: ~1 dakika

### SEÇENEK B: Scraping + Matching

```bash
python a.py --whatsapp "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"
```

✅ Çıktı: 
- `scraper_output/` (scraped listings)
- `matcher_output/` (matches + reports)

⏱️ Süre: ~1-2 dakika

---

## 📊 ÇIKTI DOSYALARI

### Scraper Output

```
✅ listings_*.json     (5+ MB) - Tüm veri - Python/Excel'de aç
✅ listings_*.csv      (200 KB) - Excel uyumlu
✅ report_*.md         (4 KB) - İstatistik raporu
```

### Matcher Output (WhatsApp ile çalıştırıldıysa)

```
✅ matches_*.json      - Tüm eşleştirmeler
✅ report_*.md         - Top 10 matches + analiz
```

---

## 🎯 SONRAKILER

- [ ] CSV'yi Excel'de aç ve filtrele
- [ ] Matching puanlarını kontrol et
- [ ] Müşterilere en yüksek skorlu matches'i gönder
- [ ] Günlük otomasyonu Cron/Task Scheduler ile ayarla

---

## 🆘 SORUN GIDERME

| Problem | Çözüm |
|---------|-------|
| ModuleNotFoundError | `pip install beautifulsoup4 requests` |
| Connection refused | İnternet kontrol et, `RATE_LIMIT` artır |
| Ollama yok | Normal! Scoring mode çalıştır |
| WhatsApp dosyası yok | Dosya yolunu kontrol et |

---

**Başarı?** → `scraper_output/` klasöründe dosyaları kontrol et ✅

Detaylı bilgi için: **README_UNIFIED_SYSTEM.md**

