"""
================================================================
portfolio_progress.py — Nexa CRM "Portföy İlerleme" Motoru
================================================================

Gayrimenkul portföyünün (konut) ilerlemesini takip eder:
  - OCR:      Proje sahibinden gelen görsellerin Gemini vision ile
              analizi (metin okuma + inşaat aşaması tespiti + sorunlar)
  - Analiz:   "Ne yaptık + nasıl devam etmeliyiz" raporu (JSON)
  - Rapor:    Markdown gövde üretimi (PDF için saklanır)
  - Sohbet:   Portföy bağlamlı chatbot context kurulumu

Kullanım:
  from portfolio_progress import (
      ocr_images, analyze_portfolio, build_report_body,
      portfolio_chat_context, portfolio_engine_status
  )

Girdiler (ocr_images):
  images: [{"key": str, "data_b64": str, "mime_type": str}, ...]
      - data_b64: ham base64 (data: öneki olabilir, otomatik temizlenir)
      - en fazla 8 görsel / çağrı (REST inline_data limiti)

Girdiler (analyze_portfolio):
  lead_knowledge: dict — lead/portföy künyesi
  ocr_results:    list — ocr_images çıktısı
  notes:          list — kullanıcı notları

Model:
  Ana: PORTFOLIO_GEMINI_MODEL env (varsayılan gemini-2.5-flash)
  Fallback zinciri: gemini-2.5-flash → gemini-2.5-flash-lite → gemini-3.5-flash-lite
  (araştırma notu: gemini-2.5-pro yeni kullanıcılar için 404 döndürüyor)
================================================================
"""

import os
import json
import base64
import re
import time
from datetime import datetime, timezone
import html as _html

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("PORTFOLIO_GEMINI_MODEL", "gemini-2.5-flash")

# 429 "limit: 0" (ücretsiz kota yok) veya 404 (model yok) durumunda sırayla denenir
GEMINI_FALLBACKS     = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite"]
MAX_IMAGES_PER_CALL  = 8
GEMINI_MAX_RETRIES   = 3
GEMINI_RETRY_DELAY   = 8   # saniye; 503 yük hatasında başlangıç bekleme

OCR_PROMPT = """Bu görsel(ler) bir gayrimenkul projesinin ilerleme fotoğraf(ları)dır.
Görevin her görsel için:
1. Görselde gördüğün TÜM yazıları Türkçe olarak OCR et (tabela, levha, belge, el yazısı).
2. İnşaat/durum analizi: hangi aşamada (TEMEL / KABA / İNCE / TESLİM / BELİRSİZ),
   tamamlanmış işler, devam eden işler, olası sorunlar (çatlak, eksik izolasyon vb.).
3. Proje sahibi görselin neyi belgelediğini bilmiyoruz — tahminlerini 'muhtemel' gibi
   yumuşak ifadelerle yaz. Emin olmadığını 'belirsiz' olarak işaretle.

Çıktı SADECE JSON, başka hiçbir metin yazma:
{
  "bulgular": [
    {
      "gorsel_index": 1,
      "ocr_metni": "görseldeki tüm okunabilir yazılar",
      "asama": "TEMEL|KABA|INCE|TESLIM|BELIRSIZ",
      "tamamlanan_isler": ["..."],
      "devam_eden_isler": ["..."],
      "sorunlar": [{"sorun": "...", "onem": "yuksek|orta|dusuk"}]
    }
  ]
}"""

