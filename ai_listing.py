"""
ai_listing.py — İlan URL scrape + Gemini 2.5 Flash multimodal analiz
================================================================
Desteklenen kaynaklar (doğrudan BS4 scrape):
  HepsiEmlak · Zingat · Emlakjet · cb.com.tr · Genel (OG tags)

Sahibinden (bot korumalı):
  Google PageSpeed Insights API → network-requests → shbdn.com görselleri

Fotoğraf analizi:
  Yüklenen veya scrape'den inen görüntüler Gemini Vision'a iletilir.

Kullanım (app.py):
  from ai_listing import scrape_listing, analyze_listing, ai_listing_status
================================================================
"""

from __future__ import annotations

import os
import re
import json
import time
import base64
import html as html_mod
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# Selenium opsiyonel — sadece sahibinden scrape için gerekli
try:
    from selenium import webdriver
    from selenium.webdriver import ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    _SELENIUM = True
except ImportError:
    _SELENIUM = False

# ── Konfigürasyon ─────────────────────────────────────────────────────────────
GEMINI_MODEL      = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")
SCRAPE_TIMEOUT    = 15
PAGESPEED_WEB_URL = "https://pagespeed.web.dev/?hl=tr"
DEFAULT_PS_WAIT   = 50   # saniye — sahibinden için bekleme süresi

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "DNT":             "1",
}


def ai_listing_status() -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return {"ok": bool(key), "configured": bool(key), "model": GEMINI_MODEL}


# ================================================================
# SCRAPERS
# ================================================================

# ================================================================
# SELENIUM HELPERS (Sahibinden için)
# ================================================================

def _make_chrome(headless: bool = True) -> "webdriver.Chrome":
    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")

    # Temel sandbox / container bayrakları
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")   # /dev/shm küçük container'lar için kritik
    opts.add_argument("--no-zygote")               # zygote process container'da crash verir
    opts.add_argument("--single-process")           # container'da daha stabil

    # GPU / render
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-3d-apis")

    # Hafıza / performans
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-sync")
    opts.add_argument("--disable-translate")
    opts.add_argument("--mute-audio")
    opts.add_argument("--no-first-run")
    opts.add_argument("--safebrowsing-disable-auto-update")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--log-level=3")
    opts.add_argument("--silent")

    # Render/Linux: apt ile kurulan sistem Chrome'unu kullan
    SYSTEM_CHROME    = "/usr/bin/chromium-browser"
    SYSTEM_CHROMEDRV = "/usr/bin/chromedriver"
    if os.path.exists(SYSTEM_CHROME) and os.path.exists(SYSTEM_CHROMEDRV):
        opts.binary_location = SYSTEM_CHROME
        svc = Service(SYSTEM_CHROMEDRV)
    else:
        # Lokal geliştirme: ChromeDriverManager otomatik indir
        svc = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=svc, options=opts)


def _accept_cookies(driver, timeout: int = 5) -> None:
    xpaths = [
        "//button[contains(.,'Tümünü kabul')]",
        "//button[contains(.,'Accept all')]",
        "//button[contains(.,'Kabul et')]",
        "//button[@id='onetrust-accept-btn-handler']",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            btn.click()
            time.sleep(0.4)
            return
        except Exception:
            pass


def _type_url_robust(driver, target_url: str, max_attempts: int = 4) -> bool:
    """PageSpeed URL input'una URL'yi güvenilir şekilde yazar."""
    css = "input[name='url']"
    for attempt in range(1, max_attempts + 1):
        try:
            inp = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css))
            )
            time.sleep(0.3)
            # Yöntem 1: JS ile direkt value ata
            driver.execute_script(
                "arguments[0].focus(); arguments[0].value = '';", inp
            )
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                inp, target_url,
            )
            time.sleep(0.3)
            val = driver.execute_script("return arguments[0].value;", inp)
            if val == target_url:
                print(f"    ✓ URL girildi (deneme {attempt})")
                return True
            # Yöntem 2: send_keys
            inp.click()
            inp.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            inp.send_keys(Keys.DELETE)
            inp.clear()
            time.sleep(0.2)
            inp.send_keys(target_url)
            time.sleep(0.4)
            val = driver.execute_script("return arguments[0].value;", inp)
            if val == target_url:
                print(f"    ✓ URL girildi send_keys (deneme {attempt})")
                return True
            print(f"    ⚠ Deneme {attempt} başarısız, tekrar deneniyor...")
            time.sleep(1)
        except Exception as exc:
            print(f"    ⚠ Deneme {attempt} hatası: {exc}")
            time.sleep(1.5)
    print("    ✗ URL girilemedi.")
    return False


# ── PSI Fotoğraf + Specs Maps (detay_okuycu_pagespeed.py'den uyarlandı) ──────

