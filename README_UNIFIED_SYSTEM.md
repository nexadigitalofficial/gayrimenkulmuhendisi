# 🚀 CB SCRAPER + AI MATCHER - TEK DOSYA ENTEGRE SISTEM

## 📦 NE ALDIĞINIZ

Şimdi **tek bir Python dosyasında** tüm sistem mevcut:

✅ **Web Scraping** - CB.com.tr'den 600+ ilan çekme  
✅ **WhatsApp Parsing** - ARAYIŞ + PORTFÖY parsing (Turkish NLP)  
✅ **AI Matching** - Ollama/Qwen2.5 entegrasyonu  
✅ **Otomatik Raporlama** - JSON + Markdown output  
✅ **Fallback Mode** - Ollama olmadan da çalışır (scoring only)  

---

## ⚡ HIZLI BAŞLANGIÇ

### 1️⃣ Kurulum (1 dakika)

```bash
# Python 3.7+ gerekli
python --version

# Dependencies'leri kur
pip install requests beautifulsoup4 python-dotenv
```

### 2️⃣ A) Sadece Scraping (Web'ten 600+ ilan çek)

```bash
python a.py
```

**Çıktı:**
- `scraper_output/listings_*.json` (Tüm veri)
- `scraper_output/listings_*.csv` (Excel uyumlu)
- `scraper_output/report_*.md` (İstatistik raporu)

### 2️⃣ B) Scraping + Matching (Scraping + AI Eşleştirme)

```bash
# WhatsApp mesajlarını dışa aktar (txt dosyası)
python a.py --whatsapp "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"
```

**Çıktı:**
- Scraper: `scraper_output/`
- Matcher: `matcher_output/matches_*.json` + `report_*.md`

---

## 📊 ÖRNEK ÇALIŞMA AKIŞI

### Senaryo 1: Sadece Web'ten Veri Çek

```bash
$ python a.py

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
🚀 CB SCRAPER + AI MATCHER - TAM SISTEM
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

📥 STEP 1: WEB SCRAPING
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

📥 Sayfa 1 çekiliyor...
✅ Sayfa 1 başarıyla yüklendi
📊 Sayfa 1'de 20 ilan bulundu
  ✅ [1/20] ÇAMLIDERE'DE MÜSTAKİL 2+1...
  ✅ [2/20] VELUX ANKARA SATILIK 4+1...
  ... (devam)

(~30 saniye sonra)

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
✅ SCRAPING TAMAMLANDI
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

📊 Toplam İlan: 587
📁 Çıktı: scraper_output/

Matching için WhatsApp dosyası sağlayın:
   python a.py --whatsapp <file.txt>
```

### Senaryo 2: WhatsApp ile Matching

```bash
$ python a.py --whatsapp "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
🚀 CB SCRAPER + AI MATCHER - TAM SISTEM
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

📥 STEP 1: WEB SCRAPING
(... 30 saniye ...)

📥 STEP 2: WhatsApp PARSING
📊 45 mesaj bulundu
   ✅ ARAYIŞ: Yiğit Narin - Çankaya 3+1...
   ✅ PORTFÖY: Bağlıca Daire ₺5.1M...
   ... (devam)

✅ Parsing tamamlandı: 12 ARAYIŞ, 5 PORTFÖY

📥 STEP 3: MATCHING
✅ Portföyler hazırlandı:
   - WhatsApp: 5
   - CB.com.tr: 587
   - Toplam: 592

🔄 Matching başlatılıyor...

(... 10 saniye ...)

✅ Matching tamamlandı: 42 eşleştirme bulundu

╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
✅ TAM SİSTEM TAMAMLANDI
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

📊 SCRAPER SONUÇLARI:
   - Toplam İlan: 587
   - Kaynaklar: CB.com.tr (VIP)

🤖 MATCHER SONUÇLARI:
   - Toplam ARAYIŞ: 12
   - Toplam PORTFÖY: 592
   - Bulunan Match: 42
   - Ortalama Score: 87.3%
   - 90+ Score: 18

📁 ÇIKTI DOSYALARI:
   - Scraper: scraper_output/
   - Matcher: matcher_output/
```