ANALIZ_PROMPT = """Sen Türkiye'nin en deneyimli gayrimenkul proje danışmanlarından birisin.
Aşağıdaki portföy bilgilerini analiz ederek ultra detaylı ilerleme değerlendirmesi yap.

## PORTFÖY KÜNYESİ
{lead_knowledge}

## KULLANICI NOTLARI (zaman çizelgesi)
{notes_text}

## GÖRSEL ANALİZ BULGULARI (OCR + durum tespiti)
{ocr_text}

## GÖREV
Hem "şu ana kadar ne yaptık" hem "nasıl devam etmeliyiz" sorularını yanıtla.
Kurallar:
- SADECE yukarıdaki veriden konuş, dışarıdan bilgi ekleme, tahmin etme.
- Eksik bilgi varsa bunu "kanıt yok" olarak belirt.
- Tüm metinler Türkçe, mesleki ve somut olsun.

Çıktı SADECE JSON, başka hiçbir metin yazma:
{{
  "ozet": "3-4 cümlelik yönetici özeti",
  "ne_yaptik": ["somut tamamlanmış işler"],
  "ne_yapilmadi": ["henüz başlanmamış/eksik işler"],
  "kpi": {{
    "suanki_durum_pct": 0-100,
    "tamamlanan_adimlar": n,
    "kalan_adimlar": n,
    "aktivite_duzeyi": "yuksek|orta|dusuk",
    "kanit_kapsama_pct": 0-100
  }},
  "riskler": [{{"risk": "...", "seviye": "YUKSEK|ORTA|DUSUK", "cozum": "..."}}],
  "aksiyonlar": [{{"yapilacak": "...", "aciliyet": "HEMEN|BU_HAFTA|SONRAKI_HAFTA",
                   "beklenen_sonuc": "..."}}],
  "kanit_oranlari": [{{"kanit": "...", "goruntu_var": true|false, "aciklama": "..."}}]
}}"""


def portfolio_engine_status() -> dict:
    configured = bool(GEMINI_API_KEY)
    return {
        "ok":         configured,
        "configured": configured,
        "model":      GEMINI_MODEL,
        "fallbacks":  GEMINI_FALLBACKS,
        "error":      None if configured else "GEMINI_API_KEY tanımlanmamış",
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_base64(data_b64: str) -> str:
    if "," in data_b64:
        data_b64 = data_b64.split(",", 1)[1]
    return data_b64.strip()


def _strip_code_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?", "", text.strip())
    return re.sub(r"```$", "", text.strip()).strip()


def _gemini_call(payload: dict, model: str, timeout: int = 120) -> dict:
    """Tek Gemini REST çağrısı. Fallback/retry mantığını _call_with_fallback yönetir.

    Dönüş: {"ok": True, "data": parsed_json}
           {"ok": False, "error": msg, "retryable": bool, "switch_model": bool}
    """
    import requests as req

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )
    try:
        resp = req.post(url, json=payload, timeout=timeout)
        data = resp.json()
    except req.exceptions.Timeout:
        return {"ok": False, "error": "API timeout", "retryable": True, "switch_model": False}
    except Exception as e:
        return {"ok": False, "error": str(e), "retryable": True, "switch_model": False}

    if resp.ok:
        candidates = data.get("candidates", [])
        if not candidates:
            return {"ok": False, "error": "Gemini boş yanıt döndürdü",
                    "retryable": True, "switch_model": False}
        raw = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in raw).strip()
        try:
            return {"ok": True, "data": json.loads(_strip_code_fences(text))}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"JSON parse hatası: {e}",
                    "retryable": False, "switch_model": False}

    err     = data.get("error", {})
    err_msg = err.get("message", str(data))
    status  = resp.status_code

    # Model yok (404) → yedek modele geç
    if status == 404 or "not found" in err_msg.lower():
        return {"ok": False, "error": err_msg, "retryable": False, "switch_model": True}

    # Kotası bitmiş (429 limit:0) → yedek modele geç
    if status == 429 and "limit: 0" in err_msg:
        return {"ok": False, "error": err_msg, "retryable": False, "switch_model": True}

    # 503 yük / 429 hız → retry edilebilir (süre bilgisi hata mesajında)
    return {"ok": False, "error": err_msg, "retryable": True, "switch_model": False}