_PSI_CD_MAP: dict = {
    "cd13": "Kategori 1",    "cd14": "Kategori 2",   "cd15": "Marka",
    "cd16": "Seri",          "cd17": "Model",         "cd19": "Ülke",
    "cd20": "Şehir",         "cd21": "İlçe",          "cd24": "Bestmatch",
    "cd29": "Cihaz Tipi",    "cd30": "Ekran DPI",     "cd32": "Motor Hacmi",
    "cd33": "Motor Gücü",    "cd34": "Kilometre",     "cd37": "Vites",
    "cd38": "Model Yılı",    "cd39": "Kimden",        "cd42": "Model Detay",
    "cd43": "İlan No",       "cd46": "Eurotax",       "cd49": "Kasa Tipi",
    "cd50": "Takas",         "cd53": "Fiyat (Sayısal)", "cd56": "Satıcı Tipi",
    "cd60": "Data Center",   "cd73": "Mahalle",       "cd74": "Mahalle (detay)",
    "cd82": "İşletim Sistemi",
}

_PSI_EP_MAP: dict = {
    "ep.content_group":     "Sayfa Türü",
    "ep.kategori_1":        "Kategori 1",   "ep.kategori_2": "Kategori 2",
    "ep.kategori_3":        "Marka",        "ep.kategori_4": "Seri",
    "ep.kategori_5":        "Model",
    "ep.CD_MotorHacmi":     "Motor Hacmi",  "ep.motor_hacmi": "Motor Hacmi",
    "ep.cd_motorGucu":      "Motor Gücü",   "ep.motor_gucu":  "Motor Gücü",
    "ep.CD_Km":             "Kilometre",    "ep.km":          "Kilometre",
    "ep.CD_Vites":          "Vites",        "ep.vites":       "Vites",
    "ep.CD_ModelYil":       "Model Yılı",   "ep.model_yili":  "Model Yılı",
    "ep.CD_Kimden":         "Kimden",       "ep.kimden":      "Kimden",
    "ep.model_js":          "Model Detay",
    "ep.CD_ilanNo":         "İlan No",      "ep.ilan_no":     "İlan No",
    "ep.eurotax":           "Eurotax",
    "ep.CD_KasaTipi":       "Kasa Tipi",    "ep.kasa_tipi":   "Kasa Tipi",
    "ep.CD_Takas":          "Takas",        "ep.takas":       "Takas",
    "ep.js_price":          "Fiyat (Sayısal)",
    "ep.CD_IlanOwnerType":  "Satıcı Tipi",  "ep.js_owner_type": "Satıcı Tipi",
    "ep.CD_Yer1":           "Ülke",         "ep.yer_1":       "Ülke",
    "ep.CD_Yer2":           "Şehir",        "ep.yer_2":       "Şehir",
    "ep.CD_Yer3":           "İlçe",         "ep.yer_3":       "İlçe",
    "ep.CD_Yer4":           "Mahalle",      "ep.yer_4":       "Mahalle",
    "ep.CD_Yer5":           "Mahalle (detay)", "ep.yer_5":    "Mahalle (detay)",
    "ep.data_center":       "Data Center",
    "ep.site_preference":   "Site Tercihi",
    "ep.kategori_2":        "Kategori 2",
}


def _extract_psi_photos(raw_text: str) -> list[dict]:
    """
    PSI HTML'inden tüm fotoğrafları ayıklar; tip (full/thumb/other) ile döner.
    Döner: [{"url": "...", "type": "full|thumb|other", "format": "avif|jpg|..."}]
    """
    unescaped = html_mod.unescape(raw_text)
    result: list[dict] = []
    seen: set = set()

    pattern = re.compile(
        r"https?://i\d+\.shbdn\.com/photos/[^\s\"'<>&]+\.(?:avif|jpg|jpeg|png|webp)",
        re.IGNORECASE,
    )
    for url in pattern.findall(unescaped):
        url = url.split("?", 1)[0].split("#", 1)[0]
        if "blank" in url or url in seen:
            continue
        seen.add(url)

        fname = url.rsplit("/", 1)[-1]
        fmt   = fname.rsplit(".", 1)[-1].lower() if "." in fname else "?"

        if fname.startswith(("x5_", "x3_")):
            ptype = "full"
        elif fname.startswith(("thmb_", "lthmb_")):
            ptype = "thumb"
        else:
            ptype = "other"

        result.append({"url": url, "type": ptype, "format": fmt})

    return result


