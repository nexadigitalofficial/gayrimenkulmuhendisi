# ✅ Buyer Extension Entegrasyon Checklist

**Nexa CRM'e AI Buyer Extension entegrasyonu adım adım kontrol listesi**

---

## 📋 Ön Hazırlık (5 dakika)

- [ ] Dosyaları indir:
  - `buyer_engine.py`
  - `app_buyer_routes.py`
  - `buyer_panel.html`
  - `test_buyer_engine.py`
  - `INTEGRATION_GUIDE.md`
  - `README_BUYER_EXTENSION.md`

- [ ] Python paketi kontrol et: `pip list | grep sentence-transformers`
  - Yüklü değilse: `pip install sentence-transformers`

- [ ] Gemini API key'i kontrol et:
  - [ ] `.env`'de `GEMINI_API_KEY` var mı?
  - Yoksa: [Google AI Studio](https://aistudio.google.com/) → API key oluştur

- [ ] Firebase credentials'ı kontrol et:
  - [ ] `FIREBASE_SERVICE_ACCOUNT` `.env`'de tanımlı mı?

---

## 🚀 Adım 1: buyer_engine.py Kurulumu (2 dakika)

```bash
# Dosyayı proje dizinine kopyala
cp buyer_engine.py /path/to/nexa-crm/
```

- [ ] Dosya proje dizininde mi?
- [ ] Python syntax kontrol: `python -m py_compile buyer_engine.py`
  - Hata yoksa ✅ devam et

---

## 🔧 Adım 2: app.py'ye İmport Ekleme (3 dakika)

**Dosya:** `app.py`  
**Satır:** ~42 (import'ların sonuna)

```python
from buyer_engine import (
    BuyerProfile,
    BuyerMatcher,
    ListingMatch,
    NotificationEngine,
    MatchingTier,
    buyer_engine_status,
    parse_natural_language_criteria,
)
```

- [ ] İmport'lar eklendi mi?
- [ ] Syntax hata mı? (Kırmızı çizgi yok)
- [ ] app.py başlangıcı test: `python app.py` (Ctrl+C ile durdur)
  - Hata alırsan: ImportError hatası → buyer_engine.py path doğru mu?

---

## 📡 Adım 3: API Routes Ekleme (10 dakika)

**Dosya:** `app.py`  
**Konum:** `bootstrap_app()` çağrısından **ÖNCE** (dosyanın sonunda)

Routes listesi:
- [ ] `/api/buyer/status`
- [ ] `/api/buyer/profile/create` (POST)
- [ ] `/api/buyer/profile/list` (GET)
- [ ] `/api/buyer/profile/get` (GET)
- [ ] `/api/buyer/profile/update` (POST)
- [ ] `/api/buyer/profile/delete` (POST)
- [ ] `/api/buyer/match-listing` (POST)
- [ ] `/api/buyer/matches/list` (GET)
- [ ] `/api/buyer/matches/stats` (GET)
- [ ] `/api/buyer/notify` (POST)
- [ ] `/api/buyer/parse-criteria` (POST)
- [ ] `/api/buyer/dashboard` (GET)

**Kaynak:** `app_buyer_routes.py` → Tüm @app.route ile başlayan bölümleri kopyala

```python
# app.py'nin sonuna ekle (bootstrap_app() çağrısından önce):

@app.route("/api/buyer/status")
def api_buyer_status():
    """Buyer Engine durumu."""
    return jsonify(buyer_engine_status())

# ... (diğer routes)
```

- [ ] Tüm 12 route eklendi mi?
- [ ] Syntax hata mı?
- [ ] app.py test: `python app.py` (başlangıç hatası yok)

---

## 🖼️ Adım 4: crm.html'e UI Entegrasyonu (5 dakika)

**Dosya:** `crm.html`

### A) Tab Navigation'a Ekle

Tab butonları arasına ekle (genellikle satır ~50-70):

```html
<button onclick="switchToBuyerPanel(currentUserID)" class="tab-button">
  🎯 Buyer Panel
</button>
```

- [ ] Tab butonu eklendi mi?

### B) İçeriğe Ekle

Tab container'lar arasına ekle:

```html
<div id="buyerPanelContainer" style="display:none;">
  <!-- buyer_panel.html içeriğini BURAYA kopyala -->
</div>
```

- [ ] Container div'i eklendi mi?

### C) buyer_panel.html İçeriğini Kopyala

`buyer_panel.html` dosyasında `<div style="font-family: 'Jost'...` ile başlayan **tüm HTML'i** kopyala, `buyerPanelContainer` içine yapıştır.

- [ ] HTML içeriği yapıştırıldı mı?

### D) Script'i Ekle

crm.html'in script kısmına ekle:

```javascript
function switchToBuyerPanel(uid) {
  // Diğer tab'ları gizle
  document.querySelectorAll('[id$="Container"]').forEach(el => el.style.display = "none");
  document.getElementById("buyerPanelContainer").style.display = "block";
  
  // Buyer panel'i initialize et
  if (typeof initBuyerPanel === 'function') {
    initBuyerPanel(uid);
  }
}
```

- [ ] switchToBuyerPanel fonksiyonu ekledim?
- [ ] crm.html tarayıcıda açıldı mı ve hata yok mu?

---

## 🌍 Adım 5: .env Konfigürasyonu (3 dakika)

**Dosya:** `.env`

Şu satırları ekle (yoksa):

```env
# Buyer Engine
BUYER_MIN_MATCH_SCORE=50
BUYER_VECTOR_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_BUYER_NOTIFICATIONS=true

# Gemini (AI matching + NL parsing) — zaten olması gerek
GEMINI_API_KEY=your_key_here

# Email (zaten olması gerek)
EMAIL_PROVIDER=smtp
EMAIL_FROM=yigitnarinofficial@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=yigitnarinofficial@gmail.com
SMTP_PASSWORD=your_app_password
```

- [ ] `GEMINI_API_KEY` tanımlı mı?
- [ ] `EMAIL_PROVIDER` ve SMTP ayarları var mı?
- [ ] `.env` dosyası kaydedildi mi?

---

## ✅ Adım 6: Test (5 dakika)

### Test 1: Engine Status

```bash
curl http://localhost:5000/api/buyer/status
```

**Beklenen yanıt:**
```json
{"ok": true, "matcher": true, "vector_model": true}
```

- [ ] ✅ Yanıt alındı mı?

### Test 2: Unit Testler

```bash
python test_buyer_engine.py
```

**Beklenen sonuç:**
```
✅ TÜM TESTLER BAŞARILI
```

- [ ] ✅ Testler geçti mi?

### Test 3: Profil Oluştur

```bash
curl -X POST http://localhost:5000/api/buyer/profile/create \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "test_user_123",
    "name": "Test Alıcı",
    "email": "test@example.com",
    "phone": "05324514008",
    "criteria": {
      "min_price": 3000000,
      "max_price": 6000000,
      "neighborhoods": ["Çankaya"]
    }
  }'
```

**Beklenen yanıt:**
```json
{"ok": true, "buyer_id": "...", "profile": {...}}
```

- [ ] ✅ Profil oluşturuldu mu?

### Test 4: Dashboard

```bash
curl "http://localhost:5000/api/buyer/dashboard?uid=test_user_123"
```

**Beklenen yanıt:**
```json
{"ok": true, "dashboard": {"active_buyers": 1, ...}}
```

- [ ] ✅ Dashboard data geldi mi?

### Test 5: Browser UI

1. `http://localhost:5000/crm.html` aç
2. 🎯 Buyer Panel tab'ına tıkla
3. Dashboard/Profiles/Matches tab'larını test et

- [ ] ✅ Buyer panel açıldı mı?
- [ ] ✅ Profil oluşturabildin mi?
- [ ] ✅ Dashboard görüntülendi mi?

---

## 🔄 Adım 7: Entegrasyon Doğrulaması (5 dakika)

Mevcut sisteminiz ile uyum:

### mailer.py Uyumu
- [ ] `build_lead_confirmation_email()` fonksiyonu var mı?
- [ ] `send_transactional_email()` fonksiyonu çalışıyor mu?
- [ ] Email gönderiliyor mu? (`/api/mailer/status`)

### wa_cloud.py Uyumu
- [ ] `send_whatsapp()` fonksiyonu var mı?
- [ ] `send_whatsapp_template()` opsiyonel mi?
- [ ] WhatsApp bağlı mı? (`/api/wa/status`)

### ai_listing.py Uyumu
- [ ] Scraper çalışıyor mu?
- [ ] Listing data doğru format mı?
  - [ ] id, property_type, location, price, area, rooms, age, amenities

### Firebase Uyumu
- [ ] Firestore bağlı mı?
- [ ] `/users/{uid}/buyers` collection oluşturulabildi mi?
- [ ] `/users/{uid}/buyer_matches` oluşturulabildi mi?

---

## 🎯 Adım 8: İlk Kullanım (5 dakika)

1. **Admin Panel'i Aç**
   - http://localhost:5000/crm.html
   - Login yap

2. **Buyer Panel'i Aç**
   - 🎯 Buyer Panel tab'ına tıkla

3. **Dashboard'ı Gör**
   - 0 profil, 0 eşleşme görmeli

4. **Profil Oluştur**
   - `+ Yeni Profil` butonuna tıkla
   - Ad, email, fiyat aralığı, semtler gir
   - Kaydet

5. **Test İlanı Eşleştir**
   ```bash
   curl -X POST http://localhost:5000/api/buyer/match-listing \
     -H "Content-Type: application/json" \
     -d '{
       "uid": "test_user_123",
       "listing": {
         "id": "test_listing_1",
         "property_type": "Daire",
         "location": "Çankaya",
         "price": 4500000,
         "area": 110,
         "rooms": 3,
         "age": 5
       }
     }'
   ```

6. **Eşleşmeleri Gör**
   - Buyer Panel → Eşleşmeler tab'ı
   - Oluşturulan eşleşmeyi gör

- [ ] ✅ Tüm adımlar başarılı mı?

---

## 🚨 Hızlı Troubleshooting

| Hata | Çözüm |
|------|-------|
| `ModuleNotFoundError: buyer_engine` | buyer_engine.py proje dizininde mi? |
| `ImportError: sentence_transformers` | `pip install sentence-transformers` |
| `Firebase bağlı değil` | `.env`'de FIREBASE_SERVICE_ACCOUNT var mı? |
| `API 503 Firebase bağlı değil` | app.py'de `init_firebase_admin()` çağrılıyor mu? |
| `Eşleşme bulunamıyor` | Min skor (50) vs gerçek skor kontrol et |
| `Email gönderilemedi` | `/api/mailer/status` kontrol et |

---

## 📦 Production Checklist

Deployment öncesi:

- [ ] `GEMINI_API_KEY` set ve valid
- [ ] `FIREBASE_SERVICE_ACCOUNT` set ve valid
- [ ] Email provider configured ve test edilmiş
- [ ] WhatsApp (WA_PHONE_ID, WA_ACCESS_TOKEN) opsiyonel olması kabul edildi
- [ ] Rate limiting aktif (`flask-limiter`)
- [ ] CORS settings doğru (`nexacrm.com`, prodction domain)
- [ ] Error logging configured
- [ ] Database backup scheduled
- [ ] Firestore indexes created:
  - [ ] `buyer_matches` → `buyer_id` + `created_at` (descending)
- [ ] Cron job setup (batch matching) — opsiyonel

---

## 📊 Performans Optimizasyonu

Production sonrası:

- [ ] Vector model caching enabled
- [ ] Database query optimization
  - [ ] Firestore indexes kullanılıyor
  - [ ] N+1 queries yok
- [ ] Rate limiting tuned
  - [ ] `/api/buyer/*` → 100/hour
  - [ ] `/api/buyer/match-listing` → 10/hour (ağır)
- [ ] Monitoring setup
  - [ ] API latency
  - [ ] Error rate
  - [ ] Gemini API quota usage

---

## 🎓 Sonraki Adımlar

Tamamlandıktan sonra:

1. **Batch Processing** (Opsiyonel)
   - Yeni ilanlar otomatik eşleştirilsin
   - Cron job: saatlik/günlük

2. **Webhook Integration** (Opsiyonel)
   - Sahibinden scraper → `/api/buyer/match-listing` trigger
   - Realtime matching

3. **Lead Scoring** (Gelişmiş)
   - Buyer feedback ile model fine-tune
   - "interested" vs "not_interested" vs "enquiry_sent"

4. **Analytics Dashboard**
   - Conversion rate (match → enquiry)
   - Popular neighborhoods/price ranges
   - Buyer demographics

5. **SMS Integration** (Opsiyonel)
   - Telegram/WhatsApp yerine SMS

---

## ✨ Başarı Kriterleri

Entegrasyon başarılı kabul edilirse:

✅ Buyer Extension `/api/buyer/status` → `{"ok": true}`  
✅ Dashboard 0+ profil gösteriyor  
✅ Profil oluştur → Firebase'e kaydediliyor  
✅ İlanı eşleştir → Eşleşme oluşturuluyor  
✅ Email gönderimi çalışıyor  
✅ crm.html'de Buyer Panel tab'ı görünüyor ve çalışıyor  
✅ Unit testler tüm pass veriyor  

---

## 📞 Hızlı İletişim

Takılırsanız:

1. `test_buyer_engine.py` çalıştır → Çıktıya bak
2. API endpoint'lerinin status'ünü kontrol et:
   - `/api/buyer/status`
   - `/api/mailer/status`
   - `/api/gemini/status` (varsa)
3. Logs'a bak (`app.py` çıktısı)
4. Detaylı hata mesajını not et

---

**Tarih:** 2026-07-07  
**Versiyon:** 1.0  
**Status:** ✅ Production-Ready

🎉 **Başarılar!** Buyer Extension kurulumunuzu tamamladınız.