def _call_with_fallback(payload: dict, preferred_model: str | None = None) -> dict:
    """Fallback zinciri + backoff retry ile Gemini çağrısı yapar.

    Sıra: preferred_model (yoksa GEMINI_MODEL) → GEMINI_FALLBACKS (tekrar edenler atlanır)
    """
    models_to_try = []
    for m in ([preferred_model, GEMINI_MODEL] + GEMINI_FALLBACKS):
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = "Bilinmeyen hata"
    for attempt_model in models_to_try:
        delay = GEMINI_RETRY_DELAY
        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            result = _gemini_call(payload, attempt_model)
            if result.get("ok"):
                if attempt_model != models_to_try[0]:
                    print(f"✅ Gemini yanıt verdi (yedek: {attempt_model})")
                return result

            last_error = result.get("error", last_error)

            if result.get("switch_model"):
                print(f"⛔ {attempt_model}: {last_error} — yedek modele geçiliyor...")
                break

            if result.get("retryable"):
                print(f"⏳ {attempt_model} ({attempt}/{GEMINI_MAX_RETRIES}): {last_error} — {delay}s bekleniyor...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue

            # retryable değil → bu modelden vazgeç
            break

        print(f"❌ {attempt_model} tüm denemeler başarısız — yedek modele geçiliyor...")

    return {"ok": False, "error": last_error}


def ocr_images(
    images: list,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Görsel listesini Gemini vision ile OCR eder (en fazla 8 görsel / çağrı).

    images: [{"key": str, "data_b64": str, "mime_type": str}]
    Dönüş:  {"ok": True, "bulgular": [{gorsel_index, ocr_metni, asama,
             tamamlanan_isler, devam_eden_isler, sorunlar, ...}]}
            {"ok": False, "error": str}
    """
    global GEMINI_API_KEY
    if api_key:
        GEMINI_API_KEY = api_key

    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY tanımlanmamış"}

    if not images:
        return {"ok": False, "error": "Görsel listesi boş"}

    batch = images[:MAX_IMAGES_PER_CALL]

    parts: list = []
    for i, img in enumerate(batch):
        mime = img.get("mime_type") or "image/jpeg"
        b64  = _clean_base64(img.get("data_b64", ""))
        if not b64:
            continue
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
        parts.append({"text": f"[Görüntü {i+1}: gayrimenkul projesi ilerleme fotoğrafı]"})
    parts.append({"text": OCR_PROMPT})

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature":      0.2,
            "maxOutputTokens":  4096,
            "responseMimeType": "application/json",
        },
    }

    result = _call_with_fallback(payload, model)

    if not result.get("ok"):
        return result

    data = result.get("data", {})
    bulgular = data.get("bulgular") if isinstance(data, dict) else None
    if bulgular is None and isinstance(data, list):
        bulgular = data

    if not isinstance(bulgular, list):
        # Model her görsel için tek JSON ürettiyse tek öğeye sar
        if isinstance(data, dict) and "gorsel_index" in data:
            bulgular = [data]
        else:
            return {"ok": False, "error": "Model beklenen JSON şemasını döndürmedi"}

    # Görsel anahtarını bulguya bağla (gorsel_index 1-bazlı)
    merged = []
    for b in bulgular:
        idx = b.get("gorsel_index")
        if isinstance(idx, int) and 1 <= idx <= len(batch):
            b["key"] = batch[idx - 1].get("key")
        elif len(merged) < len(batch):
            b["key"] = batch[len(merged)].get("key")
        merged.append(b)

    return {"ok": True, "bulgular": merged}


def analyze_portfolio(
    lead_knowledge: dict,
    ocr_results: list,
    notes: list,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Portföy ilerleme analizi: ne yaptık + nasıl devam etmeliyiz (JSON).

    Dönüş: {"ok": True, "analiz": {...Bölüm 5.1 şeması...}} | {"ok": False, "error"}
    """
    global GEMINI_API_KEY
    if api_key:
        GEMINI_API_KEY = api_key

    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY tanımlanmamış"}

    def _kv(k, label):
        v = lead_knowledge.get(k)
        return f"{label}: {v}" if v else f"{label}: Belirtilmiş"

    lead_text = "\n".join([
        _kv("name", "Proje/Portföy adı"),
        _kv("phone", "İletişim"),
        _kv("district", "Konum/İlçe"),
        _kv("price", "Hedef/Değer (TL)"),
        _kv("stage", "Mevcut aşama"),
        _kv("notes", "Ek notlar"),
    ])

    notes_text = ""
    if notes:
        for n in notes[:15]:
            dt  = str(n.get("createdAt", ""))[:16] if n.get("createdAt") else ""
            txt = (n.get("text", "") or "")[:300]
            notes_text += f"  [{dt}] {txt}\n"
    else:
        notes_text = "  (kullanıcı notu yok)"

    ocr_text = ""
    if ocr_results:
        for b in ocr_results:
            ocr_text += (
                f"- Görsel [{b.get('key', '?')}]: aşama={b.get('asama', '?')} | "
                f"OCR: {(b.get('ocr_metni') or '')[:400]}\n"
            )
            if b.get("sorunlar"):
                for s in b.get("sorunlar", []):
                    ocr_text += f"    sorun: {s.get('sorun')} ({s.get('onem', '?')})\n"
    else:
        ocr_text = "  (görsel analizi yok)"

    prompt = ANALIZ_PROMPT.format(
        lead_knowledge=lead_text,
        notes_text=notes_text,
        ocr_text=ocr_text,
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature":      0.3,
            "maxOutputTokens":  8192,
            "responseMimeType": "application/json",
        },
    }

    result = _call_with_fallback(payload, model)
    if not result.get("ok"):
        return result

    data = result.get("data", {})
    if not isinstance(data, dict):
        return {"ok": False, "error": "Model beklenen JSON şemasını döndürmedi"}

    analiz = {
        "ozet":             data.get("ozet", ""),
        "ne_yaptik":        data.get("ne_yaptik", []),
        "ne_yapilmadi":     data.get("ne_yapilmadi", []),
        "kpi":              data.get("kpi", {}),
        "riskler":          data.get("riskler", []),
        "aksiyonlar":       data.get("aksiyonlar", []),
        "kanit_oranlari":   data.get("kanit_oranlari", []),
        "generated_at":     _now_iso(),
        "model":            result.get("model", GEMINI_MODEL),
    }
    return {"ok": True, "analiz": analiz}


def build_report_body(
    analiz: dict,
    lead_knowledge: dict,
    media: list,
    notes: list,
    report_id: str,
    verdict_summary: str | None = None,
) -> str:
    """Analiz + kanıtlardan PDF için Markdown gövde üretir (Firestore'da saklanır)."""
    from datetime import datetime as _dt

    title = lead_knowledge.get("name") or lead_knowledge.get("title") or "Portföy"

    lines = [
        f"# İLERLEME RAPORU — {title}",
        f"> Rapor No: {report_id} | Tarih: {_dt.now().strftime('%d.%m.%Y %H:%M')} | "
        f"Model: {analiz.get('model', GEMINI_MODEL)}",
        "",
        "## 1. Yönetici Özeti",
        analiz.get("ozet") or verdict_summary or "(özet üretilemedi)",
        "",
        "## 2. Mevcut Durum",
    ]

    kpi = analiz.get("kpi", {}) or {}
    pct = kpi.get("suanki_durum_pct")
    lines.append(f"- Genel ilerleme: %{pct if pct is not None else '—'}")
    lines.append(f"- Tamamlanan adımlar: {kpi.get('tamamlanan_adimlar', '—')}")
    lines.append(f"- Kalan adımlar: {kpi.get('kalan_adimlar', '—')}")
    lines.append(f"- Aktivite düzeyi: {kpi.get('aktivite_duzeyi', '—')}")
    lines.append(f"- Kanıt kapsaması: %{kpi.get('kanit_kapsama_pct', '—')}")
    lines.append("")

    lines.append("## 3. Ne Yaptık (Kanıtlarla)")
    for item in analiz.get("ne_yaptik", []) or []:
        lines.append(f"- {item}")
    lines.append("")

    if notes:
        lines.append("## 4. Zaman Çizelgesi (Notlar)")
        for n in sorted(notes, key=lambda x: str(x.get("createdAt", "")), reverse=True)[:15]:
            dt = str(n.get("createdAt", ""))[:16] if n.get("createdAt") else ""
            lines.append(f"- [{dt}] {str(n.get('text', ''))[:300]}")
        lines.append("")

    lines.append("## 5. Eksikler ve Dikkat Edilecekler")
    for item in analiz.get("ne_yapilmadi", []) or []:
        lines.append(f"- {item}")
    lines.append("")

    riskler = analiz.get("riskler", []) or []
    if riskler:
        lines.append("## 6. Riskler")
        lines.append("| Risk | Seviye | Çözüm |")
        lines.append("|---|---|---|")
        for r in riskler:
            lines.append(f"| {r.get('risk', '')} | {r.get('seviye', '')} | {r.get('cozum', '')} |")
        lines.append("")

    lines.append("## 7. KPI")
    lines.append("| Gösterge | Değer |")
    lines.append("|---|---|")
    lines.append(f"| Tamamlanan adım | {kpi.get('tamamlanan_adimlar', '—')} |")
    lines.append(f"| Kalan adım | {kpi.get('kalan_adimlar', '—')} |")
    lines.append(f"| Genel durum | %{kpi.get('suanki_durum_pct', '—')} |")
    lines.append(f"| Akış aktivitesi | {kpi.get('aktivite_duzeyi', '—')} |")
    lines.append(f"| Kanıt kapsaması | %{kpi.get('kanit_kapsama_pct', '—')} |")
    lines.append(f"| Görsel sayısı | {len(media)} |")
    lines.append("")

    aksiyonlar = analiz.get("aksiyonlar", []) or []
    if aksiyonlar:
        lines.append("## 8. Aksiyon Planı (Nasıl Devam Etmeliyiz)")
        for grup in ("HEMEN", "BU_HAFTA", "SONRAKI_HAFTA"):
            items = [a for a in aksiyonlar if str(a.get("aciliyet", "")).upper() == grup]
            if not items:
                continue
            lbl = {"HEMEN": "Hemen", "BU_HAFTA": "Bu Hafta", "SONRAKI_HAFTA": "Sonraki Hafta"}[grup]
            lines.append(f"### {lbl}")
            for a in items:
                sonuc = a.get("beklenen_sonuc", "")
                lines.append(f"- {a.get('yapilacak', '')}" + (f" → {sonuc}" if sonuc else ""))
            lines.append("")

    lines.append("## 9. Kapanış")
    lines.append("Bu rapor, portföy görsellerinin AI destekli analizi ve danışman "
                 "notlarından otomatik üretilmiştir. Sonraki kontrol için 7-14 gün "
                 "içinde yeni görselleri sisteme yüklemeniz önerilir.")
    return "\n".join(lines)


def portfolio_chat_context(
    lead_knowledge: dict,
    notes: list,
    ocr_results: list,
    last_reports: list,
) -> str:
    """Portföy chatbot system_instruction için bağlam metni üretir."""
    ctx = []
    ctx.append(f"PORTFÖY: {lead_knowledge.get('name', 'Belirtilmemiş')} | "
               f"Konum: {lead_knowledge.get('district', '?')} | "
               f"Aşama: {lead_knowledge.get('stage', '?')} | "
               f"Hedef: {lead_knowledge.get('price', '?')} TL")
    if lead_knowledge.get("notes"):
        ctx.append(f"GENEL NOT: {str(lead_knowledge.get('notes'))[:400]}")

    if notes:
        ctx.append("ZAMAN ÇİZELGESİ (son 15 not):")
        for n in notes[:15]:
            dt  = str(n.get("createdAt", ""))[:16] if n.get("createdAt") else ""
            ctx.append(f"  [{dt}] {str(n.get('text', ''))[:200]}")

    if ocr_results:
        ctx.append("GÖRSEL KANITLAR (OCR özetleri):")
        for b in ocr_results[:8]:
            ctx.append(f"  - {b.get('key', '?')}: aşama={b.get('asama', '?')} | "
                       f"{(b.get('ocr_metni') or '')[:250]}")

    if last_reports:
        latest = last_reports[0]
        ctx.append(f"SON RAPOR ÖZETİ ({str(latest.get('createdAt', ''))[:10]}):")
        body_md = str(latest.get("bodyMd", ""))[:800]
        ctx.append(body_md)

    return "\n".join(ctx)


# ================================================================
# PDF RENDER (ReportLab) — kapak + doughnut + progress + tablo + galeri
# ================================================================

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts")

_NAVY    = None  # lazy: reportlab.colors.HexColor
_GOLD    = None
_GREEN   = None
_RED     = None
_ORANGE  = None
_LIGHT   = None
_HEX_GRAY = None


def _init_colors():
    global _NAVY, _GOLD, _GREEN, _RED, _ORANGE, _LIGHT, _HEX_GRAY
    if _NAVY is None:
        from reportlab.lib import colors as _c
        _NAVY    = _c.HexColor("#1B2A4A")
        _GOLD    = _c.HexColor("#C9A227")
        _GREEN   = _c.HexColor("#2E7D32")
        _RED     = _c.HexColor("#C62828")
        _ORANGE  = _c.HexColor("#EF6C00")
        _LIGHT   = _c.HexColor("#F2F4F8")
        _HEX_GRAY = _c.HexColor("#707070")


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu",
            os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold",
            os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))