def _parse_photos_from_raw(raw_text: str) -> list[str]:
    """
    PSI HTML'inden shbdn.com fotoğraf URL'lerini çıkar.
    Katman 1: x5_/x3_ (tam boyut)
    Katman 2: thmb_ (thumbnail, x5_ yoksa)
    Katman 3: prefix temizlenmiş genel fallback
    """
    raw_text = html_mod.unescape(raw_text)
    photos: list[str] = []
    seen:   set = set()

    # Katman 1 — tam boyut
    full_pat = re.compile(
        r"https?://i\d+\.shbdn\.com/photos/[^\s\"'<>&]+/x5_[^\s\"'<>&]+\.(?:avif|jpg|jpeg|png|webp)",
        re.IGNORECASE,
    )
    for url in full_pat.findall(raw_text):
        url = url.split("?", 1)[0].split("#", 1)[0]
        if "blank" not in url and url not in seen:
            seen.add(url)
            photos.append(url)

    # Katman 2 — thumbnail (sadece tam boyut bulunamadıysa ekle)
    thumb_pat = re.compile(
        r"https?://i\d+\.shbdn\.com/photos/[^\s\"'<>&]+/thmb_[^\s\"'<>&]+\.(?:avif|jpg|jpeg|png|webp)",
        re.IGNORECASE,
    )
    thumb_photos: list[str] = []
    seen_thumb: set = set()
    for url in thumb_pat.findall(raw_text):
        url = url.split("?", 1)[0].split("#", 1)[0]
        if "blank" not in url and url not in seen_thumb:
            seen_thumb.add(url)
            thumb_photos.append(url)

    # Katman 3 — genel fallback, prefix kaldır
    fallback_pat = re.compile(
        r"https?://i\d+\.shbdn\.com/photos/[^\s\"'<>&]+\.(?:avif|jpg|jpeg|png|webp)",
        re.IGNORECASE,
    )
    for url in fallback_pat.findall(raw_text):
        url   = url.split("?", 1)[0].split("#", 1)[0]
        clean = re.sub(r"/(?:x5_|x3_|x2_|x1_|thmb_|lthmb_)", "/", url)
        if "blank" not in clean and clean not in seen:
            seen.add(clean)
            photos.append(clean)

    # Tam boyut yoksa thumbnail'ları kullan
    if not photos and thumb_photos:
        photos = thumb_photos

    return photos


