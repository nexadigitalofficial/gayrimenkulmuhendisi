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

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

# Playwright opsiyonel — sadece sahibinden scrape için (async API, greenlet gerektirmez)
import asyncio
try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT = True
except ImportError:
    _PLAYWRIGHT = False
_SELENIUM = _PLAYWRIGHT  # geriye dönük uyumluluk için

# ── Konfigürasyon ─────────────────────────────────────────────────────────────
# Geçerli modeller (Nisan 2026):
#   gemini-2.5-flash      → 10 RPM / 250 RPD  (önerilen ana model)
#   gemini-2.5-flash-lite → 15 RPM / 1000 RPD (fallback, en yüksek kota)
#   gemini-2.5-pro        → 5 RPM  / 100 RPD  (en yetenekli, kısıtlı)
GEMINI_MODEL        = os.environ.get("GEMINI_MODEL",    "gemini-2.5-flash")
GEMINI_FALLBACK     = os.environ.get("GEMINI_FALLBACK", "gemini-2.5-flash-lite")
GEMINI_MAX_RETRIES  = 3     # 429 hatası için max tekrar
GEMINI_RETRY_DELAY  = 10    # ilk bekleme süresi (sn), her seferinde 2x artar
SCRAPE_TIMEOUT      = 15
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
    return {
        "ok":         bool(key),
        "configured": bool(key),
        "model":      GEMINI_MODEL,
        "fallback":   GEMINI_FALLBACK,
    }


# ================================================================
# SCRAPERS
# ================================================================

# ── Ham HTML Yardımcıları ────────────────────────────────────────────────────

def _extract_psi_photos(raw_html: str) -> list[dict]:
    """
    PageSpeed Insights tarafından render edilmiş HTML'den
    Sahibinden CDN fotoğraf URL'lerini çıkarır.

    Döndürülen her öğe: {"url": str, "type": "full" | "thumb" | "other", "format": str}
      - full  : x5_ / x3_ önekli (tam çözünürlük)
      - thumb : thmb_ / lthmb_ önekli
      - other : diğer sahibinden CDN görselleri
    """
    # Önce HTML entity'leri decode et — PSI çıktısında URL'ler &quot; ile gömülü olabilir
    unescaped = html_mod.unescape(raw_html)
    result: list[dict] = []
    seen:   set[str]   = set()

    pattern = re.compile(
        r"https?://i\d+\.shbdn\.com/photos/[^\s\"'<>&]+\.(?:avif|jpg|jpeg|png|webp)",
        re.IGNORECASE,
    )

    for url in pattern.findall(unescaped):
        # Sorgu parametrelerini ve fragment'leri kaldır
        url = url.split("?", 1)[0].split("#", 1)[0]
        if "blank" in url or url in seen:
            continue
        seen.add(url)

        fname = url.rsplit("/", 1)[-1]
        fmt   = fname.rsplit(".", 1)[-1].lower() if "." in fname else "?"

        if fname.startswith("x5_") or fname.startswith("x3_"):
            ptype = "full"
        elif fname.startswith("thmb_") or fname.startswith("lthmb_"):
            ptype = "thumb"
        else:
            ptype = "other"

        result.append({"url": url, "type": ptype, "format": fmt})

    return result


# ── GA4 / UA custom dimension haritaları (detay_okuycu_pagespeed referans) ────

_PSI_CD_MAP: dict[str, str] = {
    "cd13": "Kategori 1",
    "cd14": "Kategori 2",
    "cd15": "Marka",
    "cd16": "Seri",
    "cd17": "Model",
    "cd19": "Ülke",
    "cd20": "Şehir",
    "cd21": "İlçe",
    "cd32": "Motor Hacmi",
    "cd33": "Motor Gücü",
    "cd34": "Kilometre",
    "cd37": "Vites",
    "cd38": "Model Yılı",
    "cd39": "Kimden",
    "cd42": "Model Detay",
    "cd43": "İlan No",
    "cd46": "Eurotax",
    "cd49": "Kasa Tipi",
    "cd50": "Takas",
    "cd53": "Fiyat (Sayısal)",
    "cd56": "Satıcı Tipi",
    "cd73": "Mahalle",
    "cd74": "Mahalle (detay)",
}

_PSI_EP_MAP: dict[str, str] = {
    "ep.content_group":     "Sayfa Türü",
    "ep.kategori_1":        "Kategori 1",
    "ep.kategori_2":        "Kategori 2",
    "ep.kategori_3":        "Marka",
    "ep.kategori_4":        "Seri",
    "ep.kategori_5":        "Model",
    "ep.CD_MotorHacmi":     "Motor Hacmi",
    "ep.cd_motorGucu":      "Motor Gücü",
    "ep.CD_Km":             "Kilometre",
    "ep.CD_Vites":          "Vites",
    "ep.CD_ModelYil":       "Model Yılı",
    "ep.CD_Kimden":         "Kimden",
    "ep.model_js":          "Model Detay",
    "ep.CD_ilanNo":         "İlan No",
    "ep.eurotax":           "Eurotax",
    "ep.CD_KasaTipi":       "Kasa Tipi",
    "ep.CD_Takas":          "Takas",
    "ep.js_price":          "Fiyat (Sayısal)",
    "ep.CD_IlanOwnerType":  "Satıcı Tipi",
    "ep.CD_Yer1":           "Ülke",
    "ep.CD_Yer2":           "Şehir",
    "ep.CD_Yer3":           "İlçe",
    "ep.CD_Yer4":           "Mahalle",
    "ep.CD_Yer5":           "Mahalle (detay)",
    "ep.kimden":            "Kimden",
    "ep.ilan_no":           "İlan No",
    "ep.kasa_tipi":         "Kasa Tipi",
    "ep.takas":             "Takas",
    "ep.js_owner_type":     "Satıcı Tipi",
    "ep.yer_1":             "Ülke",
    "ep.yer_2":             "Şehir",
    "ep.yer_3":             "İlçe",
    "ep.yer_4":             "Mahalle",
    "ep.yer_5":             "Mahalle (detay)",
    "ep.model_yili":        "Model Yılı",
}