def _make_styles():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors as _c
    _init_colors(); _register_fonts()
    return {
        "title":    ParagraphStyle("t",   fontName="DejaVu-Bold", fontSize=20, leading=26,
                                   textColor=_NAVY, spaceBefore=14, spaceAfter=6),
        "h2":       ParagraphStyle("h2",  fontName="DejaVu-Bold", fontSize=14, leading=18,
                                   textColor=_NAVY, spaceBefore=18, spaceAfter=6),
        "h3":       ParagraphStyle("h3",  fontName="DejaVu-Bold", fontSize=11.5, leading=15,
                                   textColor=_GOLD, spaceBefore=10, spaceAfter=4),
        "body":     ParagraphStyle("b",   fontName="DejaVu", fontSize=9.5, leading=13.5,
                                   textColor=_c.black, spaceAfter=4),
        "quote":    ParagraphStyle("q",   fontName="DejaVu", fontSize=9, leading=12.5,
                                   textColor=_c.HexColor("#707070"), leftIndent=10, spaceAfter=4),
        "meta":     ParagraphStyle("m",   fontName="DejaVu", fontSize=8.5, leading=12,
                                   textColor=_c.HexColor("#707070"), spaceAfter=10),
        "caption":  ParagraphStyle("c",   fontName="DejaVu", fontSize=7.5, leading=9.5,
                                   textColor=_c.HexColor("#707070"), alignment=TA_CENTER),
    }