---

## 📁 ÇIKTI DOSYALARI

### Scraper Çıktıları (`scraper_output/`)

```
listings_20260710_123456.json (5+ MB)
├─ Tüm veri - JSON formatında
├─ Machine-readable
└─ Programatik işleme için ideal

listings_20260710_123456.csv (200-300 KB)
├─ Excel uyumlu
├─ 587 satır × 16 kolon
└─ Manual analiz için ideal

report_20260710_123456.md (4-5 KB)
├─ İstatistik raporu
├─ Emlak türlerine göre dağılım
└─ Fiyat analizi
```

### Matcher Çıktıları (`matcher_output/`)

```
matches_20260710_123456.json
├─ Tüm eşleştirmeler
├─ Scoring breakdown
└─ AI analiz (varsa)

report_20260710_123456.md
├─ Top 10 matches
├─ Scoring kriterleri
└─ Kalite metrikleri
```

---

## 🎯 KULLANIM SENARYOLARI

### Senaryo 1: Yeni İlanları Bul

```bash
# Her sabah çalıştır
python a.py

# Results → scraper_output/listings_*.csv
# Excel'de aç, filtrele, analiz et
```

### Senaryo 2: Müşteri Taleplerini Eşleştir

```bash
# WhatsApp grubundan mesajları dışa aktar
# Format: [HH:MM, DD.MM.YYYY] Kişi: Mesaj

python a.py --whatsapp whatsapp_export.txt

# Results → matcher_output/matches_*.json
# Top matches → müşteriye iletişim kur
```

### Senaryo 3: Günlük Otomasyonu (Cron Job)

```bash
# Linux/Mac crontab:
0 9 * * * cd /path/to && python a.py --whatsapp whatsapp.txt >> logs/$(date +\%Y\%m\%d).log 2>&1

# Windows Task Scheduler:
# Tetikleyici: Günlük, 09:00
# İşlem: python a.py --whatsapp whatsapp.txt
# Konumu: C:\scripts\
```

---

## 🔧 KONFİGURASYON

Dosyanın başında değiştirilebilir ayarlar:

```python
# Scraper settings (satırlar 31-39)
BASE_URL = "https://www.cb.com.tr/satilik"
OFFICE_ID = "470"  # Coldwell Banker VIP Ankara
MAX_PAGES = 15
TIMEOUT = 10
RETRY_ATTEMPTS = 3
RATE_LIMIT = 0.5  # Sayfalar arası bekleme

# Matcher settings (satırlar 41-43)
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"
ENABLE_AI_ANALYSIS = True  # False if Ollama not available
```

### Hızlandırma (Riskli)

```python
MAX_PAGES = 5          # 15 yerine 5
RATE_LIMIT = 0.1       # 0.5 yerine 0.1
RETRY_ATTEMPTS = 1     # 3 yerine 1
TIMEOUT = 5            # 10 yerine 5
```

### Yavaşlatma (Güvenli - Önerilir)

```python
RATE_LIMIT = 1.0       # 0.5 yerine 1.0
RETRY_ATTEMPTS = 5     # 3 yerine 5
TIMEOUT = 15           # 10 yerine 15
```

---

## 🤖 AI MATCHING (Ollama)

### Ollama Kurulumu

**Windows/Mac/Linux:**
```bash
# 1. İndir: https://ollama.ai
# 2. Kur: ollama install

# 3. Terminal aç ve model çek:
ollama pull qwen2.5:7b

# 4. Ollama serve çalıştır:
ollama serve
# (Arka planda çalışsın)
```

### Llama Olmadan da Çalışır!

Eğer Ollama yüklü değilse, sistem otomatik olarak **fallback scoring** kullanır:

- ✅ Fiyat, oda, lokasyon, tür eşleştirmesi (6-factor scoring)
- ✅ Akıllı tavsiyeler
- ⚠️ AI analiz yok (Ollama gerekli)

```python
# Eğer Ollama yok:
ENABLE_AI_ANALYSIS = False
# Sistem sadece scoring yapacak, AI analiz olmayacak
```

