# 🏢 CB.COM.TR PROFESSIONAL SCRAPER REHBERI

## ⚡ HIZLI BAŞLANGIÇ

### 1. Requirements'i Yükle
```bash
pip install -r requirements_scraper.txt
```

### 2. Scraper'ı Çalıştır
```bash
python scraper.py
```

### 3. Sonuçları Kontrol Et
```bash
ls -lh scraper_output/
```

---

## 📊 SCRAPER ÖZELLİKLERİ

### ✅ Temel Özellikler
- **15 sayfayı** otomatik olarak çeker
- **Retry mekanizması** ile hata toleransı
- **Rate limiting** ile zararsız scraping
- **Türkçe karakter** tam desteği
- **User-Agent spoofing** ile engel aşma
- **Logging** detaylı çıktı

### 📁 Oluşturulan Dosyalar
```
scraper_output/
├── listings_20260710_123456.json     (Tüm veri - JSON)
├── listings_20260710_123456.csv      (Excel uyumlu)
└── report_20260710_123456.md         (İstatistik rapor)
```

### 💾 Veri Formatı
Her ilandan çıkarılan bilgiler:
```json
{
  "id": "358156",
  "title": "ÇAMLIDERE'DE MÜSTAKİL 2+1 ÖZEL YAPIM TAŞ VİLLA",
  "type": "Villa",
  "city": "ANKARA",
  "district": "ÇAMLIDERE",
  "neighborhood": "BEYLER",
  "area": "120",
  "rooms": "2+1",
  "price": "₺5.350.000",
  "consultant": "Yiğit Narin",
  "office": "CB VIP",
  "url": "https://www.cb.com.tr/ankara-camlidere-beyler-satilik/villa/358156",
  "image": "https://...",
  "latitude": "40,510168",
  "longitude": "32,477800",
  "scraped_at": "2026-07-10T12:34:56.789123"
}
```

---

## 🔧 SCRAPER YAPISI

### Scraper Sınıfı Metotları

#### `fetch_page(page_num)` 
Tek bir sayfayı çeker
- ✅ Retry mekanizması (3 deneme)
- ✅ User-Agent spoofing
- ✅ UTF-8 encoding
- ✅ BeautifulSoup parsing

**Örnek:**
```python
soup = scraper.fetch_page(1)
```

#### `parse_listing(card)`
HTML kartından veri çıkarır
- ✅ Tüm HTML fieldları
- ✅ Regex ile sayı ekstraksiyon
- ✅ Hata handling

**Örnek:**
```python
listing = scraper.parse_listing(card_div)
```

#### `scrape_page(page_num)`
Bir sayfadaki tüm ilanları çeker
- ✅ Logging (progress)
- ✅ Rate limiting

**Örnek:**
```python
listings = scraper.scrape_page(1)  # Sayfa 1'den ~20 ilan
```

#### `scrape_all()`
Tüm 15 sayfayı çeker
- ✅ Loop tüm sayfalar
- ✅ Hata tracking
- ✅ Timer

**Örnek:**
```python
scraper.scrape_all()  # ~600 ilan
```

#### `save_json()`, `save_csv()`, `save_markdown()`
Farklı formatlarda kaydet

**Örnek:**
```python
scraper.save_json()       # listings_*.json
scraper.save_csv()        # listings_*.csv
scraper.save_markdown()   # report_*.md
```

#### `save_all()`
Tüm formatları kaydet

---

## 📋 KONFİGURASYON

Scraper'ın başında değiştirilebilir ayarlar:

```python
BASE_URL = "https://www.cb.com.tr/satilik"    # Hedef URL
MAX_PAGES = 15                                  # Sayfa sayısı
TIMEOUT = 10                                    # Request timeout (saniye)
RETRY_ATTEMPTS = 3                              # Retry sayısı
RETRY_DELAY = 2                                 # Retry bekleme (saniye)
RATE_LIMIT = 0.5                                # Sayfalar arasında bekleme
```

### Ayarları Değiştirme

```python
# Daha hızlı (risk yüksek)
RATE_LIMIT = 0.1
RETRY_ATTEMPTS = 1

# Daha yavaş (risk düşük)
RATE_LIMIT = 2
RETRY_ATTEMPTS = 5
TIMEOUT = 20
```

