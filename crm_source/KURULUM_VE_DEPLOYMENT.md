# NEXA CRM Pro — Kurulum ve Deployment Rehberi

**Hazırlanma Tarihi:** 07.07.2026  
**Versiyon:** 1.0  
**Durum:** ✅ Hazır Dağıtım

---

## 📋 HIZLI BAŞLANGAÇ (5 dakika)

### Adım 1: Dosyaları İndir ve Düzenle

```bash
# Tüm dosyaları tek klasöre koy
nexa-crm/
├── app.py
├── crm.html              (✅ DIV'ler düzeltildi)
├── admin.html
├── ai_analysis.html
├── buyer_engine.py
├── ai_listing.py
├── fsbo_engine.py
├── valuation.py
├── mailer.py
├── wa_cloud.py
├── .env.template         (→ .env olarak kopyala)
├── requirements.txt
└── service-account.json  (Firebase credential)
```

### Adım 2: Environment Dosyası Oluştur

```bash
# .env.template'ten .env dosyası oluştur
cp .env.template .env

# .env dosyasını düzenle ve değerleri doldur
nano .env
# Gerekli:
# - FIREBASE_SERVICE_ACCOUNT
# - GEMINI_API_KEY
# - EMAIL bilgileri (isteğe bağlı)
```

### Adım 3: Python Dependencies Yükle

```bash
# Virtual environment oluştur (opsiyonel ama önerilir)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ya da
venv\Scripts\activate     # Windows

# Dependencies yükle
pip install -r requirements.txt
```

### Adım 4: Test Başlat

```bash
python3 app.py

# Beklenen çıktı:
# ✅ Firebase Admin SDK başlatıldı
# ✅ Background Scheduler başlatıldı
# 📋 Listing refresh...
# 
# 🚀 Unified Sunucu Başlatıldı: http://0.0.0.0:5000
#    📊 CRM Paneli : http://0.0.0.0:5000/crm
```

### Adım 5: Tarayıcıda Aç

```
http://localhost:5000/crm
```

✅ **Başarılı olduğunda:** CRM sayfası yüklenir, Firebase auth dialogu görüntülenir.

---

## 🔍 TEŞHIS VE SORUN GIDERME

### Test 1: Dosyalar Mevcut mu?

```bash
ls -lh nexa-crm/ | grep -E "app.py|crm.html|requirements.txt"
```

✅ Tüm dosyalar göz üne alınmalı.

### Test 2: Python Syntax Hatası Var mı?

```bash
python3 -m py_compile app.py buyer_engine.py ai_listing.py
echo "✅ Syntax OK" || echo "❌ Hata var"
```

### Test 3: İmport'lar Çalışıyor mu?

```bash
python3 << 'EOF'
try:
    from app import app
    print("✅ app.py import başarılı")
    
    # Routes kontrol
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    crm_route = [r for r in routes if '/crm' in r]
    print(f"✅ CRM Route: {crm_route}")
    
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
EOF
```

### Test 4: Firebase Bağlantısı

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()
sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "service-account.json")

if os.path.exists(sa_path):
    print(f"✅ Firebase credential dosyası var: {sa_path}")
else:
    print(f"❌ Firebase credential bulunamadı: {sa_path}")
EOF
```

### Test 5: Browser Console Hatası (F12)

Sayfayı açtıktan sonra **F12 → Console** sekmesinde:

```javascript
// Şu hatalar aranır:
console.log("Vue:", typeof Vue);           // "function" olmalı
console.log("Firebase:", typeof firebase); // "object" olmalı
console.log("Auth:", typeof firebase?.auth); // "function" olmalı
```

---

## 🌐 CLOUD DEPLOYMENT (Render/Vercel)

### Render.com'a Deploy

```bash
# 1. Git repo oluştur
git init
git add .
git commit -m "NEXA CRM v1.0"

# 2. GitHub'a push et
git remote add origin https://github.com/yourusername/nexa-crm.git
git branch -M main
git push -u origin main

# 3. Render.com'da:
#    - https://dashboard.render.com/
#    - New → Web Service
#    - Connect to GitHub repo
#    - Environment Variables ekle (.env içeriği)
#    - Deploy et
```

### Environment Variables (Render)

Render Dashboard → Service Settings → Environment:

```
FIREBASE_SERVICE_ACCOUNT={"type":"service_account","project_id":"..."}
GEMINI_API_KEY=your_key
EMAIL_FROM=your_email
SMTP_PASSWORD=your_app_password
WA_PHONE_NUMBER_ID=your_id
WA_ACCESS_TOKEN=your_token
PORT=5000
```

### Build Command (Render)

```
pip install -r requirements.txt
```

### Start Command (Render)

```
python3 app.py
```

---

## 📦 PRODUCTION CHECKLIST

- [ ] `.env` dosyası oluşturuldu (sensible bilgiler dolduruldu)
- [ ] `.gitignore` dosyasında `.env` ve `service-account.json` var
- [ ] `requirements.txt` yüklendi
- [ ] `python3 app.py` hata vermeden başlıyor
- [ ] `/crm` sayfası yükleniyor (F12 Console'da hata yok)
- [ ] Firebase authentication çalışıyor
- [ ] CORS ayarları doğru (ALLOWED_ORIGINS)
- [ ] Email/WhatsApp bilgileri doğru (test edin)
- [ ] SSL sertifikası var (production için)

---

## 🔐 SECURITY BEST PRACTICES

### 1. Secrets Yönetimi

```bash
# ❌ YAPMA
git add .env                                    # .env'ı commit etme
export GEMINI_API_KEY="my_secret_key"          # Terminal'de expose etme
print(os.environ['GEMINI_API_KEY'])             # Logs'a secret yazma