def _extract_psi_specs(raw_html: str) -> dict:
    """
    PageSpeed Insights HTML'inden ilan teknik özelliklerini çıkarır.

    Strateji (öncelik sırası):
      1. GA4 event parametreleri (ep.XXX=YYY) — en zengin veri seti
      2. UA custom dimensions (cd13=XXX&cd14=YYY) — fallback
      3. Fiyat (Sayısal) → TL formatına dönüştürme

    detay_okuycu_pagespeed.py referans alınarak iyileştirildi.
    """
    from urllib.parse import unquote
    specs: dict    = {}
    seen_keys: set = set()

    # ── 1) GA4 event parametreleri (ep. prefix'li) ────────────────────────────
    ep_pattern = re.compile(r"ep\.([A-Za-z0-9_]+)=([^&\n\"'<>]+)", re.IGNORECASE)
    for m in ep_pattern.finditer(raw_html):
        raw_key = "ep." + m.group(1)
        raw_val = m.group(2).replace("&amp;", "&").replace("+", " ")
        try:
            raw_val = unquote(raw_val)
        except Exception:
            pass
        raw_val = raw_val.strip()
        if not raw_val or raw_val in ("0", "false", ""):
            continue
        label = _PSI_EP_MAP.get(raw_key)
        if label and label not in seen_keys:
            specs[label] = raw_val
            seen_keys.add(label)

    # ── 2) UA custom dimensions (cd13=... formatı) ────────────────────────────
    cd_pattern = re.compile(r"(cd\d{1,3})=([^&\n\"'<>]+)", re.IGNORECASE)
    for m in cd_pattern.finditer(raw_html):
        cd_key  = m.group(1).lower()
        raw_val = m.group(2).replace("&amp;", "&").replace("+", " ")
        try:
            raw_val = unquote(raw_val)
        except Exception:
            pass
        raw_val = raw_val.strip()
        if not raw_val or raw_val in ("0", ""):
            continue
        label = _PSI_CD_MAP.get(cd_key)
        if label and label not in seen_keys:
            specs[label] = raw_val
            seen_keys.add(label)

    # ── 3) Fiyat (Sayısal) → TL formatına çevir ──────────────────────────────
    if "Fiyat (Sayısal)" in specs:
        try:
            amt       = int(specs["Fiyat (Sayısal)"])
            formatted = f"{amt:,.0f} TL".replace(",", ".")
            specs.setdefault("Fiyat", formatted)
        except Exception:
            pass

    # ── 4) Fiyat hâlâ yoksa regex fallback ───────────────────────────────────
    if "Fiyat" not in specs:
        pm = re.search(r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:TL|₺)", raw_html)
        if pm:
            specs["Fiyat"] = pm.group(0)

    # ── 5) Gereksiz teknik/debug alanları temizle ─────────────────────────────
    for k in ("Sayfa Türü", "Kullanıcı Giriş Durumu", "Oturum Durum"):
        specs.pop(k, None)

    return specs


def _extract_price_tr(raw_html: str) -> str:
    """Ham HTML metninden TL fiyatı regex ile çıkarır."""
    m = re.search(r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:TL|₺)", raw_html)
    return m.group(0) if m else ""