---

## 🚀 ADVANCED KULLANIM

### 1. Programmatik Erişim

```python
from scraper import CBScraper

# Scraper oluştur
scraper = CBScraper()

# Tüm ilanları çek
listings = scraper.scrape_all()

# İşle
for listing in listings:
    print(f"{listing['title']}: {listing['price']}")

# Kaydet
scraper.save_all()
```

### 2. Filtreli Veri Alma

```python
# Yalnızca Ankara ilanları
ankara_listings = [
    l for l in listings if l['city'] == 'ANKARA'
]

# Sadece villalar
villas = [l for l in listings if l['type'] == 'Villa']

# 1M+ fiyat
expensive = [
    l for l in listings 
    if '₺' in l['price'] and 
    float(l['price'].replace('₺','').replace('.','')) > 1000000
]
```

### 3. Kendi Analizi Ekle

```python
# İstatistikleri hesapla
import statistics

prices = []
for listing in listings:
    if listing['price'] != 'N/A':
        price = float(listing['price'].replace('₺','').replace('.',''))
        prices.append(price)

print(f"Ortalama: {statistics.mean(prices):,.0f}")
print(f"Medyan: {statistics.median(prices):,.0f}")
print(f"Std Dev: {statistics.stdev(prices):,.0f}")
```

---

## 📊 ÇIKTI ÖRNEKLERİ

### listings_*.json
```json
{
  "source": "cb.com.tr",
  "scraped_at": "2026-07-10T12:34:56.789123",
  "total_listings": 587,
  "listings": [
    {
      "id": "358156",
      "title": "ÇAMLIDERE'DE MÜSTAKİL 2+1 ÖZEL YAPIM TAŞ VİLLA",
      "type": "Villa",
      "city": "ANKARA",
      "price": "₺5.350.000",
      ...
    }
  ],
  "errors": []
}
```

### listings_*.csv (Excel)
```
id,title,type,city,district,neighborhood,area,rooms,price,consultant,office,url,latitude,longitude,scraped_at
358156,ÇAMLIDERE'DE MÜSTAKİL 2+1...,Villa,ANKARA,ÇAMLIDERE,BEYLER,120,2+1,₺5.350.000,Yiğit Narin,CB VIP,https://...,40,510168,32,477800,2026-07-10T12:34:56
358085,VELUX ANKARA SATILIK 4+1...,Ofis,ANKARA,YENİMAHALLE,İNÖNÜ,190,4+1,₺12.500.000,..,...
```

### report_*.md
```markdown
# CB.COM.TR SCRAPER RAPORU

Tarih: 2026-07-10 12:34:56
Kaynak: cb.com.tr VIP Satılık İlanları
Toplam İlan: 587

## İSTATİSTİKLER

| Metrik | Değer |
|--------|-------|
| **Toplam İlan** | 587 |
| **Ortalama Fiyat** | ₺5,234,567 |
| **En Düşük Fiyat** | ₺850,000 |
| **En Yüksek Fiyat** | ₺45,000,000 |

## EMLAK TÜRLERİ DAĞILIMI

- **Daire:** 210 ilan (35.8%)
- **Villa:** 156 ilan (26.6%)
- **Ofis:** 145 ilan (24.7%)
- ...
```

---

## ⚙️ HATA GIDERME

### Problem: "Connection refused"
**Çözüm:** İnternet bağlantısı kontrol et
```bash
ping www.cb.com.tr
```

### Problem: "Timeout after 10 seconds"
**Çözüm:** TIMEOUT değerini artır
```python
TIMEOUT = 30
```

### Problem: "No module named 'bs4'"
**Çözüm:** BeautifulSoup4'ü kur
```bash
pip install beautifulsoup4==4.12.2
```

### Problem: "Sayfada veri bulunamıyor"
**Çözüm:** CB.com.tr yapısı değişebilir, `parse_listing()` güncelle

---

## 📈 PERFORMANS

### Beklenen Sonuçlar

