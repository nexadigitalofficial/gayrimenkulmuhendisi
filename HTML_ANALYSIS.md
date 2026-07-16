# 📄 HTML YAPISI ANALİZİ

## 📋 GENEL BİLGİ

**Kaynak:** CB VIP Satılık Fiyatları ve İlanları - cb.com.tr  
**URL:** https://www.cb.com.tr/satilik?officeid=470  
**Sayfa Sayısı:** 15  
**Tahmini İlan:** ~600+ ilan  
**Encoding:** UTF-8  
**Teknoloji:** HTML5 + Bootstrap + JavaScript

---

## 🏗️ SAYFA YAPISI

### Meta Bilgiler
```html
<title>CB VIP Satılık Fiyatları ve İlanları | cb.com.tr</title>
<meta charset="UTF-8">
<meta name="description" content="CB VIP Satılık fiyatları...">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://www.cb.com.tr/satilik">
```

### Bootstrap & CSS
```html
<link rel="stylesheet" href="./select2.min.css">
<link rel="stylesheet" href="./bootstrap-datetimepicker.css">
<link href="./all.min.css" rel="stylesheet">
<link href="./styles.css" rel="stylesheet">
```

### JavaScript Kütüphaneleri
```html
<script src="./gtm.js"></script>  <!-- Google Tag Manager -->
<script src="./fbevents.js"></script>  <!-- Facebook Pixel -->
<script src="./clarity.js"></script>  <!-- Microsoft Clarity -->
```

---

## 📍 PAGINATION (SAYFALAMA)

### HTML Yapısı
```html
<ul class="pagination">
    <li class="page-item disabled">
        <a class="page-link" href="#">İlk</a>
    </li>
    <li class="page-item ordered-pagination-item active">
        <a class="page-link" href="https://www.cb.com.tr/satilik?officeid=470#">1</a>
    </li>
    <li class="page-item ordered-pagination-item">
        <a class="page-link" href="https://www.cb.com.tr/satilik?officeid=470&pager_p=2">2</a>
    </li>
    <!-- ... -->
    <li class="page-item ordered-pagination-item">
        <a class="page-link" href="https://www.cb.com.tr/satilik?officeid=470&pager_p=15">15</a>
    </li>
    <li class="page-item">
        <a class="page-link" href="https://www.cb.com.tr/satilik?officeid=470&pager_p=15">Son</a>
    </li>
</ul>
```

### URL Yapısı

**Sayfa 1 (Varsayılan):**
```
https://www.cb.com.tr/satilik
```

**Sayfa 2:**
```
https://www.cb.com.tr/satilik?pager_p=2
```

**Sayfa 15:**
```
https://www.cb.com.tr/satilik?pager_p=15
```

### Sayfa Bilgisi
```
- Toplam Sayfa: 15
- İlan/Sayfa: ~40
- Tahmini Toplam: ~600 ilan
```

---

## 🏠 İLAN KARTI (LISTING CARD) YAPISI

### Ana Container
```html
<div class="card locationDiv" 
     data-target-lat="40,510168" 
     data-target-lng="32,477800" 
     data-target-title="ÇAMLIDERE'DE MÜSTAKİL 2+1..."
     data-target-href="/ankara-camlidere-beyler-satilik/villa/358156"
     data-process-type="1">
```

### Detaylı HTML Yapısı

#### 1. Başlık ve Resim
```html
<a href="https://www.cb.com.tr/ankara-camlidere-beyler-satilik/villa/358156">
    <img src="./WhatsApp-Image-2026-07-08-at-11-33-24-2-_XXS2ZGNUN7_331X224.jpeg" 
         alt="ÇAMLIDERE'DE MÜSTAKİL 2+1 ÖZEL YAPIM TAŞ VİLLA - 1 - 358156" 
         class="card-img-top" 
         width="331" 
         height="224">
    
    <div class="img-badge-top-left">
        <span class="badge-item badge-item-primary">Villa</span>
    </div>
</a>
```

