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

# Playwright opsiyonel — sadece sahibinden scrape için gerekli
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    _PLAYWRIGHT = True
except ImportError:
    _PLAYWRIGHT = False
_SELENIUM = _PLAYWRIGHT  # geriye dönük uyumluluk için

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
# PLAYWRIGHT HELPERS (Sahibinden için)
# ================================================================

def _pw_accept_cookies(page) -> None:
    selectors = [
        "button:has-text('Tümünü kabul')",
        "button:has-text('Accept all')",
        "button:has-text('Kabul et')",
        "#onetrust-accept-btn-handler",
    ]
    for sel in selectors:
        try:
            page.locator(sel).click(timeout=4000)
            page.wait_for_timeout(400)
            return
        except Exception:
            pass


def _pw_type_url(page, target_url: str, max_attempts: int = 4) -> bool:
    """PageSpeed URL input'una URL'yi güvenilir şekilde yazar."""
    for attempt in range(1, max_attempts + 1):
        try:
            inp = page.locator("input[name='url']")
            inp.wait_for(state="visible", timeout=15000)
            page.wait_for_timeout(300)
            # JS ile value ata
            page.evaluate(
                """(args) => {
                    const el = args[0];
                    el.focus(); el.value = '';
                    el.value = args[1];
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                }""",
                [inp.element_handle(), target_url],
            )
            page.wait_for_timeout(300)
            val = page.evaluate("el => el.value", inp.element_handle())
            if val == target_url:
                print(f"    ✓ URL girildi (deneme {attempt})")
                return True
            # send_keys fallback
            inp.click()
            inp.fill(target_url)
            page.wait_for_timeout(300)
            val = page.evaluate("el => el.value", inp.element_handle())
            if val == target_url:
                print(f"    ✓ URL fill ile girildi (deneme {attempt})")
                return True
            print(f"    ⚠ Deneme {attempt} başarısız, tekrar...")
            page.wait_for_timeout(1000)
        except Exception as exc:
            print(f"    ⚠ Deneme {attempt} hatası: {exc}")
            page.wait_for_timeout(1500)
    print("    ✗ URL girilemedi.")
    return False


# ================================================================
# SAHIBINDEN SCRAPER — Selenium + PageSpeed Web
# ================================================================

def _scrape_via_pagespeed(url: str) -> dict:
    """
    Playwright ile pagespeed.web.dev'e gidip URL'yi analiz ettirir.
    Selenium'dan çok daha stabil — container ortamında (Render vb.) çalışır.
    """
    if not _PLAYWRIGHT:
        return {
            "ok": False,
            "error": "Playwright kurulu değil: pip install playwright && playwright install chromium",
        }

    headless = os.environ.get("PS_HEADLESS", "1") != "0"
    wait_sec  = int(os.environ.get("PS_WAIT_SEC", str(DEFAULT_PS_WAIT)))

    print(f"🌐 Playwright PageSpeed başlatılıyor... (headless={headless}, wait={wait_sec}s)")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
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
            ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()

            try:
                page.goto(PAGESPEED_WEB_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                _pw_accept_cookies(page)
                page.wait_for_timeout(500)

                if not _pw_type_url(page, url):
                    return {"ok": False, "error": "URL PageSpeed'e girilemedi"}

                # Analiz et butonunu bul ve tıkla
                try:
                    btn = page.locator(
                        "button:has-text('Analiz et'), button:has-text('Analyze')"
                    ).first
                    btn.wait_for(state="visible", timeout=15000)
                    # URL hâlâ doğru mu?
                    inp = page.locator("input[name='url']")
                    val = page.evaluate("el => el.value", inp.element_handle())
                    if val != url:
                        if not _pw_type_url(page, url):
                            return {"ok": False, "error": "URL doğrulama başarısız"}
                    btn.click()
                except Exception:
                    print("    ⚠ Buton bulunamadı, Enter ile gönderiliyor...")
                    page.locator("input[name='url']").press("Enter")

                print(f"    ✓ Analiz başlatıldı → bekleniyor ({wait_sec}s)")
                print("    ⏳", end="", flush=True)
                for i in range(wait_sec):
                    page.wait_for_timeout(1000)
                    if (i + 1) % 10 == 0:
                        print(f" {wait_sec - i - 1}s", end="", flush=True)
                print()

                # /analysis/ URL'sine geçmesini bekle
                try:
                    page.wait_for_url("**/analysis/**", timeout=20000)
                except Exception:
                    pass

                raw_html = page.content()

            finally:
                ctx.close()
                browser.close()

        # ── Fotoğraf çıkarma ──────────────────────────────────────────────────
        psi_photos   = _extract_psi_photos(raw_html)
        full_photos  = [p["url"] for p in psi_photos if p["type"] == "full"]
        thumb_photos = [p["url"] for p in psi_photos if p["type"] == "thumb"]
        other_photos = [p["url"] for p in psi_photos if p["type"] == "other"]

        def _photo_key(u: str) -> str:
            fname = u.rsplit("/", 1)[-1]
            clean = re.sub(r"^(?:x5_|x3_|x2_|x1_|thmb_|lthmb_)", "", fname)
            return u.rsplit("/", 1)[0] + "/" + clean

        full_keys      = {_photo_key(u) for u in full_photos}
        orphan_thumbs  = [u for u in thumb_photos if _photo_key(u) not in full_keys]

        if full_photos or thumb_photos:
            photos = full_photos + orphan_thumbs
        elif other_photos:
            photos = other_photos
        else:
            photos = _parse_photos_from_raw(raw_html)

        # ── Specs + fiyat + lokasyon ──────────────────────────────────────────
        specs    = _extract_specs_from_raw(raw_html)
        price    = specs.get("Fiyat") or _extract_price_tr(raw_html)

        loc_parts = [x for x in [
            specs.get("Mahalle", ""),
            specs.get("İlçe", ""),
            specs.get("Şehir", ""),
        ] if x]
        location = ", ".join(loc_parts) if loc_parts else _extract_location_from_raw(raw_html)

        title = url
        try:
            from bs4 import BeautifulSoup as _BS
            soup_tmp = _BS(html_mod.unescape(raw_html), "html.parser")
            t_tag = soup_tmp.find("title")
            if t_tag:
                title = t_tag.get_text(strip=True) or url
        except Exception:
            pass

        print(f"    ✓ Fotoğraf: {len(photos)} | Fiyat: {price} | Lokasyon: {location}")

        return {
            "ok":          True,
            "source":      "sahibinden_playwright_pagespeed",
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
        print(f"    ✗ Playwright hatası: {e}")
        return {"ok": False, "error": str(e)}


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