| Metrik | Değer |
|--------|-------|
| **Toplam İlan** | ~600 |
| **Sayfa Başına** | ~40 ilan |
| **Çalışma Süresi** | ~30-60 saniye |
| **Hız** | ~10-20 ilan/saniye |
| **JSON Boyutu** | ~5-10 MB |
| **CSV Boyutu** | ~200-300 KB |

### Hızlandırma

Daha hızlı çalışması için:
```python
RATE_LIMIT = 0.1    # Emniyetle azalvtırma
TIMEOUT = 5         # Daha kısa timeout
RETRY_ATTEMPTS = 1  # Retry'ı azalt
```

### Yavaşlatma (İyi Pratik)

Serverı aşırı yüklememen için:
```python
RATE_LIMIT = 1.0    # 1 saniye/sayfa
TIMEOUT = 15        # Daha uzun timeout
RETRY_ATTEMPTS = 5  # Daha fazla retry
```

---

## 🔒 ETİK UYUMSUZLUK

✅ Yapılması güzel:
- Makul hızlarda scrape (rate limiting)
- User-Agent ayarla
- İnsan gibi davran
- Robots.txt kontrol et
- Sunucuya yük binmeme

❌ Yapılmaması gereken:
- DDoS tarzı saldırı
- Sunucuyu çökerterek scraping
- Verileri yeniden satış
- Telif hakkı ihlali
- Bot tespiti sistemini engelleme

---

## 📝 LOGGING

Scraper detaylı log çıkarır:

```
========================================================================
🚀 CB.COM.TR SCRAPER BAŞLANIYOR
========================================================================

📥 Sayfa 1 çekiliyor... https://www.cb.com.tr/satilik
✅ Sayfa 1 başarıyla yüklendi
📊 Sayfa 1'de 20 ilan bulundu
  ✅ [1/20] ÇAMLIDERE'DE MÜSTAKİL 2+1...
  ✅ [2/20] VELUX ANKARA SATILIK 4+1...
📈 Toplam: 20 ilan (Sayfa 1/15)

📥 Sayfa 2 çekiliyor...
...

========================================================================
✅ SCRAPING TAMAMLANDI
========================================================================
📊 Toplam İlanlar: 587
⏱️  Toplam Süre: 45.32 saniye
⚠️  Hatalar: 0
========================================================================
```

---

## 🎯 CHECKLIST

Başlamadan önce kontrol et:

- [ ] Python 3.7+ yüklü
- [ ] `pip install -r requirements_scraper.txt` çalıştırıldı
- [ ] İnternet bağlantısı aktif
- [ ] CB.com.tr açılabiliyor (İnternette test et)
- [ ] Yazma izni var (scraper_output klasöründe)

Çalıştırdıktan sonra kontrol et:

- [ ] Scraper çalıştı (logs görüldü)
- [ ] scraper_output/ klasörü oluştu
- [ ] listings_*.json dosyası var
- [ ] listings_*.csv dosyası var
- [ ] report_*.md dosyası var

---

## 🚀 SONRAKI ADIMLAR

### 1. Veri Analizi
CSV'yi Excel'de aç
```
Sayfa 1: Home → Sürü
Tuşu kullan: Veriye sürü uygula, grafik yap
```

### 2. Veritabanına Kaydet
```python
import sqlite3

conn = sqlite3.connect('listings.db')
# ... JSON'dan okuyup insert
```

### 3. Web Dashboard
Flask + ChartJS ile dashboard
```python
# Grafikleri göster
# İstatistikleri güncelle
# Filtre ekle
```

### 4. Telegram Bot
```python
# Yeni ilanları bildir
# Fiyat değişimlerini takip et
```

---

## 📞 DESTEK

Sorularınız için:

1. **Logs kontrol et**: Hata mesajlarını oku
2. **Konfigürasyon değiştir**: Rate limit, timeout, retry
3. **HTML inspect**: CB.com.tr siteyi inspect et, yapı değişimi kontrol et
4. **BeautifulSoup docs**: Selector sorunları için bs4 dokümantasyonu

---

**Scraper Versiyonu:** 1.0  
**Python:** 3.7+  
**Kütüphaneler:** requests, BeautifulSoup4  
**Encoding:** UTF-8  
**Durum:** ✅ Production Ready  

**Başarılar!** 🚀