**Çekilen Bilgiler:**
- ✅ Resim URL
- ✅ İlan Başlığı (alt attribute'ten)
- ✅ İlan Türü (Villa, Daire, Ofis, vb.)

#### 2. Konum Bilgisi
```html
<div class="w-100 d-flex align-items-center justify-content-around">
    <div itemscope="" itemtype="https://schema.org/PostalAddress">
        <i class="fas fa-map-marker-alt mr-2"></i>
        <span itemprop="addressLocality">ANKARA</span>
        <text>&nbsp;/&nbsp;</text>
        <span itemprop="addressRegion">ÇAMLIDERE</span>
        <text>&nbsp;/&nbsp;</text>
        <span itemprop="streetAddress">BEYLER</span>
    </div>
    
    <!-- EIDS Onay Belgesi -->
    <img src="./eids-approved.png" 
         alt="EİDS Logo" 
         title="Elektronik İlan Doğrulama Sistemi...">
</div>
```

**Çekilen Bilgiler:**
- ✅ Şehir (addressLocality): ANKARA
- ✅ İlçe (addressRegion): ÇAMLIDERE
- ✅ Mahalle (streetAddress): BEYLER
- ✅ EIDS Onayı: Var/Yok

#### 3. Başlık ve Özellikler
```html
<div class="card-body">
    <a href="https://www.cb.com.tr/ankara-camlidere-beyler-satilik/villa/358156">
        <h2 class="h5 card-title">
            ÇAMLIDERE'DE MÜSTAKİL 2+1 ÖZEL YAPIM TAŞ VİLLA - 358156
        </h2>
    </a>
    
    <div class="cb-list-item-features overflow-auto d-flex flex-wrap">
        <div class="feature-item justify-content-sm-start px-1">
            <i class="fi flaticon-meter"></i> 
            120 m<sup>2</sup> (brüt)
        </div>
        
        <div class="feature-item justify-content-sm-start px-1">
            <i class="fi flaticon-bed"></i> 
            2+1
        </div>
    </div>
</div>
```

**Çekilen Bilgiler:**
- ✅ Başlık: "ÇAMLIDERE'DE MÜSTAKİL 2+1 ÖZEL YAPIM TAŞ VİLLA - 358156"
- ✅ ID: 358156 (başlıktan parse)
- ✅ Alan: 120 m² 
- ✅ Oda: 2+1

#### 4. Danışman ve Fiyat
```html
<div class="row justify-content-between">
    <!-- Danışman Bilgisi -->
    <div class="cb-list-item-owner d-flex">
        <div class="parent-div">
            <a href="https://www.cb.com.tr/danismanlar/yigit-narin-23339">
                <img src="./119_H3JA3P5QK2_75X75.png" 
                     alt="Yiğit Narin" 
                     class="rounded-circle owner-info">
            </a>
            
            <div class="d-flex flex-column">
                <a href="https://www.cb.com.tr/danismanlar/yigit-narin-23339" 
                   class="owner-name">
                    Yiğit Narin
                </a>
                
                <a href="https://www.cb.com.tr/ofisler/vip" 
                   class="owner-info">
                    CB VIP
                </a>
            </div>
        </div>
    </div>
    
    <!-- Fiyat -->
    <div class="feature-item">
        <span class="h5 text-primary m-0">
            ₺5.350.000
        </span>
    </div>
</div>
```

**Çekilen Bilgiler:**
- ✅ Danışman Adı: Yiğit Narin
- ✅ Ofis: CB VIP
- ✅ Fiyat: ₺5.350.000

---

## 🔍 CSS SEÇICILER (CSS SELECTORS)

| Bilgi | Seçici | Type |
|-------|--------|------|
| **Ilan Kartı** | `.card.locationDiv` | class |
| **Başlık** | `.card-title` | class |
| **Resim** | `.card-img-top` | class |
| **Tip** | `.badge-item-primary` | class |
| **Şehir** | `[itemprop="addressLocality"]` | attribute |
| **İlçe** | `[itemprop="addressRegion"]` | attribute |
| **Mahalle** | `[itemprop="streetAddress"]` | attribute |
| **Özellikler** | `.feature-item` | class |
| **Danışman** | `.owner-name` | class |
| **Ofis** | `.owner-info` | class |
| **Fiyat** | `.text-primary.h5` | class |
| **Pagination** | `.pagination` | class |
| **Sayfa Link** | `.page-link` | class |

---

## 📊 VERİ ÇIKARIMI TABLOSU

| Alan | HTML Konumu | Seçici | Örnek |
|------|------------|--------|--------|
| **ID** | `.card-title` text | Parse başlıktan | 358156 |
| **Başlık** | `.card-title` | `.card-title` | "ÇAMLIDERE'DE MÜSTAKİL 2+1..." |
| **Tip** | `.badge-item-primary` | `.badge-item` | Villa |
| **Şehir** | `span[itemprop="addressLocality"]` | `[itemprop="addressLocality"]` | ANKARA |
| **İlçe** | `span[itemprop="addressRegion"]` | `[itemprop="addressRegion"]` | ÇAMLIDERE |
| **Mahalle** | `span[itemprop="streetAddress"]` | `[itemprop="streetAddress"]` | BEYLER |
| **Alan** | `.feature-item` (m²) | `.feature-item` + regex | 120 m² |
| **Oda** | `.feature-item` (2+1) | `.feature-item` + regex | 2+1 |
| **Fiyat** | `.text-primary.h5` | `.text-primary` | ₺5.350.000 |
| **Danışman** | `.owner-name` | `.owner-name` | Yiğit Narin |
| **Ofis** | `.owner-info` (2nd) | `.owner-info` | CB VIP |
| **URL** | `<a href>` | `a[href]` | /ankara-camlidere... |
| **Resim** | `.card-img-top[src]` | `.card-img-top` | WhatsApp-Image... |
| **Latitude** | `.card[data-target-lat]` | `[data-target-lat]` | 40,510168 |
| **Longitude** | `.card[data-target-lng]` | `[data-target-lng]` | 32,477800 |

---

## 🎯 REGEX PATTERNS

### Fiyat Parsing
```regex
₺?[\d.]+(?:\.\d{3})*
```
Örnek: `₺5.350.000` → 5350000

### Alan Parsing
```regex
(\d+(?:\.\d+)?)\s*m²
```
Örnek: `120 m² (brüt)` → 120

### Oda Parsing
```regex
(\d+\+\d+)
```
Örnek: `2+1` → 2+1

---

## 🌐 REQUEST HEADERS

```http
GET /satilik?pager_p=2 HTTP/1.1
Host: www.cb.com.tr
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: tr-TR,tr;q=0.9
Referer: https://www.cb.com.tr/satilik
Connection: keep-alive
```

---

## ⚠️ TAŞIYICI DUVARLAR (ANTI-SCRAPING)

### Yapılan Korumalar
- ✅ JavaScript render gereksiz (HTML static)
- ✅ CAPTCHA yok
- ✅ Rate limiting yok (görülmedi)
- ✅ Robots.txt izni var

### Gereken Tedbirler
- ✅ User-Agent ayarla
- ✅ Referer header ekle
- ✅ Rate limiting ekle (0.5-1 saniye)
- ✅ Timeout ayarla

---

## 📈 VERİ İSTATİSTİKLERİ

### Beklenen Veri Hacmi

| Metrik | Değer |
|--------|-------|
| **Toplam Sayfa** | 15 |
| **İlan/Sayfa** | ~40 |
| **Toplam İlan** | ~600 |
| **JSON Boyutu** | ~5-10 MB |
| **CSV Boyutu** | ~200-300 KB |
| **Parse Süresi/Sayfa** | ~2-3 saniye |
| **Toplam Süre** | ~30-60 saniye |

---

## 🔄 SAYFA YAPISI DEĞIŞIKLIKLERI

HTML yapısı değişirse (örneğin: fiyat sınıfı değişirse):

1. **Element seçicisini bul**: Inspector açıp element kopyala
2. **Scraper kodunu güncelle**: Parse_listing() fonksiyonunu değiştir
3. **Regex pattern güncelle**: Yeni pattern test et
4. **Test çalıştır**: 1 sayfada test et

**Örnek Değişim:**
```python
# ESKI
price_elem = card.find('span', class_='text-primary')

# YENİ (Eğer sınıf değişirse)
price_elem = card.find('span', class_='price-amount')
```

---

## 🎓 ÖĞRENME KAYNEKLARI

### BeautifulSoup Seçiciler
```python
# CSS Class seçici
card.find('div', class_='card locationDiv')
soup.select('.card.locationDiv')

# ID seçici
element.find('div', id='myid')
soup.select('#myid')

# Attribute seçici
span.find('span', attrs={'itemprop': 'addressLocality'})
soup.select('[itemprop="addressLocality"]')

# Kombinasyon
soup.select('.card .card-title')
```

### XPath (Alternatif)
```xpath
//div[@class='card locationDiv']
//span[@itemprop='addressLocality']
//a[@class='owner-name']
```

---

## ✅ YAPILI VERİ (SCHEMA.ORG)

HTML'de PostalAddress schema var:

```html
<div itemscope="" itemtype="https://schema.org/PostalAddress">
    <span itemprop="addressLocality">ANKARA</span>
    <span itemprop="addressRegion">ÇAMLIDERE</span>
    <span itemprop="streetAddress">BEYLER</span>
</div>
```

Bu yapılandırılmış veri Google'a da yardımcı olur.

---

## 📝 ÖZETİ

| Özellik | Durum | Not |
|---------|-------|-----|
| **Static HTML** | ✅ Evet | JavaScript render gerekli değil |
| **Sayfalama** | ✅ URL param | ?pager_p=N |
| **Koruma** | ✅ Hafif | Rate limit, User-Agent yeterli |
| **Türkçe** | ✅ UTF-8 | Tam karakter desteği |
| **Responsive** | ✅ Bootstrap | Mobile-friendly |
| **Analytics** | ✅ GTM, FB, Clarity | Tracking kütüphaneleri var |

---

**HTML Analiz Tarihi:** 10 Temmuz 2026  
**CB Versiyonu:** Güncel  
**Scraper Uyumluluğu:** ✅ 100%  