---

## 📊 MATCHING SKORU NASIL ÇALIŞIR?

### 6-Factor Weighted Algorithm

```
OVERALL SCORE = 
  (Price Score × 0.25) +        # Fiyat uyumluluğu
  (Rooms Score × 0.25) +        # Oda sayısı
  (Location Score × 0.20) +     # Lokasyon
  (Type Score × 0.15) +         # Emlak türü
  (Features Score × 0.10) +     # Özellikler
  (Urgency Score × 0.05)        # Aciliyet

Örnek:
  (1.0 × 0.25) +      # ✅ Fiyat perfect
  (0.8 × 0.25) +      # ✅ Oda çok yakın
  (1.0 × 0.20) +      # ✅ Lokasyon exact
  (0.9 × 0.15) +      # ✅ Tür match
  (0.7 × 0.10) +      # ⚠️ Özellikleri kısmen
  (1.0 × 0.05)        # ✅ Acil arıyordu
  ─────────────────────
  = 0.895 = 89.5% ✅ İyi
```

### Kalite Seviyeleri

```
90-100%: ⭐⭐⭐⭐⭐ Çok İyi (HEMEN ARA)
70-89%:  ⭐⭐⭐⭐ İyi (Ara)
50-69%:  ⭐⭐⭐ Orta (Değerlendir)
30-49%:  ⭐⭐ Düşük (Son çare)
<30%:    ⭐ Çok Düşük (Görmezden gel)
```

---

## 🆘 SORUN GIDERME

### Problem: "Connection refused"

```
❌ Error: Connection refused

Çözüm:
1. İnternet bağlantısı kontrol et: ping www.cb.com.tr
2. CB.com.tr açılıyor mu? (Tarayıcıda test et)
3. Rate limiting: RATE_LIMIT'i 2.0'a çıkar
```

### Problem: "No module named 'bs4'"

```bash
pip install beautifulsoup4==4.12.2
pip install requests==2.31.0
```

### Problem: "Ollama connection failed"

```
⚠️ Ollama connection failed - using fallback

Normal! Sistem score-based matching kullanacak.

Eğer AI analysis istiyorsan:
1. Ollama'yı indir: https://ollama.ai
2. ollama pull qwen2.5:7b
3. ollama serve (ayrı terminal)
4. Scripti yeniden çalıştır
```

### Problem: "WhatsApp dosyası bulunamadı"

```
Dosya yolu kontrol et:
✅ python a.py --whatsapp "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"
❌ python a.py --whatsapp whatsapp.txt  (yol yanlış)

Windows:
python a.py --whatsapp "C:\Users\Yigit\Downloads\whatsapp.txt"

Mac/Linux:
python a.py --whatsapp ~/Downloads/whatsapp.txt
```

---

## 📈 PERFORMANS

### Beklenen Sonuçlar

| İşlem | Süre | Çıktı |
|-------|------|-------|
| Scraping (15 sayfa) | 30-60s | 587 ilan |
| WhatsApp Parsing | 2-3s | 12 ARAYIŞ, 5 PORTFÖY |
| Matching (7,650 combo) | 5-10s | 42 match |
| Ollama AI Analysis | 10-15s | Her match için analiz |
| **TOPLAM** | **~1 dakika** | **Tüm raporlar** |

### Sistem Kaynakları

```
RAM: 500 MB - 1 GB (Ollama olmadan)
     8 GB (Ollama ile)

CPU: Low (Scraping)
     Medium (Matching)
     High (Ollama AI)

Disk: 50-100 MB (çıktı dosyaları)
```

---

## 📝 ENTEGRASYON ÖRNEKLERI

### Python'dan Direkt Kullanım

```python
# a.py ile aynı klasöre koy
from a import CBScraper, WhatsAppCBParser, OllamaMatcher

# Scraping
scraper = CBScraper()
listings = scraper.scrape_all()
print(f"Çekilen: {len(listings)} ilan")

# Parsing
parser = WhatsAppCBParser()
arayislar, portfoyler = parser.parse_file("whatsapp.txt")

# Matching
matcher = OllamaMatcher()
matches = matcher.match_all(arayislar, portfoyler)

for match in matches[:5]:
    print(f"{match.overall_score:.1f}% - {match.recommendation}")
```