# ✅ YAP
# .gitignore'a ekle
echo ".env" >> .gitignore
echo "service-account.json" >> .gitignore
echo "*.log" >> .gitignore

# Environment variables kullan (CI/CD veya .env dosyası)
# Logging'te password vs. gösterme
```

### 2. Database Şifreleri

```python
# .env dosyasında sakla
DATABASE_URL=postgresql://user:pass@host/db

# app.py'de:
db_url = os.environ.get("DATABASE_URL")
# Asla hard-code etme!
```

### 3. CORS Yapılandırması

```python
# app.py satır ~52
CORS(app, origins=[
    "https://nexacrm.com",      # Production domain
    "https://nexa-crm.onrender.com",  # Render domain
    # "http://localhost:5000",   # Development ONLY
], supports_credentials=True)

# Üretimde localhost KALDIR!
```

### 4. Rate Limiting

```python
# Mevcut (satır ~60)
if _limiter_available:
    limiter = Limiter(...)
    # 200 istek/saat limit var
```

---

## 📊 MONİTÖRİNG

### Logs Kontrol

```bash
# Render'da
# Service Settings → Logs → View Logs

# Lokal'de
tail -f nexa-crm.log
```

### Hata Takibi

```bash
# Sentry.io ile (optional)
pip install sentry-sdk
```

```python
# app.py başında
import sentry_sdk
sentry_sdk.init(dsn="your_sentry_dsn")
```

---

## 🚀 PERFORMANS OPTİMİZASYONU

### 1. Caching

```python
# app.py - routes öncesi
from flask import cache

cache.init_app(app, config={'CACHE_TYPE': 'simple'})

@app.route("/api/listings")
@cache.cached(timeout=300)
def get_listings():
    # ...
    pass
```

### 2. CDN (Production)

```html
<!-- crm.html -->
<!-- CloudFlare CDN kullan -->
<script src="https://cdn.jsdelivr.net/npm/vue@3"></script>
```

### 3. Database Connection Pooling

```python
# Render'da otomatik, lokal'de:
pip install sqlalchemy-utils
```

---

## 📱 MOBIL UYUMLULUĞU

CRM HTML zaten responsive (Tailwind CSS).

**Test et:**
```bash
# Chrome Dev Tools
F12 → Toggle Device Toolbar (Ctrl+Shift+M)
- iPhone 12 / iPad / Android test et
```

---

## 🔄 UPDATE SÜRECI

### Yeni Sürüm Deploy Etme

```bash
# 1. Lokal'de test et
python3 app.py

# 2. Git'e commit et
git add .
git commit -m "v1.1: Yeni özellik"

# 3. Push et
git push origin main

# 4. Render otomatik deploy eder
# (Auto-deploy aktif ise)
```

---

## 📞 SORUN GIDERME KAYNAKLAR

### Sık Sorunlar

| Sorun | Çözüm |
|-------|-------|
| Firebase connection timeout | Firebase credentials kontrol et |
| DIV render hatası | `/crm` sayfasını reload et (F5) |
| CORS blocked | `ALLOWED_ORIGINS` kontrol et |
| ModuleNotFoundError | `pip install -r requirements.txt` yeniden çalıştır |
| 500 error | Console logs'u kontrol et |

### Destek

```bash
# Log dosyası gönder
cat nexa-crm.log | head -100

# System info
python3 --version
pip list | grep -E "Flask|firebase|google"
```

---

## ✅ DEPLOYMENT BAŞARISI ÖRNEĞİ

```bash
$ python3 app.py

======================================================================
🚀 NEXA CRM - Bootstrap Başlatılıyor
======================================================================

✅ Firebase Admin SDK başlatıldı
   📁 Credential: service-account.json

✅ Background Scheduler başlatıldı

📋 Listing refresh in progress...

======================================================================
✅ Bootstrap Tamamlandı
======================================================================

✅ Unified Sunucu Başlatıldı: http://0.0.0.0:5000
   🌐 Web Sitesi : http://0.0.0.0:5000/
   📊 CRM Paneli : http://0.0.0.0:5000/crm
   🔧 Admin Panel: http://0.0.0.0:5000/admin
   🤖 AI Analiz  : http://0.0.0.0:5000/ai-analysis
   📂 Projeler   : http://0.0.0.0:5000/sunum
```

🎉 **Hazır! Tarayıcıda `http://localhost:5000/crm` açabilirsin.**

---

**Başarılar! 🎯**

Sorunda kalırsan, yukarıdaki "Sorun Giderme" bölümünü kontrol et.