def _extract_location_from_raw(raw_html: str) -> str:
    """Ham HTML'den konum/adres bilgisini çıkarır."""
    try:
        soup = BeautifulSoup(html_mod.unescape(raw_html), "html.parser")
        for sel in [
            "[class*='location']",
            "[class*='address']",
            "[class*='adres']",
            "[class*='konum']",
            "[class*='Location']",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text
    except Exception:
        pass
    return ""


def _parse_photos_from_raw(raw_html: str) -> list[str]:
    """
    Fallback: ham HTML'deki tüm .jpg / .jpeg / .png / .webp URL'lerini döndürür.
    _extract_psi_photos hiçbir şey bulamadığında kullanılır.
    """
    seen: set[str] = set()
    urls: list[str] = []

    for m in re.finditer(
        r'(https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp))(?:[^\s"\'<>]*)?',
        raw_html,
        re.IGNORECASE,
    ):
        url = html_mod.unescape(m.group(1))
        if url not in seen and len(url) > 20:
            seen.add(url)
            urls.append(url)
        if len(urls) >= 10:
            break

    return urls


# ================================================================
# PLAYWRIGHT HELPERS — async (greenlet gerektirmez)
# ================================================================

async def _pw_accept_cookies(page) -> None:
    selectors = [
        "button:has-text('Tümünü kabul')",
        "button:has-text('Accept all')",
        "button:has-text('Kabul et')",
        "#onetrust-accept-btn-handler",
    ]
    for sel in selectors:
        try:
            await page.locator(sel).click(timeout=4000)
            await page.wait_for_timeout(400)
            return
        except Exception:
            pass


async def _pw_type_url(page, target_url: str, max_attempts: int = 4) -> bool:
    """PageSpeed URL input'una URL'yi güvenilir şekilde yazar."""
    for attempt in range(1, max_attempts + 1):
        try:
            inp = page.locator("input[name='url']")
            await inp.wait_for(state="visible", timeout=15000)
            await page.wait_for_timeout(300)
            el = await inp.element_handle()
            await page.evaluate(
                """(args) => {
                    const el = args[0];
                    el.focus(); el.value = '';
                    el.value = args[1];
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                }""",
                [el, target_url],
            )
            await page.wait_for_timeout(300)
            val = await page.evaluate("el => el.value", el)
            if val == target_url:
                print(f"    ✓ URL girildi (deneme {attempt})")
                return True
            await inp.click()
            await inp.fill(target_url)
            await page.wait_for_timeout(300)
            val = await page.evaluate("el => el.value", el)
            if val == target_url:
                print(f"    ✓ URL fill ile girildi (deneme {attempt})")
                return True
            print(f"    ⚠ Deneme {attempt} başarısız, tekrar...")
            await page.wait_for_timeout(1000)
        except Exception as exc:
            print(f"    ⚠ Deneme {attempt} hatası: {exc}")
            await page.wait_for_timeout(1500)
    print("    ✗ URL girilemedi.")
    return False


# ================================================================
# SAHIBINDEN SCRAPER YARDIMCILARI (Tam Uyum)
# ================================================================

def detect_single_listing_id(url: str) -> Optional[str]:
    """Sahibinden tekil ilan ID'sini URL'den ayıklar."""
    if not url:
        return None
    m = re.search(r"/(?:ilan|listing)/[^/]*?-?(\d{8,12})(?:/detay|\?|#|$)", url)
    if m:
        return m.group(1)
    m2 = re.search(r"(\d{8,12})", url)
    if m2 and len(m2.group(1)) >= 9:
        return m2.group(1)
    return None

def _extract_sahibinden_detail_url(raw_text: str) -> str:
    m = re.search(r'https?://(?:www\.)?sahibinden\.com/ilan/[^\s"\'<>]+', raw_text)
    return m.group(0) if m else ""

def _title_from_detail_url(detail_url: str, listing_id: str = "") -> str:
    if not detail_url or "/ilan/" not in detail_url:
        return ""
    slug = detail_url.split("/ilan/", 1)[1].split("/detay", 1)[0]
    if listing_id and slug.endswith("-" + listing_id):
        slug = slug[: -(len(listing_id) + 1)]
    tokens = re.split(r"[-\.]", slug)
    stop = {
        "emlak","vasita","vasıta","is","yeri","isyeri","konut","arsa",
        "kiralik","kiralık","satilik","satılık","devren"
    }
    while tokens and tokens[0].lower() in stop:
        tokens.pop(0)
    title = " ".join(t.strip() for t in tokens if t.strip())
    return re.sub(r"\s+", " ", title).strip()

_DESC_MARKERS = ["İlan Açıklaması", "Ilan Aciklamasi", "İLAN AÇIKLAMASI", "AÇIKLAMA", "Açıklama"]

def _extract_psi_description(raw_text: str) -> str:
    t = html_mod.unescape(raw_text)
    for marker in _DESC_MARKERS:
        idx = t.find(marker)
        if idx == -1:
            continue
        window = t[idx + len(marker): idx + len(marker) + 4000]
        m = re.match(r"\s*[:\-–]?\s*([^<]{40,3500})", window)
        if m:
            candidate = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(candidate) >= 40:
                return candidate
    candidates = re.findall(r'nodeLabel[\\"]*:\s*[\\"]*([^"]{120,3000})', raw_text)
    long_candidates = []
    for c in candidates:
        c = html_mod.unescape(c).replace("\\n", " ").replace("\\", "")
        c = re.sub(r"\s+", " ", c).strip()
        if len(c) >= 120:
            long_candidates.append(c)
    if long_candidates:
        return max(long_candidates, key=len)[:3500]
    return ""

def _sahibinden_avif_to_jpg(url: str) -> str:
    if url.lower().endswith(".avif"):
        return url[:-5] + ".jpg"
    return url


# ================================================================
# SAHIBINDEN SCRAPER — Selenium + PageSpeed Web
# ================================================================

async def _scrape_via_pagespeed_async(url: str) -> dict:
    """Async Playwright ile PageSpeed scrape — greenlet gerektirmez."""
    headless = os.environ.get("PS_HEADLESS", "1") != "0"
    wait_sec  = int(os.environ.get("PS_WAIT_SEC", str(DEFAULT_PS_WAIT)))
    print(f"🌐 Playwright (async) PageSpeed başlatılıyor... (headless={headless}, wait={wait_sec}s)")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--disable-extensions",
                "--disable-background-networking",
                "--mute-audio",
                "--no-first-run",
            ],
        )
        ctx  = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        raw_html = ""
        try:
            await page.goto(PAGESPEED_WEB_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await _pw_accept_cookies(page)
            await page.wait_for_timeout(500)

            if not await _pw_type_url(page, url):
                return {"ok": False, "error": "URL PageSpeed'e girilemedi"}

            try:
                btn = page.locator(
                    "button:has-text('Analiz et'), button:has-text('Analyze')"
                ).first
                await btn.wait_for(state="visible", timeout=15000)
                inp = page.locator("input[name='url']")
                el  = await inp.element_handle()
                val = await page.evaluate("el => el.value", el)
                if val != url:
                    if not await _pw_type_url(page, url):
                        return {"ok": False, "error": "URL doğrulama başarısız"}
                await btn.click()
            except Exception:
                print("    ⚠ Buton bulunamadı, Enter ile gönderiliyor...")
                await page.locator("input[name='url']").press("Enter")

            print(f"    ✓ Analiz başlatıldı → bekleniyor ({wait_sec}s)")
            for i in range(wait_sec):
                await page.wait_for_timeout(1000)
                if (i + 1) % 10 == 0:
                    print(f"    ⏳ {wait_sec - i - 1}s kaldı")

            try:
                await page.wait_for_url("**/analysis/**", timeout=20000)
            except Exception:
                pass

            raw_html = await page.content()
        finally:
            await ctx.close()
            await browser.close()

    # ── Fotoğraf çıkarma ──────────────────────────────────────────────────────
    psi_photos   = _extract_psi_photos(raw_html)
    full_photos  = [p["url"] for p in psi_photos if p["type"] == "full"]
    thumb_photos = [p["url"] for p in psi_photos if p["type"] == "thumb"]
    other_photos = [p["url"] for p in psi_photos if p["type"] == "other"]

    def _photo_key(u: str) -> str:
        fname = u.rsplit("/", 1)[-1]
        clean = re.sub(r"^(?:x5_|x3_|x2_|x1_|thmb_|lthmb_)", "", fname)
        return u.rsplit("/", 1)[0] + "/" + clean

    full_keys     = {_photo_key(u) for u in full_photos}
    orphan_thumbs = [u for u in thumb_photos if _photo_key(u) not in full_keys]

    if full_photos or thumb_photos:
        photos = full_photos + orphan_thumbs
    elif other_photos:
        photos = other_photos
    else:
        photos = _parse_photos_from_raw(raw_html)

    specs    = _extract_psi_specs(raw_html)
    price    = specs.get("Fiyat") or _extract_price_tr(raw_html)
    loc_parts = [x for x in [specs.get("Mahalle",""), specs.get("İlçe",""), specs.get("Şehir","")] if x]
    location  = ", ".join(loc_parts) if loc_parts else _extract_location_from_raw(raw_html)

    # ── Sahibinden Scraper Mantığı: URL slug'ından temiz başlık türet ──
    listing_id = detect_single_listing_id(url)
    extracted_url = _extract_sahibinden_detail_url(raw_html) or url
    title = _title_from_detail_url(extracted_url, listing_id) or _title_from_detail_url(url, listing_id)
    if not title or len(title) < 4:
        candidates = re.findall(r'nodeLabel[\\"]*:\s*[\\"]*([^"]{10,120})', raw_html)
        for c in candidates:
            c_clean = html_mod.unescape(c).strip()
            if any(w in c_clean.lower() for w in ["satılık", "kiralık", "daire", "villa", "arsa", "otel", "bina", "rezidans", "ofis"]):
                title = c_clean
                break
    if not title or "pagespeed" in title.lower():
        title = f"Sahibinden İlanı #{listing_id}" if listing_id else "Gayrimenkul Portföy İlanı"

    # ── Sahibinden Scraper Mantığı: Açıklama Çıkarma ──
    description = _extract_psi_description(raw_html)

    # ── Fotoğraflar: AVIF → JPG normalizasyonu ve tekilleştirme ──
    clean_photos = []
    for ph in photos:
        ph_clean = _sahibinden_avif_to_jpg(ph)
        if ph_clean and ph_clean not in clean_photos:
            clean_photos.append(ph_clean)

    print(f"    ✓ Fotoğraf: {len(clean_photos)} | Başlık: {title[:40]}... | Fiyat: {price} | Lokasyon: {location}")
    return {
        "ok": True, "source": "sahibinden_playwright_pagespeed",
        "title": title, "price": price, "location": location,
        "specs": specs, "description": description,
        "images": clean_photos, "photo_count": len(clean_photos),
        "photo_types": {"full": len(full_photos), "thumb": len(thumb_photos), "other": len(other_photos)},
        "screenshot": "",
    }


def _scrape_via_psi_api(url: str) -> dict:
    """
    Google PageSpeed Insights v5 REST API ile bulut tabanlı render.
    Headless Chromium/Playwright gerektirmez. Cloudflare/Akamai bot korumalarını aşar.
    """
    api_key = os.environ.get("PAGESPEED_API_KEY", "AIzaSyClEth2ooknGZJ53WrgY1QKdrQunZfsNXg")
    psi_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    listing_id = detect_single_listing_id(url)
    title = _title_from_detail_url(url, listing_id) or (f"Sahibinden İlanı #{listing_id}" if listing_id else "Gayrimenkul Portföy İlanı")

    params = {
        "url": url,
        "category": "performance",
        "hl": "tr"
    }
    if api_key:
        params["key"] = api_key

    photos = []
    specs = {}
    description = ""
    price = ""
    location = "Ankara"

    try:
        resp = requests.get(psi_url, params=params, timeout=45)
        if resp.status_code == 200:
            raw_text = resp.text
            psi_photos = _extract_psi_photos(raw_text)
            full_photos  = [p["url"] for p in psi_photos if p["type"] == "full"]
            thumb_photos = [p["url"] for p in psi_photos if p["type"] == "thumb"]
            other_photos = [p["url"] for p in psi_photos if p["type"] == "other"]

            raw_photos = full_photos or thumb_photos or other_photos or _parse_photos_from_raw(raw_text)
            clean_photos = []
            for ph in raw_photos:
                ph_c = _sahibinden_avif_to_jpg(ph)
                if ph_c and ph_c not in clean_photos:
                    clean_photos.append(ph_c)
            photos = clean_photos

            specs = _extract_psi_specs(raw_text)
            price = specs.get("Fiyat") or _extract_price_tr(raw_text)
            loc_parts = [x for x in [specs.get("Mahalle",""), specs.get("İlçe",""), specs.get("Şehir","")] if x]
            if loc_parts:
                location = ", ".join(loc_parts)

            description = _extract_psi_description(raw_text)
            extracted_title = _title_from_detail_url(_extract_sahibinden_detail_url(raw_text), listing_id)
            if extracted_title and len(extracted_title) > 3:
                title = extracted_title

            return {
                "ok": True,
                "source": "sahibinden_psi_api",
                "title": title,
                "price": price,
                "location": location,
                "specs": specs,
                "description": description,
                "images": photos,
                "photo_count": len(photos),
            }
    except Exception as exc:
        print(f"    ⚠ PSI REST API hatası: {exc}")

    return {"ok": False, "error": "PSI REST API başarısız"}


def _scrape_via_slug_fallback(url: str) -> dict:
    """
    Her koşulda çalışan güvenli URL slug ayrıştırıcı.
    Kullanıcıya asla 'hata' vermez, Yiğit Narin sunum şablonu için geçerli ilan nesnesi üretir.
    """
    listing_id = detect_single_listing_id(url)
    title = _title_from_detail_url(url, listing_id)
    if not title or len(title) < 4:
        title = f"Sahibinden Portföy İlanı #{listing_id}" if listing_id else "Gayrimenkul Portföy İlanı"

    specs = {}
    if listing_id:
        specs["İlan No"] = listing_id
    specs["Konum"] = "Ankara"

    desc = f"İlan No: {listing_id or 'Belirtilmedi'} — Portföy detayları, yer gösterimi ve yatırım analizi için Gayrimenkul ve Yatırım Danışmanınız Yiğit Narin (+90 532 451 40 08) ile iletişime geçebilirsiniz."

    return {
        "ok": True,
        "source": "sahibinden_slug_fallback",
        "title": title,
        "price": "",
        "location": "Ankara",
        "specs": specs,
        "description": desc,
        "images": [],
        "photo_count": 0,
    }


def _scrape_via_pagespeed(url: str) -> dict:
    """
    Sahibinden Scraper Ana Mantığı (3 Kademeli Dayanıklı Altyapı):
    1. Kademe: Playwright headless PageSpeed ile tam render ve yüksek çözünürlüklü fotoğraflar.
    2. Kademe: Google PageSpeed Insights REST API ile cloud render (Playwright yoksa veya takılırsa).
    3. Kademe: Akıllı URL Slug ve ID analiz fallback'i (PDF üretimini asla kırmaz).
    """
    if _PLAYWRIGHT:
        try:
            res = asyncio.run(_scrape_via_pagespeed_async(url))
            if res and res.get("ok"):
                return res
            print(f"    ⚠ Playwright ok: False döndü: {res.get('error', '')}, PSI API deneniyor...")
        except Exception as e:
            print(f"    ✗ Playwright hatası: {e}, PSI API fallback devreye giriyor...")

    # 2. Kademe: Google PageSpeed REST API
    try:
        res_psi = _scrape_via_psi_api(url)
        if res_psi and res_psi.get("ok") and (res_psi.get("images") or res_psi.get("title")):
            return res_psi
    except Exception as e:
        print(f"    ✗ PSI API hatası: {e}")

    # 3. Kademe: Güvenli Slug Fallback (Her zaman ok: True döner)
    return _scrape_via_slug_fallback(url)

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
    Sahibinden ve Coldwell Banker (Cloudflare korumalı) için PageSpeed altyapısı kullanılır.
    """
    domain = urlparse(url).netloc.lower()

    if "sahibinden.com" in domain:
        return _scrape_via_pagespeed(url)
    elif "cb.com.tr" in domain or "coldwellbanker" in domain:
        # CB bot korumalı (403) olduğu için Sahibinden scraper mantığıyla PageSpeed üzerinden çekilir
        return _scrape_via_pagespeed(url)
    elif "hepsiemlak.com" in domain:
        return _scrape_hepsiemlak(url)
    elif "zingat.com" in domain:
        return _scrape_zingat(url)
    elif "emlakjet.com" in domain:
        return _scrape_emlakjet(url)
    else:
        res = _scrape_generic(url)
        if not res.get("ok"):
            # Bot koruması veya 403 durumunda PageSpeed scraper mantığına devret
            return _scrape_via_pagespeed(url)
        return res


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

    # ── Gemini client ─────────────────────────────────────────────────────────
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ Gemini client oluşturulamadı: {e}")
        return {"ok": False, "error": f"Gemini client hatası: {e}"}

    # ── Part listesi ──────────────────────────────────────────────────────────
    parts: list = []
    for mime, b64 in all_images[:12]:
        try:
            raw_bytes = base64.b64decode(b64)
            parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=f"image/{mime}"))
        except Exception as img_err:
            print(f"⚠ Görsel eklenirken hata: {img_err}")
    parts.append(types.Part.from_text(text=prompt))

    contents = [types.Content(role="user", parts=parts)]

    # JSON çıktısını zorla — parse hatasını ortadan kaldırır
    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.3,
        max_output_tokens=8192,
    )

    # ── Retry + Fallback mekanizması ──────────────────────────────────────────
    def _call_gemini(model_name: str) -> tuple[str, str | None]:
        """(raw_text, error) döner. 429 için exponential backoff uygular."""
        delay = GEMINI_RETRY_DELAY
        last_err = ""
        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            try:
                resp = client.models.generate_content(
                    model   = model_name,
                    contents= contents,
                    config  = gen_config,
                )
                text = (resp.text or "").strip()
                if text:
                    return text, None
                return "", "Gemini boş yanıt döndürdü"
            except Exception as exc:
                last_err = str(exc)
                is_429  = "429" in last_err or "RESOURCE_EXHAUSTED" in last_err
                is_404  = "404" in last_err or "NOT_FOUND" in last_err
                if is_404:
                    # Model yok — retry anlamsız
                    print(f"❌ Model bulunamadı ({model_name}): {exc}")
                    return "", f"Model bulunamadı: {model_name}"
                if is_429 and attempt < GEMINI_MAX_RETRIES:
                    print(f"⏳ 429 kota aşıldı ({model_name}), {delay}s bekleniyor... (deneme {attempt}/{GEMINI_MAX_RETRIES})")
                    time.sleep(delay)
                    delay *= 2
                else:
                    print(f"❌ Gemini API hatası ({model_name}): {exc}")
        return "", last_err

    raw_text = ""
    used_model = GEMINI_MODEL

    raw_text, err = _call_gemini(GEMINI_MODEL)

    if not raw_text and GEMINI_FALLBACK and GEMINI_FALLBACK != GEMINI_MODEL:
        print(f"🔄 Fallback model deneniyor: {GEMINI_FALLBACK}")
        used_model = GEMINI_FALLBACK
        raw_text, err = _call_gemini(GEMINI_FALLBACK)

    if not raw_text:
        quota_hint = ""
        if err and ("429" in err or "RESOURCE_EXHAUSTED" in err):
            quota_hint = (
                " | 💡 Çözüm: aistudio.google.com > Billing'i aktif edin "
                "(kart gerekmez) → Tier 1'e geçince limit 30x artar."
            )
        return {"ok": False, "error": f"Gemini hatası: {err}{quota_hint}"}

    print(f"✅ Gemini yanıtı alındı ({used_model}) — {len(raw_text)} karakter")

    # ── JSON temizleme (response_mime_type olsa da bazı modeller ``` ekler) ──
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
    report["model_used"]   = used_model

    return {"ok": True, "report": report}


# ================================================================
# CONTACT EXTRACT — CRM için ekran görüntüsünden kişi bilgisi
# ================================================================

def extract_contact_from_images(images_b64: list[str]) -> dict:
    """
    Ekran görüntüsünden tüm CRM alanlarını (Gemini Agent) doldurur.

    Parametreler:
        images_b64 — ["data:image/jpeg;base64,...", ...] listesi (maks 3)

    Dönüş (tüm alanlar None olabilir):
        {
          "ok": True,
          "seller_name", "phone",
          "listing_title", "listing_type",
          "price" (int), "district",
          "category" (fsbo|portfolio|client|project),
          "source"  (website|whatsapp|meta|manual),
          "stage",
          "notes", "rooms", "area_m2", "building_age", "floor"
        }
        {"ok": False, "error": "..."}
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY tanımlı değil"}

    if not images_b64:
        return {"ok": False, "error": "Görüntü listesi boş"}

    # Görselleri parse et (maks 3)
    parts: list = []
    for img_data in images_b64[:3]:
        parsed = _parse_uploaded(img_data)
        if parsed:
            mime, b64 = parsed
            try:
                raw_bytes = base64.b64decode(b64)
                parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=f"image/{mime}"))
            except Exception:
                pass

    if not parts:
        return {"ok": False, "error": "Geçerli görüntü verisi bulunamadı"}

    prompt = """Sen bir gayrimenkul CRM veri çıkarma ajanısın.
Sana verilen 1-3 ekran görüntüsü Türkiye'deki bir gayrimenkul ilanına ait mobil/web uygulama ekranlarıdır
(sahibinden.com, hepsiemlak, zingat, emlakjet, milligazete vb.).

GÖREV: Ekranlardaki TÜM metni oku ve aşağıdaki JSON alanlarını doldur.
ÇIKTI: Sadece geçerli JSON. Markdown, açıklama, kod bloğu YOK.

EKRAN OKUMA REHBERİ (sahibinden mobil için):
- Başlık: Sayfanın en üstündeki BÜYÜK HARF metin (örn: "SAHİBİNDEN 3+1 SATILIK,TURAN GÜNEŞ ARKA SOKAĞI...")
- Satıcı adı: Fotoğrafın hemen altındaki isim kutusu (örn: "Orkun K.") VEYA telefon pop-up'ındaki isim
- Telefon: Yeşil buton içindeki veya "Cep" / "Sabit" yanındaki numara (örn: "0 (546) 590 61 XX")
  → Parantez, boşluk, tire kaldır → 05465906100 formatına getir
  → Numara kısmi görünüyorsa (son rakamlar gizli/bulanık) yine de gördüğün kadarını yaz
- Fiyat: "Fiyat" satırındaki mavi/renkli rakam (örn: "13.900.000 TL" → 13900000)
- Konum breadcrumb: "Ankara, Çankaya, Yıldızevler Mh." → district=Çankaya, city=Ankara
- Kategori breadcrumb: "Emlak > Konut > Satılık > Daire" → listing_type=Satılık
- Emlak Tipi satırı: "Satılık Daire", "Kiralık Daire" vb.
- "Hesap Açma Tarihi" → satıcı bireysel kullanıcı → category=fsbo
- İlan başlığında "SAHİBİNDEN" kelimesi → category=fsbo (mülk sahibi)
- İlan başlığında "3+1", "2+1" gibi ifade → rooms alanı

JSON ŞEMASI:
{
  "seller_name":   "Satıcı adı — fotoğraf altı veya telefon pop-up'ından (örn: Orkun K.)",
  "phone":         "05XXXXXXXXX — 11 hane, sadece rakam, 0 ile başlayan",
  "listing_title": "İlanın TAM başlığı — sayfanın en üstündeki büyük metin, kelimesi kelimesine",
  "listing_type":  "Satılık veya Kiralık",
  "price":         "Sadece rakamlar, noktalama yok (örn: 13900000)",
  "district":      "Sadece ilçe (örn: Çankaya) — şehir veya mahalle değil",
  "category":      "fsbo | portfolio | client | project",
  "source":        "website | whatsapp | meta | manual",
  "stage":         "ilk_temas | degerleme | sozlesme | ilanda | gorunum | teklif | satildi",
  "notes":         "Kısa özet: oda sayısı, m², kat, bina yaşı, öne çıkan özellikler",
  "rooms":         "3+1 gibi oda formatı",
  "area_m2":       "Sadece sayı (brüt m²)",
  "building_age":  "Sayı (yıl)",
  "floor":         "7/10 gibi kat/toplam format"
}

DOLDURMA KURALLARI:
1. Ekranda net göremediğin alanı null bırak — ASLA tahmin etme.
2. Telefon: parantez/boşluk/tire kaldır, 0 ile başlayan 11 hane yap.
   Kısmi görünüyorsa (son 2 hane gizli) yine de gördüğün kadarıyla doldur.
3. price: SADECE rakamlar — 13.900.000 TL → 13900000
4. district: İlçe adı — "Ankara, Çankaya, Yıldızevler Mh." → "Çankaya"
5. listing_type: breadcrumb'daki "Satılık"/"Kiralık" VEYA "Emlak Tipi" satırından al.
6. category:
   - Başlıkta "SAHİBİNDEN" VEYA "Hesap Açma Tarihi" var → "fsbo"
   - Emlakçı/ofis adı var → "portfolio"
7. source: sahibinden/hepsiemlak/zingat mobil ekranı → "website"
8. stage: yeni ilan ekran görüntüsü → "ilk_temas"
9. notes: başlıktan ve görünen özellik tablolarından kısa özet yap."""
    parts.append(types.Part.from_text(text=prompt))
    contents = [types.Content(role="user", parts=parts)]

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
        max_output_tokens=800,
    )

    import time

    # Deneme sırası: ana model → fallback → ek güvenilir modeller (503'e karşı)
    models_to_try = [GEMINI_MODEL]
    if GEMINI_FALLBACK and GEMINI_FALLBACK != GEMINI_MODEL:
        models_to_try.append(GEMINI_FALLBACK)
    for extra in ("gemini-1.5-flash", "gemini-1.5-pro"):
        if extra not in models_to_try:
            models_to_try.append(extra)

    client     = genai.Client(api_key=api_key)
    last_error = "Bilinmeyen hata"

    def _clean_str(val) -> str | None:
        """JSON'dan gelen değeri temizle; boş/null ise None döndür."""
        if not isinstance(val, str):
            return None
        val = val.strip()
        if val.lower() in ("null", "none", "", "yok", "bilinmiyor"):
            return None
        return val

    for model_name in models_to_try:
        for attempt in range(2):           # her model için en fazla 2 deneme
            try:
                if attempt > 0:
                    time.sleep(2)

                print(f"🔄 extract_contact deniyor: {model_name} (deneme {attempt+1})")
                resp = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config,
                )
                raw = (resp.text or "").strip()

                # JSON temizle
                if "```" in raw:
                    for part in raw.split("```"):
                        p = part.strip().lstrip("json").strip()
                        if p.startswith("{"):
                            raw = p
                            break
                start = raw.find("{")
                end   = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]

                data          = json.loads(raw)
                seller_name   = _clean_str(data.get("seller_name"))
                phone         = _clean_str(data.get("phone"))
                listing_title = _clean_str(data.get("listing_title"))
                listing_type  = _clean_str(data.get("listing_type"))
                rooms         = _clean_str(data.get("rooms"))
                area_m2       = _clean_str(data.get("area_m2"))
                building_age  = _clean_str(data.get("building_age"))
                floor         = _clean_str(data.get("floor"))
                notes_raw     = _clean_str(data.get("notes"))
                category      = _clean_str(data.get("category"))
                source        = _clean_str(data.get("source"))
                stage         = _clean_str(data.get("stage"))

                # price: sadece rakam bırak
                price_raw = _clean_str(data.get("price"))
                price: int | None = None
                if price_raw:
                    digits = "".join(filter(str.isdigit, price_raw))
                    price = int(digits) if digits else None

                # district
                district = _clean_str(data.get("district"))

                # listing_type normalize
                if listing_type and listing_type not in ("Satılık", "Kiralık"):
                    if "kira" in listing_type.lower():
                        listing_type = "Kiralık"
                    elif "satı" in listing_type.lower():
                        listing_type = "Satılık"
                    else:
                        listing_type = None

                # category normalize
                valid_cats = ("fsbo", "portfolio", "client", "project")
                if category and category not in valid_cats:
                    cat_lower = category.lower()
                    if "fsbo" in cat_lower or "sahib" in cat_lower:
                        category = "fsbo"
                    elif "portf" in cat_lower or "emlak" in cat_lower:
                        category = "portfolio"
                    elif "client" in cat_lower or "müşteri" in cat_lower or "musteri" in cat_lower:
                        category = "client"
                    elif "proje" in cat_lower or "project" in cat_lower:
                        category = "project"
                    else:
                        category = None

                # source normalize
                valid_src = ("website", "whatsapp", "meta", "manual")
                if source and source not in valid_src:
                    src_lower = source.lower()
                    if "whatsapp" in src_lower or "wa" in src_lower:
                        source = "whatsapp"
                    elif "meta" in src_lower or "facebook" in src_lower or "instagram" in src_lower:
                        source = "meta"
                    elif "site" in src_lower or "web" in src_lower or "sahibinden" in src_lower or "hepsi" in src_lower:
                        source = "website"
                    else:
                        source = "manual"

                # stage normalize — valid stage id'leri CRM ile eşleştir
                valid_stages = (
                    "ilk_temas", "degerleme", "sozlesme", "ilanda",
                    "gorunum", "teklif", "satildi",
                    "aktif", "tamamlandi",
                )
                if stage and stage not in valid_stages:
                    stage = "ilk_temas"   # default: yeni ilan → ilk temas

                # notes: ek bilgileri birleştir
                notes_parts = []
                if notes_raw:
                    notes_parts.append(notes_raw)
                if rooms:         notes_parts.append(f"Oda: {rooms}")
                if area_m2:       notes_parts.append(f"Alan: {area_m2} m²")
                if floor:         notes_parts.append(f"Kat: {floor}")
                if building_age:  notes_parts.append(f"Bina yaşı: {building_age}")
                if listing_type:  notes_parts.append(f"Tür: {listing_type}")
                notes_combined = " | ".join(notes_parts) if notes_parts else None

                print(f"✅ extract_contact (FULL) başarılı: {model_name} | "
                      f"seller={seller_name} | price={price} | district={district} | cat={category}")
                return {
                    "ok":            True,
                    # Kimlik
                    "seller_name":   seller_name,
                    "phone":         phone,
                    # İlan
                    "listing_title": listing_title,
                    "listing_type":  listing_type,
                    # CRM alanları
                    "price":         price,
                    "district":      district,
                    "category":      category,
                    "source":        source,
                    "stage":         stage,
                    "notes":         notes_combined,
                    # Detaylar (opsiyonel referans)
                    "rooms":         rooms,
                    "area_m2":       area_m2,
                    "building_age":  building_age,
                    "floor":         floor,
                }

            except Exception as e:
                last_error = str(e)
                print(f"❌ extract_contact [{model_name}] deneme {attempt+1}: {e}")
                if "503" not in last_error and "UNAVAILABLE" not in last_error:
                    break   # 503 değilse bu modeli bırak
                time.sleep(3)

    print(f"❌ extract_contact_from_images tüm modeller başarısız: {last_error}")
    return {"ok": False, "error": f"AI servisi şu an yoğun, lütfen tekrar deneyin. ({last_error[:120]})"}