### Veri Analizi (Pandas)

```python
import json
import pandas as pd

# Load JSON
with open('scraper_output/listings_*.json') as f:
    data = json.load(f)

# To DataFrame
df = pd.DataFrame(data['listings'])

# Analiz
print(df['price'].describe())
print(df['type'].value_counts())
print(df.groupby('district')['price'].mean())

# Excel'e kaydet
df.to_excel('output.xlsx', index=False)
```

### Telegram Bildirimi

```bash
#!/bin/bash
# run_scraper.sh

cd /path/to/scripts
python a.py --whatsapp whatsapp.txt

# Telegram'a gönder
MESSAGE="✅ Scraper tamamlandı: $(date)"
CHAT_ID="123456789"
TOKEN="your_bot_token"

curl -s -X POST https://api.telegram.org/bot$TOKEN/sendMessage \
  -d "chat_id=$CHAT_ID&text=$MESSAGE"
```

---

## 🎓 DOSYA YAPISI

```
📂 Çalışma Klasörü
├── 📄 a.py                    ← MAIN SCRIPT
├── 📄 requirements.txt         (pip install -r)
│
├── 📂 scraper_output/
│   ├── listings_20260710_123456.json
│   ├── listings_20260710_123456.csv
│   └── report_20260710_123456.md
│
├── 📂 matcher_output/
│   ├── matches_20260710_123456.json
│   └── report_20260710_123456.md
│
└── 📄 _Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt (isteğe bağlı)
```

---

## 🔐 SIRADA NELER VAR?

### Gelecek Geliştirmeler

- [ ] WhatsApp Cloud API entegrasyonu
- [ ] Real-time Google Drive backup
- [ ] Email bildirimleri
- [ ] Telegram bot entegrasyonu
- [ ] Dashboard (Flask web UI)
- [ ] Veritabanı desteği (SQLite/PostgreSQL)
- [ ] Advanced NLP (spaCy/NLTK)
- [ ] Fotoğraf analizi (Computer Vision)

---

## 📞 DESTEK

### Sorular?

1. **"A.py nasıl çalışır?"** → README'yi oku (bu dosya)
2. **"Matching kalitesi düşük?"** → Scoring weights'i ayarla
3. **"Ollama yok ama matching istiyorum?"** → Fallback mode otomatik
4. **"WhatsApp dosyası nerede?"** → WhatsApp'ta Sohbetleri Dışa Aktar

### Hızlı Çözümler

```bash
# Sadece scraping
python a.py

# WhatsApp ile full system
python a.py --whatsapp whatsapp.txt

# Yardım
python a.py --help

# Konfigürasyon (a.py'nin başında)
# MAX_PAGES, RATE_LIMIT, TIMEOUT, vb.
```

---

## ✅ BAŞLANGAÇ CHECKLIST

- [ ] Python 3.7+ yüklü
- [ ] `pip install requests beautifulsoup4` çalıştı
- [ ] `a.py` dosyası var
- [ ] İnternet bağlantısı aktif
- [ ] `python a.py` çalıştı (ilk test)
- [ ] `scraper_output/` klasörü oluştu
- [ ] `listings_*.json` dosyası var (✅ başarı!)

**Matching istiyorsan:**
- [ ] WhatsApp mesajları dışa aktar
- [ ] `python a.py --whatsapp <file.txt>` çalıştır
- [ ] `matcher_output/` klasörü oluştur
- [ ] `matches_*.json` dosyası var (✅ başarı!)

---

## 🎉 BAŞARIYLA BAŞLADINIZ!

```bash
python a.py
# Veya
python a.py --whatsapp "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"
```

**Başarılar!** 🚀

---

*Son Güncelleme: 10.07.2026*  
*Versiyon: 1.0 - Unified System*  
*Status: ✅ Production Ready*

**Made with ❤️ by Yiğit Narin @ NEXA Digital**