def _extract_pct(body_md: str, label: str = "Genel durum") -> int | None:
    m = re.search(re.escape(label) + r"\s*\|\s*%(\d+)", body_md)
    return int(m.group(1)) if m else None


def _parse_body_md(body_md: str, styles: dict, story: list) -> list:
    """Markdown gövdeyi reportlab flowable listesine çevirir. (Galeri/görseller ayrıca)"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
    _init_colors()

    lines = body_md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("# ") and not line.startswith("## "):
            story.append(Paragraph(_html.escape(line[2:].strip()), styles["title"]))
            story.append(HRFlowable(width="100%", thickness=1.2,
                                    color=_GOLD, spaceAfter=6))
        elif line.startswith("## "):
            story.append(Paragraph(_html.escape(line[3:].strip()), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(_html.escape(line[4:].strip()), styles["h3"]))
        elif line.startswith("> "):
            story.append(Paragraph(_html.escape(line[2:].strip()), styles["quote"]))
        elif line.strip() == "---":
            story.append(HRFlowable(width="100%", thickness=0.6, color=_LIGHT))
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            i -= 1  # döngü artırımı dengede kalsın
            if len(rows) >= 2 and all(set(r) <= {"", "-", ":", ":-", "-:", ":-:"} for r in rows[1]):
                rows.pop(1)
            if rows:
                ncols = max(len(r) for r in rows)
                norm = [r + [""] * (ncols - len(r)) for r in rows]
                # Hücreleri Paragraph ile sar (Helvetica Türkçe karakteri çizemez)
                from reportlab.lib.styles import ParagraphStyle
                cell_style  = ParagraphStyle("cell",  fontName="DejaVu", fontSize=8.5, leading=11)
                cell_bold   = ParagraphStyle("cellb", fontName="DejaVu-Bold", fontSize=8.5, leading=11,
                                             textColor=colors_white())
                for ri, row in enumerate(norm):
                    for ci, cv in enumerate(row):
                        norm[ri][ci] = Paragraph(_html.escape(cv), cell_bold if ri == 0 else cell_style)
                t = Table(norm, repeatRows=1)
                style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                    ("GRID", (0, 0), (-1, -1), 0.4, _LIGHT),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
                for ri, r in enumerate(norm[1:], start=1):
                    for ci, cv in enumerate(r):
                        raw = cv.text if hasattr(cv, "text") else ""
                        sev = raw.upper()
                        if sev == "YUKSEK":
                            style_cmds.extend([
                                ("BACKGROUND", (ci, ri), (ci, ri), _c_light_red()),
                                ("TEXTCOLOR", (ci, ri), (ci, ri), _RED),
                            ])
                        elif sev == "ORTA":
                            style_cmds.append(("BACKGROUND", (ci, ri), (ci, ri), _c_light_orange()))
                        elif sev == "DUSUK":
                            style_cmds.append(("BACKGROUND", (ci, ri), (ci, ri), _c_light_green()))
                t.setStyle(TableStyle(style_cmds))
                t.hAlign = "LEFT"
                story.append(t)
                story.append(Spacer(1, 8))
        elif line.startswith("- "):
            txt = line[2:].strip()
            story.append(Paragraph("• " + _html.escape(txt), styles["body"]))
        elif line.strip() == "":
            story.append(Spacer(1, 3))
        else:
            story.append(Paragraph(_html.escape(line.strip()), styles["body"]))
        i += 1

    return story


def _c_light_red():    from reportlab.lib import colors; return colors.Color(1, 0.88, 0.88)
def _c_light_orange(): from reportlab.lib import colors; return colors.Color(1, 0.93, 0.83)
def _c_light_green():  from reportlab.lib import colors; return colors.Color(0.86, 0.95, 0.86)
def colors_white():    from reportlab.lib import colors; return colors.white


def _make_progress_drawing(pct: int, width: float = 210, height: float = 24):
    from reportlab.graphics.shapes import Drawing, Rect, String
    _init_colors()
    d = Drawing(width, height)
    d.add(Rect(0, height - 18, width, 12, rx=6, ry=6, fillColor=_LIGHT, strokeColor=_LIGHT))
    w = max(0, width * pct / 100)
    if w > 0:
        d.add(Rect(0, height - 18, w, 12, rx=6, ry=6, fillColor=_GREEN, strokeColor=_GREEN))
    d.add(String(width / 2, height - 16.5, f"%{pct}", fontName="DejaVu-Bold",
                 fontSize=8, fillColor=colors_white(), textAnchor="middle"))
    return d


def _make_doughnut_drawing(pct: int, size: float = 110):
    from reportlab.graphics.shapes import Drawing, Circle, String
    from reportlab.graphics.charts.piecharts import Pie
    _init_colors()
    d = Drawing(size, size)
    cx = cy = size / 2
    r = size / 2 - 4

    p_rem = Pie(); p_rem.x = cx - r; p_rem.y = cy - r
    p_rem.width = 2 * r; p_rem.height = 2 * r
    p_rem.data = [100]; p_rem.labels = []
    p_rem.slices[0].fillColor = _LIGHT
    p_rem.startAngle = 90
    d.add(p_rem)

    if pct > 0:
        p_done = Pie(); p_done.x = cx - r; p_done.y = cy - r
        p_done.width = 2 * r; p_done.height = 2 * r
        p_done.data = [pct]; p_done.labels = []
        p_done.slices[0].fillColor = _GREEN
        p_done.startAngle = 90
        d.add(p_done)

    hole = r * 0.62
    d.add(Circle(cx, cy, hole, fillColor=colors_white(), strokeColor=colors_white()))
    d.add(String(cx, cy - 4, f"%{pct}", fontName="DejaVu-Bold", fontSize=13,
                 fillColor=_NAVY, textAnchor="middle"))
    return d


def _load_thumb(data_b64: str, max_w: int = 260, max_h: int = 195):
    """base64 → PIL thumbnail → JPEG BytesIO. Hata varsa None.

    Dönüş: {"buf": BytesIO, "w": int, "h": int}
    """
    import io
    from PIL import Image
    try:
        b64 = _clean_base64(data_b64)
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        img.thumbnail((max_w, max_h))
        w, h = img.size
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=72)
        buf.seek(0)
        return {"buf": buf, "w": w, "h": h}
    except Exception as e:
        print(f"WARN thumbnail hata: {type(e).__name__}: {e}")
        return None


def render_report_pdf(
    body_md: str,
    images: list,
    output: object,
    title_override: str | None = None,
) -> int:
    """bodyMd + görsel listesinden ReportLab PDF üretir.

    images: [{"data_b64", "name", "createdAt", "stage"}] — en fazla 9 görsel
    output: writable BytesIO/file
    Dönüş:  üretilen sayfa sayısı
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, KeepTogether)
    _init_colors(); _register_fonts()

    styles = _make_styles()

    # Veri çıkarımı
    pct_m = _extract_pct(body_md)
    pct = int(pct_m) if pct_m is not None else 0
    title = title_override
    if not title:
        m = re.search(r"# İLERLEME RAPORU[—–-]?\s*(.*)", body_md)
        title = (m.group(1).strip() if m and m.group(1).strip() else "Portföy İlerleme Raporu")
    m_date = re.search(r"Tarih:\s*([\d\.:% ]+)", body_md)
    report_date = m_date.group(1).strip() if m_date else ""

    story: list = []
    story.append(PageBreak())  # sayfa 1 = kapak (onFirstPage)

    _parse_body_md(body_md, styles, story)

    # ── Görsel Galeri (9. Kapanış'tan önce) ──
    thumbs = []
    for img in images[:9]:
        thumb = _load_thumb(img.get("data_b64", ""))
        if thumb is None:
            continue
        thumb.update({k: v for k, v in img.items() if k not in ("data_b64", "buf", "w", "h")})
        thumbs.append(thumb)

    if thumbs:
        story.append(Paragraph("Görsel Galeri (Kanıtlar)", styles["h2"]))
        from reportlab.platypus import Image as RLImage
        cells = []
        row = []
        cw = (A4[0] - 36 * mm) / 3
        for thumb in thumbs:
            buf, iw, ih = thumb["buf"], thumb["w"], thumb["h"]
            avail = cw - 4 * mm
            disp_h = avail * min(1.0, (ih / iw) if iw else 0.75)
            pil = RLImage(buf, width=avail, height=disp_h)
            cap = thumb.get("name", "")
            dt = str(thumb.get("createdAt", ""))[:10]
            st2 = thumb.get("stage", "")
            cap_txt = _html.escape(cap + (f" · {dt}" if dt else "") + (f" · {st2.upper()}" if st2 else ""))
            cell = [pil, Paragraph(cap_txt, styles["caption"])]
            row.append(cell)
            if len(row) == 3:
                cells.append(row); row = []
        if row:
            cells.append(row)
        if cells:
            gal = Table(cells, colWidths=[(A4[0] - 36 * mm) / 3] * 3)
            gal.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(gal)

    # ── Durum görselleştirme bloğu ("## 2. Mevcut Durum" başlığından hemen sonra) ──
    visual_block = Table(
        [[_make_doughnut_drawing(pct), _make_progress_drawing(pct)]],
        colWidths=[36 * mm, (A4[0] - 36 * mm) - 36 * mm],
    )
    visual_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    # Başlığın altına yerleştir
    for idx, f in enumerate(story):
        if isinstance(f, Paragraph) and f.style.name == "h2" and "Mevcut Durum" in f.text:
            story.insert(idx + 1, visual_block)
            story.insert(idx + 2, Spacer(1, 10))
            break

    # ── Kapak ve alt bilgi ──
    def _on_first_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(_NAVY)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setFillColor(_GOLD)
        canvas.rect(0, A4[1] - 7 * mm, A4[0], 4 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors_white())
        canvas.setFont("DejaVu-Bold", 28)
        canvas.drawCentredString(A4[0] / 2, A4[1] - 90 * mm, "İLERLEME RAPORU")
        canvas.setFont("DejaVu", 13)
        canvas.drawCentredString(A4[0] / 2, A4[1] - 100 * mm, "Portföy İlerleme & Analiz Dokümanı")
        canvas.setFillColor(_GOLD)
        canvas.setFont("DejaVu-Bold", 15)
        canvas.drawCentredString(A4[0] / 2, 95 * mm, title[:80])
        canvas.setFillColor(_GREEN)
        canvas.setFont("DejaVu-Bold", 17)
        canvas.drawCentredString(A4[0] / 2, 82 * mm, f"%{pct} tamamlandı")
        canvas.setFillColor(colors_white())
        canvas.setFont("DejaVu", 10)
        canvas.drawCentredString(A4[0] / 2, 60 * mm, report_date or "")
        canvas.setFont("DejaVu-Bold", 11)
        canvas.drawCentredString(A4[0] / 2, 25 * mm, "NEXA CRM")
        canvas.setFont("DejaVu", 8.5)
        canvas.drawCentredString(A4[0] / 2, 20 * mm,
                                 "Bu rapor yapay zeka destekli görsel analizi ve danışman notlarından üretilmiştir.")
        canvas.restoreState()

    def _on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(_HEX_GRAY)
        canvas.drawString(18 * mm, 9 * mm, title[:60])
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Sayfa {doc.page}")
        canvas.setFillColor(_GOLD)
        canvas.rect(0, 0, A4[0], 2.5 * mm, stroke=0, fill=1)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        output, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=title, author="Nexa CRM",
    )
    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    return doc.page


if __name__ == "__main__":
    # Hızlı sağlık kontrolü: python portfolio_progress.py
    print(json.dumps(portfolio_engine_status(), ensure_ascii=False, indent=2))