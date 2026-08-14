# ULTRA DETAYLI IMPLEMENTATION PLANI
## "Portföy İlerleme" Özelliği — CRM (templates/crm.html + app.py)

**Tarih:** 14 Ağustos 2026
**Kapsam:** Mevcut CRM'deki her portföye (konut) not ekleme, medya/görsel yükleme,
o portföye özel AI sohbet (chatbot) ve tek tuşla ultra detaylı, görsel zengin
PDF "İlerleme Raporu" üretimi. Rapor, proje sahibinin gönderdiği görsellerin
OCR + görsel analizini içerir: **"şu ana kadar ne yaptık + nasıl devam etmeliyiz"**.

---

## 1. ÖZET VE HEDEFLER

| Başlık | Değer |
|---|---|
| Kullanıcı ihtiyacı | Portföy ilerlemesini kaydetmek, kanıt görsellerle görselleştirmek, AI ile analiz etmek ve profesyonel PDF rapor çıkarmak |
| Çıktı 1 | `templates/crm.html` içinde yeni "İlerleme" sekmesi (medya, notlar, chatbot, rapor butonu) |
| Çıktı 2 | Yeni backend modülü `portfolio_progress.py` (OCR + analiz + rapor + PDF + chat) |
| Çıktı 3 | Firestore'da yeni alt koleksiyonlar (medya/not/rapor geçmişi) |
| Çıktı 4 | Gemini vision tabanlı OCR (mevcut kırık Tesseract yerine) |
| Harici bağımlılık | ReportLab 4.x + Pillow (requirements.txt'e eklenecek) |

**Kritik kararlar (araştırma sonucu ve gerekçeleri):**

1. **OCR → Gemini vision REST** (Tesseract DEĞİL). Mevcut `pytesseract` pip paketi eksik
   (`_TESSERACT=False`), Tesseract binary kurulu ama paketsiz → mevcut OCR çalışmıyor.
   Türkçe el yazısı, tabela fotoğrafı, tapu/belge taraması, tablo içerikleri için Gemini
   vision üstün. Desen: `fsbo_engine.py::_call_gemini_multimodal` (inline_data, 8 görsel limiti).
2. **PDF → ReportLab** (WeasyPrint DEĞİL). Pure Python, Render'da sorunsuz, native
   Doughnut/Pie/Bar chart desteği, TTF font gömme (Türkçe karakter). WeasyPrint Windows'ta
   Pango/Cairo native DLL ister — riskli.
3. **Medya → Firestore base64** (mevcut `_compressImage` deseni; 1400px/JPEG 0.78q).
   Firebase Storage kitaplığı yüklü (crm.html:16) ama kullanılmıyor; Storage geçişi
   Blaze planı gerektirir. Spark planda kalma adına **Faz 1'de base64** ile devam;
   planın sonunda Storage'a geçiş yolu ayrıntılı verilir. Doküman limiti 1 MiB ve
   1400px/0.78q ≈ 150-250 KB base64 → güvenli bölgede.
4. **Ana model `gemini-2.5-flash`** korunur (`fsbo_engine.py:54`), fallback zinciri
   eklenir: `gemini-2.5-flash → gemini-2.5-flash-lite → gemini-3.5-flash-lite`.
   (`gemini-2.5-pro` yeni kullanıcılar için 404; 3.x ailesi güncel GA.)

---

## 2. MEVCUT DURUM ANALİZİ (Doğrulanmış Bulgular)

| Konu | Bulgu | Konum |
|---|---|---|
| Firebase SDK | v9.22.0, `firebase-storage-compat.js` **yüklü ama hiç kullanılmıyor** | crm.html:16 |
| Firebase init | projectId `nexacrm-44a49`, storageBucket `nexacrm-44a49.firebasestorage.app` | crm.html:3768-3780 |
| Firebase backend | `firebase_admin` init; **storage import edilmemiş** | app.py:9796-9828 |
| Görsel sıkıştırma | `_compressImage(imgFile, 1400, 0.78)` → dataUrl | crm.html ~4564 |
| Medya yazma deseni | `collRef.add({dataUrl, ...})` — doküman başına 1 görsel | crm.html ~4600 |
| Lead panel sekmeleri | `ozet / medya / gecmis / fsbo / chat` (leadPanelTab) | crm.html ~4406-4446 |
| Chat context | `_buildLeadContext` (5 son takip + son 8 mesaj + notlar) | crm.html 5562-5587 |
| CRM chat API | `POST /api/crm/chat` — auth'suz, system_instruction + context | app.py 13192-13277 |
| AI görsel API | `POST /api/ai/analyze` | app.py 12862-12879 |
| FSBO görsel API | `POST /api/fsbo/analyze` (8 görsel limiti, multimodal REST) | app.py 13018-13061 |
| Auth | `_require_admin(request)`: Firebase ID token doğrulama | app.py:10779 |
| Gemini client | `google-genai 0.3.0`, `types.Part.from_bytes` deseni | ai_listing.py |
| Gemini model | `GEMINI_MODEL = "gemini-2.5-flash"` | fsbo_engine.py:54 |
| Tesseract | Binary kurulu, **pip paketi (pytesseract) eksik** → `_TESSERACT=False` | app.py:1958-2022 |
| OCR kullanımı | `_psi_api_extract_description` tek Tesseract kullanımı — şu an çalışmıyor | app.py:1958-2022 |
| Bağımlılıklar | requirements.txt: **reportlab, Pillow, pytesseract YOK** | requirements.txt |
| Firestore doküman limiti | 1 MiB; base64 +%33; 1400px/0.78q görsel ≈ 150-250 KB base64 → OK | — |
| Depolama | Spark 1 GiB Firestore + 5 GB Storage (bedava) | — |

**Firestore mevcut şema:** `users/{uid}/contacts/{id}` (üst dökümanda portföy bilgisi),
alt koleksiyonlar `screenshots`, `ai_data`; ayrıca `reminders`, `followups`; web tarafı
`leads/{id}` + `events`; `buyers`, `buyer_matches`, `office_scans`, `scanned_listings`,
`ai_analyses`. Yeni özellik **contacts altına 3 yeni alt koleksiyon** ekleyecek (Bölüm 4).

---

## 3. MİMARİ VİZYON

```
┌──────────────────────────── templates/crm.html (Vue3) ────────────────────────────┐
│  Lead Detay Paneli → YENİ SEKME "İlerleme" (leadPanelTab = "portfoy")            │
│   ├─ Medya grid: yükle (input multiple) → _compressImage → Firestore              │
│   ├─ Not akışı: zaman çizelgesi + aşama seçici                                    │
│   ├─ "İlerleme Raporu Oluştur" → POST /api/portfolio/report → tam ekran modal     │
│   │    (aşama: analiz → OCR → rapor üret → PDF hazır → indir)                     │
│   └─ Chatbot paneli → POST /api/portfolio/chat (portföy bağlamlı)                 │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│  app.py (mevcut)                                                                  │
│   ├─ _require_admin (10779) — tüm yeni route'larda                              │
│   ├─ firebase db takma adı (db.collection)                                       │
│   └─ YENİ route sarmalayıcılarım (thin wrapper)                                  │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│  portfolio_progress.py (YENİ MODÜL — ai_listing/fsbo_engine deseni)              │
│   ├─ ocr:  Görsel(ler) → Gemini vision → {ocr_text, structural, viz, kanitlar}   │
│   ├─ analiz: medya + notlar + lead verisi → ilerleme durumu + KPI + risk + aksiyon│
│   ├─ rapor: analiz + görseller → Markdown gövde (bodyMd, kaydedilir)             │
│   ├─ pdf:  bodyMd + görseller → ReportLab PDF (BytesIO)                          │
│   └─ chat: lead ctx + OCR metinleri + son rapor → sohbet (portföy bağlamlı)      │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                    Firestore (nexacrm-44a49) — yeni alt koleksiyonlar
                    users/{uid}/contacts/{id}/portfolio_media|_notes|_reports
```

**Akış şeması — "Rapor Oluştur" butonu:**

```
Kullanıcı butona basar
  → crm.html: mevcut medya + notlar + lead özeti toplanır
  → POST /api/portfolio/report {contactId, userId, leadId?, allMedia?}
  → portfolio_progress.analyze: (a) Gemini vision OCR her görsel
                                  (b) durum analizi (hedef, yapılan, eksik)
                                  (c) KPI hesabı + risk + aksiyon listesi
  → bodyMd (Markdown) üretilir → Firestore reports alt koleksiyonuna yazılır
  → PDF ReportLab ile üretilir → yanıt {reportId, pdfBase64?, bodyMd}
  → crm.html modal: analiz özeti (ökonomik metin) + İndir butonu (base64 → blob → a[download])
  → PDF: Kapak → İletişim → Eksekütif Özet → Ne Yaptık (OCR kanıt) →
         Durum görselleştirme (progress bar, doughnut) → Görsel galeri →
         Riskler → KPI Tablosu → Aksiyon Planı (nasıl devam etmeliyiz) → Kapanış
```

---

## 4. FIRESTORE VERİ MODELİ (Yeni Alt Koleksiyonlar)

Kitap böyle kaldı: `screenshots` deseni (doküman başına 1 görsel). Tüm yazma işlemleri
**frontend'den** (Vue3 + Firebase SDK) yapılır; backend sadece okur/analiz eder
(madde 4.5'te is_web ikiz yazma notu).

### 4.1 `users/{uid}/contacts/{contactId}/portfolio_media` (her görsel 1 doküman)

| Alan | Tip | Açıklama |
|---|---|---|
| dataUrl | string | Sıkıştırılmış base64 (1400px/0.78 — mevcut `_compressImage`) |
| name | string | Orijinal dosya adı |
| mimeType | string | image/jpeg, image/png, image/webp |
| sizeBytes | number | Orijinal dosya boyutu (format: KB gösterilecek) |
| createdAt | timestamp | Yükleme zamanı (sıralama anahtarı) |
| stage | string | Çekildiği aşama etiketi: `insaat`, `temel`, `kaba`, `ince`, `teslim`, `belirsiz` |
| caption | string | Kullanıcının opsiyonel açıklaması |
| ocrText | string | Gemini OCR sonucu (üretildikten sonra eklenir) |
| ocrStatus | string | `pending` / `done` / `failed` |
| ocrModel | string | Hangi fallback modeli kullanıldı (debug) |
| analyzedAt | timestamp | OCR zamanı |
| thumbDataUrl | string (ops) | 320px thumbnail (galeri hızı için, opsiyonel Faz 2) |

> Doküman sınırı: 1 MiB. 1400px/0.78 ≈ 150-250 KB base64 → güvenli. Anlık toplu
> OCR'da 8 görsel / çağrı (fsbo deseni) → liste sorgusu 7-8 görsel turunda.

### 4.2 `users/{uid}/contacts/{contactId}/portfolio_notes` (zaman çizelgesi)

| Alan | Tip | Açıklama |
|---|---|---|
| text | string | Not içeriği (max ~2000 karakter, UI'da sınırlanır) |
| type | string | `note` (kullanıcı), `stage` (aşama değişikliği), `system` (AI analiz özeti) |
| stage | string | Notun bağlı olduğu aşama etiketi (ops) |
| refMediaIds | array<string> | Nottaki görsellere gönderme (ops) |
| createdAt | timestamp | Sıralama anahtarı |

### 4.3 `users/{uid}/contacts/{contactId}/portfolio_reports` (rapor geçmişi)

| Alan | Tip | Açıklama |
|---|---|---|
| status | string | `pending` → `done` / `failed` (modalda canlı gösterilir) |
| bodyMd | string | Tam Markdown gövde (yeniden PDF üretimi için saklanır) |
| meta | map | {mediaCount, noteCount, leadTitle, totalTokens, elapsedSec, modelChain} |
| pdfBase64 | string (ops) | PDF gövdesi (< 800 KB ise; aşarsa yeniden üretilebilir kuralı) |
| pdfUrl | string (ops) | Faz 2'de Storage'a kopyalanırsa |
| createdAt | timestamp | Raport tarihi |
| modelVersion | string | Hangi model zinciri (ör. `gemini-2.5-flash`) |

### 4.4 `users/{uid}/contacts/{contactId}/ai_data` kullanımı

Mevcut `ai_data` alt koleksiyonu isteğe bağlı sohbet geçmişi için korunur:
`{role: 'user'|'assistant', content, ts}` — portföy sohbeti `portfolioChatMessages`
alanıyla ayırt edilir (ya da `type: 'portfolio'`). En son N=10 mesaj `_buildPortfolioContext`
ile backend'e gider. (Mevcut /api/crm/chat deseni: mesaj geçmişi frontend'de tutulur,
backend'e context olarak gönderilir — aynı desen.)

### 4.5 Web tarafı (is_web) ikiz yazma

Mevcut desen: `is_web` → `leads/{id}` özel koleksiyonları (`portfolio_*` ya da tek
dokümanda `portfolioMedia/portfolioNotes` array'leri). **Faz 3 kararı:** İlk sürümde
yalnızca `contacts` yolu desteklenir; `leads` ikiz yolu "Faz 6 (isteğe bağlı)" olarak
planlanır — mevcut kodda leads ve contacts yazma yardımcıları ayrı (4380/5325).

---

## 5. BACKEND MİMARİSİ — `portfolio_progress.py` (Yeni Modül)

Konum: repo kökü (ai_listing.py, fsbo_engine.py ile aynı seviye).
İçe aktarım stili: `ai_listing.py` gibi — app.py'nin `firebase_admin` singleton'ına
**gerek yok**, tüm Firestore okumaları route içinde `db`'den yapılıp modüle **veri
olarak** geçilir (fsbo_engine'nin db bağımsızlığı deseni).

### 5.1 Fonksiyon imzaları

```python
# --- OCR: Gemini vision (fsbo_engine._call_gemini_multimodal deseni) ---
def ocr_images(api_key: str, images: list[dict], model: str = GEMINI_MODEL
              ) -> list[dict]:
    """images: [{'mime_type','data_b64'}] (en fazla 8 / çağrı)
       Dönüş: [{added_hours? hayır} {mediaKey, ocr_text, yapi, bulgular, hata?}]
       İç: REST POST https://generativelanguage.googleapis.com/v1beta/models/...
           contents: [{inline_data:{mime_type,data}}]
           generationConfig: temperature 0.2, maxOutputTokens 4096
       Fallback zinciri: GEMINI_MODEL → "gemini-2.5-flash-lite" → "gemini-3.5-flash-lite"
       Retry: 429 → 3 sn bekle (backoff); 404 → sonraki model; 500 → 2 deneme"""

# --- Analiz: yapılanlar + kalanlar + risk + aksiyon ---
def analyze_portfolio(api_key: str, lead_knowledge: dict, ocr_results: list[dict],
                      notes: list[dict], model: str = GEMINI_MODEL) -> dict:
    """Dönüş (JSON mode): {
        'ozet': str, 'ne_yaptik': [str], 'ne_yapilmadi': [str],
        'kpi': {'suanki_durum_pct', 'tamamlanan_adimlar', 'kalan_adimlar', ...},
        'riskler': [{'risk','seviye':'YUKSEK|ORTA|DUSUK','cozum'}],
        'aksiyonlar': [{'yapilacak','aciliyet':'HEMEN|BU_HAFTA|SONRAKI_HAFTA','beklenen_sonuc'}],
        'kanit_oranlari': [{'kanit', 'goruntu_var': bool, 'aciklama'}]}"""

# --- Rapor gövdesi: Markdown ---
def build_report_body(model_output: dict, lead_knowledge: dict, media: list[dict],
                      notes: list[dict], report_id: str) -> str:
    """Bölüm başlıkları (Agent F şeması) — Bölüm 7."""

# --- PDF üretimi: ReportLab ---
def render_report_pdf(body_md: str, images: list[dict], output: BytesIO) -> None:
    """Markdown→flowable parser + kapak + doughnut + bar chart + tablo + callout."""

# --- Sohbet: portföy bağlamlı ---
def portfolio_chat_context(lead: dict, notes: list[dict], media_ocrs: list[dict],
                           last_reports: list[dict]) -> str:
    """system_instruction için metin: lead özeti + zaman çizelgesi + OCR kanıtları
       + son rapor özeti + kullanıcı talimatı (Bölüm 8)."""
```

### 5.2 app.py'ye eklenecek route sarmalayıcılar

| Route | Açıklama | Auth |
|---|---|---|
| `POST /api/portfolio/ocr` | Seçili `mediaIds`'in OCR'ı (boşsa tümü). `mediaId` → Firestore'dan `dataUrl` oku, base64'e çevir, Gemini'ya gönder, sonucu `portfolio_media/ocrText`'e geri yaz | `_require_admin` |
| `POST /api/portfolio/report` | OCR (eksikler) + analiz + Markdown + **PDF üret** → `portfolio_reports` (status: done, bodyMd, pdfBase64 ≤800KB) → `{reportId, pdfBase64?, bodyMd, analiz, meta}` | `_require_admin` |
| `GET /api/portfolio/report/<uid>/<contact_id>/<report_id>/pdf?is_web=1` | Saklı `bodyMd`'den PDF'i yeniden üret, `send_file` ile indir | `_require_admin` |
| `POST /api/portfolio/chat` | `{contactId, message, history[]}` → bağlam kur → Gemini sohbet → `{reply}`; geçmiş `ai_data`'ya (`portfolioChat`) kaydedilir | `_require_admin` |

> **Not:** Ayrı `/api/portfolio/analyze` eklenmedi — analiz `report` içinde birleşik.

> Güvenlik notları: tüm route'larda `_require_admin`; `contactId` her zaman
> `request.json['uid']` (admin token'dan alınır, client'tan değil) ile belgeli:
> `uid = firebase_auth['uid']`; Firestore okuması `db.collection('users').document(uid)...
> GEMINI_API_KEY `.env` / ortam değişkeninden MODÜL seviyesinde alınır (fsbo deseni).

### 5.3 Model fallback zinciri (modül başı)

```python
GEMINI_MODEL         = os.environ.get("PORTFOLIO_GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACKS     = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite"]
MAX_IMAGES_PER_CALL  = 8      # REST inline limit & token bütçesi
OCR_TOKEN_BUDGET     = 1024   # görsel başına ~258 token (160 token/görsel + metin)
RETRY_BACKOFF        = (2, 4, 8)  # saniye
```

---

## 6. PDF RAPOR TASARIMI (ReportLab)

**Sayfa: A4, TTF: `DejaVuSans.ttf` + `DejaVuSans-Bold.ttf`** (repo içine `static/fonts/`
kopyalanacak; Türkçe karakter güvenliği). Renk paleti: koyu lacivert `#1B2A4A`,
altın vurgu `#C9A227`, yeşil `#2E7D32`, kırmızı `#C62828`.

| # | Bölüm | Görsel öğeler |
|---|---|---|
| 0 | **Kapak** | Tam sayfa lacivert zemin, büyük başlık "İLERLEME RAPORU", portföy adı, tarih, "Nexa CRM" logosu (metin), alt bilgi |
| 1 | **İletişim / Künye** | Tablo: sahip adı, iletişim, adres/konum, aşama, görsel sayısı, rapor tarihi |
| 2 | **Eksekütif Özet** | 3-4 cümle AI özeti + "genel durum" rozeti (% tamamlanma) |
| 3 | **İlerleme Durumu** | **Doughnut chart** (tamamlandı/kalan %) + **progress bar** + adım listesi (✓/✗) |
| 4 | **Ne Yaptık (OCR Kanıtı)** | Her görsel: küçük thumbnail + OCR metni kutusu + "bulgu" rozetleri (temel atılmış, kaba inşaat...) |
| 5 | **Görsel Galeri** | 3x3 ızgara (240px thumbnail, altyazı + tarih) |
| 6 | **Risk Analizi** | 3 sütunlu tablo (risk / seviye / çözüm), seviye renk kodlu |
| 7 | **KPI Tablosu** | Tablo: tamamlanan adım, kalan adım, durum %, görsel kanıt, ortalama ilerleme |
| 8 | **Aksiyon Planı** | Zaman çizelgesi: HEMEN / BU HAFTA / SONRAKİ HAFTA satırları, her biri: eylem + beklenen sonuç |
| 9 | **Kapanış** | "Sonraki rapor: N gün sonra" + imza kutusu (metin) |

**ReportLab API özeti (canlı kod şablonu):**

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, KeepTogether)
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie

doc = SimpleDocTemplate(output, pagesize=A4,
    rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
styles = get_styles()          # DejaVu kayıtlı, Türkçe ekstra stiller
story = [Section('KAPAK', ...), PageBreak(), Section('OZET', ...), ...]
doc.build(story, onFirstPage=draw_cover, onLaterPages=draw_footer)
# Doughnut: Pie() çift halka (secondHasValues) ya da iki Pie üst üste
# Progress bar: RoundedRect çizim (graphics.shapes.RoundedRect + fillRect)
```

---

## 7. RAPOR BÖLÜM YAPISI (Markdown bodyMd — saklanır, yeniden üretilir)

```
# İLERLEME RAPORU — {portföy adı}
> Tarih: ... | Görsel: N | Not: M | Model: gemini-2.5-flash

## 1. Yönetici Özeti
{AI özeti}

## 2. Mevcut Durum
- Genel ilerleme: %X
- Tamamlanan adımlar: A, B, C
- Devam eden: D, E
- Henüz başlanmamış: F, G

## 3. Ne Yaptık (Kanıtlarla)
### Görsel 1 — {açıklama} ({tarih})
OCR: {metin} → Bulgular: {liste}
### Görsel 2 — ...

## 4. Eksikler ve Dikkat Edilecekler
- {AI tespiti}

## 5. Riskler
| Risk | Seviye | Çözüm |
|---|---|---|

## 6. KPI
| Gösterge | Değer |

## 7. Aksiyon Planı
### Hemen
- ...
### Bu Hafta
- ...
### Sonraki Hafta
- ...

## 8. Kapanış
{öneri + sonraki kontrol önerisi}
```

---

## 8. CHATBOT TASARIMI

**Endpoint:** `POST /api/portfolio/chat` → yeni `portfolio_chat_context()` →
`/api/crm/chat` ile aynı mekanik (system_instruction + history + user message).

**System instruction (Türkçe) — taşınan içerik:**
- Rol: "Sen Nexa CRM'in Portföy İlerleme Danışmanısın. Sadece verilen bilgilerden konuş."
- Portföy künyesi: ad, sahip, konum, aşama, hedef
- Zaman çizelgesi: son 15 not (tarih + metin)
- Kanıt görselleri: son OCR metinleri (kısa listeler)
- Son rapor özeti (varsa): 2-3 cümle + aksiyon listenin ilk 3'ü
- Kural: "Görselde olmayan hiçbir şeyi doğrulama; emin değilsen 'görselden doğrulayamıyorum' de"

**Öneri kategorileri (Agent F):**
1. Takibi gereken müşteri (randevu hatırlat, beklemede olan karar)
2. Kanal önerisi (hangi platformda öne çıkar)
3. Fiyat pozisyonlaması (kıyas, pazarlık senaryosu)
4. Acil aksiyon (yarın yapılacak)
5. Risk uyarısı (görseldeki sorun, eksik kanıt)
6. Sonraki hafta planı
7. Görsel eksikliği (hangi aşamanın fotoğrafı yok)
8. Rapor taslağı (hızlı özet çıktısı)

**Değerlendirme KPI önerileri (Agent F — PDF Bölüm 7 tablosuna girer):**
- Tamamlanan adım sayısı / toplam adım
- Görsel kanıt sayısı + aşama kapsama %'si
- Son 30 gün not sıklığı (aktivite)
- Risk sayısı (YÜKSEK ağırlıklı skor)
- Lansman hazırlığı %'si

---

## 9. FRONTEND DEĞİŞİKLİKLERİ (templates/crm.html)

### 9.1 Yeni sekme — "İlerleme" (Ana entegrasyon)

| Değişiklik | Konum (mevcut satır) | Detay |
|---|---|---|
| `leadPanelTab` değerlerine `'portfoy'` ekle | ~4406-4446 | Sekme başlığı "İlerleme", ikon: `📈` |
| Sekme içeriği `<template v-if="leadPanelTab==='portfoy'">` | 4446 sonrası | `PortfolioPanel` bileşeni |
| `_buildLeadContext`'e portföy verisi eklensin | 5562-5587 | `portfolioNotes`, `portfolioMedia` alanları (chat context zenginleşir) |
| Medya yükleme: `accept="image/*" multiple` input | 2746 deseni | `change` → `_compressImage` döngüsü → `portfolio_media` add (4564/4600 deseni) |
| Aşama seçici | panel | `insaat/temel/kaba/ince/teslim/belirsiz` chip'leri |
| Not ekleme + zaman çizelgesi | panel | `portfolio_notes` add + ters kronolojik liste |
| Chatbot paneli | panel | /api/portfolio/chat; gelen `reply` Markdown render (mevcut chat render deseni) |
| "İlerleme Raporu Oluştur" butonu | panel üstü | Modal açar (9.2) |
| Rapor geçmişi listesi | panel alt | `portfolio_reports` listele; "İndir" ve "Yeniden İndir" butonları |

### 9.2 Rapor üretim modalı (durum akışı)

```
adım 1: 'analiz'   — "Görseller analiz ediliyor (OCR)..." (toplam N görsel, sayaç)
adım 2: 'rapor'    — "Rapor yazılıyor..."
adım 3: 'pdf'      — "PDF hazırlanıyor..."
adım 4: 'hazir'    — Özet kutucuklar: % durum, ne yaptık (ilk 3), risk (ilk 3)
                     + ✅ "İndir" (pdfBase64 → blob → a[download]) + "Kapat"
hata:   'hata'     — hata + "Tekrar Dene"
```
Modal kapatılınca kanal bozulmaz: rapor `portfolio_reports`'a kaydedilmiş olur,
geçmiş listesinden tekrar indirilebilir. (Devam: backend ne kadar sürer? ~8 görsel:
OCR turları ~4x3 sn + analiz ~8 sn + PDF ~2 sn → **~30-45 sn**; modal sabır metni içerir.)

### 9.3 Yardımcı fonksiyonlar (yeniden kullanım envanteri)

- `_compressImage(f, 1400, 0.78)` — zaten var, aynen kullan (4564 deseni)
- `db.collection('users').doc(uid).collection('contacts').doc(id).collection('portfolio_media')` — yazma yardımcısı `addPortfolioMedia(contact, files[])`
- `toBase64(pdfBase64)` → `data:application/pdf;base64,...` → anchor download
- Chat `history` kalıbı mevcut `/api/crm/chat`'ten kopyalanır (son 10 mesaj)

---

## 10. PROMPT ŞABLONLARI

### 10.1 OCR (görsel başına, vision)

```
Bu görsel bir gayrimenkul projesinin ilerleme fotoğrafıdır. Görevin:
1. Görselde gördüğün TÜM yazıları Türkçe olarak OCR et (tabela, levha, belge, el yazısı).
2. İnşaat/durum analizi: yapı aşaması (TEMEL / KABA / İNCE / TESLİM / BELİRSİZ),
   tamamlanmış işler, devam eden işler, görseldeki olası sorunlar (çatlak, eksik izolasyon vs.).
3. Çıktı SADECE JSON:
   {"ocr_metni":"...","asama":"...","tamamlanan_isler":[],"devam_eden_isler":[],
    "sorunlar":[{"sorun":"...","onem":"yuksek|orta|dusuk"}]}
```

### 10.2 Analiz (özet + eksik + aksiyon)

```
Sen bir gayrimenkul proje danışmanısın. {lead künyesi} için elimizde şunlar var:
- Notlar (zaman çizelgesi): {notlar}
- Görsel OCR bulguları: {bulgular}
Görev: (1) ne yaptık listesi (2) ne yapılmadı listesi (3) riskler
(4) 7 günlük aksiyon planı (HEMEN/BU HAFTA/SONRAKI HAFTA) (5) % tamamlanma.
Kurallar: sadece verdiğim veriden konuş, tahmin etme, eksik ise "kanıt yok" de.
Çıktı JSON: {... Bölüm 5.1 şeması ...}
```

### 10.3 Sohbet system_instruction — Bölüm 8'de verildi.

---

## 11. HATA YÖNETİMİ & GÜVENLİK

| Konu | Kural |
|---|---|
| Auth | Tüm yeni route'larda `_require_admin(request)`; `uid` yalnızca token'dan |
| Firestore izolasyonu | `db.collection('users').document(uid)...` — başka kullanıcı verisi okunamaz |
| API key | `GEMINI_API_KEY` ortam/.env; repo'ya asla yazma |
| Rate limit | Yeni route'lara `@limiter.limit("10 per minute")` (Flask-Limiter zaten var) |
| 429/404 | Gemini fallback zinciri + backoff (2/4/8 sn); 2 deneme hakkı |
| Görsel bütçesi | OCR: max 8 görsel/çağrı; rapor: max 24 görsel (3 tur) — üstünde uyar |
| PDF boyutu | > 800 KB → pdfBase64 saklanmaz, yeniden üretilebilir (bodyMd korunur) |
| DataUrl doğrulama | `data:image/(jpeg|png|webp);base64,` prefix'ine bak, aksi halde reddet |
| Frontend | Birden fazla çift tıklama koruması (isGenerating flag) |
| Loglama | `app.logger` + `meta.elapsedSec` (debug yoksa sessiz) |

---

## 12. UYGULAMA FAZLARI (Kod Yazım Sırası)

### Faz 0 — Bağımlılıklar (5 dk) ✅ TAMAMLANDI
```
pip install reportlab pillow
# requirements.txt'e ekle:
reportlab>=4.0
Pillow>=10.0
```
- `static/fonts/DejaVuSans.ttf` + `DejaVuSans-Bold.ttf` repo'ya kopyalandı
  (**Not:** GitHub/CDN indirilemediği için ReportLab paketindeki Bitstream Vera
  fontları kullanıldı — `DejaVu` adıyla kaydedildi; Türkçe tam destek doğrulandı).

### Faz 1 — `portfolio_progress.py` iskelet + OCR (2-3 saat)
- `ocr_images()`: REST çağrısı + fallback + retry (`_call_gemini_multimodal` deseni)
- Test: `python -c` ile 1 fotoğraf → JSON çıktı
- `analyze_portfolio()` + `build_report_body()`
- Test: sahte lead dict ile tam pipeline

### Faz 2 — PDF üretimi (3-4 saat)
- `render_report_pdf()`: kapak, stiller, doughnut, progress, tablo, galeri
- Test: `python scripts/test_pdf.py` → `test_rapor.pdf`'i aç, Türkçe karakter + görseller doğrula

### Faz 3 — app.py route'ları (1-2 saat)
- 5 route (Bölüm 5.2) + `_require_admin` + limiter + izolasyon
- Test: curl/permission token ile 200/401/403 matrisi

### Faz 4 — crm.html UI (3-4 saat)
- Sekme + panel bileşeni + medya yükleme + not akışı + modal + chatbot + geçmiş
- Test: elle E2E — yükle → OCR → rapor → indir → sohbet → ikinci PDF

### Faz 5 — Entegrasyon Testi + Deploy (1-2 saat)
- Smoke test (mevcut `/api/projects` dahil) — garanti: diğer özellikler bozulmasın
- Push (REST API ile), Render deploy, canlı kontrol

**Toplam efor tahmini: ~12-15 saat (tek seansta 1-2 gün)**

---

## 13. MALİYET TABLOSU (Gemini kullanımı)

| Kalem | Miktar | Token/çıktı tahmini | Maliyet (yaklaşık) |
|---|---|---|---|
| OCR (8 görsel, vision) | 8 görsel, ~1150 token girdi | ~4 Kop çıktı | ~$0.01 |
| Analiz (metin) | ~8-12 Kop girdi | ~3-4 Kop çıktı | ~$0.005 |
| Sohbet (ortalama tur) | ~5-8 Kop girdi | ~2 Kop çıktı | ~$0.002 |
| **1 tam rapor turu** | — | — | **~$0.02** |
| Aylık 50 rapor + sohbet | — | — | **~$2-4** |

> Spark planda Firestore yazma/okuma bedava kotası dahil; depolama: medyada
> 1400px/0.78 → ~200 KB base64 → 1 GiB ≈ ~4.000-5.000 görsel. 12-15 MB liste getirme
> limiti: `portfolio_media` listesinde thumbnail getirme (Faz 2 opsiyonu) gerekirse.

---

## 14. RİSKLER VE AÇIK SORULAR

### Riskler
| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| `gemini-2.5-flash` yeni anahtarda 404 | Orta | Yüksek | Fallback zinciri hazır (3.5-flash-lite) |
| 1 MiB doküman limiti aşımı (çok büyük boyutlu görseller) | Düşük | Orta | 1400px/0.78 sabit; yüklemede boyut uyarısı |
| Render bellek: 24 görsel PDF | Düşük | Orta | Görseller raster thumbnail'e çekilir (IPTC ~300px) |
| Rapor süresi 45 sn → tarayıcı zaman aşımı | Orta | Orta | Modal "sürüyor" durumu; `status:'pending'` → poll yerine tek yanıt (45 sn < Render 60 sn limit) |
| Türkçe font eksik → PDF bozuk | Düşük | Yüksek | DejaVu TTF repo'ya sabitlenir, Faz 2'de görsel doğrulama |
| Kullanıcı testinde CRON/APIScheduler etkilenmesi | Düşük | Yüksek | Sadece yeni route ekle; mevcut koda dokunma |

### Açık sorular (uygulamaya başlamadan onayını isterim)
1. **OCR ne zaman?** Sadece "Rapor Oluştur"da mı, yoksa medya yüklenir yüklenmez otomatik mi (arka planda `ocrStatus: pending`) olsun? *(Öneri: yüklemede otomatik, 10 sn gecikmeli; raporda kesinleştir)*
2. **Rapor sırasında OCR** — tüm görseller mi, yalnızca `ocrStatus != done` olanlar mı? *(Öneri: sadece eksikler, hız kazanır)*
3. **Aşama etiketleri** sabit liste mi (`insaat/temel/kaba/ince/teslim/belirsiz`) istersin, yoksa serbest metin mi?
4. **Rapor dili/tonu** — tamamen Türkçe, profesyonel mi; ingilizce şablon gerekir mi?
5. **Chatbot mesaj geçmişi** Firestore'a kaydedilsin mi (`ai_data`'ya), yoksa oturum içi mi kalsın? *(Öneri: kaydedilsin — raporun "not akışı"na düşer)*
6. **Storage'ın Blaze planına geçiş** gerekli mi (Faz 2'de thumbnail + Storage'a yedek) yoksa base64 yeterli mi? *(Öneri: ilk sürüm base64, Spark'ta kal)*
7. 3/ klasörüyle **entegrasyon**: proje portföyünde "3/" projelerinin de bu rapor mekanizmasına bağlanması istenir mi? *(Öneri: hayır — ayrı tutalım, veri modeli çakışmasın)*

---

## 15. BAĞIMLILIKLAR / KAYNAK DOSYALAR (hızlı başvuru)

- `fsbo_engine.py` — `_call_gemini_multimodal` (220-350), `_build_prompt` (74-217), `GEMINI_MODEL` (54)
- `ai_listing.py` — `types.Part.from_bytes`, `_parse_uploaded`, `_download_image_b64`
- `app.py` — `_require_admin` (10779), `/api/crm/chat` (13192-13277), `/api/ai/analyze` (12862), `/api/fsbo/analyze` (13018), firebase init (9796-9828), OCR kırık desen (1958-2022)
- `templates/crm.html` — init (3768-3780), input file (2746), `_compressImage` (~4564), media add (~4600), panel sekmeler (4406-4446), `_buildLeadContext` (5562-5587), storage-compat (16)
- `requirements.txt` — reportlab>=4.0, Pillow>=10.0 eklenecek
- Model dokümanı: https://ai.google.dev/gemini-api/docs/models