def _extract_price_tr(raw_text: str) -> str:
    """Metinden en büyük TL fiyatını çıkar."""
    t = html_mod.unescape(raw_text)
    candidates = []
    for m in re.finditer(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(TL|₺)", t):
        try:
            amt = float(m.group(1).replace(".", "").replace(",", "."))
            if amt >= 1000:
                candidates.append((amt, m.group(0)))
        except Exception:
            pass
    return max(candidates, key=lambda x: x[0])[1] if candidates else "—"


def _extract_location_from_raw(raw_text: str) -> str:
    """
    PSI çıktısından şehir / ilçe / mahalle bilgisini çıkar.
    Önce GA4 ep. parametreleri, bulunamazsa UA cd. parametrelerine düşer.
    """
    from urllib.parse import unquote as _uq
    t = html_mod.unescape(raw_text)

    def _find(patterns: list[str]) -> str:
        for pat in patterns:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                val = _uq(m.group(1).replace("+", " ")).strip()
                if val and val not in ("0", "null", "undefined"):
                    return val
        return ""

    sehir  = _find([r"ep\.(?:CD_Yer2|yer_2)=([^&\n<>]+)",  r"cd20=([^&\n<>]+)"])
    ilce   = _find([r"ep\.(?:CD_Yer3|yer_3)=([^&\n<>]+)",  r"cd21=([^&\n<>]+)"])
    mahalle= _find([r"ep\.(?:CD_Yer4|yer_4)=([^&\n<>]+)",  r"cd73=([^&\n<>]+)"])

    parts = [x for x in [mahalle, ilce, sehir] if x]
    return ", ".join(parts) if parts else ""


def _extract_specs_from_raw(raw_text: str) -> dict:
    """PSI çıktısından GA4 ep. + UA cd. parametrelerini çıkar (full version)."""
    from urllib.parse import unquote as _unquote
    specs: dict = {}
    seen_keys: set = set()
    t = html_mod.unescape(raw_text)

    # ── GA4 ep. parametreleri ────────────────────────────────────────────────
    ep_pattern = re.compile(r"ep\.([A-Za-z0-9_]+)=([^&\n\"'<>]+)", re.IGNORECASE)
    for m in ep_pattern.finditer(t):
        raw_key = "ep." + m.group(1)
        val = _unquote(m.group(2).replace("&amp;", "&").replace("+", " ")).strip()
        if not val or val in ("0", "false"):
            continue
        label = _PSI_EP_MAP.get(raw_key)
        if label and label not in seen_keys:
            specs[label] = val
            seen_keys.add(label)

    # ── UA custom dimensions (cd13–cd82) ────────────────────────────────────
    cd_pattern = re.compile(r"(cd\d{1,3})=([^&\n\"'<>]+)", re.IGNORECASE)
    for m in cd_pattern.finditer(t):
        cd_key = m.group(1).lower()
        val = _unquote(m.group(2).replace("&amp;", "&").replace("+", " ")).strip()
        if not val or val in ("0", ""):
            continue
        label = _PSI_CD_MAP.get(cd_key)
        if label and label not in seen_keys:
            specs[label] = val
            seen_keys.add(label)

    # ── Fiyat sayısaldan TL'ye ──────────────────────────────────────────────
    if "Fiyat (Sayısal)" in specs:
        try:
            specs["Fiyat"] = f"{int(specs['Fiyat (Sayısal)']):,.0f} ₺".replace(",", ".")
        except Exception:
            pass

    # Gereksiz teknik alanları temizle
    for k in ("Cihaz Tipi", "Ekran DPI", "Data Center", "Bestmatch",
              "Site Tercihi", "Kullanıcı Giriş Durumu", "Oturum Durum"):
        specs.pop(k, None)

    return specs


# ================================================================
# SAHIBINDEN SCRAPER — Selenium + PageSpeed Web
# ================================================================

def _scrape_via_pagespeed(url: str) -> dict:
    """
    Selenium ile pagespeed.web.dev'e gidip URL'yi analiz ettirir.
    Dönen HTML'den fotoğraf + fiyat + lokasyon çıkarır.
    Render/sunucu ortamında çalışmaz — sadece lokal kullanım.
    """
    if not _SELENIUM:
        return {
            "ok": False,
            "error": "Selenium kurulu değil: pip install selenium webdriver-manager",
        }

    headless = os.environ.get("PS_HEADLESS", "1") != "0"
    wait_sec = int(os.environ.get("PS_WAIT_SEC", str(DEFAULT_PS_WAIT)))

    print(f"🌐 Selenium PageSpeed başlatılıyor... (headless={headless}, wait={wait_sec}s)")
    driver = None
    try:
        driver = _make_chrome(headless=headless)
        driver.get(PAGESPEED_WEB_URL)
        time.sleep(2)
        _accept_cookies(driver, timeout=6)
        time.sleep(0.5)

        if not _type_url_robust(driver, url):
            return {"ok": False, "error": "URL PageSpeed'e girilemedi"}

        # Analiz et butonunu bul ve tıkla
        try:
            btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//span[normalize-space()='Analiz et' or normalize-space()='Analyze']"
                    "/ancestor::button[1]",
                ))
            )
            # URL'nin hâlâ doğru olduğunu doğrula
            inp = driver.find_element(By.CSS_SELECTOR, "input[name='url']")
            val = driver.execute_script("return arguments[0].value;", inp)
            if val != url:
                if not _type_url_robust(driver, url):
                    return {"ok": False, "error": "URL doğrulama başarısız"}
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            print("    ⚠ Buton bulunamadı, Enter ile gönderiliyor...")
            inp = driver.find_element(By.CSS_SELECTOR, "input[name='url']")
            inp.send_keys(Keys.RETURN)

        print(f"    ✓ Analiz başlatıldı → bekleniyor ({wait_sec}s)")
        print("    ⏳", end="", flush=True)
        for i in range(wait_sec):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f" {wait_sec - i - 1}s", end="", flush=True)
        print()

        # /analysis/ sayfasına geçmesini bekle
        try:
            WebDriverWait(driver, 20).until(
                lambda d: "/analysis/" in d.current_url
            )
        except Exception:
            pass

        raw_html = driver.page_source

        # ── Fotoğraf çıkarma — full + thumb akıllı birleştirme ───────────────
        psi_photos   = _extract_psi_photos(raw_html)
        full_photos  = [p["url"] for p in psi_photos if p["type"] == "full"]
        thumb_photos = [p["url"] for p in psi_photos if p["type"] == "thumb"]
        other_photos = [p["url"] for p in psi_photos if p["type"] == "other"]

        # Her fotoğraf için "foto kimliği": prefix kaldırılmış dosya adı bazlı key
        # Örn: ".../x5_sbXXYY.avif" ve ".../thmb_sbXXYY.avif" → aynı fotoğraf
        def _photo_key(u: str) -> str:
            fname = u.rsplit("/", 1)[-1]
            clean = re.sub(r"^(?:x5_|x3_|x2_|x1_|thmb_|lthmb_)", "", fname)
            return u.rsplit("/", 1)[0] + "/" + clean

        # Full fotoğrafların key seti — thumb'dan fazlası var mı?
        full_keys = {_photo_key(u) for u in full_photos}

        # Full ile eşleşmeyen orphan thumbnail'lar (yeni fotoğraflar)
        orphan_thumbs = [u for u in thumb_photos if _photo_key(u) not in full_keys]

        if full_photos or thumb_photos:
            # Tam boyut önce, ardından eşleşmeyen thumbnail'lar (yeni fotoğraflar)
            photos = full_photos + orphan_thumbs
        elif other_photos:
            photos = other_photos
        else:
            photos = _parse_photos_from_raw(raw_html)

        # ── Specs + fiyat + lokasyon ──────────────────────────────────────────
        specs    = _extract_specs_from_raw(raw_html)
        price    = specs.get("Fiyat") or _extract_price_tr(raw_html)

        # Lokasyon: specs'ten türet (zaten parse edildi), yoksa raw regex
        loc_parts = [x for x in [
            specs.get("Mahalle", ""),
            specs.get("İlçe", ""),
            specs.get("Şehir", ""),
        ] if x]
        location = ", ".join(loc_parts) if loc_parts else _extract_location_from_raw(raw_html)

        # Başlık: title tag veya URL'den çıkar
        title = url
        try:
            soup_tmp = BeautifulSoup(html_mod.unescape(raw_html), "lxml")
            t_tag = soup_tmp.find("title")
            if t_tag:
                title = t_tag.get_text(strip=True) or url
        except Exception:
            pass

        print(f"    ✓ Fotoğraf: {len(photos)} (full={len(full_photos)}, thumb={len(thumb_photos)}) | Fiyat: {price} | Lokasyon: {location}")

        return {
            "ok":          True,
            "source":      "sahibinden_selenium_pagespeed",
            "title":       title,
            "price":       price,
            "location":    location,
            "specs":       specs,
            "description": "",
            "images":      photos,
            "photo_count": len(photos),
            "photo_types": {
                "full":  len(full_photos),
                "thumb": len(thumb_photos),
                "other": len(other_photos),
            },
            "screenshot":  "",
        }

    except Exception as e:
        print(f"    ✗ Selenium hatası: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _scrape_hepsiemlak(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            return {"ok": False}
        soup = BeautifulSoup(resp.content, "html.parser")

        title = (soup.select_one("h1.det-title") or soup.select_one("h1") or "").get_text(strip=True) if soup.select_one("h1") else ""

        price_el = soup.select_one(".fz24-text") or soup.select_one("[class*='price']")
        price = price_el.get_text(strip=True) if price_el else ""

        specs: dict = {}
        for item in soup.select(".spec-item li, .det-advert-props li, [class*='spec']"):
            t = item.get_text(strip=True)
            if "m²" in t or "m2" in t.lower():      specs["area"]  = t
            elif "oda" in t.lower():                  specs["rooms"] = t
            elif "kat" in t.lower():                  specs["floor"] = t
            elif any(x in t.lower() for x in ["yaş", "bina yaşı", "yıl"]):
                specs["age"] = t

        images = [
            img.get("src", "") for img in soup.select("img")
            if ("hepsiemlak" in (img.get("src") or "") or "cdn" in (img.get("src") or ""))
            and img.get("src")
        ]

        desc_el = soup.select_one(".det-desc, [class*='description']")
        desc = desc_el.get_text(strip=True)[:600] if desc_el else ""

        loc_el = soup.select_one("[class*='location'], [class*='address']")
        loc = loc_el.get_text(strip=True) if loc_el else ""

        return {
            "ok": True, "source": "hepsiemlak",
            "title": title, "price": price, "location": loc,
            "specs": specs, "images": images[:8], "description": desc,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scrape_zingat(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            return {"ok": False}
        soup = BeautifulSoup(resp.content, "html.parser")

        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one(".price, [class*='price'], [class*='fiyat']")
        price = price_el.get_text(strip=True) if price_el else ""

        specs: dict = {}
        for item in soup.select("li, .spec"):
            t = item.get_text(strip=True)
            if "m²" in t: specs["area"]  = t
            elif "oda" in t.lower(): specs["rooms"] = t
            elif "kat" in t.lower(): specs["floor"] = t

        images = [
            img.get("src", "") for img in soup.select("img")
            if img.get("src") and ("zingat" in img.get("src","") or "cdn" in img.get("src",""))
        ]

        desc_el = soup.select_one("[class*='desc'], [class*='aciklama']")
        desc = desc_el.get_text(strip=True)[:600] if desc_el else ""

        loc_el = soup.select_one("[class*='location'], [class*='konum']")
        loc = loc_el.get_text(strip=True) if loc_el else ""

        return {
            "ok": True, "source": "zingat",
            "title": title, "price": price, "location": loc,
            "specs": specs, "images": images[:8], "description": desc,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scrape_emlakjet(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            return {"ok": False}
        soup = BeautifulSoup(resp.content, "html.parser")

        title_el = soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one("[class*='price'], [class*='Price']")
        price = price_el.get_text(strip=True) if price_el else ""

        specs: dict = {}
        page_text = soup.get_text()
        m_area  = re.search(r"(\d{2,4})\s*m[²2]", page_text)
        m_rooms = re.search(r"(\d+\+\d+|\d+\s*oda)", page_text, re.IGNORECASE)
        if m_area:  specs["area"]  = m_area.group(0)
        if m_rooms: specs["rooms"] = m_rooms.group(0)

        images = []
        for img in soup.select("img[src*='emlakjet'], img[src*='ejcdn']"):
            src = img.get("src", "")
            if src: images.append(src)

        return {
            "ok": True, "source": "emlakjet",
            "title": title, "price": price, "location": "",
            "specs": specs, "images": images[:8], "description": "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scrape_generic(url: str) -> dict:
    """OG tags + regex fallback — desteklenmeyen siteler için."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            return {"ok": False}
        soup = BeautifulSoup(resp.content, "html.parser")

        og_title = soup.find("meta", property="og:title")
        og_desc  = soup.find("meta", property="og:description")
        og_img   = soup.find("meta", property="og:image")

        title = og_title.get("content","") if og_title else ""
        if not title:
            h1 = soup.select_one("h1")
            title = h1.get_text(strip=True) if h1 else ""

        desc = og_desc.get("content","") if og_desc else ""

        images = []
        if og_img:
            images.append(og_img.get("content",""))

        page_text = soup.get_text()
        price_m = re.search(r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:TL|₺)", page_text)
        price = price_m.group(0) if price_m else ""

        area_m = re.search(r"(\d{2,4})\s*m[²2]", page_text)
        specs: dict = {}
        if area_m:
            specs["area"] = area_m.group(0)

        return {
            "ok": True, "source": "generic",
            "title": title, "price": price, "location": "",
            "specs": specs, "images": images[:5],
            "description": desc[:600],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def scrape_listing(url: str) -> dict:
    """
    URL'ye göre uygun scraper'ı seç, ilan verilerini çek ve döndür.
    Sahibinden için PageSpeed API kullanılır (Selenium gerektirmez).
    """
    domain = urlparse(url).netloc.lower()

    if "sahibinden.com" in domain:
        return _scrape_via_pagespeed(url)
    elif "hepsiemlak.com" in domain:
        return _scrape_hepsiemlak(url)
    elif "zingat.com" in domain:
        return _scrape_zingat(url)
    elif "emlakjet.com" in domain:
        return _scrape_emlakjet(url)
    else:
        return _scrape_generic(url)


# ================================================================
# GÖRSEL İNDİRME
# ================================================================

def _download_image_b64(img_url: str) -> tuple[str, str] | None:
    """
    URL → (mime_type, base64_string). Başarısız olursa None.

    Shbdn fotoğrafları .avif formatında gelir; Gemini bu formatı inline olarak
    desteklemez. Bu yüzden .avif URL'leri için önce .jpg varyantı denenir.
    """
    def _fetch(url: str) -> tuple[str, str] | None:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, stream=True)
            if not resp.ok:
                return None
            ct = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            if not ct.startswith("image/"):
                return None
            mime = ct.split("/")[-1] if "/" in ct else "jpeg"
            # Gemini inline desteklenen formatlar: jpeg, png, webp, gif
            # avif desteklenmez → jpeg olarak işaretle (bytes uyumsuz olabilir)
            if mime not in ("jpeg", "png", "webp", "gif"):
                return None   # bu URL'yi geç, fallback dene
            raw = b"".join(resp.iter_content(65536))
            return mime, base64.b64encode(raw).decode("utf-8")
        except Exception:
            return None

    # .avif URL ise önce .jpg varyantını dene
    if img_url.lower().endswith(".avif"):
        jpg_url = img_url[:-5] + ".jpg"
        result  = _fetch(jpg_url)
        if result:
            return result
        # .jpg de yoksa thumbnail'den büyük versiyon dene (x5_ → x3_)
        if "/x5_" in img_url:
            x3_url = img_url.replace("/x5_", "/x3_").replace(".avif", ".jpg")
            result  = _fetch(x3_url)
            if result:
                return result
        # thmb_ versiyonuna düş
        if "/thmb_" not in img_url:
            thmb_url = re.sub(r"/(?:x5_|x3_|x2_|x1_)", "/thmb_", img_url).replace(".avif", ".jpg")
            result    = _fetch(thmb_url)
            if result:
                return result
        # Son çare: bytes'ı avif olarak al ama jpeg mime ile gönder (bazı modellerde geçer)
        try:
            resp = requests.get(img_url, headers=HEADERS, timeout=10, stream=True)
            if resp.ok:
                raw = b"".join(resp.iter_content(65536))
                return "jpeg", base64.b64encode(raw).decode("utf-8")
        except Exception:
            pass
        return None

    return _fetch(img_url)


def _parse_uploaded(img_data: str) -> tuple[str, str] | None:
    """Frontend'den gelen base64 string veya data URI → (mime, b64)."""
    if not img_data:
        return None
    if img_data.startswith("data:"):
        try:
            header, b64 = img_data.split(";base64,", 1)
            mime = header.split("/")[-1].lower()
            # Gemini inline desteklenenler
            mime = mime if mime in ("jpeg", "png", "webp", "gif") else "jpeg"
            return mime, b64
        except Exception:
            return None
    # Salt base64 string → jpeg varsay
    return "jpeg", img_data


# ================================================================
# ANA ANALİZ
# ================================================================

def analyze_listing(
    listing_data:    dict | None,
    manual_data:     dict | None,
    uploaded_images: list[str] | None,
) -> dict:
    """
    Scrape çıktısı + manuel giriş + yüklenen fotoğrafları birleştirip
    Gemini 2.5 Flash multimodal ile ultra-detaylı gayrimenkul analizi üretir.

    Parametreler:
        listing_data    — scrape_listing() çıktısı (veya None)
        manual_data     — {price, area, rooms, floor, age, location, notes, listing_type}
        uploaded_images — ["data:image/jpeg;base64,...", ...] listesi

    Dönüş:
        {"ok": True,  "report": {...}}
        {"ok": False, "error": "..."}
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY tanımlı değil"}

    # ── Veri birleştirme ──────────────────────────────────────────────────────
    ld = listing_data or {}
    md = manual_data or {}

    def pick(*keys: str, fallback: str = "—") -> str:
        for k in keys:
            v = ld.get(k) or md.get(k) or (ld.get("specs") or {}).get(k)
            if v and str(v).strip():
                return str(v).strip()
        return fallback

    title    = pick("title",    "manual_title",    fallback="Belirtilmemiş")
    price    = pick("price",    "Fiyat", "manual_price", fallback="Belirtilmemiş")
    location = pick("location", "manual_location", fallback="Belirtilmemiş")
    area     = pick("area",     "manual_area",     fallback="")
    rooms    = pick("rooms",    "manual_rooms",    fallback="")
    floor    = pick("floor",    "manual_floor",    fallback="")
    age      = pick("age",      "manual_age",      fallback="")
    desc     = pick("description", "manual_notes", fallback="")
    l_type   = pick("type",     "listing_type",    fallback="Belirtilmemiş")
    source   = ld.get("source", "manuel")

    # Specs'ten eksik alanları tamamla
    specs = ld.get("specs") or {}
    if location == "Belirtilmemiş" and specs:
        loc_parts = [x for x in [
            specs.get("Mahalle", ""),
            specs.get("İlçe", ""),
            specs.get("Şehir", ""),
        ] if x]
        if loc_parts:
            location = ", ".join(loc_parts)
    if not rooms and specs.get("Oda Sayısı"):
        rooms = specs["Oda Sayısı"]
    if not area and specs.get("Alan"):
        area = specs["Alan"]
    ilan_no = specs.get("İlan No", "")
    kimden  = specs.get("Kimden", "")
    kategori = specs.get("Kategori 1", "") or specs.get("Kategori 2", "")

    # ── Görselleri hazırla ────────────────────────────────────────────────────
    all_images: list[tuple[str, str]] = []  # [(mime, b64), ...]

    # Scrape'den screenshot
    screenshot = ld.get("screenshot", "")
    if screenshot and len(all_images) < 2:
        parsed = _parse_uploaded(screenshot)
        if parsed:
            all_images.append(parsed)

    # Scrape'den URL'ler (tam boyut öncelikli, cap 12)
    for img_url in ld.get("images", []):
        if len(all_images) >= 12:
            break
        if img_url.startswith("data:"):
            parsed = _parse_uploaded(img_url)
            if parsed:
                all_images.append(parsed)
        else:
            result = _download_image_b64(img_url)
            if result:
                all_images.append(result)

    # Upload'dan gelen görseller (cap 15 toplam)
    for img_data in (uploaded_images or []):
        if len(all_images) >= 15:
            break
        parsed = _parse_uploaded(img_data)
        if parsed:
            all_images.append(parsed)

    has_photos = len(all_images) > 0
    print(f"🖼  Toplam görsel: {len(all_images)} (kaynak: {source})")

    # ── Prompt ────────────────────────────────────────────────────────────────
    prompt = f"""Sen Türkiye'nin en deneyimli gayrimenkul analiz uzmanısın.
Bir ilan hakkında {'fotoğraflar da dahil olmak üzere ' if has_photos else ''}kapsamlı bir analiz yapmanı istiyorum.

════════════════ İLAN BİLGİLERİ ════════════════
Başlık        : {title}
Fiyat         : {price}
Tür           : {l_type}
Konum         : {location}
Brüt Alan     : {area}
Oda/Salon     : {rooms}
Kat           : {floor}
Bina Yaşı     : {age}
{'İlan No      : ' + ilan_no if ilan_no else ''}
{'Kimden       : ' + kimden if kimden else ''}
{'Kategori     : ' + kategori if kategori else ''}
Açıklama/Not  : {desc[:800] if desc != '—' else 'Yok'}
Veri Kaynağı  : {source}
{'📸 ' + str(len(all_images)) + ' adet fotoğraf ektedir. Her birini detaylıca incele.' if has_photos else '⚠ Fotoğraf gönderilmedi.'}
════════════════════════════════════════════════

KURALLAR:
1. SADECE geçerli JSON döndür. Markdown, açıklama, kod bloğu YOK.
2. Tüm metinler Türkçe.
3. Fiyatlar TL cinsinden, binlik nokta ayraçlı (örn: "4.750.000 TL").
4. Sayısal skorlar 1–10 aralığında tam sayı.
5. pros/cons/strengths vb. listelerde ≥ 3 madde.
6. Fotoğraf varsa photo_analysis alanını doldur; yoksa "condition_score":0 yaz, diğer alanları boş bırak.
7. investment_analysis.verdict: "AL" / "BEKLE" / "GEÇ" yaz.
8. advisor_notes.talking_points danışman için, müşteriye söylenmesi gereken güçlü noktalar.
9. Gerçekçi ol — spekülatif bilgileri "tahmini" olarak işaretle.

JSON YAPISI (TÜM ALANLARI DOLDUR):
{{
  "property_summary": {{
    "title": "{title}",
    "price": "{price}",
    "location": "{location}",
    "area": "{area}",
    "rooms": "{rooms}",
    "floor": "{floor}",
    "building_age": "{age}",
    "type": "{l_type}"
  }},
  "price_analysis": {{
    "listed_price": "{price}",
    "estimated_fair_value": "X.XXX.XXX TL",
    "price_per_sqm": "XX.XXX TL/m²",
    "market_comparison": "Piyasa ortalamasının %X altında/üstünde",
    "negotiation_room": "%X–Y",
    "verdict": "Uygun/Pahalı/Ucuz",
    "verdict_detail": "2-3 cümle"
  }},
  "investment_analysis": {{
    "investment_score": 7,
    "score_label": "İyi",
    "verdict": "AL",
    "estimated_monthly_rent": "XX.XXX TL",
    "gross_yield_pct": 4.2,
    "payback_years": 20,
    "value_increase_1yr": "%X–Y",
    "value_increase_5yr": "%X–Y",
    "target_buyer": "Yatırımcı/Birinci ev/Kiralık vb.",
    "reasoning": "3-4 cümle"
  }},
  "photo_analysis": {{
    "overall_condition": "Yeni/İyi/Orta/Kötü",
    "condition_score": 8,
    "detected_rooms": ["salon","mutfak"],
    "flooring": "parke/seramik/mermer/?",
    "natural_light": "Bol/Orta/Az",
    "view": "Açık/Kapalı/Boğaz/Park/?",
    "renovation_needed": false,
    "renovation_estimate": "",
    "positive_visuals": ["güçlü görsel özellik"],
    "issues_detected": ["sorun 1"],
    "staging_tips": ["sunum önerisi 1"]
  }},
  "swot": {{
    "strengths":     ["güçlü yön 1","güçlü yön 2","güçlü yön 3"],
    "weaknesses":    ["zayıf yön 1","zayıf yön 2"],
    "opportunities": ["fırsat 1","fırsat 2"],
    "threats":       ["tehdit 1","tehdit 2"]
  }},
  "location_analysis": {{
    "neighborhood_score": 7,
    "transport_access": "Metro/Otobüs/Özel araç gerekli",
    "nearby_amenities": ["okul","hastane","AVM"],
    "development_outlook": "Gelişmekte/Stabil/Gerileme",
    "earthquake_risk": "Düşük/Orta/Yüksek",
    "noise_risk": "Düşük/Orta/Yüksek",
    "comments": "2-3 cümle"
  }},
  "advisor_notes": {{
    "talking_points": ["güçlü nokta 1","güçlü nokta 2","güçlü nokta 3"],
    "objections_to_prepare": ["olası itiraz 1","olası itiraz 2"],
    "closing_suggestion": "Kapanış stratejisi",
    "red_flags": ["risk 1"]
  }},
  "recommendation": {{
    "verdict": "AL/GEÇ/BEKLE",
    "confidence": "Yüksek/Orta/Düşük",
    "summary": "3-4 cümle genel değerlendirme",
    "next_steps": ["adım 1","adım 2","adım 3"]
  }},
  "disclaimer": "Bu analiz Gemini yapay zekası tarafından üretilmiştir; yatırım tavsiyesi değildir. Kesin değerleme için SPK lisanslı ekspertiz önerilir."
}}"""

    # ── Gemini çağrısı ────────────────────────────────────────────────────────
    try:
        client = genai.Client(api_key=api_key)

        parts: list = []

        # Görsel partlar önce
        for mime, b64 in all_images[:12]:
            try:
                raw_bytes = base64.b64decode(b64)
                parts.append(
                    types.Part.from_bytes(
                        data=raw_bytes,
                        mime_type=f"image/{mime}",
                    )
                )
            except Exception as e:
                print(f"⚠ Görsel eklenirken hata: {e}")

        # Text prompt
        parts.append(types.Part.from_text(text=prompt))

        response = client.models.generate_content(
            model    = GEMINI_MODEL,
            contents = [types.Content(role="user", parts=parts)],
        )
        raw_text = response.text.strip()

    except Exception as e:
        print(f"\u274c Gemini API hatas\u0131 ({GEMINI_MODEL}): {e}")
        fallback_model = "gemini-2.0-flash"
        if GEMINI_MODEL != fallback_model:
            try:
                print(f"\U0001f504 Fallback model deneniyor: {fallback_model}")
                response = client.models.generate_content(
                    model    = fallback_model,
                    contents = [types.Content(role="user", parts=parts)],
                )
                raw_text = response.text.strip()
            except Exception as e2:
                print(f"\u274c Fallback da ba\u015far\u0131s\u0131z: {e2}")
                return {"ok": False, "error": f"Gemini hatas\u0131: {e} | Fallback hatas\u0131: {e2}"}
        else:
            return {"ok": False, "error": f"Gemini hatas\u0131: {e}"}

    # \u2500\u2500 JSON \u00e7\u0131karma ──────────────────────────────────────────────────────────
    if "```" in raw_text:
        for part in raw_text.split("```"):
            p = part.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw_text = p
                break

    start = raw_text.find("{")
    end   = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        raw_text = raw_text[start:end]

    try:
        report = json.loads(raw_text)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON parse hatası: {e}", "raw": raw_text[:400]}

    report["generated_at"] = time.strftime("%d.%m.%Y %H:%M")
    report["has_photos"]   = has_photos
    report["photo_count"]  = len(all_images)
    report["data_source"]  = source

    return {"ok": True, "report": report}
