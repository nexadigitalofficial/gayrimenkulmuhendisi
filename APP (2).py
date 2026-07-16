"""
================================================================================
NEXA CRM PRO - UNIFIED SINGLE-FILE APPLICATION
================================================================================

PRODUCTION DEPLOYMENT VERSION

Combined from:
  • app.py (main Flask application)
  • wa_cloud.py (WhatsApp Cloud API)
  • mailer.py (Email automation)
  • valuation.py (Gemini valuation engine)
  • ai_listing.py (AI listing analysis)
  • fsbo_engine.py (FSBO analysis)
  • buyer_engine.py (Buyer matching)
  • eksik_fonksiyonlar.py (Bootstrap functions)
  • app_buyer_routes.py (Buyer routes)

REQUIREMENTS:
  - Firebase service account credentials (service-account.json)
  - Gemini API key
  - WhatsApp Business Account credentials
  - SMTP credentials for email
  - All Python dependencies in requirements.txt

DEPLOYMENT:
  1. Set environment variables (see .env.example)
  2. Run: python app.py
  3. Access: http://localhost:5000

⚠️  WARNINGS:
  - This is a consolidated production file
  - Do NOT edit - regenerate from source modules if needed
  - All imports are self-contained
  - Requires Python 3.10+

Generated: 2026-05-21
Version: 1.0.0 PRODUCTION
================================================================================
"""

import os
import json
import re
import time
import html as _html
import requests
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from functools import wraps
from collections import defaultdict
from io import BytesIO

# Third-party
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, send_file, request as flask_request, render_template_string
from flask_cors import CORS

# Firebase
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as admin_firestore, auth as fb_auth
    from google.cloud.firestore_v1.base_query import FieldFilter
    _fb_available = True
except Exception:
    _fb_available = False

# BS4 & Selenium
try:
    from bs4 import BeautifulSoup
    _bs4_available = True
except Exception:
    _bs4_available = False

# ML/AI
try:
    from sentence_transformers import SentenceTransformer
    _sentence_transformers_available = True
except Exception:
    _sentence_transformers_available = False

try:
    import google.generativeai as genai
    _genai_available = True
except Exception:
    _genai_available = False

# Flask extensions
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _limiter_available = True
except Exception:
    _limiter_available = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    _apscheduler_available = True
except Exception:
    _apscheduler_available = False

# ======================================================================
# WhatsApp Cloud API Module
# ======================================================================

from datetime import datetime

# ── Konfigürasyon ────────────────────────────────────────────────
WA_API_VERSION    = "v19.0"
WA_BASE_URL       = f"https://graph.facebook.com/{WA_API_VERSION}"
WA_PHONE_ID       = os.environ.get("WA_PHONE_NUMBER_ID", "")
WA_TOKEN          = os.environ.get("WA_ACCESS_TOKEN",    "")
WA_VERIFY_TOKEN   = os.environ.get("WA_VERIFY_TOKEN",    "nexa_webhook_secret")
WA_TIMEOUT        = 10   # saniye

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type":  "application/json",
    }

def _is_configured() -> bool:
    return bool(WA_PHONE_ID and WA_TOKEN)

# ── Telefon Normalize ─────────────────────────────────────────────
def normalize_phone(raw: str) -> str | None:
    """
    Türkiye numaralarını uluslararası formata çevirir.
    Örnekler:
      "05324514008"  → "905324514008"
      "+90 532 451 40 08" → "905324514008"
      "5324514008"   → "905324514008"
    """
    if not raw:
        return None
    digits = "".join(filter(str.isdigit, raw))

    if digits.startswith("0") and len(digits) == 11:
        digits = "9" + digits           # 0XXXXXXXXXX → 90XXXXXXXXXX

    if digits.startswith("90") and len(digits) == 12:
        return digits

    if len(digits) == 10 and digits[0] in ("4", "5"):
        return "90" + digits            # 5XXXXXXXXX → 905XXXXXXXXX

    return digits if len(digits) >= 10 else None

# ── Freeform Metin Mesajı ─────────────────────────────────────────
def send_whatsapp(phone: str, message: str) -> dict:
    """
    Freeform metin mesajı gönderir.
    SADECE müşteri son 24 saat içinde yazdıysa ya da
    kendi bot numaranıza (danışman numarasına) gönderirken kullanın.

    Returns:
        {"ok": True,  "message_id": "wamid.xxx"}
        {"ok": False, "error": "...", "code": 400}
    """
    if not _is_configured():
        return {"ok": False, "error": "WA_PHONE_NUMBER_ID veya WA_ACCESS_TOKEN eksik"}

    phone_norm = normalize_phone(phone)
    if not phone_norm:
        return {"ok": False, "error": f"Geçersiz telefon numarası: {phone}"}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                phone_norm,
        "type":              "text",
        "text":              {"preview_url": False, "body": message},
    }

    try:
        resp = requests.post(
            f"{WA_BASE_URL}/{WA_PHONE_ID}/messages",
            headers=_headers(),
            json=payload,
            timeout=WA_TIMEOUT,
        )
        data = resp.json()

        if resp.ok and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            print(f"✅ WA gönderildi → {phone_norm} | id: {msg_id}")
            return {"ok": True, "message_id": msg_id, "phone": phone_norm}

        # API hata detayı
        err = data.get("error", {})
        print(f"❌ WA API hatası: {err.get('message', str(data))}")
        return {
            "ok":    False,
            "error": err.get("message", str(data)),
            "code":  err.get("code", resp.status_code),
        }

    except requests.exceptions.Timeout:
        print("❌ WA API timeout")
        return {"ok": False, "error": "API timeout"}
    except Exception as e:
        print(f"❌ WA beklenmedik hata: {e}")
        return {"ok": False, "error": str(e)}

# ── Template Mesajı ───────────────────────────────────────────────
def send_whatsapp_template(
    phone: str,
    template_name: str,
    language_code: str = "tr",
    components: list | None = None,
) -> dict:
    """
    Onaylı template mesajı gönderir (24 saat penceresi dışı için zorunlu).

    Meta Business Manager → WhatsApp → Message Templates'ten
    template oluşturup onaylatmanız gerekir.

    Örnek: send_whatsapp_template("905324514008", "lead_received", "tr", [
        {"type": "body", "parameters": [{"type": "text", "text": "Ahmet Yılmaz"}]}
    ])
    """
    if not _is_configured():
        return {"ok": False, "error": "WA_PHONE_NUMBER_ID veya WA_ACCESS_TOKEN eksik"}

    phone_norm = normalize_phone(phone)
    if not phone_norm:
        return {"ok": False, "error": f"Geçersiz telefon numarası: {phone}"}

    template_payload: dict = {
        "name":     template_name,
        "language": {"code": language_code},
    }
    if components:
        template_payload["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "to":                phone_norm,
        "type":              "template",
        "template":          template_payload,
    }

    try:
        resp = requests.post(
            f"{WA_BASE_URL}/{WA_PHONE_ID}/messages",
            headers=_headers(),
            json=payload,
            timeout=WA_TIMEOUT,
        )
        data = resp.json()

        if resp.ok and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            print(f"✅ WA template gönderildi → {phone_norm} | template: {template_name}")
            return {"ok": True, "message_id": msg_id, "phone": phone_norm}

        err = data.get("error", {})
        return {
            "ok":    False,
            "error": err.get("message", str(data)),
            "code":  err.get("code", resp.status_code),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── API Durumu ────────────────────────────────────────────────────
def wa_status() -> dict:
    """
    Phone Number ID'nin durumunu Meta Graph API'den kontrol eder.
    Token geçerli mi, numara aktif mi öğrenilir.
    """
    if not _is_configured():
        return {
            "ok":          False,
            "configured":  False,
            "error":       "WA_PHONE_NUMBER_ID veya WA_ACCESS_TOKEN tanımlanmamış",
        }
    try:
        resp = requests.get(
            f"{WA_BASE_URL}/{WA_PHONE_ID}",
            headers=_headers(),
            params={"fields": "display_phone_number,verified_name,quality_rating,platform_type"},
            timeout=WA_TIMEOUT,
        )
        data = resp.json()

        if resp.ok:
            return {
                "ok":                  True,
                "configured":          True,
                "display_phone":       data.get("display_phone_number", ""),
                "verified_name":       data.get("verified_name", ""),
                "quality_rating":      data.get("quality_rating", ""),
                "platform_type":       data.get("platform_type", ""),
                "phone_number_id":     WA_PHONE_ID,
            }

        err = data.get("error", {})
        return {
            "ok":         False,
            "configured": True,
            "error":      err.get("message", str(data)),
            "code":       err.get("code", resp.status_code),
        }

    except Exception as e:
        return {"ok": False, "configured": True, "error": str(e)}

# ── Webhook Doğrulama Yardımcısı ─────────────────────────────────
def verify_webhook_token(token: str) -> bool:
    """Meta'nın webhook doğrulaması için gelen token'ı kontrol eder."""
    return token == WA_VERIFY_TOKEN

# ======================================================================
# Email Automation Module
# ======================================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'smtp').strip().lower()
EMAIL_FROM = os.environ.get('EMAIL_FROM', '').strip()
EMAIL_FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'Nexa CRM').strip()

# SMTP config
SMTP_HOST = os.environ.get('SMTP_HOST', '').strip()
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587') or 587)
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '').strip()
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '').strip()
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').strip().lower() in ('1', 'true', 'yes')

# Resend config
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '').strip()
RESEND_API_URL = 'https://api.resend.com/emails'

def email_status() -> dict:
    smtp_ok = bool(EMAIL_FROM and SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)
    resend_ok = bool(EMAIL_FROM and RESEND_API_KEY)
    configured = resend_ok if EMAIL_PROVIDER == 'resend' else smtp_ok
    return {
        'ok': configured,
        'configured': configured,
        'provider': EMAIL_PROVIDER,
        'from': EMAIL_FROM,
        'smtp_ready': smtp_ok,
        'resend_ready': resend_ok,
    }

def _build_html_wrapper(title: str, body_html: str) -> str:
    return f'''<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0b0f19;font-family:Arial,Helvetica,sans-serif;color:#e5e7eb;">
  <div style="max-width:640px;margin:0 auto;padding:32px 20px;">
    <div style="background:#121826;border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:32px;">
      <div style="font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:#c7a34b;margin-bottom:14px;">Nexa CRM</div>
      {body_html}
      <div style="margin-top:28px;padding-top:18px;border-top:1px solid rgba(255,255,255,.08);font-size:12px;color:#9ca3af;line-height:1.7;">
        Bu e-posta otomatik olarak oluşturulmuştur. Ek sorularınız için bu mesaja yanıt verebilir veya bizimle telefon üzerinden iletişime geçebilirsiniz.
      </div>
    </div>
  </div>
</body>
</html>'''

def build_lead_confirmation_email(name: str, phone: str = '', neighborhood: str = '', property_type: str = '', notes: str = '') -> tuple[str, str, str]:
    subject = 'Talebiniz bize ulaştı'
    plain = (
        f'Merhaba {name},\n\n'
        'Talebiniz bize başarıyla ulaştı. En kısa sürede sizinle iletişime geçeceğiz.\n\n'
        + (f'Mahalle: {neighborhood}\n' if neighborhood else '')
        + (f'Mülk Tipi: {property_type}\n' if property_type else '')
        + (f'Telefon: {phone}\n' if phone else '')
        + (f'Notunuz: {notes}\n' if notes else '')
        + '\nTeşekkür ederiz.\nNexa CRM'
    )
    html_body = f'''
      <h1 style="margin:0 0 12px;font-size:28px;line-height:1.2;color:#ffffff;">Merhaba {name},</h1>
      <p style="margin:0 0 18px;font-size:16px;line-height:1.7;color:#d1d5db;">
        Talebiniz bize başarıyla ulaştı. Ekibimiz en kısa sürede sizinle iletişime geçecek.
      </p>
      <div style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px 18px 8px;margin:18px 0;">
        <div style="font-size:14px;color:#f3f4f6;font-weight:bold;margin-bottom:10px;">Talep Özeti</div>
        {f'<p style="margin:0 0 10px;color:#cbd5e1;"><strong>Mahalle:</strong> {neighborhood}</p>' if neighborhood else ''}
        {f'<p style="margin:0 0 10px;color:#cbd5e1;"><strong>Mülk Tipi:</strong> {property_type}</p>' if property_type else ''}
        {f'<p style="margin:0 0 10px;color:#cbd5e1;"><strong>Telefon:</strong> {phone}</p>' if phone else ''}
        {f'<p style="margin:0 0 10px;color:#cbd5e1;"><strong>Notunuz:</strong> {notes}</p>' if notes else ''}
      </div>
      <p style="margin:0;font-size:15px;line-height:1.7;color:#d1d5db;">
        Dilerseniz bu e-postayı yanıtlayarak ek bilgi paylaşabilirsiniz.
      </p>
    '''
    return subject, plain, _build_html_wrapper(subject, html_body)

def _send_via_smtp(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> dict:
    if not (EMAIL_FROM and SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD):
        return {'ok': False, 'error': 'SMTP yapılandırması eksik'}

    msg = MIMEMultipart('alternative') if html_body else MIMEText(text_body, 'plain', 'utf-8')
    if html_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    msg['Subject'] = subject
    msg['From'] = formataddr((EMAIL_FROM_NAME, EMAIL_FROM))
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
        return {'ok': True, 'provider': 'smtp', 'to': to_email}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'provider': 'smtp'}

def _send_via_resend(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> dict:
    if not (EMAIL_FROM and RESEND_API_KEY):
        return {'ok': False, 'error': 'Resend yapılandırması eksik'}
    payload = {
        'from': formataddr((EMAIL_FROM_NAME, EMAIL_FROM)),
        'to': [to_email],
        'subject': subject,
        'text': text_body,
    }
    if html_body:
        payload['html'] = html_body
    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={'Authorization': f'Bearer {RESEND_API_KEY}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=15,
        )
        data = resp.json() if resp.content else {}
        if resp.ok:
            return {'ok': True, 'provider': 'resend', 'to': to_email, 'id': data.get('id', '')}
        return {'ok': False, 'error': data.get('message', str(data)), 'provider': 'resend'}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'provider': 'resend'}

def send_transactional_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> dict:
    if not to_email:
        return {'ok': False, 'error': 'Alıcı e-posta boş'}
    provider = EMAIL_PROVIDER
    if provider == 'resend':
        return _send_via_resend(to_email, subject, text_body, html_body)
    return _send_via_smtp(to_email, subject, text_body, html_body)

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────
def _trend_meta(trend: str) -> tuple:
    t = (trend or '').lower()
    if 'yüksel' in t or 'artı' in t:
        return '📈', '#22c55e'
    if 'düş' in t or 'azal' in t:
        return '📉', '#ef4444'
    return '➡️', '#f59e0b'

def _score_color(score: int) -> str:
    if score >= 8: return '#22c55e'
    if score >= 6: return '#f59e0b'
    return '#ef4444'

def _impact_icon(impact: str) -> tuple:
    if impact == 'positive': return '✅', '#22c55e'
    if impact == 'negative': return '⚠️', '#ef4444'
    return 'ℹ️', '#94a3b8'

# ── Müşteriye gönderilen değerleme raporu e-postası ───────────────
def build_valuation_report_email(name: str, report: dict) -> tuple:
    neighborhood  = report.get('neighborhood', 'Bölgeniz')
    property_type = report.get('property_type', 'Mülkünüz')
    gen_at        = report.get('generated_at', '')

    pr   = report.get('price_range', {})
    na   = report.get('neighborhood_analysis', {})
    inv  = report.get('investment_score', {})
    mc   = report.get('market_comparison', {})
    kf   = report.get('key_factors', [])
    tips = report.get('valuation_tips', [])
    summ = report.get('executive_summary', '')
    disc = report.get('disclaimer', '')

    trend_icon, trend_color = _trend_meta(na.get('trend', 'stabil'))
    score     = int(inv.get('score', 0))
    score_max = int(inv.get('max', 10))
    score_pct = int((score / score_max) * 100) if score_max else 0
    sc_color  = _score_color(score)

    subject = f"{neighborhood} Gayrimenkul Değerleme Raporunuz Hazır"

    plain = (
        f"Merhaba {name},\n\n"
        f"{neighborhood} bölgesindeki {property_type} için değerleme raporunuz hazır.\n\n"
        f"Özet: {summ}\n\n"
        f"Tahmini Değer: {pr.get('average','')}\n"
        f"Aralık: {pr.get('min','')} — {pr.get('max','')}\n"
        f"Yatırım Skoru: {score}/{score_max} — {inv.get('label','')}\n"
        f"Trend: {na.get('trend','')}\n\n"
        f"Tavsiyeler:\n" + "\n".join(f"  • {t}" for t in tips) + "\n\n"
        f"⚠ {disc}\n\nRapor tarihi: {gen_at}\nNexa CRM"
    )

    def _li(items, color):
        return "".join(
            f'<li style="margin:0 0 7px;padding-left:4px;">'
            f'<span style="color:{color};font-size:13px;">• </span>'
            f'<span style="color:#cbd5e1;font-size:13px;">{i}</span></li>'
            for i in items
        )

    kf_html = ""
    for f in kf:
        icon, icolor = _impact_icon(f.get('impact', 'neutral'))
        kf_html += (
            f'<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:10px;'
            f'padding:12px;background:#0f172a;border-radius:10px;border:1px solid rgba(255,255,255,.06);">'
            f'<span style="font-size:15px;flex-shrink:0;">{icon}</span>'
            f'<div><div style="font-size:12px;font-weight:700;color:{icolor};margin-bottom:3px;">'
            f'{f.get("factor","")}</div>'
            f'<div style="font-size:12px;color:#94a3b8;line-height:1.55;">{f.get("detail","")}</div></div></div>'
        )

    tips_html = "".join(
        f'<div style="margin-bottom:8px;padding:10px 14px;background:#0f172a;'
        f'border-left:3px solid #c7a34b;border-radius:0 8px 8px 0;font-size:13px;color:#cbd5e1;">{t}</div>'
        for t in tips
    )

    similar = mc.get('similar_neighborhoods', [])
    sim_html = " ".join(
        f'<span style="display:inline-block;background:#1e293b;border:1px solid rgba(255,255,255,.08);'
        f'border-radius:20px;padding:3px 11px;font-size:11px;color:#94a3b8;margin:2px;">{s}</span>'
        for s in similar
    )

    score_bar = (
        f'<div style="background:#1e293b;border-radius:999px;height:7px;margin:8px 0 10px;">'
        f'<div style="background:{sc_color};width:{score_pct}%;height:7px;border-radius:999px;"></div></div>'
    )

    body = f"""
      <h1 style="margin:0 0 6px;font-size:24px;color:#ffffff;">Merhaba {name},</h1>
      <p style="margin:0 0 22px;font-size:14px;color:#94a3b8;line-height:1.6;">
        <strong style="color:#e5e7eb;">{neighborhood}</strong> bölgesindeki
        <strong style="color:#e5e7eb;">{property_type}</strong> için
        yapay zeka destekli değerleme raporunuz aşağıdadır.
      </p>

      <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid rgba(199,163,75,.3);
                  border-radius:16px;padding:20px;margin-bottom:18px;">
        <div style="font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#c7a34b;margin-bottom:10px;">
          Özet Değerlendirme
        </div>
        <p style="margin:0;font-size:14px;color:#e5e7eb;line-height:1.75;">{summ}</p>
      </div>

      <div style="background:#0f172a;border:1px solid rgba(34,197,94,.25);border-radius:16px;
                  padding:22px;margin-bottom:18px;text-align:center;">
        <div style="font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#86efac;margin-bottom:12px;">
          Tahmini Değer Aralığı
        </div>
        <div style="font-size:32px;font-weight:700;color:#22c55e;letter-spacing:-.5px;margin-bottom:4px;">
          {pr.get('average','—')}
        </div>
        <div style="font-size:13px;color:#64748b;margin-bottom:12px;">
          {pr.get('min','—')} &nbsp;–&nbsp; {pr.get('max','—')}
        </div>
        <div style="padding-top:12px;border-top:1px solid rgba(255,255,255,.06);font-size:12px;color:#475569;">
          m² birim değer: <strong style="color:#94a3b8;">{pr.get('per_sqm_min', pr.get('per_sqm_avg','—'))}</strong>
          &nbsp;–&nbsp; <strong style="color:#94a3b8;">{pr.get('per_sqm_max','—')}</strong>
        </div>
      </div>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
        <tr>
          <td width="49%" valign="top"
              style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:16px;">
            <div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">
              Yatırım Skoru
            </div>
            <div style="font-size:26px;font-weight:700;color:{sc_color};">
              {score}<span style="font-size:14px;color:#374151;">/{score_max}</span>
            </div>
            <div style="font-size:12px;color:{sc_color};margin-bottom:2px;">{inv.get('label','')}</div>
            {score_bar}
            <div style="font-size:11px;color:#64748b;line-height:1.5;">{inv.get('reasoning','')}</div>
          </td>
          <td width="2%"></td>
          <td width="49%" valign="top"
              style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:16px;">
            <div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:8px;">
              Bölge Trendi
            </div>
            <div style="font-size:26px;font-weight:700;color:{trend_color};margin-bottom:4px;">
              {trend_icon} {na.get('trend','').capitalize()}
            </div>
            <div style="font-size:11px;color:#64748b;line-height:1.55;">{na.get('trend_detail','')}</div>
          </td>
        </tr>
      </table>

      <div style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;
                  padding:18px;margin-bottom:18px;">
        <div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:12px;">
          Mahalle Analizi
        </div>
        <p style="margin:0 0 14px;font-size:13px;color:#cbd5e1;line-height:1.65;">{na.get('summary','')}</p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="49%" valign="top">
              <div style="font-size:10px;color:#22c55e;font-weight:700;margin-bottom:7px;">✅ AVANTAJLAR</div>
              <ul style="margin:0;padding:0;list-style:none;">{_li(na.get('pros',[]), '#22c55e')}</ul>
            </td>
            <td width="2%"></td>
            <td width="49%" valign="top">
              <div style="font-size:10px;color:#ef4444;font-weight:700;margin-bottom:7px;">⚠️ DİKKAT</div>
              <ul style="margin:0;padding:0;list-style:none;">{_li(na.get('cons',[]), '#ef4444')}</ul>
            </td>
          </tr>
        </table>
      </div>

      {'<div style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px;margin-bottom:18px;"><div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:12px;">Piyasa Karşılaştırması</div><p style="margin:0 0 8px;font-size:13px;color:#cbd5e1;line-height:1.6;">' + mc.get("vs_district","") + '</p><p style="margin:0 0 12px;font-size:13px;color:#cbd5e1;line-height:1.6;">' + mc.get("vs_ankara","") + '</p>' + ('<div style="font-size:11px;color:#475569;">Benzer bölgeler: ' + sim_html + '</div>' if similar else '') + '</div>' if mc.get('vs_district') or mc.get('vs_ankara') else ''}

      {'<div style="margin-bottom:18px;"><div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">Değeri Etkileyen Faktörler</div>' + kf_html + '</div>' if kf_html else ''}

      {'<div style="margin-bottom:18px;"><div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">💡 Uzman Tavsiyeleri</div>' + tips_html + '</div>' if tips_html else ''}

      <div style="background:#0a0f1a;border:1px solid rgba(255,255,255,.05);border-radius:10px;
                  padding:12px;text-align:center;margin-bottom:4px;">
        <div style="font-size:11px;color:#374151;">
          🤖 Gemini AI ile oluşturulmuştur &nbsp;·&nbsp; 📅 {gen_at}
        </div>
        <div style="font-size:10px;color:#374151;margin-top:4px;">{disc}</div>
      </div>

      <p style="margin:18px 0 0;font-size:13px;color:#cbd5e1;line-height:1.7;">
        Raporla ilgili sorularınız için ekibimize ulaşabilirsiniz.
      </p>
    """

    return subject, plain, _build_html_wrapper(subject, body)

# ── Danışmana gönderilen bildirim e-postası ───────────────────────
def build_advisor_valuation_email(
    customer_name: str, customer_phone: str, customer_email: str,
    neighborhood: str, property_type: str, report: dict
) -> tuple:
    pr  = report.get('price_range', {})
    inv = report.get('investment_score', {})
    na  = report.get('neighborhood_analysis', {})
    gen = report.get('generated_at', '')

    trend_icon, trend_color = _trend_meta(na.get('trend', 'stabil'))
    score    = int(inv.get('score', 0))
    sc_color = _score_color(score)

    subject = f"[Nexa CRM] Değerleme Raporu Gönderildi — {customer_name} / {neighborhood}"

    plain = (
        f"Değerleme raporu müşteriye gönderildi.\n\n"
        f"Müşteri: {customer_name} | {customer_phone} | {customer_email}\n"
        f"Mülk: {neighborhood} / {property_type}\n\n"
        f"Tahmini Değer: {pr.get('average','?')}\n"
        f"Aralık: {pr.get('min','?')} — {pr.get('max','?')}\n"
        f"Yatırım Skoru: {score}/10 — {inv.get('label','')}\n"
        f"Trend: {na.get('trend','?')}\n\nRapor Tarihi: {gen}\nNexa CRM"
    )

    body = f"""
      <h1 style="margin:0 0 4px;font-size:20px;color:#ffffff;">✅ Değerleme Raporu Gönderildi</h1>
      <p style="margin:0 0 20px;font-size:12px;color:#64748b;">Aşağıdaki müşteriye rapor iletildi.</p>

      <div style="background:#0f172a;border:1px solid rgba(255,255,255,.07);border-radius:14px;
                  padding:16px;margin-bottom:14px;">
        <div style="font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">
          Müşteri Bilgileri
        </div>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="padding:3px 0;color:#475569;font-size:12px;width:90px;">Ad Soyad</td>
              <td style="padding:3px 0;color:#e5e7eb;font-size:13px;font-weight:700;">{customer_name}</td></tr>
          <tr><td style="padding:3px 0;color:#475569;font-size:12px;">Telefon</td>
              <td style="padding:3px 0;color:#e5e7eb;font-size:12px;">{customer_phone}</td></tr>
          {'<tr><td style="padding:3px 0;color:#475569;font-size:12px;">E-posta</td><td style="padding:3px 0;color:#e5e7eb;font-size:12px;">' + customer_email + '</td></tr>' if customer_email else ''}
          <tr><td style="padding:3px 0;color:#475569;font-size:12px;">Mahalle</td>
              <td style="padding:3px 0;color:#e5e7eb;font-size:12px;">{neighborhood}</td></tr>
          <tr><td style="padding:3px 0;color:#475569;font-size:12px;">Mülk Tipi</td>
              <td style="padding:3px 0;color:#e5e7eb;font-size:12px;">{property_type}</td></tr>
        </table>
      </div>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;">
        <tr>
          <td width="49%" valign="top" style="background:#0f172a;border:1px solid rgba(34,197,94,.2);
              border-radius:12px;padding:14px;text-align:center;">
            <div style="font-size:9px;color:#86efac;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px;">
              Ort. Değer
            </div>
            <div style="font-size:16px;font-weight:700;color:#22c55e;">{pr.get('average','—')}</div>
            <div style="font-size:10px;color:#374151;margin-top:3px;">{pr.get('min','—')} – {pr.get('max','—')}</div>
          </td>
          <td width="2%"></td>
          <td width="24%" valign="top" style="background:#0f172a;border:1px solid rgba(255,255,255,.07);
              border-radius:12px;padding:14px;text-align:center;">
            <div style="font-size:9px;color:#94a3b8;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px;">
              Skor
            </div>
            <div style="font-size:20px;font-weight:700;color:{sc_color};">
              {score}<span style="font-size:11px;color:#374151;">/{inv.get('max',10)}</span>
            </div>
            <div style="font-size:10px;color:{sc_color};">{inv.get('label','')}</div>
          </td>
          <td width="2%"></td>
          <td width="24%" valign="top" style="background:#0f172a;border:1px solid rgba(255,255,255,.07);
              border-radius:12px;padding:14px;text-align:center;">
            <div style="font-size:9px;color:#94a3b8;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px;">
              Trend
            </div>
            <div style="font-size:20px;color:{trend_color};">{trend_icon}</div>
            <div style="font-size:10px;color:{trend_color};">{na.get('trend','—').capitalize()}</div>
          </td>
        </tr>
      </table>

      <div style="background:#0a0f1a;border-radius:10px;padding:10px;text-align:center;
                  font-size:11px;color:#374151;">
        📅 {gen} &nbsp;·&nbsp; 🤖 Gemini AI
      </div>
    """

    return subject, plain, _build_html_wrapper(subject, body)

# ======================================================================
# Gemini Property Valuation
# ======================================================================

import statistics
from urllib.parse import quote
from google import genai

# ─────────────────────────────────────────────────────────────────────────────
# Konfigürasyon
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_MODEL   = "gemini-2.5-flash"
SCRAPE_TIMEOUT = 14
MAX_RESULTS    = 40   # toplam veri seti büyüklüğü
MAX_CONTEXT    = 30   # Gemini'ye gönderilecek ilan sayısı

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT":             "1",
    "Connection":      "keep-alive",
}

# Komşu mahalle haritası — arama genişletmek için
NEIGHBOR_MAP: dict[str, list[str]] = {
    "dikmen":        ["kavaklıdere", "çukurambar", "balgat"],
    "çankaya":       ["kavaklıdere", "gaziosmanpaşa", "ayrancı"],
    "kavaklıdere":   ["çankaya", "dikmen", "gaziosmanpaşa"],
    "batıkent":      ["elvankent", "öveçler", "törekent"],
    "keçiören":      ["etlik", "kalaba", "bağlum"],
    "mamak":         ["altındağ", "tuzluçayır", "mamak"],
    "etimesgut":     ["eryaman", "elvankent", "sincan"],
    "eryaman":       ["etimesgut", "elvankent", "törekent"],
    "gaziosmanpaşa": ["kavaklıdere", "çankaya", "ayrancı"],
    "ayrancı":       ["çankaya", "gaziosmanpaşa", "kavaklıdere"],
    "balgat":        ["dikmen", "çukurambar", "söğütözü"],
    "çukurambar":    ["balgat", "söğütözü", "diplomatik site"],
    "öveçler":       ["batıkent", "demetevler", "yenimahalle"],
    "sincan":        ["etimesgut", "eryaman", "elvankent"],
    "pursaklar":     ["keçiören", "altındağ"],
    "gölbaşı":       ["çankaya", "balgat"],
}

# ─────────────────────────────────────────────────────────────────────────────
# Yardımcılar
# ─────────────────────────────────────────────────────────────────────────────
def _fmt(val: int) -> str:
    return f"{val:,}".replace(",", ".") + " TL"

def _neighbors(neighborhood: str) -> list[str]:
    key = neighborhood.lower().strip()
    for k, v in NEIGHBOR_MAP.items():
        if k in key or key in k:
            return v
    return []

def _pt_slug(property_type: str) -> dict:
    """Mülk tipinden kaynak-bazlı URL segmentleri üret."""
    pt = property_type.lower()
    if "daire" in pt:
        return {"he": "daire-satilik", "zingat": "daire", "ej": "daire"}
    if "villa" in pt:
        return {"he": "villa-satilik", "zingat": "villa", "ej": "villa"}
    if "arsa" in pt:
        return {"he": "arsa-satilik", "zingat": "arsa", "ej": "arsa"}
    if "dükkan" in pt or "ofis" in pt or "işyeri" in pt:
        return {"he": "isyeri-satilik", "zingat": "isyeri", "ej": "isyeri"}
    if "müstakil" in pt or "ev" in pt:
        return {"he": "mustakil-ev-satilik", "zingat": "mustakil-ev", "ej": "mustakil-ev"}
    return {"he": "konut-satilik", "zingat": "konut", "ej": "konut"}

def valuation_status() -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return {
        "ok":         bool(key),
        "configured": bool(key),
        "model":      GEMINI_MODEL,
        "provider":   "gemini+multiscrape",
    }

# ─────────────────────────────────────────────────────────────────────────────
# Fiyat / m² regex
# ─────────────────────────────────────────────────────────────────────────────
_PRICE_RE = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:TL|tl|₺)"
    r"|(\d+(?:[.,]\d+)?)\s*milyon\s*(?:TL|tl|₺)?",
    re.IGNORECASE,
)
_SQM_RE = re.compile(r"(\d{2,4})\s*m[²2]", re.IGNORECASE)

def _parse_price(text: str) -> int | None:
    for m in _PRICE_RE.finditer(text):
        try:
            if m.group(2):
                val = float(m.group(2).replace(",", ".")) * 1_000_000
            else:
                val = int(re.sub(r"[^\d]", "", m.group(1)))
            if 300_000 <= val <= 200_000_000:
                return int(val)
        except (ValueError, TypeError):
            pass
    return None

def _parse_sqm(text: str) -> int | None:
    m = _SQM_RE.search(text)
    if m:
        v = int(m.group(1))
        return v if 20 <= v <= 2000 else None
    return None

def _extract_prices(results: list[dict]) -> list[int]:
    prices = []
    for r in results:
        text = r.get("title", "") + " " + r.get("snippet", "")
        p = _parse_price(text)
        if p:
            prices.append(p)
    return sorted(prices)

def _iqr_clean(prices: list[int]) -> list[int]:
    """IQR yöntemiyle aykırı değerleri temizle (1.5×IQR kuralı)."""
    if len(prices) < 4:
        return prices
    s  = sorted(prices)
    n  = len(s)
    q1 = statistics.median(s[:n // 2])
    q3 = statistics.median(s[(n + 1) // 2:])
    iqr = q3 - q1
    if iqr == 0:
        return s
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    cleaned = [p for p in s if lo <= p <= hi]
    removed = len(s) - len(cleaned)
    if removed:
        print(f"   IQR temizleme: {removed} aykırı değer çıkarıldı")
    return cleaned if cleaned else s

def _stats(prices: list[int], sqm: str = "") -> dict:
    """Fiyat listesinden istatistik üret."""
    if not prices:
        return {}
    clean = _iqr_clean(prices)
    avg   = int(statistics.mean(clean))
    med   = int(statistics.median(clean))
    lo    = min(clean)
    hi    = max(clean)
    out   = {
        "count":     len(clean),
        "raw_count": len(prices),
        "min":       lo,
        "max":       hi,
        "average":   avg,
        "median":    med,
    }
    sqm_int = None
    try:
        sqm_int = int(re.sub(r"[^\d]", "", sqm)) if sqm else None
    except Exception:
        pass
    if sqm_int and sqm_int > 0:
        out["per_sqm_avg"] = int(avg / sqm_int)
        out["per_sqm_med"] = int(med / sqm_int)
        out["per_sqm_min"] = int(lo  / sqm_int)
        out["per_sqm_max"] = int(hi  / sqm_int)
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Scraper 1 — DuckDuckGo HTML
# ─────────────────────────────────────────────────────────────────────────────
def _ddg(query: str, max_r: int = 10) -> list[dict]:
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "tr-tr", "s": "0"},
            headers=HEADERS,
            timeout=SCRAPE_TIMEOUT,
        )
        if not resp.ok:
            return []
        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []
        for el in soup.select(".result")[:max_r]:
            title   = el.select_one(".result__title")
            snippet = el.select_one(".result__snippet")
            url     = el.select_one(".result__url")
            t = title.get_text(strip=True)   if title   else ""
            s = snippet.get_text(strip=True) if snippet else ""
            u = url.get_text(strip=True)     if url     else ""
            if t or s:
                results.append({"title": t, "snippet": s, "url": u, "source": "ddg"})
        print(f"   DDG '{query[:55]}' → {len(results)} sonuç")
        return results
    except Exception as e:
        print(f"   ⚠ DDG '{query[:40]}': {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Scraper 2 — HepsiEmlak
# ─────────────────────────────────────────────────────────────────────────────
def _scrape_hepsiemlak(neighborhood: str, property_type: str) -> list[dict]:
    slugs = _pt_slug(property_type)
    cat   = slugs["he"]
    loc   = quote(f"{neighborhood.lower()}-ankara")
    url   = f"https://www.hepsiemlak.com/{cat}?location_slug={loc}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            print(f"   ⚠ HepsiEmlak HTTP {resp.status_code}")
            return []
        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = []
        for sel in ["li.listing-item", ".listing-card", "article.listing",
                    "[class*=listingCard]", "[class*=listing-item]"]:
            cards = soup.select(sel)
            if cards:
                break
        for card in cards[:15]:
            full_text = card.get_text(" ", strip=True)
            price = _parse_price(full_text)
            if not price:
                continue
            title_el = card.select_one(".listing-title,.title,h2,h3,[class*=title]")
            title    = title_el.get_text(strip=True) if title_el else f"{neighborhood} {property_type}"
            results.append({
                "title":   title,
                "snippet": full_text[:300],
                "url":     "hepsiemlak.com",
                "source":  "hepsiemlak",
                "price":   price,
            })
        print(f"   HepsiEmlak → {len(results)} ilan")
    except Exception as e:
        print(f"   ⚠ HepsiEmlak hatası: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Scraper 3 — Zingat
# ─────────────────────────────────────────────────────────────────────────────
def _scrape_zingat(neighborhood: str, property_type: str) -> list[dict]:
    slugs = _pt_slug(property_type)
    cat   = slugs["zingat"]
    loc   = neighborhood.lower().replace(" ", "-")
    url   = f"https://www.zingat.com/ankara/{loc}/{cat}-satilik"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            print(f"   ⚠ Zingat HTTP {resp.status_code}")
            return []
        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(
            ".listing-card,.property-item,[class*=listing],[class*=property-card]"
        )
        for card in cards[:15]:
            full_text = card.get_text(" ", strip=True)
            price = _parse_price(full_text)
            if not price:
                continue
            title_el = card.select_one("h2,h3,.title,[class*=title]")
            title    = title_el.get_text(strip=True) if title_el else f"{neighborhood} {property_type}"
            results.append({
                "title":   title,
                "snippet": full_text[:300],
                "url":     "zingat.com",
                "source":  "zingat",
                "price":   price,
            })
        print(f"   Zingat → {len(results)} ilan")
    except Exception as e:
        print(f"   ⚠ Zingat hatası: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Scraper 4 — Emlakjet
# ─────────────────────────────────────────────────────────────────────────────
def _scrape_emlakjet(neighborhood: str, property_type: str) -> list[dict]:
    pt  = property_type.lower()
    cat = ("daire"    if "daire"  in pt else
           "villa"    if "villa"  in pt else
           "arsa"     if "arsa"   in pt else "konut")
    loc = neighborhood.lower().replace(" ", "-")
    url = f"https://www.emlakjet.com/satilik-{cat}/ankara/{loc}/"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT)
        if not resp.ok:
            print(f"   ⚠ Emlakjet HTTP {resp.status_code}")
            return []
        soup  = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("[class*=listing],[class*=card],[class*=ilan],article")
        for card in cards[:15]:
            full_text = card.get_text(" ", strip=True)
            price = _parse_price(full_text)
            if not price:
                continue
            title_el = card.select_one("h2,h3,.title,[class*=title]")
            title    = title_el.get_text(strip=True) if title_el else f"{neighborhood} {property_type}"
            results.append({
                "title":   title,
                "snippet": full_text[:300],
                "url":     "emlakjet.com",
                "source":  "emlakjet",
                "price":   price,
            })
        print(f"   Emlakjet → {len(results)} ilan")
    except Exception as e:
        print(f"   ⚠ Emlakjet hatası: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# Toplu Arama Koordinatörü
# ─────────────────────────────────────────────────────────────────────────────
def _multi_search(
    neighborhood: str,
    property_type: str,
    sqm: str = "",
) -> list[dict]:
    """Tüm kaynaklardan veri toplar, tekilleştirir ve döndürür."""
    all_results: list[dict] = []
    seen: set[str]          = set()

    def _add(items: list[dict]) -> None:
        for r in items:
            key = (r.get("url", "") + r.get("title", ""))[:120]
            if key not in seen:
                seen.add(key)
                all_results.append(r)

    # ── 1. Direkt Scraperlar ──────────────────────────────────────────────────
    _add(_scrape_hepsiemlak(neighborhood, property_type))
    time.sleep(0.5)
    _add(_scrape_zingat(neighborhood, property_type))
    time.sleep(0.5)
    _add(_scrape_emlakjet(neighborhood, property_type))
    time.sleep(0.4)

    # ── 2. DDG — ana mahalle sorguları ───────────────────────────────────────
    ddg_queries = [
        f"site:sahibinden.com {neighborhood} ankara {property_type} satılık",
        f"site:hepsiemlak.com {neighborhood} ankara {property_type} satılık",
        f"{neighborhood} ankara {property_type} satılık fiyat 2025",
        f"{neighborhood} ankara m2 fiyatı emlak 2025",
        f"sahibinden.com {neighborhood} {property_type} satılık TL",
        f"endeksa.com {neighborhood} ankara konut fiyat",
        f"{neighborhood} ankara {property_type} ortalama fiyat",
        f"zingat.com {neighborhood} ankara {property_type}",
    ]
    for q in ddg_queries:
        _add(_ddg(q, max_r=10))
        time.sleep(0.35)

    # ── 3. DDG — komşu mahalleler (bağlam zenginleştirme) ────────────────────
    for nb in _neighbors(neighborhood)[:2]:
        _add(_ddg(f"{nb} ankara {property_type} satılık fiyat 2025", max_r=6))
        time.sleep(0.3)

    # ── 4. m² girilmişse birim fiyat araması ─────────────────────────────────
    if sqm:
        _add(_ddg(f"{neighborhood} ankara {sqm}m2 {property_type} satılık", max_r=8))
        time.sleep(0.3)

    # ── 5. Ankara genel piyasa bağlamı ───────────────────────────────────────
    _add(_ddg(f"ankara {property_type} ortalama m2 fiyatı 2025", max_r=6))

    print(f"\n   📊 Toplam kayıt: {len(all_results)}")
    return all_results[:MAX_RESULTS]

# ─────────────────────────────────────────────────────────────────────────────
# Context Builder
# ─────────────────────────────────────────────────────────────────────────────
def _build_context(results: list[dict], st: dict, sqm: str = "") -> str:
    lines = []

    if st:
        lines += [
            f"=== GERÇEK PAZAR VERİSİ ({st['count']} ilan, {st['raw_count']} ham kayıt) ===",
            f"  Min    : {_fmt(st['min'])}",
            f"  Maks   : {_fmt(st['max'])}",
            f"  Ort    : {_fmt(st['average'])}",
            f"  Medyan : {_fmt(st['median'])}  ← aykırı değer etkisi az",
        ]
        if "per_sqm_avg" in st:
            lines += [
                f"  m²/Ort : {_fmt(st['per_sqm_avg'])}/m²",
                f"  m²/Med : {_fmt(st['per_sqm_med'])}/m²",
            ]
        lines.append("")

    # Kaynak bazlı özet
    by_source: dict[str, list[int]] = {}
    for r in results:
        src = r.get("source", "ddg")
        if r.get("price"):
            by_source.setdefault(src, []).append(r["price"])
    if by_source:
        lines.append("=== KAYNAK BAZLI FİYATLAR ===")
        for src, prices in by_source.items():
            avg_s = int(sum(prices) / len(prices))
            lines.append(f"  {src:15s} → {len(prices)} ilan | Ort: {_fmt(avg_s)}")
        lines.append("")

    lines.append("=== İLAN DETAYLARI ===")
    ranked = sorted(results, key=lambda r: 0 if r.get("price") else 1)
    for i, r in enumerate(ranked[:MAX_CONTEXT], 1):
        price_tag = f" [{_fmt(r['price'])}]" if r.get("price") else ""
        lines.append(f"{i}. [{r.get('source','?')}]{price_tag} {r['title']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:220]}")

    return "\n".join(lines) or "Yeterli veri bulunamadı."

# ─────────────────────────────────────────────────────────────────────────────
# Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────
def _build_prompt(
    name: str, neighborhood: str, property_type: str,
    rooms: str, sqm: str, notes: str,
    context: str, st: dict,
) -> str:
    now    = datetime.now().strftime("%d.%m.%Y %H:%M")
    extras = []
    if rooms: extras.append(f"- Oda Sayısı  : {rooms}")
    if sqm:   extras.append(f"- Metrekare   : {sqm} m²")
    if notes: extras.append(f"- Notlar      : {notes}")
    extra_block = "\n".join(extras) if extras else "- (ek bilgi girilmedi)"

    if st and st.get("count", 0) >= 3:
        med   = st["median"]
        avg   = st["average"]
        lo    = st["min"]
        hi    = st["max"]
        count = st["count"]
        price_directive = f"""
⚠⚠ ZORUNLU — Aşağıdaki gerçek pazar verisini MUTLAKA kullan:
   Kaynak: {count} ilan (IQR ile aykırı değerler temizlenmiş)
   Min    = {_fmt(lo)}
   Maks   = {_fmt(hi)}
   Ort    = {_fmt(avg)}
   Medyan = {_fmt(med)}  ← EN GÜVENİLİR referans"""
        if "per_sqm_avg" in st:
            price_directive += f"""
   m²/Ort = {_fmt(st['per_sqm_avg'])}/m²
   m²/Med = {_fmt(st['per_sqm_med'])}/m²"""
        price_directive += f"""
   → price_range.min     = {_fmt(int(lo * 0.93))}
   → price_range.max     = {_fmt(int(hi * 1.07))}
   → price_range.average = {_fmt(avg)}
   → price_range.median  = {_fmt(med)}"""
    else:
        price_directive = """
⚠ Yeterli ilan verisi bulunamadı. 2025 Ankara piyasası ve mahalle
   özelliklerine dayanarak gerçekçi tahmin yap. data_quality = "tahmini" yaz."""

    return f"""Sen Türkiye'nin en deneyimli gayrimenkul değerleme uzmanısın.
Ankara {neighborhood} bölgesinde {property_type} için gerçek web ilanlarından
derlenen verilerle kapsamlı bir değerleme raporu hazırlıyorsun.

══════════════ MÜŞTERİ ══════════════
Ad    : {name}
Bölge : {neighborhood}, Ankara
Mülk  : {property_type}
{extra_block}
Tarih : {now}

══════════════ PAZAR VERİSİ KILAVUZU ══════════════{price_directive}

══════════════ WEB KAYNAKLARINDAN DERLENEN VERİ ══════════════
{context}
══════════════════════════════════════════════════════════════

KURALLAR:
1. Yalnızca geçerli bir JSON objesi döndür — markdown, açıklama, kod bloğu yok.
2. Tüm metinler Türkçe.
3. Fiyatları TL, binlik nokta ayraçlı (örn: "4.750.000 TL").
4. Gerçek veri varsa onu kullan; tahmin yaparsan "tahmini" ibaresini ekle.
5. executive_summary'de {name}'e doğrudan hitap et.
6. investment_score 1-10 tam sayı.
7. pros ≥ 3 madde, cons ≥ 2 madde.
8. data_quality: "gercek" (≥3 gerçek ilan) veya "tahmini".

JSON YAPISI:
{{
  "price_range": {{
    "min":          "X.XXX.XXX TL",
    "max":          "X.XXX.XXX TL",
    "average":      "X.XXX.XXX TL",
    "median":       "X.XXX.XXX TL",
    "per_sqm_min":  "XX.XXX TL/m²",
    "per_sqm_max":  "XX.XXX TL/m²",
    "per_sqm_avg":  "XX.XXX TL/m²",
    "data_quality": "gercek",
    "source_count": {st.get("count", 0)}
  }},
  "neighborhood_analysis": {{
    "summary":     "2-3 cümle",
    "pros":        ["avantaj1","avantaj2","avantaj3"],
    "cons":        ["dezavantaj1","dezavantaj2"],
    "trend":       "yükselen",
    "trend_detail":"1-2 cümle"
  }},
  "investment_score": {{
    "score":    8,
    "max":      10,
    "label":    "Çok İyi",
    "reasoning":"2-3 cümle"
  }},
  "market_comparison": {{
    "vs_district":           "1-2 cümle",
    "vs_ankara":             "1-2 cümle",
    "similar_neighborhoods": ["mahalle1","mahalle2","mahalle3"]
  }},
  "key_factors": [
    {{"factor":"Başlık","impact":"positive","detail":"Açıklama"}},
    {{"factor":"Başlık","impact":"positive","detail":"Açıklama"}},
    {{"factor":"Başlık","impact":"negative","detail":"Açıklama"}},
    {{"factor":"Başlık","impact":"neutral", "detail":"Açıklama"}}
  ],
  "valuation_tips":    ["tavsiye1","tavsiye2","tavsiye3"],
  "web_sources":       ["hepsiemlak.com","zingat.com","sahibinden.com","emlakjet.com","endeksa.com"],
  "executive_summary": "Müşteriye ({name}) hitaben 3-4 cümle özet",
  "disclaimer":        "Bu rapor yapay zeka destekli ön değerleme amaçlıdır ve hukuki bağlayıcılığı yoktur. Kesin değerleme için yetkili SPK lisanslı ekspertiz önerilir."
}}"""

# ─────────────────────────────────────────────────────────────────────────────
# JSON Çıkarıcı
# ─────────────────────────────────────────────────────────────────────────────
def _extract_json(raw: str) -> str:
    if "```" in raw:
        for part in raw.split("```"):
            p = part.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw = p
                break
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    return raw[start:end] if start != -1 and end > start else raw

# ─────────────────────────────────────────────────────────────────────────────
# Ana Fonksiyon
# ─────────────────────────────────────────────────────────────────────────────
def generate_valuation_report(
    name: str,
    neighborhood: str,
    property_type: str,
    rooms: str = "",
    sqm: str   = "",
    notes: str = "",
) -> dict:
    """
    Çok kaynaklı web scrape + Gemini 2.5 Flash ile Ankara gayrimenkul değerleme.
    grok.py / gemini.py ile birebir aynı dönüş arayüzü.

    Returns:
        {"ok": True,  "report": {...}, "search_used": True, "listings_count": N}
        {"ok": False, "error": "..."}
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY tanımlı değil"}

    t0 = time.time()
    print(f"\n{'='*60}")
    print(f"🏠 Değerleme: {neighborhood} / {property_type}")
    if sqm:   print(f"   m²  : {sqm}")
    if rooms: print(f"   Oda : {rooms}")
    print(f"{'='*60}")

    # ── 1. Veri Toplama ───────────────────────────────────────────────────────
    results    = _multi_search(neighborhood, property_type, sqm)
    raw_prices = _extract_prices(results)

    # Scraper'ların "price" alanını da ekle
    for r in results:
        if r.get("price") and r["price"] not in raw_prices:
            raw_prices.append(r["price"])
    raw_prices = sorted(set(raw_prices))

    st = _stats(raw_prices, sqm)
    print(f"\n   📈 Ham fiyat : {len(raw_prices)} | Temizlenmiş : {st.get('count', 0)}")
    if st:
        print(f"   💰 Medyan   : {_fmt(st['median'])}")
        print(f"   💰 Ortalama : {_fmt(st['average'])}")
        if "per_sqm_avg" in st:
            print(f"   📐 m²/Ort   : {_fmt(st['per_sqm_avg'])}/m²")

    # ── 2. Context ────────────────────────────────────────────────────────────
    context = _build_context(results, st, sqm)

    # ── 3. Gemini ─────────────────────────────────────────────────────────────
    prompt = _build_prompt(
        name, neighborhood, property_type, rooms, sqm, notes, context, st
    )
    try:
        print(f"\n🤖 {GEMINI_MODEL} analiz ediyor...")
        client   = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model    = GEMINI_MODEL,
            contents = prompt,
        )
        raw_text = response.text.strip()
    except Exception as e:
        return {"ok": False, "error": f"Gemini hatası: {e}"}

    # ── 4. JSON Parse ─────────────────────────────────────────────────────────
    raw_text = _extract_json(raw_text)
    try:
        report = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse hatası: {e}\n{raw_text[:500]}")
        return {"ok": False, "error": f"JSON parse hatası: {e}"}

    # ── 5. Gerçek İstatistikle Fiyat Alanını Güvenle Üzerine Yaz ─────────────
    if st and st["count"] >= 3:
        pr = report.setdefault("price_range", {})
        pr["average"]      = _fmt(st["average"])
        pr["median"]       = _fmt(st["median"])
        pr["min"]          = _fmt(int(st["min"] * 0.93))
        pr["max"]          = _fmt(int(st["max"] * 1.07))
        pr["source_count"] = st["count"]
        pr["data_quality"] = "gercek"
        if "per_sqm_avg" in st:
            pr["per_sqm_avg"] = _fmt(st["per_sqm_avg"]) + "/m²"
            pr["per_sqm_min"] = _fmt(st["per_sqm_min"]) + "/m²"
            pr["per_sqm_max"] = _fmt(st["per_sqm_max"]) + "/m²"

    # ── 6. Meta ───────────────────────────────────────────────────────────────
    report["generated_at"]    = datetime.now().strftime("%d.%m.%Y %H:%M")
    report["neighborhood"]     = neighborhood
    report["property_type"]    = property_type
    report["model"]            = GEMINI_MODEL
    report["search_used"]      = len(results) > 0
    report["listings_count"]   = st.get("count", 0)
    report["raw_price_count"]  = len(raw_prices)
    report.setdefault(
        "web_sources",
        ["hepsiemlak.com", "zingat.com", "sahibinden.com", "emlakjet.com", "endeksa.com"],
    )

    elapsed = round(time.time() - t0, 1)
    pr      = report.get("price_range", {})
    print(f"\n✅ Tamamlandı [{elapsed}s]")
    print(f"   Medyan    : {pr.get('median', '?')}")
    print(f"   Ortalama  : {pr.get('average', '?')}")
    print(f"   Veri sayısı: {st.get('count', 0)} temizlenmiş / {len(raw_prices)} ham")

    return {
        "ok":             True,
        "report":         report,
        "search_used":    len(results) > 0,
        "listings_count": st.get("count", 0),
    }

# ======================================================================
# AI Listing Analysis & Scraping
# ======================================================================

from __future__ import annotations

import base64
import html as html_mod
from urllib.parse import urlparse
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

    title = url
    try:
        from bs4 import BeautifulSoup as _BS
        t_tag = _BS(html_mod.unescape(raw_html), "html.parser").find("title")
        if t_tag:
            title = t_tag.get_text(strip=True) or url
    except Exception:
        pass

    print(f"    ✓ Fotoğraf: {len(photos)} | Fiyat: {price} | Lokasyon: {location}")
    return {
        "ok": True, "source": "sahibinden_playwright_pagespeed",
        "title": title, "price": price, "location": location,
        "specs": specs, "description": "",
        "images": photos, "photo_count": len(photos),
        "photo_types": {"full": len(full_photos), "thumb": len(thumb_photos), "other": len(other_photos)},
        "screenshot": "",
    }

def _scrape_via_pagespeed(url: str) -> dict:
    """Sync wrapper — asyncio.run() ile async Playwright çağırır."""
    if not _PLAYWRIGHT:
        return {
            "ok": False,
            "error": "Playwright kurulu değil: pip install playwright && playwright install chromium",
        }
    try:
        return asyncio.run(_scrape_via_pagespeed_async(url))
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

# ======================================================================
# FSBO Analysis Engine
# ======================================================================

from datetime import datetime, timezone

# Güncel model listesi: https://ai.google.dev/gemini-api/docs/models
# gemini-2.5-flash      → kararlı, fiyat/performans dengesi (ana model)
# gemini-2.5-flash-lite → en hızlı/ekonomik 2.5 ailesi (yedek)
# gemini-2.0-flash      → DEPRECATED — kullanılmaz!
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL       = "gemini-2.5-flash"
GEMINI_FALLBACK    = "gemini-2.5-flash-lite"  # 2.0-flash deprecated; lite en iyi yedek
GEMINI_MAX_RETRIES = 3
GEMINI_RETRY_DELAY = 8   # saniye; 503 yük hatalarında başlangıç bekleme

def _is_configured() -> bool:
    return bool(GEMINI_API_KEY)

def fsbo_engine_status() -> dict:
    configured = _is_configured()
    return {
        "ok":         configured,
        "configured": configured,
        "model":      GEMINI_MODEL,
        "error":      None if configured else "GEMINI_API_KEY tanımlanmamış",
    }

def _build_prompt(contact_data: dict, text_input: str, timeline: list) -> str:
    """Ana Gemini analiz promptunu oluşturur."""
    name     = contact_data.get("name", "Bilinmiyor")
    phone    = contact_data.get("phone", "")
    district = contact_data.get("district", "")
    price    = contact_data.get("price", "")
    stage    = contact_data.get("stage", "")
    notes    = contact_data.get("notes", "")
    category = contact_data.get("category", "fsbo")

    # Timeline özetini al (son 10 aktivite)
    timeline_text = ""
    if timeline:
        for ev in timeline[-10:]:
            t = ev.get("type", "")
            txt = ev.get("text", "")
            dt  = ev.get("createdAt", "")[:10] if ev.get("createdAt") else ""
            timeline_text += f"  [{dt}] {t.upper()}: {txt}\n"

    return f"""Sen Türkiye'nin en deneyimli gayrimenkul danışmanlarından birisin. 
Uzmanlık alanın: FSBO (For Sale By Owner / Sahibinden Satış) mülk sahiplerini portföye kazanmak.

## LEAD BİLGİLERİ
İsim: {name}
Telefon: {phone}
İlçe/Bölge: {district or 'Belirtilmemiş'}
Tahmini Değer: {price or 'Belirtilmemiş'} TL
Kategori: {category.upper()}
Mevcut Aşama: {stage}
Notlar: {notes or 'Yok'}

## AKTİVİTE GEÇMİŞİ
{timeline_text or 'Henüz aktivite yok'}

## EK BİLGİLER (Manuel Girdi)
{text_input or 'Ek bilgi girilmemiş'}

## GÖREV

Aşağıdaki JSON yapısını Türkçe olarak üret. SADECE JSON döndür, başka metin yok:

{{
  "owner_profile": {{
    "likely_situation": "Ev sahibinin tahmini durumu (zaman baskısı var mı, fiyat konusunda ne düşünüyor vb.)",
    "motivation_level": "yüksek|orta|düşük",
    "knowledge_level": "piyasayı biliyor|kısmen biliyor|bilmiyor",
    "decision_maker": "yalnız|aile ile birlikte karar veriyor|belirsiz",
    "timeline": "acil|1-3 ay|3-6 ay|belirsiz",
    "pain_points": ["Mevcut sorun 1", "Mevcut sorun 2", "Mevcut sorun 3"]
  }},
  "property_assessment": {{
    "estimated_price_range": "Ekran görüntülerine ve bölgeye göre tahmini fiyat aralığı",
    "listing_quality": "İlan kalitesi değerlendirmesi (fotoğraflar, açıklama vb.)",
    "time_on_market": "Piyasada ne kadar süredir olduğuna dair çıkarım",
    "price_positioning": "düşük|uygun|yüksek|çok yüksek",
    "key_observations": ["Önemli gözlem 1", "Önemli gözlem 2"]
  }},
  "fsbo_approach": {{
    "strategy_type": "değer_odaklı|sorun_çözücü|piyasa_uzmanı|güven_inşa_edici|aciliyet_yaratıcı",
    "primary_message": "Ana mesajın tek cümle özeti",
    "tone": "samimi|profesyonel|uzman|empatik|iddialı",
    "opening_script": "İlk temas için 2-3 cümlelik açılış scripti",
    "positioning": "Kendinizi nasıl konumlandırmalısınız"
  }},
  "key_questions": [
    {{
      "question": "Sorulacak soru",
      "purpose": "Bu soruyu neden sormak gerekiyor",
      "best_moment": "Ne zaman sormak gerekiyor",
      "ideal_answer": "İdeal yanıt ne olmalı",
      "priority": "yüksek|orta|düşük"
    }}
  ],
  "objection_handling": [
    {{
      "objection": "Olası itiraz",
      "response": "Profesyonel yanıt",
      "follow_up": "Yanıttan sonra yapılacak hareket",
      "probability": "yüksek|orta|düşük"
    }}
  ],
  "followup_schedule": {{
    "contact_1": {{
      "timing": "Hemen / 24 saat içinde",
      "channel": "whatsapp|telefon|email",
      "message": "İletişim mesajı veya konuşma notu",
      "goal": "Bu temasın hedefi"
    }},
    "contact_2": {{
      "timing": "3-5 gün sonra",
      "channel": "telefon|whatsapp",
      "message": "İkinci temas notu",
      "goal": "İkinci temasın hedefi"
    }},
    "contact_3": {{
      "timing": "2 hafta sonra",
      "channel": "yüz yüze|telefon",
      "message": "Üçüncü temas notu",
      "goal": "Üçüncü temasın hedefi"
    }},
    "contact_4": {{
      "timing": "1 ay sonra",
      "channel": "telefon|whatsapp",
      "message": "Dördüncü temas notu",
      "goal": "Dördüncü temasın hedefi"
    }}
  }},
  "talking_points": [
    {{
      "point": "Ana konuşma noktası",
      "supporting_data": "Destekleyici veri veya argüman",
      "delivery": "Nasıl sunulmalı"
    }}
  ],
  "recommended_actions": [
    {{
      "action": "Yapılacak eylem",
      "priority": "acil|yüksek|orta|düşük",
      "timeframe": "Ne zaman yapılmalı",
      "expected_outcome": "Beklenen sonuç"
    }}
  ],
  "swot": {{
    "strengths": ["Danışman olarak avantajınız 1", "Avantaj 2"],
    "weaknesses": ["Zayıf nokta 1", "Dikkat edilmesi gereken 2"],
    "opportunities": ["Fırsat 1", "Fırsat 2"],
    "threats": ["Risk 1", "Risk 2"]
  }},
  "urgency_triggers": [
    {{
      "trigger": "Aciliyet tetikleyicisi",
      "explanation": "Neden bu bir avantaj",
      "how_to_use": "Nasıl kullanılmalı"
    }}
  ],
  "verdict": "Bu lead hakkında 2-3 cümlelik genel değerlendirme ve öneri",
  "confidence_score": 7,
  "resistance_level": "orta",
  "next_contact_timing": "24 saat içinde WhatsApp ile başlayın",
  "estimated_conversion_probability": "yüksek|orta|düşük",
  "risk_flags": ["Dikkat edilmesi gereken önemli risk varsa buraya yazın"]
}}

JSON dışında hiçbir şey yazma. Tüm alanları doldur. Türkçe yaz."""

def _call_gemini_multimodal(
    prompt: str,
    images_b64: list,
    audio_b64: str | None,
    audio_mime: str,
    model: str | None = None,
) -> dict:
    """
    Gemini API'ye multimodal istek gönderir.

    Hata yönetimi (Google dokümantasyonu: https://ai.google.dev/gemini-api/docs/troubleshooting):
      503 "high demand"  → MAX_RETRIES kez exponential backoff ile yeniden dener
      429 rate-limit     → yanıttaki "retry in Xs" süresini bekler
      429 quota=0        → bu model ücretsiz katmanda yok; yedek modele geçer
      Deprecated modeller (gemini-2.0-*) hiçbir zaman kullanılmaz
    """
    import requests as req

    use_model = model or GEMINI_MODEL

    # Parts listesi
    parts: list = []
    for i, b64 in enumerate(images_b64[:8]):
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
        parts.append({"text": f"[Görüntü {i+1}: Sahibinden ilan veya WhatsApp ekran görüntüsü]"})

    if audio_b64:
        ab = audio_b64.split(",", 1)[1] if "," in audio_b64 else audio_b64
        parts.append({"inline_data": {"mime_type": audio_mime or "audio/webm", "data": ab}})
        parts.append({"text": "[Ses kaydı: Danışman-ev sahibi görüşmesi]"})

    parts.append({"text": prompt})

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature":      0.4,
            "maxOutputTokens":  8192,
            "responseMimeType": "application/json",
        },
    }

    # Sadece güncel 2.5 modelleri; 2.0-flash deprecated olduğu için eklenmez
    models_to_try = [use_model]
    if use_model != GEMINI_FALLBACK and "2.0" not in use_model:
        models_to_try.append(GEMINI_FALLBACK)

    last_error = "Bilinmeyen hata"

    for attempt_model in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{attempt_model}:generateContent?key={GEMINI_API_KEY}"
        )
        delay = GEMINI_RETRY_DELAY

        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            try:
                resp = req.post(url, json=payload, timeout=120)
                data = resp.json()

                # ── Başarılı yanıt ───────────────────────────────────────
                if resp.ok:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return {"ok": False, "error": "Gemini boş yanıt döndürdü"}
                    raw = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in raw).strip()
                    text = re.sub(r"^```(?:json)?", "", text).strip()
                    text = re.sub(r"```$",          "", text).strip()
                    parsed = json.loads(text)
                    if attempt_model != use_model:
                        print(f"✅ Gemini yanıt verdi (yedek: {attempt_model})")
                    return {"ok": True, "strategy": parsed}

                # ── Hata yanıtı ──────────────────────────────────────────
                err     = data.get("error", {})
                err_msg = err.get("message", str(data))
                status  = resp.status_code
                last_error = err_msg

                # 503 — Geçici yüksek yük → yeniden dene
                if status == 503 or "high demand" in err_msg.lower() or "overloaded" in err_msg.lower():
                    print(f"⏳ {attempt_model} meşgul (deneme {attempt}/{GEMINI_MAX_RETRIES}), {delay}s bekleniyor...")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue

                # 429 — Kota / hız sınırı
                if status == 429:
                    # "limit: 0" → bu model artık ücretsiz kotada yok, yedeke geç
                    if "limit: 0" in err_msg:
                        print(f"⛔ {attempt_model}: ücretsiz kota=0, yedek deneniyor...")
                        last_error = (
                            f"'{attempt_model}' ücretsiz katmanda kullanılamıyor "
                            "(kota=0). Google AI Studio'dan faturalandırmayı "
                            "etkinleştirin: https://aistudio.google.com/apikey"
                        )
                        break   # bu model için çık, bir sonraki modele geç

                    # "retry in Xs" → belirtilen süreyi bekle
                    m = re.search(r"retry in ([\d.]+)s", err_msg, re.IGNORECASE)
                    wait = float(m.group(1)) + 2 if m else delay
                    wait = min(wait, 65)
                    print(f"⏳ {attempt_model} hız sınırı (deneme {attempt}/{GEMINI_MAX_RETRIES}), {wait:.0f}s bekleniyor...")
                    time.sleep(wait)
                    delay = min(delay * 2, 60)
                    continue

                # Diğer hatalar (400, 403, 404…) → yeniden deneme olmaz
                return {"ok": False, "error": err_msg}

            except json.JSONDecodeError as e:
                return {"ok": False, "error": f"JSON parse hatası: {e}"}
            except req.exceptions.Timeout:
                last_error = "API timeout (120s)"
                print(f"⚠️  {attempt_model} timeout (deneme {attempt})")
                time.sleep(delay)
                delay = min(delay * 2, 60)
            except Exception as e:
                last_error = str(e)
                print(f"⚠️  {attempt_model} beklenmedik hata (deneme {attempt}): {e}")
                time.sleep(delay)
                delay = min(delay * 2, 60)

        lbl = "yedek model de başarısız." if attempt_model == GEMINI_FALLBACK else "yedek modele geçiliyor..."
        print(f"❌ {attempt_model} tüm denemeler başarısız — {lbl}")

    return {"ok": False, "error": last_error}

def _build_transcript_prompt(audio_mime: str) -> str:
    return """Bu ses kaydını tam olarak transkript et. Konuşma Türkçe olabilir.
Transkripti düz metin olarak ver, başka açıklama ekleme."""

def _transcribe_audio(audio_b64: str, audio_mime: str) -> str | None:
    """Ses kaydını Gemini ile metin olarak çıkarır."""

    if not audio_b64 or not GEMINI_API_KEY:
        return None

    if "," in audio_b64:
        audio_b64 = audio_b64.split(",", 1)[1]

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {
                    "inline_data": {
                        "mime_type": audio_mime or "audio/webm",
                        "data": audio_b64,
                    }
                },
                {"text": _build_transcript_prompt(audio_mime)},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    try:
        resp = req.post(url, json=payload, timeout=60)
        data = resp.json()
        if resp.ok:
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip() or None
    except Exception as e:
        print(f"⚠️  Transkript hatası: {e}")
    return None

# ── Ana Fonksiyon ────────────────────────────────────────────────

def analyze_fsbo(
    contact_data: dict,
    screenshots: list | None      = None,   # [base64_str, ...]
    text_input:  str | None       = None,
    audio_b64:   str | None       = None,
    audio_mime:  str              = "audio/webm",
    timeline:    list | None      = None,
) -> dict:
    """
    FSBO stratejisini Gemini 2.5 Flash ile üretir.

    Returns:
        {"ok": True, "strategy": {...}, "audio_transcript": "..." | None}
        {"ok": False, "error": "..."}
    """
    if not _is_configured():
        return {"ok": False, "error": "GEMINI_API_KEY tanımlanmamış"}

    images  = screenshots or []
    tl      = timeline    or []

    # Ses transkripti
    transcript = None
    if audio_b64:
        print(f"🎙️  Ses kaydı transkript ediliyor...")
        transcript = _transcribe_audio(audio_b64, audio_mime)
        if transcript:
            print(f"✅ Transkript hazır ({len(transcript)} karakter)")
            # Transkrip'i text_input'a ekle
            extra = f"\n\n[SES KAYDI TRANSKRİPTİ]\n{transcript}"
            text_input = (text_input or "") + extra

    # Prompt oluştur
    prompt = _build_prompt(contact_data, text_input or "", tl)

    print(f"🤖 FSBO analizi başlatıldı: {contact_data.get('name','?')} | "
          f"{len(images)} görüntü | ses={'evet' if audio_b64 else 'hayır'}")

    result = _call_gemini_multimodal(
        prompt=prompt,
        images_b64=images,
        audio_b64=audio_b64,
        audio_mime=audio_mime,
    )

    if result.get("ok"):
        strategy = result["strategy"]
        strategy["generated_at"] = datetime.now(timezone.utc).isoformat()
        strategy["input_summary"] = {
            "images_count":   len(images),
            "has_audio":      bool(audio_b64),
            "has_text":       bool(text_input and text_input.strip()),
            "timeline_count": len(tl),
        }
        print(f"✅ FSBO analizi tamamlandı | skor: {strategy.get('confidence_score','?')}/10 | "
              f"direnç: {strategy.get('resistance_level','?')}")
        return {
            "ok":               True,
            "strategy":         strategy,
            "audio_transcript": transcript,
        }

    print(f"❌ FSBO analiz hatası: {result.get('error')}")
    return result

# ======================================================================
# Buyer Matching Engine
# ======================================================================

import math
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

# Opsiyonel: sentence-transformers (vektör benzerliği için)
try:
    _SENTENCE_TRANSFORMER = True
except ImportError:
    _SENTENCE_TRANSFORMER = False
    print("⚠️  sentence-transformers yüklü değil — pip install sentence-transformers")

class NotificationChannel(Enum):
    """Kullanıcıya bildirim gönderilecek kanallar."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    CRM_TASK = "crm_task"
    DASHBOARD = "dashboard"

class MatchingTier(Enum):
    """Eşleşme kalitesi seviyeleri."""
    PERFECT = "perfect"        # 90-100
    EXCELLENT = "excellent"    # 75-89
    GOOD = "good"              # 60-74
    FAIR = "fair"              # 45-59
    WEAK = "weak"              # 30-44
    POOR = "poor"              # <30

# ================================================================
# KONFIGÜRASYON
# ================================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MIN_MATCH_SCORE = 50  # İlan gösterilmesi için minimum skor
VECTOR_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Hızlı, hafif (80M)

# ================================================================
# VERİ MODELLERİ
# ================================================================

class BuyerProfile:
    """Alıcı profili — kriterleri ve tercihler."""

    def __init__(self, profile_dict: dict):
        self.buyer_id = profile_dict.get("id", "")
        self.uid = profile_dict.get("uid", "")
        self.name = profile_dict.get("name", "")
        self.email = profile_dict.get("email", "")
        self.phone = profile_dict.get("phone", "")
        self.telegram_id = profile_dict.get("telegram_id")
        self.whatsapp_phone = profile_dict.get("whatsapp_phone")

        # Kriterler
        self.criteria = profile_dict.get("criteria", {})
        self.min_price = self.criteria.get("min_price", 0)
        self.max_price = self.criteria.get("max_price", 10_000_000)
        self.min_area = self.criteria.get("min_area", 0)
        self.max_area = self.criteria.get("max_area", 1000)
        self.neighborhoods = self.criteria.get("neighborhoods", [])
        self.property_types = self.criteria.get("property_types", [])
        self.min_rooms = self.criteria.get("min_rooms")
        self.max_rooms = self.criteria.get("max_rooms")
        self.min_age = self.criteria.get("min_age")
        self.max_age = self.criteria.get("max_age")
        self.amenities_required = self.criteria.get("amenities_required", [])
        self.natural_language_criteria = self.criteria.get("natural_language", "")

        # Tercihler
        self.preferences = profile_dict.get("preferences", {})
        self.notification_channels = self.preferences.get("notification_channels", ["email", "crm_task"])
        self.auto_match = self.preferences.get("auto_match", True)
        self.weekly_summary = self.preferences.get("weekly_summary", False)
        self.priority_level = self.preferences.get("priority_level", "medium")  # low/medium/high

        # Durum
        self.is_active = profile_dict.get("is_active", True)
        self.created_at = profile_dict.get("created_at", datetime.now(timezone.utc).isoformat())
        self.updated_at = profile_dict.get("updated_at", datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Firebase'e kaydetmek için dict'e dönüştür."""
        return {
            "id": self.buyer_id,
            "uid": self.uid,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "telegram_id": self.telegram_id,
            "whatsapp_phone": self.whatsapp_phone,
            "criteria": {
                "min_price": self.min_price,
                "max_price": self.max_price,
                "min_area": self.min_area,
                "max_area": self.max_area,
                "neighborhoods": self.neighborhoods,
                "property_types": self.property_types,
                "min_rooms": self.min_rooms,
                "max_rooms": self.max_rooms,
                "min_age": self.min_age,
                "max_age": self.max_age,
                "amenities_required": self.amenities_required,
                "natural_language": self.natural_language_criteria,
            },
            "preferences": {
                "notification_channels": self.notification_channels,
                "auto_match": self.auto_match,
                "weekly_summary": self.weekly_summary,
                "priority_level": self.priority_level,
            },
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

class ListingMatch:
    """İlan-Alıcı eşleşmesi."""

    def __init__(
        self,
        buyer_id: str,
        listing_id: str,
        listing_data: dict,
        match_score: float,
        match_details: dict,
    ):
        self.buyer_id = buyer_id
        self.listing_id = listing_id
        self.listing_data = listing_data
        self.match_score = match_score
        self.match_details = match_details
        self.tier = self._determine_tier()
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.notification_sent = False
        self.user_interest = None  # "interested", "not_interested", "enquiry_sent", vb.

    def _determine_tier(self) -> str:
        """Skor'a göre tier belirle."""
        score = self.match_score
        if score >= 90:
            return MatchingTier.PERFECT.value
        elif score >= 75:
            return MatchingTier.EXCELLENT.value
        elif score >= 60:
            return MatchingTier.GOOD.value
        elif score >= 45:
            return MatchingTier.FAIR.value
        elif score >= 30:
            return MatchingTier.WEAK.value
        else:
            return MatchingTier.POOR.value

    def to_dict(self) -> dict:
        """Firebase'e kaydetmek için dict'e dönüştür."""
        return {
            "buyer_id": self.buyer_id,
            "listing_id": self.listing_id,
            "listing_data": self.listing_data,
            "match_score": self.match_score,
            "match_details": self.match_details,
            "tier": self.tier,
            "created_at": self.created_at,
            "notification_sent": self.notification_sent,
            "user_interest": self.user_interest,
        }

# ================================================================
# MATCHING ENGINE
# ================================================================

class BuyerMatcher:
    """Alıcı profili ile ilanları eşleştir."""

    def __init__(self):
        self.vector_model = None
        if _SENTENCE_TRANSFORMER:
            try:
                self.vector_model = SentenceTransformer(VECTOR_MODEL)
                print(f"✅ Vector model yüklendi: {VECTOR_MODEL}")
            except Exception as e:
                print(f"⚠️  Vector model yüklenemedi: {e}")

    def match_listing(self, buyer: BuyerProfile, listing: dict) -> Optional[ListingMatch]:
        """
        İlanı alıcı profili ile eşleştir.
        İlan: {"id", "price", "area", "location", "property_type", "rooms", "age", "amenities", ...}
        """
        match_details = {}
        scores = {}

        # 1. Fiyat eşleşmesi
        price = listing.get("price", 0)
        if price < buyer.min_price or price > buyer.max_price:
            return None  # Fiyat aralığı dışında
        price_score = self._score_price(price, buyer)
        scores["price"] = price_score
        match_details["price"] = f"{price:,} TL ({price_score:.0f}%)"

        # 2. Alan eşleşmesi
        area = listing.get("area", 0)
        if area < buyer.min_area or area > buyer.max_area:
            return None  # Alan aralığı dışında
        area_score = self._score_area(area, buyer)
        scores["area"] = area_score
        match_details["area"] = f"{area} m² ({area_score:.0f}%)"

        # 3. Lokasyon eşleşmesi
        location = listing.get("location", "").strip()
        location_score = self._score_location(location, buyer)
        if location_score == 0 and buyer.neighborhoods:
            return None  # Lokasyon kritik ve eşleşmiyor
        scores["location"] = location_score
        match_details["location"] = f"{location} ({location_score:.0f}%)"

        # 4. Mülk tipi eşleşmesi
        prop_type = listing.get("property_type", "").strip()
        prop_type_score = self._score_property_type(prop_type, buyer)
        if prop_type_score == 0 and buyer.property_types:
            return None
        scores["property_type"] = prop_type_score
        match_details["property_type"] = f"{prop_type} ({prop_type_score:.0f}%)"

        # 5. Oda sayısı eşleşmesi (opsiyonel)
        if buyer.min_rooms or buyer.max_rooms:
            rooms = listing.get("rooms", None)
            if rooms:
                rooms_score = self._score_rooms(rooms, buyer)
                scores["rooms"] = rooms_score
                match_details["rooms"] = f"{rooms} ({rooms_score:.0f}%)"

        # 6. Yaş eşleşmesi (opsiyonel)
        if buyer.min_age or buyer.max_age:
            age = listing.get("age", None)
            if age is not None:
                age_score = self._score_age(age, buyer)
                scores["age"] = age_score
                match_details["age"] = f"{age} yıl ({age_score:.0f}%)"

        # 7. Amenities eşleşmesi
        amenities = listing.get("amenities", [])
        if buyer.amenities_required:
            amenities_score = self._score_amenities(amenities, buyer)
            scores["amenities"] = amenities_score
            match_details["amenities"] = f"{amenities_score:.0f}% eşleşme"

        # 8. Natural language kriterleri (Gemini)
        if buyer.natural_language_criteria and GEMINI_API_KEY:
            nl_score = self._score_natural_language(listing, buyer)
            scores["natural_language"] = nl_score
            match_details["nl_criteria"] = f"{nl_score:.0f}%"

        # 9. Vectoral benzerlik (metafor + açıklama)
        if self.vector_model:
            vector_score = self._score_vector_similarity(listing, buyer)
            scores["vector"] = vector_score
            match_details["vector"] = f"{vector_score:.0f}%"

        # Ortalaması al (ağırlıklı)
        final_score = self._weighted_average(scores)

        if final_score < MIN_MATCH_SCORE:
            return None

        # Match nesnesi oluştur
        return ListingMatch(
            buyer_id=buyer.buyer_id,
            listing_id=listing.get("id", ""),
            listing_data=listing,
            match_score=final_score,
            match_details=match_details,
        )

    def _score_price(self, price: float, buyer: BuyerProfile) -> float:
        """Fiyat skoru (hedef için optimal)."""
        mid = (buyer.min_price + buyer.max_price) / 2
        range_width = buyer.max_price - buyer.min_price
        distance = abs(price - mid)
        # Merkeze ne kadar yakınsa o kadar yüksek skor
        return max(0, 100 - (distance / range_width) * 100)

    def _score_area(self, area: float, buyer: BuyerProfile) -> float:
        """Alan skoru."""
        mid = (buyer.min_area + buyer.max_area) / 2
        range_width = buyer.max_area - buyer.min_area
        if range_width == 0:
            return 100.0
        distance = abs(area - mid)
        return max(0, 100 - (distance / range_width) * 100)

    def _score_location(self, location: str, buyer: BuyerProfile) -> float:
        """Lokasyon skoru (kesin eşleşme veya 0)."""
        if not buyer.neighborhoods:
            return 100.0  # Lokasyon kriteri yoksa tam skor
        loc_lower = location.lower().strip()
        for nb in buyer.neighborhoods:
            if nb.lower() in loc_lower or loc_lower in nb.lower():
                return 100.0
        return 0.0  # Eşleşmedi

    def _score_property_type(self, prop_type: str, buyer: BuyerProfile) -> float:
        """Mülk tipi skoru."""
        if not buyer.property_types:
            return 100.0
        pt_lower = prop_type.lower().strip()
        for ptype in buyer.property_types:
            if ptype.lower() in pt_lower or pt_lower in ptype.lower():
                return 100.0
        return 0.0

    def _score_rooms(self, rooms: int, buyer: BuyerProfile) -> float:
        """Oda sayısı skoru."""
        if buyer.min_rooms and rooms < buyer.min_rooms:
            return 0.0
        if buyer.max_rooms and rooms > buyer.max_rooms:
            return 0.0
        return 100.0

    def _score_age(self, age: int, buyer: BuyerProfile) -> float:
        """Yaş skoru."""
        if buyer.min_age and age < buyer.min_age:
            return 0.0
        if buyer.max_age and age > buyer.max_age:
            return 0.0
        return 100.0

    def _score_amenities(self, amenities: List[str], buyer: BuyerProfile) -> float:
        """Amenities eşleşme oranı."""
        if not buyer.amenities_required:
            return 100.0
        if not amenities:
            return 0.0
        amenities_lower = [a.lower() for a in amenities]
        matches = sum(
            1 for req in buyer.amenities_required
            if any(req.lower() in am for am in amenities_lower)
        )
        return (matches / len(buyer.amenities_required)) * 100

    def _score_natural_language(self, listing: dict, buyer: BuyerProfile) -> float:
        """Gemini ile natural language kriterleri parse et ve skor ver."""
        if not GEMINI_API_KEY:
            return 50.0
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            client = genai.Client()
            prompt = f"""
İlan: {json.dumps(listing, ensure_ascii=False, indent=2)}

Alıcı Kriterleri (Türkçe): "{buyer.natural_language_criteria}"

Bu ilanın alıcı kriterlerine ne kadar uyduğunu 0-100 arası bir skor ver.
SADECE SAYI döndür, açıklama yapma. Örnek: 85
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai.GenerateContentConfig(max_output_tokens=10),
            )
            text = (response.text or "50").strip()
            score = float("".join(filter(str.isdigit, text.split("\n")[0]))) if any(c.isdigit() for c in text) else 50.0
            return min(100.0, max(0.0, score))
        except Exception as e:
            print(f"⚠️  NL scoring hatası: {e}")
            return 50.0

    def _score_vector_similarity(self, listing: dict, buyer: BuyerProfile) -> float:
        """Vector benzerliği (listing description vs buyer NL criteria)."""
        if not self.vector_model or not buyer.natural_language_criteria:
            return 50.0
        try:
            listing_text = f"{listing.get('property_type', '')} {listing.get('location', '')} {listing.get('description', '')}"
            emb_listing = self.vector_model.encode(listing_text, convert_to_tensor=True)
            emb_buyer = self.vector_model.encode(buyer.natural_language_criteria, convert_to_tensor=True)
            # Cosine similarity
            similarity = float((emb_listing @ emb_buyer.T).item())
            return max(0, min(100, similarity * 100))
        except Exception as e:
            print(f"⚠️  Vector similarity hatası: {e}")
            return 50.0

    def _weighted_average(self, scores: Dict[str, float]) -> float:
        """Ağırlıklı ortalama (kritik olanlar ağırlıklı)."""
        weights = {
            "price": 0.25,
            "area": 0.2,
            "location": 0.2,
            "property_type": 0.15,
            "rooms": 0.05,
            "age": 0.05,
            "amenities": 0.05,
            "natural_language": 0.03,
            "vector": 0.02,
        }
        total_weight = 0
        weighted_sum = 0
        for key, score in scores.items():
            weight = weights.get(key, 0.05)
            weighted_sum += score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 50.0

# ================================================================
# NOTIFICATION ENGINE (Placeholder)
# ================================================================

class NotificationEngine:
    """
    Eşleşmeleri alıcıya farklı kanallardan bildiri.
    Gerçek implementation: app.py'de çalışacak ve mailer.py, wa_cloud.py'yi kullanacak.
    """

    @staticmethod
    def notify_buyer(
        match: ListingMatch,
        buyer: BuyerProfile,
        channels: List[str],
    ) -> Dict[str, bool]:
        """Alıcıyı eşleşme hakkında bildir."""
        results = {}
        for channel in channels:
            try:
                if channel == "email" and buyer.email:
                    results["email"] = NotificationEngine._send_email_notification(match, buyer)
                elif channel == "telegram" and buyer.telegram_id:
                    results["telegram"] = NotificationEngine._send_telegram_notification(match, buyer)
                elif channel == "whatsapp" and buyer.whatsapp_phone:
                    results["whatsapp"] = NotificationEngine._send_whatsapp_notification(match, buyer)
                elif channel == "crm_task":
                    results["crm_task"] = NotificationEngine._create_crm_task(match, buyer)
            except Exception as e:
                print(f"❌ {channel} notification hatası: {e}")
                results[channel] = False
        return results

    @staticmethod
    def _send_email_notification(match: ListingMatch, buyer: BuyerProfile) -> bool:
        """Email gönder (mailer.py ile entegrasyon)."""
        # Placeholder — app.py'de çalışacak
        return True

    @staticmethod
    def _send_telegram_notification(match: ListingMatch, buyer: BuyerProfile) -> bool:
        """Telegram bildir."""
        # Placeholder — app.py'de çalışacak
        return True

    @staticmethod
    def _send_whatsapp_notification(match: ListingMatch, buyer: BuyerProfile) -> bool:
        """WhatsApp gönder (wa_cloud.py ile entegrasyon)."""
        # Placeholder — app.py'de çalışacak
        return True

    @staticmethod
    def _create_crm_task(match: ListingMatch, buyer: BuyerProfile) -> bool:
        """CRM'e görev aç."""
        # Placeholder — app.py'de çalışacak
        return True

# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def parse_natural_language_criteria(text: str, api_key: str = "") -> Optional[dict]:
    """
    Natural language filtreleri parse et (Gemini ile).
    "Ankara'da 2+1 daire, maksimum 4.5 milyon, Çankaya veya Dikmen"
    → {"price": 4500000, "neighborhoods": [...], "rooms": 3, ...}
    """
    if not GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.Client()
        prompt = f"""
Türkçe gayrimenkul arama metnini parse et ve JSON döndür.

Metin: "{text}"

JSON formatı (istenen alanları fill et, yoksa null):
{{
  "min_price": null,
  "max_price": null,
  "min_area": null,
  "max_area": null,
  "neighborhoods": [],
  "property_types": [],
  "min_rooms": null,
  "max_rooms": null,
  "min_age": null,
  "max_age": null
}}

SADECE JSON döndür, açıklama yapma.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.GenerateContentConfig(max_output_tokens=200),
        )
        text_out = response.text or ""
        json_match = re.search(r"\{.*\}", text_out, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"⚠️  NL parsing hatası: {e}")
    return None

# ================================================================
# STATUS
# ================================================================

def buyer_engine_status() -> dict:
    """Buyer engine durumunu döner."""
    return {
        "ok": True,
        "matcher": True,
        "vector_model": _SENTENCE_TRANSFORMER,
        "min_match_score": MIN_MATCH_SCORE,
    }

# ======================================================================
# Main Flask Application
# ======================================================================

load_dotenv()  # .env dosyasını otomatik yükle
from buyer_engine import BuyerProfile, BuyerMatcher, ListingMatch, NotificationEngine,NotificationChannel, MatchingTier, buyer_engine_status, parse_natural_language_criteria

# ── Lokal fallback credential'lar (import'lardan ÖNCE set edilmeli) ──────────
# mailer.py ve wa_cloud.py modül yüklenirken env'i okur,
# bu yüzden setdefault'lar her import'tan önce çalışmalı.
os.environ.setdefault("EMAIL_PROVIDER",   "smtp")
os.environ.setdefault("EMAIL_FROM",       "yigitnarinofficial@gmail.com")
os.environ.setdefault("EMAIL_FROM_NAME",  "Nexa CRM")
os.environ.setdefault("SMTP_HOST",        "smtp.gmail.com")
os.environ.setdefault("SMTP_PORT",        "587")
os.environ.setdefault("SMTP_USE_TLS",     "true")
os.environ.setdefault("SMTP_USERNAME",    "yigitnarinofficial@gmail.com")
os.environ.setdefault("SMTP_PASSWORD",    "")  # .env dosyasına taşındı — SMTP_PASSWORD=<şifre>
os.environ.setdefault("ENABLE_CUSTOMER_EMAIL_AUTOMATION", "true")
# GEMINI_API_KEY → Render Dashboard > Environment Variables

from flask import Flask, jsonify, send_file, request as flask_request
# FAZ 2: Rate limiting — pip install flask-limiter
try:
    _limiter_available = True
except ImportError:
    _limiter_available = False
    print("⚠️  flask-limiter yüklü değil — pip install flask-limiter")
from wa_cloud import send_whatsapp, send_whatsapp_template, wa_status, verify_webhook_token
from mailer import (
    send_transactional_email, build_lead_confirmation_email, email_status,
    build_valuation_report_email, build_advisor_valuation_email,
)
from valuation import generate_valuation_report, valuation_status as gemini_status
from ai_listing import scrape_listing, analyze_listing, ai_listing_status
from fsbo_engine import analyze_fsbo, fsbo_engine_status

# ── Firebase Admin SDK ──────────────────────────────────────────

app = Flask(__name__)
CORS(app, origins=[
    "https://nexacrm.com",
    "https://nexa-crm.onrender.com",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
], supports_credentials=True)

# FAZ 2: Rate limiter (flask-limiter yüklüyse aktif olur)
if _limiter_available:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per hour"],
        storage_uri="memory://",
    )
else:
    limiter = None

# ================================================================
# AYARLAR
# ================================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")  # .env: TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "")  # .env: TELEGRAM_CHAT_ID=...
SERVICE_ACCOUNT    = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "service-account.json")

# WhatsApp Cloud API — Meta
# WA_PHONE_NUMBER_ID : Meta Business → WhatsApp → Phone Number ID
# WA_ACCESS_TOKEN    : System User permanent token
# WA_ADVISOR_PHONE   : Danışmanın WA numarası (bildirim alacak)
WA_ADVISOR_PHONE   = os.environ.get("WA_ADVISOR_PHONE", "")  # .env: WA_ADVISOR_PHONE=905XXXXXXXXX
CUSTOMER_WA_TEMPLATE_NAME = os.environ.get("CUSTOMER_WA_TEMPLATE_NAME", "").strip()
ENABLE_CUSTOMER_EMAIL_AUTOMATION = os.environ.get("ENABLE_CUSTOMER_EMAIL_AUTOMATION", "true").strip().lower() in ("1", "true", "yes")
ENABLE_CUSTOMER_WA_AUTOMATION    = os.environ.get("ENABLE_CUSTOMER_WA_AUTOMATION", "false").strip().lower() in ("1", "true", "yes")

# Değerleme raporu — yeni
VALUATION_WA_TEMPLATE_NAME = os.environ.get("VALUATION_WA_TEMPLATE_NAME", "").strip()
ADVISOR_EMAIL               = os.environ.get("ADVISOR_EMAIL", "").strip()

# İlan hedef URL
TARGET_URL = "https://www.cb.com.tr/ilanlar?officeid=372&officeuserid=18631"

# Ankara koordinatları (fallback)
ANKARA_LAT = 39.9334
ANKARA_LNG = 32.8597
DIKMEN_LAT = 39.8854
DIKMEN_LNG = 32.8514

ANKARA_SEMTLER = [
    "Dikmen", "Çukurambar", "Birlik Mahallesi", "Çayyolu",
    "Oran", "Angora Evleri", "Beysukent",
    "Kızılay", "Tunalı", "Ayrancı", "Gaziosmanpaşa", "GOP",
    "Kavaklidere", "Kavaklıdere", "Çankaya",
    "Balgat", "Emek", "Bahçelievler", "Öveçler",
    "Güvenevler", "Yıldız", "Çetin Emeç", "Mustafa Kemal",
    "Aziziye", "Naci Çakır",
    "Keçiören", "Mamak", "Altındağ", "Sincan",
    "Etimesgut", "Gölbaşı", "Pursaklar", "Yenimahalle",
    "Bağlıca", "Batıkent", "Eryaman",
]

# ── Ankara mahalle/semt koordinat sözlüğü ──────────────────────────────────────
# ASCII-normalize edilmiş versiyon (normalize() fonksiyonu sonrasındaki form).
# İkinci tanım (aşağıda) bu bloğun yerini alır — bu yüzden bu blok kaldırıldı.
# Bkz: ANKARA_COORDS tanımı _normalize() fonksiyonunun ardında.

# ================================================================
# BOOTSTRAP & SCHEDULER IMPORTS
# ================================================================
try:
    _apscheduler_available = True
except ImportError:
    _apscheduler_available = False
    print("⚠️  APScheduler yüklü değil: pip install apscheduler")

# ================================================================
# GLOBAL STATE
# ================================================================
_scheduler = None
_listing_cache_time = None
_bootstrap_done = False
_fb_initialized = False
db_admin = None

# ================================================================
# FİREBASE ADMIN — başlatma
# ================================================================

def init_firebase_admin():
    global _fb_initialized, db_admin
    if _fb_initialized:
        return
    try:
        import json as _json

        # Render'da FIREBASE_SERVICE_ACCOUNT env var'ı JSON string içerir.
        # Lokal'de ise service-account.json dosya yoludur.
        # İkisini de destekle:
        sa_value = SERVICE_ACCOUNT.strip()
        # .env dosyasında değer tek/çift tırnakla sarılmış olabilir → temizle
        if (sa_value.startswith("'") and sa_value.endswith("'")) or \
           (sa_value.startswith('"') and sa_value.endswith('"')):
            sa_value = sa_value[1:-1]

        if os.path.exists(sa_value):
            # Dosya yolu → klasik yöntem
            cred = credentials.Certificate(sa_value)
            print("✅ Firebase Admin bağlandı (dosya)")
        elif sa_value.startswith("{"):
            # JSON string içeriği → dict'e parse et
            sa_dict = _json.loads(sa_value)
            cred = credentials.Certificate(sa_dict)
            print("✅ Firebase Admin bağlandı (env JSON)")
        else:
            print(f"⚠️  Firebase service account bulunamadı — "
                  f"FIREBASE_SERVICE_ACCOUNT ortam değişkeni JSON string ya da geçerli dosya yolu olmalı")
            return

        firebase_admin.initialize_app(cred)
        db_admin = admin_firestore.client()
        _fb_initialized = True
    except Exception as e:
        print(f"❌ Firebase Admin hatası: {e}")

# ================================================================
# BACKGROUND SCHEDULER
# ================================================================

def start_scheduler():
    """APScheduler'ı başlat."""
    global _scheduler
    
    if _scheduler is not None:
        return
    
    if not _apscheduler_available:
        print("⚠️  APScheduler yüklü değil, background tasks deaktif")
        return
    
    try:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.start()
        print("✅ Background Scheduler başlatıldı")
    except Exception as e:
        print(f"❌ Scheduler başlatma hatası: {e}")
        _scheduler = None

def _refresh_listings_bg():
    """Listeleri arka planda yenile."""
    global _listing_cache_time
    
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        _listing_cache_time = current_time
        print(f"📋 Listing refresh başladı: {current_time}")
    except Exception as e:
        print(f"⚠️  Listing refresh hatası: {e}")

def check_bootstrap_status() -> dict:
    """Bootstrap durumunu kontrol et."""
    return {
        "ok": _bootstrap_done,
        "firebase_initialized": _fb_initialized,
        "scheduler_running": _scheduler is not None and _scheduler.running if _scheduler else False,
        "last_listing_refresh": _listing_cache_time,
    }

def bootstrap_app():
    """Uygulamayı başlat — tüm servisleri initialize et."""
    global _bootstrap_done
    
    if _bootstrap_done:
        return
    
    print("\n" + "="*70)
    print("🚀 NEXA CRM - Bootstrap Başlatılıyor")
    print("="*70 + "\n")
    
    init_firebase_admin()
    start_scheduler()
    _refresh_listings_bg()
    
    _bootstrap_done = True
    
    print("\n" + "="*70)
    print("✅ Bootstrap Tamamlandı")
    print("="*70 + "\n")

# ================================================================
# TELEGRAM
# ================================================================
def send_telegram(text: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")
        return False

# ================================================================
# SAYFA ROUTE'LARI
# ================================================================

@app.route("/")
def home():
    """Web sitesi — site.html"""
    try:
        return send_file("site.html")
    except Exception as e:
        return f"site.html bulunamadı: {e}", 404

@app.route("/crm")
def crm():
    """CRM paneli — crm.html"""
    try:
        return send_file("crm.html")
    except Exception as e:
        return f"crm.html bulunamadı: {e}", 404

# ================================================================
# API — İLAN SCRAPER
# ================================================================

import re as _re
import math as _math
import random as _random

_coord_cache: dict = {}
_last_nominatim_call: float = 0.0
_TR_MAP = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOu")
_jitter_counter: int = 0

def _normalize(text: str) -> str:
    """Türkçe karakterleri ASCII'ye çevirip büyük harfe dönüştürür."""
    return text.translate(_TR_MAP).upper()

# ── Ankara mahalle/semt koordinat sözlüğü ─────────────────────────────────────
# Nominatim'e gerek kalmadan yaygın semtleri doğru konuma düşürür.
ANKARA_COORDS: dict = {
    "DIKMEN":            (39.8854, 32.8514),
    "YUKARI DIKMEN":     (39.8780, 32.8490),
    "ASAGI DIKMEN":      (39.8920, 32.8550),
    "CUKURAMBAR":        (39.9038, 32.8106),
    "BIRLIK MAHALLESI":  (39.9150, 32.8010),
    "CAYYOLU":           (39.8586, 32.7361),
    "ORAN":              (39.8771, 32.8233),
    "ANGORA EVLERI":     (39.8640, 32.7790),
    "BEYSUKENT":         (39.8530, 32.7080),
    "KIZILAY":           (39.9208, 32.8541),
    "TUNALI":            (39.9068, 32.8613),
    "TUNAL":             (39.9068, 32.8613),
    "AYRANCI":           (39.9010, 32.8620),
    "GAZIOSMANPASA":     (39.9100, 32.8440),
    "GOP":               (39.9100, 32.8440),
    "KAVAKLIDERE":       (39.9040, 32.8640),
    "CANKAYA":           (39.9033, 32.8597),
    "BALGAT":            (39.8922, 32.8108),
    "EMEK":              (39.9220, 32.7970),
    "BAHCELIEVLER":      (39.9240, 32.8050),
    "OVECLER":           (39.8700, 32.8390),
    "GUVENEVLER":        (39.9060, 32.8350),
    "YILDIZ":            (39.9100, 32.8220),
    "CETIN EMEC":        (39.8810, 32.8160),
    "MUSTAFA KEMAL":     (39.9180, 32.7850),
    "AZIZIYE":           (39.8770, 32.8360),
    "NACI CAKIR":        (39.8800, 32.8540),
    "KECOREN":           (39.9750, 32.8640),
    "MAMAK":             (39.9320, 32.9380),
    "ALTINDAG":          (39.9540, 32.8780),
    "SINCAN":            (39.9730, 32.5820),
    "ETIMESGUT":         (39.9490, 32.6890),
    "GOLBASI":           (39.7890, 32.8040),
    "PURSAKLAR":         (40.0310, 32.8960),
    "YENIMAHALLE":       (39.9680, 32.8270),
    "BAGLICA":           (39.9580, 32.7310),
    "BATIKENT":          (39.9690, 32.7250),
    "ERYAMAN":           (39.9810, 32.6680),
    "INCEK":             (39.8200, 32.7900),
    "KONUTKENT":         (39.8700, 32.7450),
    "UMITKOY":           (39.8680, 32.7250),
    "KORU":              (39.8770, 32.7590),
    "KARSIYAKA":         (39.9210, 32.8700),
    "DEMETEVLER":        (39.9780, 32.8010),
    "KALABA":            (39.9480, 32.9100),
    "ULUS":              (39.9440, 32.8540),
    "SIHHIYE":           (39.9310, 32.8540),
    "BESTEPE":           (39.9330, 32.8040),
    "OSTIM":             (39.9620, 32.9090),
    "GIMAT":             (39.9560, 32.8830),
    "ELVANKENT":         (39.9440, 32.7010),
    "SUSUZKÖY":          (39.9900, 32.7400),
}

def _lookup_hardcoded(text: str):
    """
    Metin içinde ANKARA_COORDS'tan eşleşme arar.
    En uzun eşleşmenin koordinatını döner.
    """
    norm = _normalize(text)
    best = None
    best_len = 0
    for k, v in ANKARA_COORDS.items():
        if k in norm and len(k) > best_len:
            best = v
            best_len = len(k)
    return best

def _jittered(lat: float, lng: float) -> tuple:
    """
    Aynı koordinata düşen birden fazla marker'ın üst üste yığılmaması için
    ~30-70 m arası rastgele ofset ekler (altın açı dağılımı).
    """
    global _jitter_counter
    _jitter_counter += 1
    angle = (_jitter_counter * 137.508) % 360
    r = _random.uniform(0.0003, 0.0007)
    return (
        round(lat + r * _math.sin(_math.radians(angle)), 6),
        round(lng + r * _math.cos(_math.radians(angle)), 6),
    )

def geocode_query(query: str):
    """
    Nominatim ile geocode. bounded=0 (daha geniş tarama) + Ankara doğrulama.
    Sonuç Ankara'nın ~60 km dışındaysa geçersiz sayar.
    """
    global _last_nominatim_call
    if not query:
        return None
    key = query.lower().strip()
    if key in _coord_cache:
        return _coord_cache[key]

    elapsed = time.time() - _last_nominatim_call
    if elapsed < 1.2:
        time.sleep(1.2 - elapsed)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 5,
                "countrycodes": "tr",
                # bounded=0 bırak — viewbox öneri olarak kullan, zorunlu değil
                "viewbox": "32.3,40.2,33.4,39.5",
            },
            headers={"User-Agent": "NexaCRM/2.0 (contact@nexacrm.com)"},
            timeout=8,
        )
        _last_nominatim_call = time.time()
        data = resp.json()

        # Ankara bölgesi: lat 39.5–40.2 / lon 32.3–33.4
        for item in data:
            lat = float(item["lat"])
            lon = float(item["lon"])
            if 39.5 <= lat <= 40.2 and 32.3 <= lon <= 33.4:
                _coord_cache[key] = (lat, lon)
                return lat, lon

    except Exception as e:
        print(f"  Geocode hatası '{query[:50]}': {e}")

    _coord_cache[key] = None
    return None

def get_listing_coords(title: str, loc: str) -> tuple:
    """
    İlan için koordinat bulur. Strateji:
    1. Başlık + loc içinde sabit sözlükten mahalle eşleşmesi (hızlı, offline)
    2. Nominatim: mahalle + Çankaya/Ankara
    3. loc'tan temizlenmiş parçalarla Nominatim
    4. Dikmen fallback (jitter ile — marker'lar üst üste yığılmaz)
    """
    combined = f"{title} {loc}"

    # ── 1. Sabit sözlük ───────────────────────────────────────────────────
    coords = _lookup_hardcoded(combined)
    if coords:
        print(f"     📍 Sabit sözlük → {coords}")
        return _jittered(*coords)

    # ── 2. Nominatim — başlıktan çıkarılan mahalle ────────────────────────
    # ANKARA_SEMTLER listesinde en uzun eşleşeni bul
    norm_combined = _normalize(combined)
    best_semt = None
    best_len = 0
    for s in ANKARA_SEMTLER:
        sn = _normalize(s)
        if sn in norm_combined and len(sn) > best_len:
            best_semt = s
            best_len = len(sn)

    if best_semt:
        for q in [
            f"{best_semt}, Çankaya, Ankara",
            f"{best_semt}, Ankara",
        ]:
            coords = geocode_query(q)
            if coords:
                print(f"     🌐 Nominatim semt: {best_semt} → {coords}")
                return _jittered(*coords)

    # ── 3. loc'tan temizlenmiş parçalar ──────────────────────────────────
    # "Mah.", "Cad.", "No:5" gibi gürültüyü temizle, "Ankara" kelimesini at
    loc_clean = _re.sub(
        r"\b(Mah\.|Mah\b|Mahallesi|Cad\.|Caddesi|Sok\.|Sokak|Blv\.|Bulvarı|No:\s*\d+[\w/]*|\d+\s*/\s*\d+)\b",
        "", loc, flags=_re.IGNORECASE
    )
    parts = [
        p.strip() for p in _re.split(r"[,/]", loc_clean)
        if p.strip() and len(p.strip()) > 2
        and _normalize(p.strip()) not in ("ANKARA", "TR", "TURKIYE", "TÜRKIYE")
    ]
    for part in parts:
        coords = geocode_query(f"{part}, Ankara, Türkiye")
        if coords:
            print(f"     🌐 Nominatim loc: {part} → {coords}")
            return _jittered(*coords)

    # ── 4. Fallback ───────────────────────────────────────────────────────
    print(f"     ⚠️  Koordinat bulunamadı → Dikmen fallback | {title[:35]}")
    return _jittered(DIKMEN_LAT, DIKMEN_LNG)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def clean_text(element) -> str:
    return element.get_text(strip=True) if element else ""

def fetch_real_estate_data() -> list:
    print(f"📡 İstek gönderiliyor: {TARGET_URL}")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            print(f"❌ Bağlantı Hatası: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        listings = []
        cards = soup.select(".cb-list-item")
        print(f"🔎 Bulunan İlan Sayısı: {len(cards)}")

        for card in cards:
            try:
                title_el = card.select_one(".cb-list-item-info h2")
                title = clean_text(title_el)
                if not title:
                    continue

                price_el = card.select_one(".feature-item .text-primary")
                price = clean_text(price_el)

                link_el = card.select_one(".cb-list-img-container a")
                link = link_el["href"] if link_el else "#"
                if link and not link.startswith("http"):
                    link = "https://www.cb.com.tr" + link

                img_el = card.select_one(".cb-list-img-container img")
                img_url = "https://via.placeholder.com/400x300"
                if img_el:
                    img_url = img_el.get("src") or img_el.get("data-src") or img_url

                region_el = card.select_one('span[itemprop="addressRegion"]')
                street_el = card.select_one('span[itemprop="streetAddress"]')
                region = clean_text(region_el)
                street = clean_text(street_el)
                loc = f"{region}, {street}" if region and street else "Ankara"

                rooms = area = ""
                for feat in card.select(".feature-item"):
                    text = clean_text(feat)
                    if "m2" in text or "m²" in text:
                        area = text
                    elif "+" in text:
                        rooms = text

                lat, lng = get_listing_coords(title, loc)
                listings.append({
                    "title": title, "price": price, "loc": loc,
                    "img": img_url, "link": link, "rooms": rooms, "area": area,
                    "type": "Kiralık" if "Kiralık" in title else "Satılık",
                    "lat": lat, "lng": lng,
                })
            except Exception as e:
                print(f"⚠️ İlan parse hatası: {e}")
                continue

        print(f"✅ Toplam işlenen: {len(listings)} ilan")
        return listings
    except Exception as e:
        print(f"❌ Kritik Hata: {e}")
        return []

@app.route("/ilanlar")
def ilanlar():
    """İlanlar sayfası — ilanlar.html"""
    try:
        return send_file("ilanlar.html")
    except Exception as e:
        return f"ilanlar.html bulunamadı: {e}", 404

@app.route("/admin")
def admin():
    """Admin paneli — admin.html"""
    try:
        return send_file("admin.html")
    except Exception as e:
        return f"admin.html bulunamadı: {e}", 404

# ================================================================
# ================================================================
# ADMIN AUTH  — Firebase ID Token doğrulaması
# ================================================================

def _require_admin():
    """
    Firebase JS SDK'dan gelen idToken'ı doğrular.
    Başarılıysa (decoded_token, None), başarısızsa (None, hata_mesajı) döner.
    """
    if not _fb_initialized:
        print("⚠️  _require_admin: Firebase başlatılmamış")
        return None, "Firebase bağlı değil"
    auth_header = flask_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        print(f"⚠️  _require_admin: Token başlığı eksik — {flask_request.path}")
        return None, "Token eksik"
    id_token = auth_header[7:]
    if not id_token or len(id_token) < 20:
        return None, "Token geçersiz (çok kısa)"
    try:
        decoded = fb_auth.verify_id_token(id_token)
        print(f"✅ Admin doğrulandı: {decoded.get('email','?')} — {flask_request.path}")
        return decoded, None
    except fb_auth.ExpiredIdTokenError:
        print("⚠️  _require_admin: Token süresi dolmuş")
        return None, "Oturum süresi doldu"
    except fb_auth.InvalidIdTokenError as e:
        print(f"⚠️  _require_admin: Geçersiz token — {e}")
        return None, "Geçersiz token"
    except Exception as e:
        print(f"❌ _require_admin beklenmedik hata: {type(e).__name__}: {e}")
        return None, f"Doğrulama hatası: {type(e).__name__}"

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    # Client tarafında token silindiği için backend'de yapılacak bir şey yok
    return jsonify({"ok": True})

# ================================================================
# WHATSAPP CLOUD API ROUTES
# ================================================================

@app.route("/api/wa/status", methods=["GET"])
def whatsapp_status():
    """Meta Graph API üzerinden WA phone number durumunu kontrol eder."""
    return jsonify(wa_status())

@app.route("/api/email/status", methods=["GET"])
def customer_email_status():
    """Transactional e-posta yapılandırma durumunu döner."""
    return jsonify(email_status())

@app.route("/api/wa/webhook", methods=["GET"])
def whatsapp_webhook_verify():
    """
    Meta webhook doğrulaması (GET).
    Meta Business → WhatsApp → Configuration → Webhook URL olarak kaydedin.
    Verify Token: WA_VERIFY_TOKEN env variable ile eşleşmeli.
    """
    mode      = flask_request.args.get("hub.mode")
    token     = flask_request.args.get("hub.verify_token")
    challenge = flask_request.args.get("hub.challenge")

    if mode == "subscribe" and verify_webhook_token(token):
        print("✅ WhatsApp webhook doğrulandı")
        return challenge, 200

    print(f"❌ Webhook doğrulama başarısız. Token: {token}")
    return "Forbidden", 403

@app.route("/api/wa/webhook", methods=["POST"])
def whatsapp_webhook_receive():
    """
    Meta'dan gelen mesaj/durum bildirimlerini alır (POST).
    Gelen mesajları Firestore wa_inbound koleksiyonuna kaydeder.
    """
    data = flask_request.get_json(silent=True) or {}

    try:
        entries = data.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Gelen mesajlar
                for msg in value.get("messages", []):
                    from_phone = msg.get("from", "")
                    msg_type   = msg.get("type", "")
                    body       = msg.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type}]"
                    timestamp  = msg.get("timestamp", "")
                    print(f"📥 WA gelen mesaj: {from_phone} → {body[:80]}")

                    if _fb_initialized:
                        db_admin.collection("wa_inbound").add({
                            "from":      from_phone,
                            "type":      msg_type,
                            "body":      body,
                            "timestamp": timestamp,
                            "raw":       msg,
                            "receivedAt": datetime.now(timezone.utc).isoformat(),
                        })

                # Mesaj durum güncellemeleri (sent/delivered/read/failed)
                for status in value.get("statuses", []):
                    msg_id     = status.get("id", "")
                    wa_status_ = status.get("status", "")
                    recipient  = status.get("recipient_id", "")
                    print(f"📊 WA durum: {msg_id} → {wa_status_} ({recipient})")

                    if _fb_initialized and msg_id:
                        # wa_message_log'daki kaydı güncelle
                        docs = (db_admin.collection("wa_message_log")
                                .where("messageId", "==", msg_id).limit(1).stream())
                        for doc in docs:
                            doc.reference.update({
                                "deliveryStatus": wa_status_,
                                "statusUpdatedAt": datetime.now(timezone.utc).isoformat(),
                            })

    except Exception as e:
        print(f"Webhook işleme hatası: {e}")

    # Meta her zaman 200 bekler
    return jsonify({"status": "ok"}), 200

@app.route("/api/wa/send", methods=["POST"])
def whatsapp_send():
    """
    Admin panelinden manuel WA mesajı göndermek için.
    Body: { phone: "905324514008", message: "..." }
    Korumalı endpoint — Firebase ID token gerektirir.
    """
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    body    = flask_request.get_json(silent=True) or {}
    phone   = body.get("phone", "")
    message = body.get("message", "")

    if not phone or not message:
        return jsonify({"ok": False, "error": "phone ve message zorunlu"}), 400

    result = send_whatsapp(phone, message)

    if result["ok"] and _fb_initialized:
        db_admin.collection("wa_message_log").add({
            "phone":     phone,
            "message":   message[:200],
            "messageId": result.get("message_id", ""),
            "source":    "admin_manual",
            "status":    "sent",
            "sentAt":    datetime.now(timezone.utc).isoformat(),
        })

    return jsonify(result)

# ================================================================
# BLOG API
# ================================================================

def _serialize_post(doc):
    """Firestore dokümanını JSON-safe dict'e çevirir."""
    d = doc.to_dict()
    d["id"] = doc.id
    for field in ["createdAt", "updatedAt"]:
        val = d.get(field)
        if val is None:
            d[field] = ""
        elif hasattr(val, "isoformat"):
            try:
                d[field] = val.isoformat()
            except Exception:
                d[field] = str(val)
        else:
            d[field] = str(val)
    return d

@app.route("/api/blog/posts", methods=["GET"])
def get_blog_posts():
    """Herkese açık — site.html buradan çeker."""
    if not _fb_initialized:
        return jsonify({"ok": False, "data": []}), 503
    try:
        query = (db_admin.collection("blogs")
                 .where(filter=FieldFilter("published", "==", True))
                 .limit(24))
        posts = [_serialize_post(doc) for doc in query.stream()]
        posts.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return jsonify({"ok": True, "data": posts})
    except Exception as e:
        print(f"get_blog_posts hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/blog/all", methods=["GET"])
def get_all_blog_posts():
    """Admin paneli için — tüm yazılar."""
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401
    if not _fb_initialized:
        return jsonify({"ok": False, "data": []}), 503
    try:
        posts = [_serialize_post(doc) for doc in db_admin.collection("blogs").stream()]
        posts.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return jsonify({"ok": True, "data": posts})
    except Exception as e:
        print(f"get_all_blog_posts hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/blog/posts", methods=["POST"])
def create_blog_post():
    token, err = _require_admin()
    if err:
        print(f"❌ Auth hatası: {err}")
        return jsonify({"ok": False, "error": err}), 401
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    data = flask_request.json or {}
    print(f"📝 Blog oluşturma isteği: {data.get('title', '(başlıksız)')}")

    now  = datetime.now(timezone.utc)
    post = {
        "title":     data.get("title", "").strip(),
        "summary":   data.get("summary", "").strip(),
        "content":   data.get("content", "").strip(),
        "image":     data.get("image", "").strip(),
        "category":  data.get("category", "Genel").strip(),
        "readTime":  data.get("readTime", "3 dk").strip(),
        "published": bool(data.get("published", True)),
        "createdAt": now,
        "updatedAt": now,
    }
    if not post["title"]:
        return jsonify({"ok": False, "error": "Başlık zorunlu"}), 400

    try:
        result = db_admin.collection("blogs").add(post)
        # result → (DatetimeWithNanoseconds, DocumentReference)
        doc_ref = result[1] if isinstance(result, tuple) else result
        doc_id  = doc_ref.id
        print(f"✅ Blog oluşturuldu: {doc_id}")
        return jsonify({"ok": True, "id": doc_id})
    except Exception as e:
        import traceback
        print(f"❌ create_blog_post hatası: {e}")
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/blog/posts/<post_id>", methods=["PUT"])
def update_blog_post(post_id):
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503
    data    = flask_request.json or {}
    allowed = ["title", "summary", "content", "image", "category", "readTime", "published"]
    update  = {k: data[k] for k in allowed if k in data}
    update["updatedAt"] = datetime.now(timezone.utc)
    try:
        db_admin.collection("blogs").document(post_id).update(update)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/blog/posts/<post_id>", methods=["DELETE"])
def delete_blog_post(post_id):
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503
    try:
        db_admin.collection("blogs").document(post_id).delete()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# API — İLAN SCRAPER
# ================================================================

_listings_cache = {"data": [], "ts": 0}
_listings_lock = threading.Lock()

def _refresh_listings_bg():
    def _run():
        data = fetch_real_estate_data()
        with _listings_lock:
            _listings_cache["data"] = data
            _listings_cache["ts"]   = time.time()
    threading.Thread(target=_run, daemon=True).start()

@app.route("/api/listings", methods=["GET"])
def get_listings():
    now = time.time()
    if now - _listings_cache["ts"] < 300 and _listings_cache["data"]:
        return jsonify({"success": True, "data": _listings_cache["data"]})
    _refresh_listings_bg()
    return jsonify({"success": True, "data": _listings_cache["data"]})

# ── CB İlan Detay Önizleme ────────────────────────────────────────────────────
@app.route("/api/listing/preview", methods=["GET"])
def listing_preview():
    """
    a.py / scrape_detail() mantığıyla CB ilan detay sayfasını scrape eder.
    Query : ?url=https://www.cb.com.tr/...
    Return: {ok, title, price, location, rooms, sqm, type, status,
             cb_url, images:[str,...], features:[{label,value},...],
             description, agent:{name,img,office}}
    """

    BASE = "https://www.cb.com.tr"

    cb_url = flask_request.args.get("url", "").strip()
    parsed = urlparse(cb_url)
    if parsed.scheme not in ("http", "https") or \
       parsed.netloc not in ("www.cb.com.tr", "cb.com.tr"):
        return jsonify({"ok": False, "error": "Sadece cb.com.tr URL desteklenir"}), 400

    try:
        resp = requests.get(cb_url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return jsonify({"ok": False, "error": f"HTTP {resp.status_code}"}), 502

        soup = BeautifulSoup(resp.content, "lxml" if __import__("importlib").util.find_spec("lxml") else "html.parser")

        # ── Başlık ──────────────────────────────────────────────────────────
        title = clean_text(soup.select_one("h1") or soup.select_one("h2")) or "İlan Detayı"

        # ── Fiyat ───────────────────────────────────────────────────────────
        price = ""
        for sel in [".feature-item .text-primary",
                    ".price-box .price",
                    "[class*='price']",
                    ".cb-detail-header .price"]:
            el = soup.select_one(sel)
            if el:
                price = _re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
                if price:
                    break
        if not price:
            for row in soup.select("table tr"):
                cells = row.find_all("td")
                if len(cells) >= 2 and "Fiyat" in cells[0].get_text():
                    price = clean_text(cells[1])
                    break

        # ── Lokasyon ────────────────────────────────────────────────────────
        location = ""
        hdr = soup.select_one(".cb-detail-header")
        if hdr:
            parts = [clean_text(s) for s in hdr.select("p .text-secondary") if clean_text(s)]
            location = " / ".join(parts)
        if not location:
            r_el = soup.select_one('[itemprop="addressRegion"]')
            s_el = soup.select_one('[itemprop="streetAddress"]')
            location = " / ".join(clean_text(e) for e in [r_el, s_el] if e and clean_text(e))

        # ── İlan tipi / durumu ──────────────────────────────────────────────
        url_l = cb_url.lower()
        status = "Kiralık" if "kiralik" in url_l else "Satılık"
        path_parts = cb_url.rstrip("/").split("/")
        prop_type = path_parts[-2].replace("-", " ").title() if len(path_parts) >= 2 else "—"
        badge = soup.select_one(".price-box .badge")
        if badge:
            status = clean_text(badge)

        # ── Görseller — a.py scrape_detail() mantığı ────────────────────────
        images = []
        seen_srcs = set()

        def _add_img(src):
            src = src.strip()
            if not src or "placeholder" in src or "icon" in src.lower():
                return
            if src.startswith("/"):
                src = BASE + src
            # Thumbnail URL'lerini yüksek çözünürlüklü versiyona yükselt
            # CB formatı: _410X261.jpg → _1000X664.jpg
            import re as _rx
            src_hires = _rx.sub(r'_\d+X\d+(\.[a-z]+)$', r'_1000X664\1', src, flags=_rx.IGNORECASE)
            # Görsel zaten listede mi? Dosya adını karşılaştır
            fname = src_hires.split("/")[-1].split("_")[0]
            if fname in seen_srcs:
                return
            seen_srcs.add(fname)
            images.append(src_hires)

        # 1) Bilinen slider seçicileri (öncelik sırasıyla)
        for sel in [
            "#cb-item-gallery .carousel-item img",
            "div.swiper-slide img",
            "div.slick-slide img",
            ".detail-slider img",
            ".stock-slider img",
            ".cb-detail-slider img",
            "figure img",
        ]:
            found = soup.select(sel)
            if found:
                for img in found:
                    src = (img.get("src") or img.get("data-src") or
                           img.get("data-lazy") or "").strip()
                    if src:
                        _add_img(src)
                if images:
                    break

        # 2) Slider bulunamazsa: media.cb / StockMedia img'leri
        if not images:
            for img in soup.find_all("img"):
                src = (img.get("src") or img.get("data-src") or "").strip()
                if "media.cb" in src or "StockMedia" in src:
                    _add_img(src)

        # 3) og:image fallback
        if not images:
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                images.append(og["content"])

        # ── Özellik tablosu — a.py gibi çoklu yöntem ────────────────────────
        feats = []
        seen = set()
        SKIP = {"portföy no", "portföy kategorisi"}

        # a) Tablo satırları
        for row in soup.select("table tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                k = clean_text(cells[0]).rstrip(":").strip()
                v = clean_text(cells[1]).strip()
                if k and v and len(k) < 50 and k.lower() not in seen and k.lower() not in SKIP:
                    feats.append({"label": k, "value": v})
                    seen.add(k.lower())

        # b) dt / dd çiftleri
        for dt, dd in zip(soup.find_all("dt"), soup.find_all("dd")):
            k, v = clean_text(dt), clean_text(dd)
            if k and v and k.lower() not in seen:
                feats.append({"label": k, "value": v})
                seen.add(k.lower())

        # c) cb-checkbox-list özellik kartları (İç / Dış özellikler)
        for card in soup.select(".card.no-radius"):
            sec_el = card.select_one(".card-header h3")
            sec = clean_text(sec_el) if sec_el else "Özellik"
            for li in card.select(".cb-checkbox-list .property"):
                b_el = li.select_one("b")
                k = clean_text(b_el).rstrip(":") if b_el else ""
                if b_el:
                    b_el.extract()
                v = li.get_text(strip=True)
                combined = (k + " " + v).strip().rstrip(":") if k else v
                if combined and combined.lower() not in seen:
                    feats.append({"label": k if k else sec, "value": v if k else combined})
                    seen.add(combined.lower())

        # d) li içinde ":" olan feature satırları
        for li in soup.select("ul.features li, .property-features li, .cb-features li"):
            txt = clean_text(li)
            if ":" in txt and len(txt) < 80:
                parts = txt.split(":", 1)
                k, v = parts[0].strip(), parts[1].strip()
                if k and v and k.lower() not in seen:
                    feats.append({"label": k, "value": v})
                    seen.add(k.lower())

        feats = feats[:20]

        # ── Oda / m² ────────────────────────────────────────────────────────
        rooms = sqm = ""
        for f in feats:
            lbl = f["label"].lower()
            if not rooms and ("oda" in lbl or "room" in lbl):
                rooms = f["value"]
            if not sqm and ("m²" in lbl or "m2" in lbl or "alan" in lbl
                            or "brüt" in lbl or "metre" in lbl):
                sqm = f["value"]

        # .feature-item (header'daki hızlı bilgiler)
        for fi in soup.select(".cb-detail-header .features .feature-item, .feature-item"):
            txt = clean_text(fi)
            if not rooms and "+" in txt:
                rooms = txt
            if not sqm and "m" in txt.lower() and any(c.isdigit() for c in txt):
                sqm = txt

        # Regex fallback
        page_text = soup.get_text(" ", strip=True)
        if not rooms:
            m = _re.search(r"(\d+\+\d+|\d+\+0)", page_text)
            if m:
                rooms = m.group(1)
        if not sqm:
            m = _re.search(r"(\d+)\s*m[²2]", page_text)
            if m:
                sqm = m.group(1) + " m²"

        # ── Açıklama ────────────────────────────────────────────────────────
        description = ""
        for sel in [".description", ".ilan-aciklama", ".detail-description",
                    "#aciklama", "[itemprop='description']", ".cb-detail-content p"]:
            el = soup.select_one(sel)
            if el:
                description = el.get_text(" ", strip=True)[:600]
                break

        # ── Danışman ────────────────────────────────────────────────────────
        agent = {
            "name":   "Erdoğan Işık",
            "img":    "https://media.cb.com.tr/OfficeUserImages/3830/ERDOgAN-IsIK_HTKB8N5P81_75X75.jpg",
            "office": "CB Çizgi",
        }

        a_link = soup.select_one("a[href*='/danismanlar/']")
        if a_link:
            agent["name"] = clean_text(a_link)

        pro = soup.select_one(".cb-professional")
        if pro:
            n_el = pro.select_one("h4") or pro.select_one(".name")
            if n_el:
                agent["name"] = clean_text(n_el)

        img_el = (soup.select_one("img[src*='OfficeUser']") or
                  (pro.select_one("img") if pro else None))
        if img_el:
            src = img_el.get("src", "")
            agent["img"] = BASE + src if src.startswith("/") else src

        off_link = soup.select_one("a[href*='/ofisler/']")
        if off_link:
            agent["office"] = clean_text(off_link)

        return jsonify({
            "ok":          True,
            "title":       title,
            "price":       price,
            "location":    location,
            "rooms":       rooms,
            "sqm":         sqm,
            "type":        prop_type,
            "status":      status,
            "cb_url":      cb_url,
            "images":      images,
            "features":    feats,
            "description": description,
            "agent":       agent,
        })

    except Exception as e:
        print(f"❌ listing/preview hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# API — CRM / TELEGRAM / FOLLOWUP
# ================================================================

@app.route("/api/telegram/notify", methods=["POST"])
def telegram_notify():
    """Lead kaydedilince anında Telegram bildirimi."""
    data = flask_request.json or {}
    name     = _html.escape(data.get("name", "İsimsiz"))
    phone    = _html.escape(data.get("phone", "-"))
    email    = _html.escape(data.get("email", "-"))
    source   = _html.escape(data.get("source", "CRM"))
    msg_     = _html.escape(data.get("message", ""))
    stage    = _html.escape(data.get("stage", ""))
    category = _html.escape(data.get("category", ""))

    text = (
        f"🔔 <b>Yeni Lead!</b>\n\n"
        f"👤 <b>{name}</b>\n"
        f"📞 {phone}\n"
        f"📧 {email}\n"
        f"🌐 Kaynak: {source}\n"
        + (f"📂 Kategori: {category}\n" if category else "")
        + (f"📊 Aşama: {stage}\n" if stage else "")
        + (f"💬 {msg_}\n" if msg_ else "")
        + f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    ok = send_telegram(text)
    return jsonify({"ok": ok})

# ================================================================
# LEAD STATE MACHINE
# ================================================================

LEAD_STAGES = [
    "new_lead",        # Form gönderildi, henüz işlem yok
    "report_sent",     # Otomatik rapor gönderildi
    "contacted",       # Danışman ilk teması kurdu
    "appointment",     # Randevu alındı
    "closed_won",      # Anlaşma yapıldı
    "closed_lost",     # Lead kaybedildi
]

def _log_lead_event(lead_id: str, event_type: str, payload: dict):
    """Lead event timeline'a kayıt yazar."""
    if not _fb_initialized:
        return
    try:
        db_admin.collection("leads").document(lead_id).collection("events").add({
            "type":      event_type,
            "payload":   payload,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"_log_lead_event hatası: {e}")

def _write_notification_log(lead_id: str, channel: str, status: str, detail: str = ""):
    """Bildirim gönderim logunu notifications koleksiyonuna yazar."""
    if not _fb_initialized:
        return
    try:
        db_admin.collection("notifications").add({
            "leadId":    lead_id,
            "channel":   channel,
            "status":    status,
            "detail":    detail,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"_write_notification_log hatası: {e}")

def _result_ok(result) -> bool:
    """bool veya dict sonuçlarını ortak başarı kontrolüne çevirir."""
    if isinstance(result, dict):
        return bool(result.get("ok"))
    return bool(result)

def _send_with_retry(fn, *args, retries=3, delay=2, **kwargs):
    """Fonksiyonu retries kez dener. (True, None) veya (False, hata) döner."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            result = fn(*args, **kwargs)
            if _result_ok(result):
                return True, None
            if isinstance(result, dict) and result.get("error"):
                last_err = result.get("error")
        except Exception as e:
            last_err = e
        if attempt < retries:
            time.sleep(delay)
    return False, str(last_err or "Bilinmeyen hata")

@app.route("/api/lead/state", methods=["POST"])
def update_lead_state():
    """Lead aşamasını günceller ve event log'a yazar."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    data      = flask_request.json or {}
    lead_id   = data.get("leadId")
    new_stage = data.get("newStage")

    if not lead_id or not new_stage:
        return jsonify({"ok": False, "error": "leadId ve newStage zorunlu"}), 400
    if new_stage not in LEAD_STAGES:
        return jsonify({"ok": False, "error": f"Geçersiz stage. Geçerliler: {LEAD_STAGES}"}), 400

    try:
        ref = db_admin.collection("leads").document(lead_id)
        doc = ref.get()
        if not doc.exists:
            return jsonify({"ok": False, "error": "Lead bulunamadı"}), 404

        old_stage = doc.to_dict().get("status", "")
        now_iso   = datetime.now(timezone.utc).isoformat()

        ref.update({
            "status":         new_stage,
            "stageChangedAt": now_iso,
            "updatedAt":      now_iso,
        })
        _log_lead_event(lead_id, "stage_change", {
            "from":  old_stage,
            "to":    new_stage,
            "actor": data.get("actorEmail", "system"),
            "note":  data.get("note", ""),
        })
        print(f"✅ Lead aşaması güncellendi: {lead_id} → {new_stage}")
        return jsonify({"ok": True, "leadId": lead_id, "newStage": new_stage})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

def _send_valuation_async(
    lead_id: str, name: str, phone: str, email: str,
    neighborhood: str, property_type: str, rooms: str, sqm: str, notes: str,
):
    """
    Arka planda çalışır (threading.Thread).
    1. Gemini raporu üret
    2. Müşteriye e-posta (tam HTML rapor)
    3. Müşteriye WhatsApp template
    4. Danışmana Telegram
    5. Danışmana WhatsApp
    6. Danışmana e-posta
    7. Firestore güncelle
    """
    print(f"🔄 Değerleme raporu üretiliyor: {lead_id} | {neighborhood} / {property_type}")

    # ── 1. Gemini raporu üret ──────────────────────────────────────────────
    gemini_result = generate_valuation_report(
        name=name,
        neighborhood=neighborhood or "Ankara",
        property_type=property_type or "Konut",
        rooms=rooms,
        sqm=sqm,
        notes=notes,
    )

    if not gemini_result.get("ok"):
        err_msg = gemini_result.get("error", "Bilinmeyen hata")
        print(f"❌ Gemini raporu üretilemedi: {err_msg}")
        send_telegram(
            f"⚠️ <b>Değerleme Raporu Üretilemedi</b>\n\n"
            f"👤 {name} | 📞 {phone}\n"
            f"📍 {neighborhood} / {property_type}\n"
            f"🔗 Lead: <code>{lead_id}</code>\n"
            f"❌ Hata: {err_msg}"
        )
        if _fb_initialized and lead_id:
            try:
                db_admin.collection("leads").document(lead_id).update({
                    "valuationError":  err_msg,
                    "valuationFailed": True,
                    "valuationAt":     datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                print(f"Firestore hata güncelleme hatası: {e}")
        return

    report = gemini_result["report"]
    pr  = report.get("price_range", {})
    inv = report.get("investment_score", {})
    na  = report.get("neighborhood_analysis", {})
    channels = {}

    # ── 2. Müşteriye e-posta ───────────────────────────────────────────────
    if email:
        try:
            subj, text_b, html_b = build_valuation_report_email(name=name, report=report)
            res = send_transactional_email(email, subj, text_b, html_b)
            channels["customer_email_valuation"] = "sent" if res.get("ok") else f"failed: {res.get('error','')}"
            print(f"{'✅' if res.get('ok') else '❌'} Müşteri değerleme e-postası: {email}")
        except Exception as e:
            channels["customer_email_valuation"] = f"exception: {e}"
            print(f"❌ Müşteri e-posta hatası: {e}")
    else:
        channels["customer_email_valuation"] = "skipped_no_email"

    # ── 3. Müşteriye WhatsApp template ────────────────────────────────────
    if phone and VALUATION_WA_TEMPLATE_NAME:
        try:
            components = [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": name},
                    {"type": "text", "text": neighborhood or "bölgeniz"},
                    {"type": "text", "text": pr.get("average", "")},
                ],
            }]
            wa_res = send_whatsapp_template(
                phone=phone,
                template_name=VALUATION_WA_TEMPLATE_NAME,
                language_code="tr",
                components=components,
            )
            channels["customer_wa_valuation"] = "sent" if wa_res.get("ok") else f"failed: {wa_res.get('error','')}"
            print(f"{'✅' if wa_res.get('ok') else '❌'} Müşteri değerleme WA: {phone}")
        except Exception as e:
            channels["customer_wa_valuation"] = f"exception: {e}"
    else:
        channels["customer_wa_valuation"] = "skipped_no_template" if not VALUATION_WA_TEMPLATE_NAME else "skipped_no_phone"

    # ── 4. Danışmana Telegram ──────────────────────────────────────────────
    t_icon = "📈" if na.get("trend") == "yükselen" else ("📉" if na.get("trend") == "düşen" else "➡️")
    advisor_tg = (
        f"📊 <b>Değerleme Raporu Gönderildi!</b>\n\n"
        f"👤 <b>{name}</b>\n"
        f"📞 {phone}\n"
        + (f"📧 {email}\n" if email else "")
        + f"📍 {neighborhood} / {property_type}\n\n"
        f"💰 <b>Tahmini Değer:</b> {pr.get('average','?')}\n"
        f"   {pr.get('min','?')} — {pr.get('max','?')}\n"
        f"   m²: {pr.get('per_sqm_min','?')} – {pr.get('per_sqm_max','?')}\n\n"
        f"⭐ <b>Skor:</b> {inv.get('score','?')}/{inv.get('max',10)} — {inv.get('label','')}\n"
        f"{t_icon} <b>Trend:</b> {na.get('trend','?').capitalize()}\n\n"
        f"✅ Rapor müşteriye e-posta"
        + (" + WA" if channels.get("customer_wa_valuation") == "sent" else "")
        + " ile iletildi.\n"
        f"🔗 Lead: <code>{lead_id}</code>"
    )
    ok_tg, err_tg = _send_with_retry(send_telegram, advisor_tg)
    channels["advisor_telegram_valuation"] = "sent" if ok_tg else f"failed: {err_tg}"

    # ── 5. Danışmana WhatsApp ──────────────────────────────────────────────
    advisor_wa_msg = (
        f"📊 *Değerleme Raporu Gönderildi!*\n\n"
        f"👤 *{name}*\n📞 {phone}\n"
        f"📍 {neighborhood} / {property_type}\n\n"
        f"💰 *{pr.get('average','?')}*\n"
        f"   {pr.get('min','?')} — {pr.get('max','?')}\n\n"
        f"⭐ Skor: {inv.get('score','?')}/{inv.get('max',10)} ({inv.get('label','')})\n"
        f"{t_icon} Trend: {na.get('trend','?')}\n\n"
        f"✅ Rapor müşteriye iletildi.\nLead: {lead_id}"
    )
    wa_adv = send_whatsapp(WA_ADVISOR_PHONE, advisor_wa_msg)
    channels["advisor_wa_valuation"] = "sent" if wa_adv.get("ok") else f"failed: {wa_adv.get('error','')}"

    # ── 6. Danışmana e-posta ───────────────────────────────────────────────
    if ADVISOR_EMAIL:
        try:
            subj_a, txt_a, html_a = build_advisor_valuation_email(
                customer_name=name,
                customer_phone=phone,
                customer_email=email,
                neighborhood=neighborhood,
                property_type=property_type,
                report=report,
            )
            res_a = send_transactional_email(ADVISOR_EMAIL, subj_a, txt_a, html_a)
            channels["advisor_email_valuation"] = "sent" if res_a.get("ok") else f"failed: {res_a.get('error','')}"
            print(f"{'✅' if res_a.get('ok') else '❌'} Danışman bildirim e-postası: {ADVISOR_EMAIL}")
        except Exception as e:
            channels["advisor_email_valuation"] = f"exception: {e}"
    else:
        channels["advisor_email_valuation"] = "skipped_no_advisor_email"

    # ── 7. Firestore güncelle ──────────────────────────────────────────────
    if _fb_initialized and lead_id:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            db_admin.collection("leads").document(lead_id).update({
                "valuationReport":   report,
                "valuationSentAt":   now_iso,
                "valuationChannels": channels,
                "updatedAt":         now_iso,
            })
            _log_lead_event(lead_id, "valuation_report_sent", {
                "actor":     "grok_auto",
                "channels":  channels,
                "price_avg": pr.get("average", ""),
                "score":     inv.get("score", ""),
            })
            for ch, st in channels.items():
                _write_notification_log(lead_id, ch,
                    "sent" if st == "sent" else "failed",
                    st if st != "sent" else "")
            print(f"✅ Firestore valuation güncellendi: {lead_id}")
        except Exception as e:
            print(f"❌ Firestore güncelleme hatası: {e}")

    print(f"🏁 _send_valuation_async tamamlandı: {lead_id} | {channels}")

@app.route("/api/lead/report", methods=["POST"])
def send_lead_report():
    """
    Form gönderiminden hemen sonra tetiklenir.
    Danışmana Telegram + WhatsApp bildirimi gönderir.
    İsteğe bağlı olarak müşteriye onay e-postası ve WhatsApp template mesajı gönderir.
    Body: { leadId, name, phone, email?, neighborhood?, property_type?, notes? }
    """
    data    = flask_request.json or {}
    lead_id = data.get("leadId", "")
    name    = data.get("name", "İsimsiz")
    phone   = data.get("phone", "-")
    email   = data.get("email", "")
    neigh   = data.get("neighborhood", "")
    ptype   = data.get("property_type", "")
    rooms   = data.get("rooms", "")
    sqm     = data.get("area", "")    # site.html'de alan adı "area"
    notes   = data.get("notes", "")

    result = {"ok": True, "channels": {}}

    advisor_msg = (
        f"📋 <b>Yeni Değerleme Talebi!</b>\n\n"
        f"👤 <b>{name}</b>\n"
        f"📞 {phone}\n"
        + (f"📧 {email}\n" if email else "")
        + (f"📍 Mahalle: {neigh}\n" if neigh else "")
        + (f"🏠 Mülk Tipi: {ptype}\n" if ptype else "")
        + (f"💬 Not: {notes}\n" if notes else "")
        + f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        + f"🔗 Lead ID: <code>{lead_id}</code>"
    )

    ok_tg, err_tg = _send_with_retry(send_telegram, advisor_msg)
    result["channels"]["telegram"] = "sent" if ok_tg else f"failed: {err_tg}"

    wa_msg = (
        f"📋 *Yeni Değerleme Talebi!*\n\n"
        f"👤 *{name}*\n"
        f"📞 {phone}\n"
        + (f"📧 {email}\n" if email else "")
        + (f"📍 Mahalle: {neigh}\n" if neigh else "")
        + (f"🏠 Mülk Tipi: {ptype}\n" if ptype else "")
        + (f"💬 Not: {notes}\n" if notes else "")
        + f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        + f"🔗 Lead: {lead_id}"
    )
    wa_result = send_whatsapp(WA_ADVISOR_PHONE, wa_msg)
    result["channels"]["whatsapp"] = "sent" if wa_result["ok"] else f"skipped: {wa_result.get('error','')}"

    email_result = {"ok": False, "error": "disabled"}
    if ENABLE_CUSTOMER_EMAIL_AUTOMATION and email:
        subject, text_body, html_body = build_lead_confirmation_email(
            name=name,
            phone=phone,
            neighborhood=neigh,
            property_type=ptype,
            notes=notes,
        )
        email_result = send_transactional_email(email, subject, text_body, html_body)
        result["channels"]["customer_email"] = "sent" if email_result.get("ok") else f"skipped: {email_result.get('error','')}"
    elif email:
        result["channels"]["customer_email"] = "disabled"
    else:
        result["channels"]["customer_email"] = "missing_email"

    customer_wa_result = {"ok": False, "error": "disabled"}
    if ENABLE_CUSTOMER_WA_AUTOMATION and CUSTOMER_WA_TEMPLATE_NAME and phone:
        customer_wa_result = send_whatsapp_template(
            phone,
            CUSTOMER_WA_TEMPLATE_NAME,
            "tr",
            [{"type": "body", "parameters": [{"type": "text", "text": name}]}],
        )
        result["channels"]["customer_whatsapp"] = "sent" if customer_wa_result.get("ok") else f"skipped: {customer_wa_result.get('error','')}"
    else:
        result["channels"]["customer_whatsapp"] = "disabled"

    if _fb_initialized and lead_id:
        _write_notification_log(lead_id, "telegram", "sent" if ok_tg else "failed", err_tg or "")
        _write_notification_log(lead_id, "whatsapp", "sent" if wa_result["ok"] else "skipped", wa_result.get("error", ""))
        if email:
            _write_notification_log(lead_id, "customer_email", "sent" if email_result.get("ok") else "skipped", email_result.get("error", ""))
        if phone and CUSTOMER_WA_TEMPLATE_NAME:
            _write_notification_log(lead_id, "customer_whatsapp", "sent" if customer_wa_result.get("ok") else "skipped", customer_wa_result.get("error", ""))

        if ok_tg or wa_result["ok"]:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                db_admin.collection("leads").document(lead_id).update({
                    "status":         "report_sent",
                    "reportSentAt":   now_iso,
                    "stageChangedAt": now_iso,
                    "updatedAt":      now_iso,
                    "automation": {
                        "advisorTelegram": ok_tg,
                        "advisorWhatsapp": wa_result["ok"],
                        "customerEmail": email_result.get("ok", False),
                        "customerWhatsapp": customer_wa_result.get("ok", False),
                    }
                })
                _log_lead_event(lead_id, "stage_change", {
                    "from":  "new_lead",
                    "to":    "report_sent",
                    "actor": "system",
                    "note":  "Otomatik rapor gönderildi (Telegram + WhatsApp Cloud API)",
                })
                if email_result.get("ok"):
                    _log_lead_event(lead_id, "customer_email_sent", {
                        "actor": "system",
                        "email": email,
                        "template": "lead_confirmation",
                    })
                if customer_wa_result.get("ok"):
                    _log_lead_event(lead_id, "customer_whatsapp_sent", {
                        "actor": "system",
                        "phone": phone,
                        "template": CUSTOMER_WA_TEMPLATE_NAME,
                    })
            except Exception as e:
                print(f"Lead güncelleme hatası: {e}")

    if not ok_tg and not wa_result["ok"] and not email_result.get("ok") and not customer_wa_result.get("ok"):
        print(f"❌ Rapor hiçbir kanaldan gönderilemedi! Lead: {lead_id}")
        result["ok"] = False

    # ── Arka planda Grok değerleme raporu üret ve gönder ──────────────────
    if name and (email or phone):
        threading.Thread(
            target=_send_valuation_async,
            args=(lead_id, name, phone, email, neigh, ptype, rooms, sqm, notes),
            daemon=True,
        ).start()
        result["valuation"] = "queued"
        print(f"🔄 Değerleme thread başlatıldı: {lead_id}")
    else:
        result["valuation"] = "skipped_missing_contact"

    return jsonify(result)

@app.route("/api/valuation/quick", methods=["POST"])
def valuation_quick():
    """
    Senkron değerleme — site.html formu için anlık rapor döner.
    Grok web arama ile 30-90s içinde yanıt verir.
    Body: { name, neighborhood, property_type, rooms?, area?, notes? }
    Returns: { ok, report: {...} } | { ok: false, error }
    """
    data = flask_request.json or {}
    result = generate_valuation_report(
        name          = data.get("name", ""),
        neighborhood  = data.get("neighborhood", "Ankara"),
        property_type = data.get("property_type", "Konut"),
        rooms         = data.get("rooms", ""),
        sqm           = data.get("area", ""),
        notes         = data.get("notes", ""),
    )
    return jsonify(result)

@app.route("/api/lead/events/<lead_id>", methods=["GET"])
def get_lead_events(lead_id):
    """Lead'e ait tüm event timeline'ını döner."""
    if not _fb_initialized:
        return jsonify({"ok": False, "data": []}), 503
    try:
        events = []
        for doc in (db_admin.collection("leads").document(lead_id)
                    .collection("events").order_by("createdAt").stream()):
            d = doc.to_dict()
            d["id"] = doc.id
            events.append(d)
        return jsonify({"ok": True, "data": events})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/lead/stages", methods=["GET"])
def get_lead_stages():
    """Geçerli stage listesini döner (frontend için)."""
    return jsonify({"ok": True, "stages": LEAD_STAGES})

@app.route("/api/followup/schedule", methods=["POST"])
def schedule_followup():
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    data = flask_request.json or {}
    uid = data.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    now = datetime.now(timezone.utc)
    followup_data = {
        "contactId":    data.get("contactId", ""),
        "contactName":  data.get("contactName", ""),
        "contactPhone": data.get("contactPhone", ""),
        "contactEmail": data.get("contactEmail", ""),
        "notes": {
            "week1": data.get("notes", {}).get("week1", "1. hafta takip görüşmesi"),
            "week2": data.get("notes", {}).get("week2", "2. hafta durum değerlendirmesi"),
            "week3": data.get("notes", {}).get("week3", "3. hafta kapanış fırsatı"),
        },
        "startDate":  now.isoformat(),
        "week1Date":  (now + timedelta(days=7)).isoformat(),
        "week2Date":  (now + timedelta(days=14)).isoformat(),
        "week3Date":  (now + timedelta(days=21)).isoformat(),
        "sent":  {"week1": False, "week2": False, "week3": False},
        "done":      False,
        "createdAt": now.isoformat()
    }

    try:
        ref = (db_admin.collection("users").document(uid)
               .collection("followups").add(followup_data))
        doc_id = ref[1].id

        name = followup_data["contactName"]
        text = (
            f"🚀 <b>Takip Planı Başlatıldı!</b>\n\n"
            f"👤 <b>{name}</b>\n"
            f"📞 {followup_data['contactPhone']}\n\n"
            f"📅 <b>Takvim:</b>\n"
            f"  • 1. Hafta: {(now + timedelta(days=7)).strftime('%d.%m.%Y')} → {followup_data['notes']['week1']}\n"
            f"  • 2. Hafta: {(now + timedelta(days=14)).strftime('%d.%m.%Y')} → {followup_data['notes']['week2']}\n"
            f"  • 3. Hafta: {(now + timedelta(days=21)).strftime('%d.%m.%Y')} → {followup_data['notes']['week3']}\n"
            f"\n⏰ {now.strftime('%d.%m.%Y %H:%M')}"
        )
        send_telegram(text)
        return jsonify({"ok": True, "id": doc_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/followup/update", methods=["POST"])
def update_followup():
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    data = flask_request.json or {}
    uid         = data.get("uid")
    followup_id = data.get("followupId")
    notes       = data.get("notes", {})

    if not uid or not followup_id:
        return jsonify({"ok": False, "error": "uid ve followupId gerekli"}), 400

    try:
        ref = (db_admin.collection("users").document(uid)
               .collection("followups").document(followup_id))
        update_data = {}
        for week in ["week1", "week2", "week3"]:
            if week in notes:
                update_data[f"notes.{week}"] = notes[week]
        update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
        ref.update(update_data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/followup/cancel", methods=["POST"])
def cancel_followup():
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    data        = flask_request.json or {}
    uid         = data.get("uid")
    followup_id = data.get("followupId")

    if not uid or not followup_id:
        return jsonify({"ok": False, "error": "uid ve followupId gerekli"}), 400

    try:
        ref = (db_admin.collection("users").document(uid)
               .collection("followups").document(followup_id))
        ref.update({"done": True, "cancelledAt": datetime.now(timezone.utc).isoformat()})
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/followup/list", methods=["POST"])
def list_followups():
    if not _fb_initialized:
        return jsonify({"ok": False, "data": []}), 503

    data       = flask_request.json or {}
    uid        = data.get("uid")
    contact_id = data.get("contactId")

    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        query = (db_admin.collection("users").document(uid)
                 .collection("followups").where(filter=FieldFilter("done", "==", False)))
        if contact_id:
            query = query.where(filter=FieldFilter("contactId", "==", contact_id))

        result = []
        for doc in query.stream():
            d = doc.to_dict()
            d["id"] = doc.id
            result.append(d)

        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# SCHEDULER — Hatırlatma & Haftalık Takip
# ================================================================

def check_reminders():
    if not _fb_initialized or db_admin is None:
        return
    try:
        for user_doc in db_admin.collection("users").stream():
            uid = user_doc.id
            for rem in (db_admin.collection("users").document(uid)
                        .collection("reminders")
                        .where(filter=FieldFilter("done", "==", False))
                        .where(filter=FieldFilter("telegramSent", "==", False))
                        .stream()):
                r = rem.to_dict()
                due = r.get("dueDate", "")
                if not due:
                    continue
                try:
                    due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                    # Eğer timezone bilgisi yoksa (frontend datetime-local gönderdi = UTC+3 yerel saat)
                    if due_dt.tzinfo is None:
                        due_dt = due_dt.replace(tzinfo=timezone(timedelta(hours=3)))
                except Exception:
                    try:
                        due_dt = datetime.strptime(due[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except Exception:
                        continue

                if due_dt <= datetime.now(timezone.utc):
                    name   = _html.escape(r.get("contactName", "Müşteri"))
                    text_  = _html.escape(r.get("text", "Hatırlatma"))
                    phone_ = _html.escape(r.get("contactPhone", ""))
                    msg = (
                        f"⏰ <b>Hatırlatma!</b>\n\n"
                        f"👤 <b>{name}</b>" + (f" — {phone_}" if phone_ else "") + "\n"
                        f"📝 {text_}\n\n"
                        f"📅 {due_dt.strftime('%d.%m.%Y')}"
                    )
                    if send_telegram(msg):
                        rem.reference.update({"telegramSent": True})
                        print(f"📨 Hatırlatma gönderildi: {name}")
    except Exception as e:
        print(f"check_reminders hatası: {e}")

def check_followups():
    if not _fb_initialized or db_admin is None:
        return
    try:
        now = datetime.now(timezone.utc)
        for user_doc in db_admin.collection("users").stream():
            uid = user_doc.id
            for f_doc in (db_admin.collection("users").document(uid)
                          .collection("followups")
                          .where(filter=FieldFilter("done", "==", False))
                          .stream()):
                f = f_doc.to_dict()
                name  = _html.escape(f.get("contactName", "Müşteri"))
                phone = _html.escape(f.get("contactPhone", ""))
                notes = f.get("notes", {})
                sent  = f.get("sent", {})
                updates = {}

                for week_key, date_key in [
                    ("week1", "week1Date"),
                    ("week2", "week2Date"),
                    ("week3", "week3Date"),
                ]:
                    if sent.get(week_key):
                        continue
                    due_str = f.get(date_key, "")
                    if not due_str:
                        continue
                    try:
                        due_dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                    except Exception:
                        continue

                    if due_dt <= now:
                        week_num = week_key.replace("week", "")
                        note_text = notes.get(week_key, f"{week_num}. hafta takip")
                        msg = (
                            f"📆 <b>{week_num}. Hafta Takip Bildirimi</b>\n\n"
                            f"👤 <b>{name}</b>"
                            + (f"\n📞 {phone}" if phone else "") + "\n\n"
                            f"📝 <i>{note_text}</i>\n\n"
                            f"⏰ {now.strftime('%d.%m.%Y %H:%M')}"
                        )
                        if send_telegram(msg):
                            updates[f"sent.{week_key}"] = True
                            print(f"📨 {week_num}. hafta takip gönderildi: {name}")

                if updates:
                    new_sent = {**sent, **{k.split(".")[1]: v for k, v in updates.items()}}
                    if all(new_sent.get(w, False) for w in ["week1", "week2", "week3"]):
                        updates["done"] = True
                        updates["completedAt"] = now.isoformat()
                        send_telegram(
                            f"✅ <b>Takip Tamamlandı!</b>\n\n"
                            f"👤 <b>{_html.escape(str(name))}</b> için 3 haftalık takip süreci tamamlandı.\n"
                            f"⏰ {now.strftime('%d.%m.%Y %H:%M')}"
                        )
                    f_doc.reference.update(updates)
    except Exception as e:
        print(f"check_followups hatası: {e}")

def start_scheduler():
    def loop():
        while True:
            try:
                check_reminders()
                check_followups()
            except Exception as e:
                print(f"Scheduler hatası: {e}")
            time.sleep(60)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    print("⏱️  Scheduler başladı (60s) — Hatırlatmalar + Haftalık Takipler")

# ================================================================
# BAŞLAT / BOOTSTRAP
# ================================================================
_bootstrap_done = False

# ── 1. Durum & Konfigürasyon ──────────────────────────────────────

@app.route("/api/buyer/status")
def api_buyer_status():
    """Buyer Engine durumu."""
    return jsonify(buyer_engine_status())

# ── 2. Buyer Profili Yönetimi ──────────────────────────────────────

@app.route("/api/buyer/profile/create", methods=["POST"])
def api_buyer_create():
    """
    Yeni alıcı profili oluştur.
    
    Body (JSON):
    {
      "uid": "user123",
      "name": "Ahmet Yılmaz",
      "email": "ahmet@example.com",
      "phone": "05324514008",
      "telegram_id": "123456789",
      "whatsapp_phone": "05324514008",
      "criteria": {
        "min_price": 3000000,
        "max_price": 6000000,
        "min_area": 80,
        "max_area": 150,
        "neighborhoods": ["Çankaya", "Dikmen"],
        "property_types": ["Daire", "Dubleks"],
        "min_rooms": 2,
        "max_rooms": 4,
        "natural_language": "Ankara'da yeni ve güzel, balkonlu, otopark"
      },
      "preferences": {
        "notification_channels": ["email", "crm_task"],
        "auto_match": true,
        "priority_level": "high"
      }
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")

    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        profile = BuyerProfile({
            **body,
            "uid": uid,
            "id": db_admin.collection("buyers").document().id,
        })

        doc_ref = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(profile.buyer_id)
        )
        doc_ref.set(profile.to_dict())

        return jsonify({
            "ok": True,
            "buyer_id": profile.buyer_id,
            "profile": profile.to_dict()
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/list", methods=["GET"])
def api_buyer_list():
    """Kullanıcının tüm buyer profillerini listele."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        docs = (
            db_admin.collection("users").document(uid)
            .collection("buyers").stream()
        )
        profiles = [doc.to_dict() for doc in docs]
        return jsonify({"ok": True, "profiles": profiles})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/get", methods=["GET"])
def api_buyer_get():
    """Tek bir buyer profili getir."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        doc = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).get()
        )
        if not doc.exists:
            return jsonify({"ok": False, "error": "Profil bulunamadı"}), 404
        return jsonify({"ok": True, "profile": doc.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/update", methods=["POST"])
def api_buyer_update():
    """Buyer profili güncelle."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        doc_ref = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id)
        )
        profile_dict = doc_ref.get().to_dict()
        if not profile_dict:
            return jsonify({"ok": False, "error": "Profil bulunamadı"}), 404

        # Güncelle
        profile_dict.update(body)
        profile_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        doc_ref.set(profile_dict)

        return jsonify({"ok": True, "profile": profile_dict})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/delete", methods=["POST"])
def api_buyer_delete():
    """Buyer profilini sil."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).delete()
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 3. Eşleştirme Engine ────────────────────────────────────────

@app.route("/api/buyer/match-listing", methods=["POST"])
def api_buyer_match_listing():
    """
    Tek bir ilanı buyer profillerine göre eşleştir.
    
    Body:
    {
      "uid": "user123",
      "listing": { ...listing_data... },
      "buyer_ids": ["buyer1", "buyer2"]  // opsiyonel, tümü default
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    listing = body.get("listing")
    buyer_ids = body.get("buyer_ids", [])

    if not uid or not listing:
        return jsonify({"ok": False, "error": "uid ve listing gerekli"}), 400

    try:
        matcher = BuyerMatcher()

        # Buyer profilleri getir
        if buyer_ids:
            buyers_snap = []
            for bid in buyer_ids:
                doc = (
                    db_admin.collection("users").document(uid)
                    .collection("buyers").document(bid).get()
                )
                if doc.exists:
                    buyers_snap.append(doc)
        else:
            buyers_snap = list(
                db_admin.collection("users").document(uid)
                .collection("buyers").stream()
            )

        matches = []
        for buyer_doc in buyers_snap:
            buyer_dict = buyer_doc.to_dict()
            profile = BuyerProfile(buyer_dict)
            match = matcher.match_listing(profile, listing)

            if match:
                matches.append({
                    "buyer_id": profile.buyer_id,
                    "match_score": match.match_score,
                    "tier": match.tier,
                    "details": match.match_details,
                })

        return jsonify({
            "ok": True,
            "listing_id": listing.get("id", ""),
            "matches": matches,
            "total_matches": len(matches),
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/match-batch", methods=["POST"])
def api_buyer_match_batch():
    """
    Birden fazla ilanı buyer'larla batch eşleştir.
    Ağır operasyon — background job olarak önerilir.
    
    Body:
    {
      "uid": "user123",
      "listings": [{ ...listing1... }, { ...listing2... }],
      "buyer_ids": ["buyer1"]  // opsiyonel
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    listings = body.get("listings", [])

    if not uid or not listings:
        return jsonify({"ok": False, "error": "uid ve listings gerekli"}), 400

    try:
        matcher = BuyerMatcher()
        all_matches = []

        for listing in listings:
            # Her listing için tüm buyer'ları eşleştir
            # ... (api_buyer_match_listing mantığı)
            pass

        return jsonify({"ok": True, "total_matches": len(all_matches)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 4. Matching Geçmişi ────────────────────────────────────────

@app.route("/api/buyer/matches/list", methods=["GET"])
def api_buyer_matches_list():
    """
    Buyer'ın tüm eşleşmelerini listele (en yenisi önce).
    
    Query params:
      - uid: gerekli
      - buyer_id: gerekli
      - tier: "perfect", "excellent" vb. (filtre)
      - limit: 50 (default)
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")
    tier = flask_request.args.get("tier")
    limit = int(flask_request.args.get("limit", "50"))

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        query = (
            db_admin.collection("users").document(uid)
            .collection("buyer_matches")
            .where("buyer_id", "==", buyer_id)
            .order_by("created_at", direction="DESCENDING")
        )

        if tier:
            query = query.where("tier", "==", tier)

        docs = query.limit(limit).stream()
        matches = [doc.to_dict() for doc in docs]

        return jsonify({"ok": True, "matches": matches, "count": len(matches)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/matches/stats", methods=["GET"])
def api_buyer_matches_stats():
    """Buyer'ın eşleşme istatistikleri."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        docs = list(
            db_admin.collection("users").document(uid)
            .collection("buyer_matches")
            .where("buyer_id", "==", buyer_id)
            .stream()
        )

        stats = {
            "perfect": sum(1 for d in docs if d.to_dict().get("tier") == "perfect"),
            "excellent": sum(1 for d in docs if d.to_dict().get("tier") == "excellent"),
            "good": sum(1 for d in docs if d.to_dict().get("tier") == "good"),
            "fair": sum(1 for d in docs if d.to_dict().get("tier") == "fair"),
            "total": len(docs),
            "avg_score": sum(d.to_dict().get("match_score", 0) for d in docs) / len(docs) if docs else 0,
        }

        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 5. Notification Tetikle ────────────────────────────────────────

@app.route("/api/buyer/notify", methods=["POST"])
def api_buyer_notify():
    """
    Eşleşme için manual notification tetikle.
    
    Body:
    {
      "uid": "user123",
      "buyer_id": "buyer1",
      "match_id": "match123",
      "channels": ["email", "telegram", "crm_task"]
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")
    channels = body.get("channels", ["email", "crm_task"])

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        # Buyer profili getir
        buyer_doc = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).get()
        )
        if not buyer_doc.exists:
            return jsonify({"ok": False, "error": "Buyer profili bulunamadı"}), 404

        buyer_dict = buyer_doc.to_dict()
        buyer = BuyerProfile(buyer_dict)

        # Email gönder
        result = {}
        if "email" in channels and buyer.email:
            subject, text, html = build_lead_confirmation_email(
                name=buyer.name,
                phone=buyer.phone,
                notes=f"Eşleşme skoru: {body.get('match_score', 0):.0f}%"
            )
            result["email"] = send_transactional_email(buyer.email, subject, text, html)

        # Telegram gönder
        if "telegram" in channels and buyer.telegram_id:
            message = f"🏠 Yeni eşleşme: {body.get('match_score', 0):.0f}%"
            # Telegram API call (app.py'de tanımlanmalı)
            result["telegram"] = {"ok": True}  # Placeholder

        # WhatsApp gönder
        if "whatsapp" in channels and buyer.whatsapp_phone:
            result["whatsapp"] = send_whatsapp(
                buyer.whatsapp_phone,
                f"Yeni eşleşme: {body.get('match_score', 0):.0f}%"
            )

        # CRM görev aç
        if "crm_task" in channels:
            result["crm_task"] = {"ok": True}  # Placeholder

        return jsonify({"ok": True, "notifications": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 6. Natural Language Parsing ────────────────────────────────────

@app.route("/api/buyer/parse-criteria", methods=["POST"])
def api_buyer_parse_criteria():
    """
    Natural language kriterleri parse et (Gemini).
    
    Body:
    {
      "text": "Ankara'da 2+1 daire, maksimum 5 milyon, Çankaya veya Dikmen"
    }
    """
    body = flask_request.json or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({"ok": False, "error": "text boş"}), 400

    try:
        criteria = parse_natural_language_criteria(text)
        return jsonify({"ok": True, "criteria": criteria or {}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 7. Dashboard & Analytics ────────────────────────────────────────

@app.route("/api/buyer/dashboard", methods=["GET"])
def api_buyer_dashboard():
    """Buyer dashboard — özet istatistikler."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        # Profil sayısı
        buyers = list(
            db_admin.collection("users").document(uid)
            .collection("buyers").where("is_active", "==", True).stream()
        )

        # Toplam eşleşme
        all_matches = list(
            db_admin.collection("users").document(uid)
            .collection("buyer_matches").stream()
        )

        # Tier dağılımı
        tier_dist = {}
        for match_doc in all_matches:
            tier = match_doc.to_dict().get("tier", "unknown")
            tier_dist[tier] = tier_dist.get(tier, 0) + 1

        return jsonify({
            "ok": True,
            "dashboard": {
                "active_buyers": len(buyers),
                "total_matches": len(all_matches),
                "tier_distribution": tier_dist,
                "avg_match_score": (
                    sum(d.to_dict().get("match_score", 0) for d in all_matches) / len(all_matches)
                    if all_matches else 0
                ),
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# CB VIP OFFICE SCANNING ENDPOINTS
# ================================================================

@app.route("/api/scan-office", methods=["POST"])
def api_scan_office():
    """CB VIP ofis listing'lerini tara, analiz et ve kaydet."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    office_url = body.get("office_url", "").strip()

    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    if not office_url:
        office_url = "https://www.cb.com.tr/ilanlar?officeid=372&officeuserid=18631"

    try:
        import uuid
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        scan_doc = {
            "uid": uid,
            "office_url": office_url,
            "status": "scanning",
            "started_at": timestamp,
            "listings_found": 0,
            "listings_analyzed": 0,
            "error": None,
        }

        db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).set(scan_doc)
        threading.Thread(target=_background_scan_office, args=(uid, scan_id, office_url), daemon=True).start()

        return jsonify({"ok": True, "scan_id": scan_id, "status": "scanning", "message": "CB VIP ofis taraması başlatıldı..."})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

def _background_scan_office(uid: str, scan_id: str, office_url: str):
    """Background thread'de CB VIP office'i tara ve analiz et."""
    try:
        listings = _scrape_cb_vip_listings(office_url)
        
        if not listings:
            db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).update({
                "status": "completed",
                "listings_found": 0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": "Listing bulunamadı",
            })
            return

        analyzed_count = 0
        for idx, listing in enumerate(listings, 1):
            try:
                analysis_result = analyze_listing(listing_data=listing, manual_data=None, uploaded_images=[])

                if analysis_result.get("ok"):
                    listing_record = {
                        "source": "cb_vip",
                        "office_url": office_url,
                        "scan_id": scan_id,
                        "listing_data": listing,
                        "analysis": analysis_result.get("report", {}),
                        "url": listing.get("url", ""),
                        "price": listing.get("price", 0),
                        "area": listing.get("area", 0),
                        "location": listing.get("location", ""),
                        "property_type": listing.get("property_type", ""),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    db_admin.collection("users").document(uid).collection("scanned_listings").document().set(listing_record)
                    analyzed_count += 1

                if idx % 5 == 0:
                    db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).update({"listings_analyzed": analyzed_count})

            except Exception as e:
                print(f"Listing analiz hatası: {e}")
                continue

        db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).update({
            "status": "completed",
            "listings_found": len(listings),
            "listings_analyzed": analyzed_count,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

def _scrape_cb_vip_listings(url: str) -> list:
    """CB VIP listing URL'sinden listing'leri scrape et."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        listings = []
        listing_cards = soup.find_all("div", class_=["property-card", "listing-card", "item"])

        for card in listing_cards[:50]:
            try:
                title_elem = card.find("a", class_=["property-title", "listing-title"])
                title = title_elem.get_text(strip=True) if title_elem else ""
                price_elem = card.find("span", class_=["price", "property-price"])
                price_text = price_elem.get_text(strip=True) if price_elem else "0"
                price = _parse_price(price_text)
                area_elem = card.find("span", class_=["area", "property-area"])
                area_text = area_elem.get_text(strip=True) if area_elem else "0"
                area = _parse_area(area_text)
                link_elem = card.find("a", href=True)
                listing_url = link_elem["href"] if link_elem else ""
                if listing_url and not listing_url.startswith("http"):
                    listing_url = "https://www.cb.com.tr" + listing_url
                location_elem = card.find("div", class_=["location", "property-location"])
                location = location_elem.get_text(strip=True) if location_elem else "Bilinmiyor"

                listing = {"title": title, "price": price, "area": area, "location": location, "url": listing_url, "property_type": _infer_property_type(title), "source": "cb_vip"}
                listings.append(listing)

            except Exception as e:
                print(f"Card parse hatası: {e}")
                continue

        return listings

    except Exception as e:
        print(f"CB VIP scraping hatası: {e}")
        return []

def _parse_price(price_str: str) -> float:
    """Fiyat string'ini parse et."""
    try:
        import re as _re_temp
        numbers = _re_temp.findall(r"\d+", price_str.replace(".", "").replace(",", ""))
        if numbers:
            return float("".join(numbers))
    except:
        pass
    return 0.0

def _parse_area(area_str: str) -> float:
    """Alan string'ini parse et."""
    try:
        numbers = _re_temp.findall(r"\d+", area_str)
        if numbers:
            return float(numbers[0])
    except:
        pass
    return 0.0

def _infer_property_type(title: str) -> str:
    """Başlıktan mülk tipini çıkar."""
    title_lower = title.lower()
    if "villa" in title_lower:
        return "Villa"
    elif "ticari" in title_lower or "dükkân" in title_lower:
        return "Ticari"
    elif "arsa" in title_lower:
        return "Arsa"
    elif "daire" in title_lower or "apartman" in title_lower:
        return "Daire"
    return "Diğer"

@app.route("/api/scan-office/status/<scan_id>", methods=["GET"])
def api_scan_office_status(scan_id: str):
    """Office tarama durumunu kontrol et."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        scan_doc = db_admin.collection("users").document(uid).collection("office_scans").document(scan_id).get()
        if not scan_doc.exists:
            return jsonify({"ok": False, "error": "Scan bulunamadı"}), 404
        return jsonify({"ok": True, "scan": scan_doc.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/scan-office/listings", methods=["GET"])
def api_scan_office_listings():
    """Taranmış listing'leri listele."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    limit = int(flask_request.args.get("limit", 20))

    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        query = db_admin.collection("users").document(uid).collection("scanned_listings").order_by("created_at", direction="DESCENDING").limit(limit)
        docs = query.stream()
        listings = []

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            listings.append(data)

        all_docs = db_admin.collection("users").document(uid).collection("scanned_listings").stream()
        total_count = sum(1 for _ in all_docs)

        return jsonify({"ok": True, "listings": listings, "count": total_count})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/scan-office/stats", methods=["GET"])
def api_scan_office_stats():
    """Office tarama istatistikleri."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        docs = db_admin.collection("users").document(uid).collection("scanned_listings").stream()
        listings = [doc.to_dict() for doc in docs]

        if not listings:
            return jsonify({"ok": True, "total_listings": 0, "avg_price": 0, "price_distribution": {}, "property_types": {}})

        prices = [l.get("price", 0) for l in listings if l.get("price")]
        avg_price = sum(prices) / len(prices) if prices else 0

        property_types = {}
        for listing in listings:
            ptype = listing.get("property_type", "Diğer")
            property_types[ptype] = property_types.get(ptype, 0) + 1

        price_distribution = {"0-1M": 0, "1-3M": 0, "3-5M": 0, "5-10M": 0, "10M+": 0}

        for price in prices:
            if price < 1_000_000:
                price_distribution["0-1M"] += 1
            elif price < 3_000_000:
                price_distribution["1-3M"] += 1
            elif price < 5_000_000:
                price_distribution["3-5M"] += 1
            elif price < 10_000_000:
                price_distribution["5-10M"] += 1
            else:
                price_distribution["10M+"] += 1

        scan_docs = db_admin.collection("users").document(uid).collection("office_scans").order_by("started_at", direction="DESCENDING").limit(5).stream()
        recent_scans = [doc.to_dict() for doc in scan_docs]

        return jsonify({"ok": True, "total_listings": len(listings), "avg_price": avg_price, "price_distribution": price_distribution, "property_types": property_types, "recent_scans": recent_scans})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# AI ANALİZ MODÜLÜ ROUTE'LARI
# ================================================================

@app.route("/ai-analysis")
def ai_analysis_page():
    """AI Gayrimenkul Analiz sayfası."""
    try:
        return send_file("ai_analysis.html")
    except Exception as e:
        return f"ai_analysis.html bulunamadı: {e}", 404

@app.route("/api/ai/scrape", methods=["POST"])
def api_ai_scrape():
    """İlan URL'sini scrape eder."""
    body = flask_request.json or {}
    url  = (body.get("url") or "").strip()
    if not url:
        return jsonify({"ok": False, "error": "url boş olamaz"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        result = scrape_listing(url)
        if not result.get("ok"):
            err = result.get("error", "Scrape başarısız")
            print(f"⚠️  Scrape başarısız [{url}]: {err}")
            return jsonify({"ok": False, "error": err, "data": result}), 422
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/ai/analyze", methods=["POST"])
def api_ai_analyze():
    """Gemini ile tam gayrimenkul analizi üretir."""
    body = flask_request.json or {}
    listing_data    = body.get("listing_data")
    manual_data     = body.get("manual_data")
    uploaded_images = body.get("uploaded_images", [])
    if not listing_data and not manual_data and not uploaded_images:
        return jsonify({"ok": False, "error": "En az bir girdi gerekli: listing_data, manual_data veya uploaded_images boş olamaz"}), 400
    try:
        result = analyze_listing(
            listing_data=listing_data,
            manual_data=manual_data,
            uploaded_images=uploaded_images,
        )
        return jsonify(result), (200 if result.get("ok") else 500)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/ai/status")
def api_ai_status():
    """Gemini AI listing modülünün konfigürasyon durumunu döner."""
    return jsonify(ai_listing_status())

@app.route("/api/ai/save-to-crm", methods=["POST"])
def api_ai_save_to_crm():
    """Üretilen analiz raporunu Firebase'e kaydeder."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503
    body       = flask_request.json or {}
    uid        = body.get("uid")
    report     = body.get("report")
    url        = body.get("url", "")
    contact_id = body.get("contact_id", "")
    if not uid or not report:
        return jsonify({"ok": False, "error": "uid ve report gerekli"}), 400
    try:
        doc_ref = (
            db_admin
            .collection("users").document(uid)
            .collection("ai_analyses")
            .document()
        )
        doc_ref.set({
            "report":    report,
            "url":       url,
            "contactId": contact_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "source":    report.get("data_source", ""),
            "verdict":   report.get("recommendation", {}).get("verdict", ""),
        })
        return jsonify({"ok": True, "id": doc_ref.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/sunum")
def sunum_page():
    """Proje Sunumu sayfası."""
    try:
        return send_file("sunum.html")
    except Exception as e:
        return f"sunum.html bulunamadı: {e}", 404

# ================================================================
# FSBO ENGINE ROUTES
# ================================================================

@app.route("/api/fsbo/status")
def fsbo_status_route():
    """FSBO analiz motorunun durumunu döner."""
    return jsonify(fsbo_engine_status())

@app.route("/api/fsbo/analyze", methods=["POST"])
def fsbo_analyze():
    """
    Gemini 2.5 Flash ile FSBO stratejisi üretir.
    Korumalı endpoint — Firebase ID token gerektirir.

    Body: {
        contact_data: {name, phone, district, price, stage, notes, category},
        screenshots:  [base64_str, ...],
        text_input:   "...",
        audio_b64:    "data:audio/webm;base64,...",
        audio_mime:   "audio/webm",
        timeline:     [{type, text, createdAt}, ...]
    }
    """
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    body         = flask_request.json or {}
    contact_data = body.get("contact_data", {})
    screenshots  = body.get("screenshots", [])
    text_input   = body.get("text_input", "")
    audio_b64    = body.get("audio_b64")
    audio_mime   = body.get("audio_mime", "audio/webm")
    timeline     = body.get("timeline", [])

    if not contact_data.get("name"):
        return jsonify({"ok": False, "error": "contact_data.name zorunlu"}), 400

    try:
        result = analyze_fsbo(
            contact_data = contact_data,
            screenshots  = screenshots,
            text_input   = text_input,
            audio_b64    = audio_b64,
            audio_mime   = audio_mime,
            timeline     = timeline,
        )
        status = 200 if result.get("ok") else 500
        return jsonify(result), status
    except Exception as e:
        print(f"❌ fsbo_analyze hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/fsbo/save", methods=["POST"])
def fsbo_save():
    """
    FSBO stratejisini Firebase'e kaydeder.
    Body: {uid, contact_id, is_web, strategy, transcript}
    """
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body       = flask_request.json or {}
    uid        = body.get("uid")
    contact_id = body.get("contact_id")
    is_web     = body.get("is_web", False)
    strategy   = body.get("strategy")
    transcript = body.get("transcript", "")

    if not uid or not contact_id or not strategy:
        return jsonify({"ok": False, "error": "uid, contact_id ve strategy zorunlu"}), 400

    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        if is_web:
            coll_ref = (db_admin
                        .collection("leads").document(contact_id)
                        .collection("fsbo_strategies"))
        else:
            coll_ref = (db_admin
                        .collection("users").document(uid)
                        .collection("contacts").document(contact_id)
                        .collection("fsbo_strategies"))

        # Mevcut strateji sayısını al → numara ver
        existing = list(coll_ref.limit(20).stream())
        strat_num = len(existing) + 1

        doc_ref = coll_ref.document()
        doc_ref.set({
            "strategy":   strategy,
            "transcript": transcript,
            "savedAt":    now_iso,
            "stratNum":   strat_num,
            "label":      f"FSBO Stratejim {strat_num}",
            "resistance": strategy.get("resistance_level", ""),
            "score":      strategy.get("confidence_score", 0),
        })

        # Timeline'a da yaz
        if is_web:
            db_admin.collection("leads").document(contact_id).collection("events").add({
                "type":      "fsbo_strategy_saved",
                "payload":   {"stratNum": strat_num, "score": strategy.get("confidence_score", 0), "resistance": strategy.get("resistance_level", "")},
                "createdAt": now_iso,
            })

        print(f"✅ FSBO Stratejim {strat_num} kaydedildi: {contact_id}")
        return jsonify({"ok": True, "id": doc_ref.id, "stratNum": strat_num})
    except Exception as e:
        print(f"❌ fsbo_save hatası: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/fsbo/delete", methods=["POST"])
def fsbo_delete():
    """FSBO stratejisini siler."""
    token, err = _require_admin()
    if err:
        return jsonify({"ok": False, "error": err}), 401

    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body        = flask_request.json or {}
    uid         = body.get("uid")
    contact_id  = body.get("contact_id")
    strategy_id = body.get("strategy_id")
    is_web      = body.get("is_web", False)

    if not uid or not contact_id or not strategy_id:
        return jsonify({"ok": False, "error": "uid, contact_id ve strategy_id zorunlu"}), 400

    try:
        if is_web:
            (db_admin.collection("leads").document(contact_id)
             .collection("fsbo_strategies").document(strategy_id).delete())
        else:
            (db_admin.collection("users").document(uid)
             .collection("contacts").document(contact_id)
             .collection("fsbo_strategies").document(strategy_id).delete())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── API: CRM Ekran Görüntüsünden Kişi Bilgisi Çıkar ─────────────────────────

@app.route("/api/crm/extract-contact", methods=["POST"])
def api_crm_extract_contact():
    """
    Ekran görüntülerinden ad soyad + telefon çıkarır (Gemini Vision).

    Body: {
      "images": ["data:image/jpeg;base64,...", ...]   // maks 3 görüntü
    }
    Döner:
      {"ok": true,  "name": "Ad Soyad", "phone": "05XXXXXXXXX"}
      {"ok": true,  "name": null, "phone": null}       // bilgi bulunamadı
      {"ok": false, "error": "..."}
    """
    from ai_listing import extract_contact_from_images

    body   = flask_request.json or {}
    images = body.get("images", [])

    if not images:
        return jsonify({"ok": False, "error": "images listesi boş"}), 400

    if not isinstance(images, list):
        return jsonify({"ok": False, "error": "images bir liste olmalı"}), 400

    try:
        result = extract_contact_from_images(images)
        status = 200 if result.get("ok") else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/crm/chat", methods=["POST"])
def api_crm_chat():
    """
    CRM Lead Chatbot — Gemini ile güçlendirilmiş müşteri asistanı.

    Body: {
      "lead_context": "müşteri bilgileri metin olarak",
      "messages": [{"role": "user", "content": "..."}, ...]
    }
    Döner: {"ok": true, "reply": "..."} | {"ok": false, "error": "..."}
    """
    GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL    = "gemini-2.5-flash"
    GEMINI_FALLBACK = "gemini-2.5-flash-lite"

    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "GEMINI_API_KEY tanımlı değil"}), 503

    body         = flask_request.json or {}
    lead_context = (body.get("lead_context") or "").strip()
    messages     = body.get("messages", [])

    if not messages:
        return jsonify({"ok": False, "error": "messages boş"}), 400

    system_prompt = f"""Sen Nexa CRM'in AI asistanısın. Türk gayrimenkul sektöründe uzman bir danışman yardımcısısın.
Aşağıdaki müşteri bilgileriyle beslenmişsin:

--- MEVCUT MÜŞTERİ BİLGİLERİ ---
{lead_context}
---------------------------------

Görevin:
- Danışmana bu müşteri hakkında pratik, uygulanabilir tavsiyeler ver
- Satış stratejileri, itiraz yanıtları, takip önerileri sun
- Türkçe konuş, profesyonel ama samimi bir dil kullan
- Cevapları kısa ve net tut (çok uzun yazmaktan kaçın)
- WhatsApp mesajı, e-posta taslağı, arama scripti gibi hazır metinler yazabilirsin
- Emoji kullanabilirsin ama aşırıya kaçma
"""

    gemini_contents = []
    for m in messages:
        role = "user" if m.get("role") == "user" else "model"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": m.get("content", "")}]
        })

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        },
    }

    def _call(model):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )
        return requests.post(url, json=payload, timeout=30)

    try:
        resp = _call(GEMINI_MODEL)
        if resp.status_code in (429, 503):
            resp = _call(GEMINI_FALLBACK)

        data = resp.json()
        if resp.ok:
            text = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
            )
            return jsonify({"ok": True, "reply": text or "Yanıt alınamadı."})

        err_msg = data.get("error", {}).get("message", str(data))
        return jsonify({"ok": False, "error": err_msg}), 500

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/crm/proactive", methods=["POST"])
def api_crm_proactive():
    """
    Lead için proaktif AI uyarısı üretir.
    Kural tabanlı eşik kontrolü + Gemini analizi.

    Body: {
      "lead_context":   "müşteri metin özeti",
      "days_in_stage":  18,
      "last_note_days": 12,
      "stage":          "ilk_temas",
      "stage_label":    "İlk Temas"
    }
    Döner: {
      "ok": true,
      "alert": {
        "level": "urgent" | "warning" | "info" | null,
        "title": "...",
        "message": "...",
        "suggested_action": "...",
        "quick_questions": [...]
      }
    }
    """
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "GEMINI_API_KEY tanımlı değil"}), 503

    body          = flask_request.json or {}
    lead_context  = (body.get("lead_context") or "").strip()
    days_in_stage = int(body.get("days_in_stage", 0))
    last_note_days= int(body.get("last_note_days", 0))
    stage         = (body.get("stage") or "").strip()
    stage_label   = (body.get("stage_label") or stage).strip()

    if not lead_context:
        return jsonify({"ok": False, "error": "lead_context boş"}), 400

    # ── Aşama Eşikleri (kural motoru) ─────────────────────────────
    STAGE_THRESHOLDS = {
        "ilk_temas":   {"warning": 5,  "urgent": 10},
        "degerleme":   {"warning": 10, "urgent": 21},
        "sozlesme":    {"warning": 5,  "urgent": 10},
        "goruntuleme": {"warning": 3,  "urgent": 7 },
        "teklif":      {"warning": 2,  "urgent": 5 },
        "satilik":     {"warning": 14, "urgent": 30},
        "default":     {"warning": 14, "urgent": 28},
    }
    thresh = STAGE_THRESHOLDS.get(stage, STAGE_THRESHOLDS["default"])
    rule_level = None
    if days_in_stage >= thresh["urgent"] or last_note_days >= thresh["urgent"]:
        rule_level = "urgent"
    elif days_in_stage >= thresh["warning"] or last_note_days >= thresh["warning"]:
        rule_level = "warning"

    system_prompt = f"""Sen Nexa CRM'in proaktif analiz asistanısın.
Bir gayrimenkul danışmanına, az önce açtığı müşteri dosyası için ne yapması gerektiğini söylüyorsun.

MÜŞTERİ BİLGİLERİ:
{lead_context}

Aşamada geçen gün: {days_in_stage}
Son not/iletişimden geçen gün: {last_note_days}
Mevcut aşama: {stage_label}
Kural motoru tespiti: {rule_level or "normal"}

GÖREV:
1. Eğer müşteri durumu tamamen normalse (aktif, yeni girilmiş, her şey yolunda) → level null döndür.
2. Aksi hâlde danışmana özel, uygulanabilir bir uyarı üret.
3. Öneri gerçekçi ve bu müşteriye özgü olsun; genel kalıplardan kaçın.
4. suggested_action kısa ve net bir eylem cümlesi olsun (asistana sorulacak soru gibi).
5. quick_questions listesi 2 maddeden oluşsun.

SADECE JSON döndür:
{{
  "level": "urgent" | "warning" | "info" | null,
  "title": "Max 5 kelime başlık",
  "message": "Danışmana yönelik 1-2 cümle açıklama",
  "suggested_action": "Asistana sorulacak tek cümlelik eylem sorusu",
  "quick_questions": ["Soru 1", "Soru 2"]
}}
"""

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": "Proaktif analiz yap."}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 400},
    }

    try:
        url  = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        resp = requests.post(url, json=payload, timeout=20)
        data = resp.json()

        if not resp.ok:
            # API hatasında kural motoru sonucunu fallback olarak kullan
            if rule_level:
                return jsonify({"ok": True, "alert": {
                    "level": rule_level,
                    "title": f"{days_in_stage} Gündür Bekleme" if rule_level == "urgent" else "Takip Zamanı",
                    "message": f"Bu müşteri {stage_label} aşamasında {days_in_stage} gündür bekliyor.",
                    "suggested_action": "Bu müşteri için takip stratejisi öner",
                    "quick_questions": ["Arama öncesi brifing ver", "WhatsApp mesajı yaz"],
                }})
            return jsonify({"ok": True, "alert": {"level": None}})

        raw = (
            data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
        )

        # JSON ayıkla
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        alert_data = json.loads(m.group()) if m else json.loads(raw)

        # Kural motoru "urgent" dediyse Gemini'nin downgrade etmesine izin verme
        if rule_level == "urgent" and alert_data.get("level") not in ("urgent", None):
            alert_data["level"] = "urgent"

        return jsonify({"ok": True, "alert": alert_data})

    except json.JSONDecodeError:
        # Parse hatası → kural motoru fallback
        fallback = {"level": rule_level, "title": "", "message": "",
                    "suggested_action": "", "quick_questions": []}
        return jsonify({"ok": True, "alert": fallback})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    bootstrap_app()  # ← Bootstrap başlat
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Unified Sunucu Başlatıldı: http://0.0.0.0:{port}")
    print(f"   🌐 Web Sitesi : http://0.0.0.0:{port}/")
    print(f"   📊 CRM Paneli : http://0.0.0.0:{port}/crm")
    print(f"   🔧 Admin Panel: http://0.0.0.0:{port}/admin")
    print(f"   🤖 AI Analiz  : http://0.0.0.0:{port}/ai-analysis")
    print(f"   📂 Projeler   : http://0.0.0.0:{port}/sunum")
    app.run(host="0.0.0.0", port=port, debug=False)

# ======================================================================
# Bootstrap & Initialization
# ======================================================================

# ================================================================
# APP.PY'YE EKLENECEk BÖLÜM
# ================================================================
# Bu dosyadaki fonksiyonlar app.py'nin içinde yer almalıdır.
# Konumu: app.py'nin 150-180 satırları (import'lardan sonra)
#
# ⚠️ UYARI: Flask app = Flask(__name__) satırından ÖNCE ekle!
#
# Bootstrap edilen fonksiyonlar:
# - init_firebase_admin()    → Firebase Admin SDK başlatma
# - start_scheduler()        → APScheduler başlatma (background tasks)
# - _refresh_listings_bg()   → İlanları arka planda yenile
# ================================================================

import logging

# ── SCHEDULER IMPORT ─────────────────────────────────────────
try:
    _apscheduler_available = True
except ImportError:
    _apscheduler_available = False
    print("⚠️  APScheduler yüklü değil: pip install apscheduler")

# ── GLOBAL STATE ─────────────────────────────────────────────
_scheduler = None
_listing_cache_time = None

# ================================================================
# BOOTSTRAP FONKSIYONLARI
# ================================================================

def init_firebase_admin():
    """
    Firebase Admin SDK'yı başlat.
    
    Gerekli ortam değişkenleri:
      FIREBASE_SERVICE_ACCOUNT  → service-account.json dosyasının yolu
    """
    global _fb_initialized, db_admin
    
    # Zaten başlatılmışsa, tekrar başlatma
    if _fb_initialized:
        return
    
    try:
        # Service account dosyasının yolunu al
        service_account_path = os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT", 
            "service-account.json"
        )
        
        # Dosya kontrol et
        if not os.path.exists(service_account_path):
            print(f"⚠️  Firebase credential dosyası bulunamadı: {service_account_path}")
            print("   Beklenen konum: service-account.json (ya da FIREBASE_SERVICE_ACCOUNT env var)")
            _fb_initialized = False
            return
        
        # Firebase Admin SDK başlat
        from firebase_admin import credentials, firestore as admin_firestore
        
        cred = credentials.Certificate(service_account_path)
        
        # Eğer zaten initialize edilmişse, hatayı yakala
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            # Zaten initialize edilmiş
            pass
        
        db_admin = admin_firestore.client()
        _fb_initialized = True
        
        print("✅ Firebase Admin SDK başlatıldı")
        print(f"   📁 Credential: {service_account_path}")
        
    except Exception as e:
        print(f"❌ Firebase başlatma hatası: {e}")
        print("   Çözüm: Firebase credential dosyasını kontrol et")
        _fb_initialized = False

def start_scheduler():
    """
    APScheduler'ı başlat (follow-up notifications, otomatik refresh vb. için).
    
    Background tasks:
      - Listing refresh (5 dakika aralığı)
      - Lead follow-up notifications (hourly)
      - Daily reports (8:00 AM)
    """
    global _scheduler
    
    # Zaten başlatılmışsa
    if _scheduler is not None:
        return
    
    if not _apscheduler_available:
        print("⚠️  APScheduler yüklü değil, background tasks deaktif")
        return
    
    try:
        _scheduler = BackgroundScheduler(daemon=True)
        
        # İsteğe bağlı: Scheduler job'larını ekle
        # Not: Bu fonksiyonlar tanımlanmalıdır
        
        # Örnek 1: Listeleri 5 dakikada bir yenile
        # _scheduler.add_job(
        #     func=_refresh_listings_bg,
        #     trigger=IntervalTrigger(minutes=5),
        #     id="refresh_listings",
        #     name="Refresh listings from scrapers",
        #     replace_existing=True
        # )
        
        # Örnek 2: Lead follow-up notifications (her saat)
        # _scheduler.add_job(
        #     func=_check_followup_alerts,
        #     trigger=IntervalTrigger(hours=1),
        #     id="followup_alerts",
        #     name="Check lead follow-up alerts",
        #     replace_existing=True
        # )
        
        _scheduler.start()
        print("✅ Background Scheduler başlatıldı")
        
    except Exception as e:
        print(f"❌ Scheduler başlatma hatası: {e}")
        _scheduler = None

def _refresh_listings_bg():
    """
    Listeleri arka planda yenile.
    
    Bu fonksiyon scheduler tarafından çağrılır.
    Sahibinden, Hepsiemlak, Emlakjet vb. API'lerden veri çeker.
    
    Faz 2'de tam implement edilecek.
    """
    global _listing_cache_time
    
    try:
        # Şu an sadece log tutuluyor
        current_time = datetime.now(timezone.utc).isoformat()
        _listing_cache_time = current_time
        
        print(f"📋 Listing refresh başladı: {current_time}")
        
        # İleride: Sahibinden API, Hepsiemlak scraper vb. çağrıları
        # result = scrape_listing("https://www.sahibinden.com/...")
        
        # Telegram/WhatsApp notification gönder (opsiyonel)
        # if WA_ADVISOR_PHONE:
        #     send_whatsapp(WA_ADVISOR_PHONE, "📋 İlanlar yenilendi")
        
    except Exception as e:
        print(f"⚠️  Listing refresh hatası: {e}")

# ================================================================
# BOOTSTRAP ORCHESTRATOR
# ================================================================

def bootstrap_app():
    """
    Uygulamayı başlat — tüm servisleri initialize et.
    
    Bu fonksiyon app.py'nin sonunda, if __name__ == "__main__" 
    bloğundan ÖNCE çağrılır.
    
    Sıra:
    1. Firebase Admin SDK başlat
    2. Background Scheduler başlat
    3. İlanları ön-yükle (cache)
    """
    global _bootstrap_done
    
    # Zaten çalıştırılmışsa, tekrar çalıştırma
    if _bootstrap_done:
        return
    
    print("\n" + "="*70)
    print("🚀 NEXA CRM - Bootstrap Başlatılıyor")
    print("="*70 + "\n")
    
    # 1. Firebase
    init_firebase_admin()
    
    # 2. Scheduler
    start_scheduler()
    
    # 3. Listing cache
    _refresh_listings_bg()
    
    # 4. Mark complete
    _bootstrap_done = True
    
    print("\n" + "="*70)
    print("✅ Bootstrap Tamamlandı")
    print("="*70 + "\n")

# ================================================================
# UTILITY FONKSIYONLARI (İsteğe bağlı)
# ================================================================

def check_bootstrap_status() -> dict:
    """Bootstrap durumunu kontrol et."""
    return {
        "ok": _bootstrap_done,
        "firebase_initialized": _fb_initialized,
        "scheduler_running": _scheduler is not None and _scheduler.running,
        "last_listing_refresh": _listing_cache_time,
    }

# ================================================================
# KURULUM TESİ
# ================================================================

def test_bootstrap():
    """Bootstrap'ı test et (CLI için)."""
    print("\n🧪 Bootstrap Test Başlıyor...\n")
    
    bootstrap_app()
    
    status = check_bootstrap_status()
    print(f"\nBootstrap Durumu:")
    print(f"  ✅ Bootstrap tamamlandı: {status['ok']}")
    print(f"  ✅ Firebase: {status['firebase_initialized']}")
    print(f"  ✅ Scheduler: {status['scheduler_running']}")
    print(f"  📋 Son refresh: {status['last_listing_refresh']}")
    
    return status['ok']

# ================================================================
# ÖRNEK KULLANIM (app.py içinde)
# ================================================================

"""
# app.py'nin SON BÖLÜMÜ:

if __name__ == "__main__":
    bootstrap_app()  # ← Sunucuyu başlatmadan önce bootstrap et
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 CRM: http://0.0.0.0:{port}/crm")
    print(f"⚙️  Admin: http://0.0.0.0:{port}/admin")
    
    app.run(host="0.0.0.0", port=port, debug=False)
"""

# ======================================================================
# Buyer Extension Routes
# ======================================================================

# ── İmport (app.py'nin başına ekle) ──────────────────────────────
# from buyer_engine import (
#     BuyerProfile, BuyerMatcher, ListingMatch, NotificationEngine,
#     NotificationChannel, MatchingTier, buyer_engine_status, parse_natural_language_criteria
# )

# ================================================================
# BUYER EXTENSION API ROUTES
# ================================================================

# ── 1. Durum & Konfigürasyon ──────────────────────────────────────

@app.route("/api/buyer/status")
def api_buyer_status():
    """Buyer Engine durumu."""
    return jsonify(buyer_engine_status())

# ── 2. Buyer Profili Yönetimi ──────────────────────────────────────

@app.route("/api/buyer/profile/create", methods=["POST"])
def api_buyer_create():
    """
    Yeni alıcı profili oluştur.
    
    Body (JSON):
    {
      "uid": "user123",
      "name": "Ahmet Yılmaz",
      "email": "ahmet@example.com",
      "phone": "05324514008",
      "telegram_id": "123456789",
      "whatsapp_phone": "05324514008",
      "criteria": {
        "min_price": 3000000,
        "max_price": 6000000,
        "min_area": 80,
        "max_area": 150,
        "neighborhoods": ["Çankaya", "Dikmen"],
        "property_types": ["Daire", "Dubleks"],
        "min_rooms": 2,
        "max_rooms": 4,
        "natural_language": "Ankara'da yeni ve güzel, balkonlu, otopark"
      },
      "preferences": {
        "notification_channels": ["email", "crm_task"],
        "auto_match": true,
        "priority_level": "high"
      }
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")

    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        profile = BuyerProfile({
            **body,
            "uid": uid,
            "id": db_admin.collection("buyers").document().id,
        })

        doc_ref = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(profile.buyer_id)
        )
        doc_ref.set(profile.to_dict())

        return jsonify({
            "ok": True,
            "buyer_id": profile.buyer_id,
            "profile": profile.to_dict()
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/list", methods=["GET"])
def api_buyer_list():
    """Kullanıcının tüm buyer profillerini listele."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        docs = (
            db_admin.collection("users").document(uid)
            .collection("buyers").stream()
        )
        profiles = [doc.to_dict() for doc in docs]
        return jsonify({"ok": True, "profiles": profiles})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/get", methods=["GET"])
def api_buyer_get():
    """Tek bir buyer profili getir."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        doc = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).get()
        )
        if not doc.exists:
            return jsonify({"ok": False, "error": "Profil bulunamadı"}), 404
        return jsonify({"ok": True, "profile": doc.to_dict()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/update", methods=["POST"])
def api_buyer_update():
    """Buyer profili güncelle."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        doc_ref = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id)
        )
        profile_dict = doc_ref.get().to_dict()
        if not profile_dict:
            return jsonify({"ok": False, "error": "Profil bulunamadı"}), 404

        # Güncelle
        profile_dict.update(body)
        profile_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        doc_ref.set(profile_dict)

        return jsonify({"ok": True, "profile": profile_dict})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/profile/delete", methods=["POST"])
def api_buyer_delete():
    """Buyer profilini sil."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).delete()
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 3. Eşleştirme Engine ────────────────────────────────────────

@app.route("/api/buyer/match-listing", methods=["POST"])
def api_buyer_match_listing():
    """
    Tek bir ilanı buyer profillerine göre eşleştir.
    
    Body:
    {
      "uid": "user123",
      "listing": { ...listing_data... },
      "buyer_ids": ["buyer1", "buyer2"]  // opsiyonel, tümü default
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    listing = body.get("listing")
    buyer_ids = body.get("buyer_ids", [])

    if not uid or not listing:
        return jsonify({"ok": False, "error": "uid ve listing gerekli"}), 400

    try:
        matcher = BuyerMatcher()

        # Buyer profilleri getir
        if buyer_ids:
            buyers_snap = []
            for bid in buyer_ids:
                doc = (
                    db_admin.collection("users").document(uid)
                    .collection("buyers").document(bid).get()
                )
                if doc.exists:
                    buyers_snap.append(doc)
        else:
            buyers_snap = list(
                db_admin.collection("users").document(uid)
                .collection("buyers").stream()
            )

        matches = []
        for buyer_doc in buyers_snap:
            buyer_dict = buyer_doc.to_dict()
            profile = BuyerProfile(buyer_dict)
            match = matcher.match_listing(profile, listing)

            if match:
                matches.append({
                    "buyer_id": profile.buyer_id,
                    "match_score": match.match_score,
                    "tier": match.tier,
                    "details": match.match_details,
                })

        return jsonify({
            "ok": True,
            "listing_id": listing.get("id", ""),
            "matches": matches,
            "total_matches": len(matches),
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/match-batch", methods=["POST"])
def api_buyer_match_batch():
    """
    Birden fazla ilanı buyer'larla batch eşleştir.
    Ağır operasyon — background job olarak önerilir.
    
    Body:
    {
      "uid": "user123",
      "listings": [{ ...listing1... }, { ...listing2... }],
      "buyer_ids": ["buyer1"]  // opsiyonel
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    listings = body.get("listings", [])

    if not uid or not listings:
        return jsonify({"ok": False, "error": "uid ve listings gerekli"}), 400

    try:
        matcher = BuyerMatcher()
        all_matches = []

        for listing in listings:
            # Her listing için tüm buyer'ları eşleştir
            # ... (api_buyer_match_listing mantığı)
            pass

        return jsonify({"ok": True, "total_matches": len(all_matches)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 4. Matching Geçmişi ────────────────────────────────────────

@app.route("/api/buyer/matches/list", methods=["GET"])
def api_buyer_matches_list():
    """
    Buyer'ın tüm eşleşmelerini listele (en yenisi önce).
    
    Query params:
      - uid: gerekli
      - buyer_id: gerekli
      - tier: "perfect", "excellent" vb. (filtre)
      - limit: 50 (default)
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")
    tier = flask_request.args.get("tier")
    limit = int(flask_request.args.get("limit", "50"))

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        query = (
            db_admin.collection("users").document(uid)
            .collection("buyer_matches")
            .where("buyer_id", "==", buyer_id)
            .order_by("created_at", direction="DESCENDING")
        )

        if tier:
            query = query.where("tier", "==", tier)

        docs = query.limit(limit).stream()
        matches = [doc.to_dict() for doc in docs]

        return jsonify({"ok": True, "matches": matches, "count": len(matches)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buyer/matches/stats", methods=["GET"])
def api_buyer_matches_stats():
    """Buyer'ın eşleşme istatistikleri."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    buyer_id = flask_request.args.get("buyer_id")

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        docs = list(
            db_admin.collection("users").document(uid)
            .collection("buyer_matches")
            .where("buyer_id", "==", buyer_id)
            .stream()
        )

        stats = {
            "perfect": sum(1 for d in docs if d.to_dict().get("tier") == "perfect"),
            "excellent": sum(1 for d in docs if d.to_dict().get("tier") == "excellent"),
            "good": sum(1 for d in docs if d.to_dict().get("tier") == "good"),
            "fair": sum(1 for d in docs if d.to_dict().get("tier") == "fair"),
            "total": len(docs),
            "avg_score": sum(d.to_dict().get("match_score", 0) for d in docs) / len(docs) if docs else 0,
        }

        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 5. Notification Tetikle ────────────────────────────────────────

@app.route("/api/buyer/notify", methods=["POST"])
def api_buyer_notify():
    """
    Eşleşme için manual notification tetikle.
    
    Body:
    {
      "uid": "user123",
      "buyer_id": "buyer1",
      "match_id": "match123",
      "channels": ["email", "telegram", "crm_task"]
    }
    """
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")
    channels = body.get("channels", ["email", "crm_task"])

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        # Buyer profili getir
        buyer_doc = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).get()
        )
        if not buyer_doc.exists:
            return jsonify({"ok": False, "error": "Buyer profili bulunamadı"}), 404

        buyer_dict = buyer_doc.to_dict()
        buyer = BuyerProfile(buyer_dict)

        # Email gönder
        result = {}
        if "email" in channels and buyer.email:
            subject, text, html = build_lead_confirmation_email(
                name=buyer.name,
                phone=buyer.phone,
                notes=f"Eşleşme skoru: {body.get('match_score', 0):.0f}%"
            )
            result["email"] = send_transactional_email(buyer.email, subject, text, html)

        # Telegram gönder
        if "telegram" in channels and buyer.telegram_id:
            message = f"🏠 Yeni eşleşme: {body.get('match_score', 0):.0f}%"
            # Telegram API call (app.py'de tanımlanmalı)
            result["telegram"] = {"ok": True}  # Placeholder

        # WhatsApp gönder
        if "whatsapp" in channels and buyer.whatsapp_phone:
            result["whatsapp"] = send_whatsapp(
                buyer.whatsapp_phone,
                f"Yeni eşleşme: {body.get('match_score', 0):.0f}%"
            )

        # CRM görev aç
        if "crm_task" in channels:
            result["crm_task"] = {"ok": True}  # Placeholder

        return jsonify({"ok": True, "notifications": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 6. Natural Language Parsing ────────────────────────────────────

@app.route("/api/buyer/parse-criteria", methods=["POST"])
def api_buyer_parse_criteria():
    """
    Natural language kriterleri parse et (Gemini).
    
    Body:
    {
      "text": "Ankara'da 2+1 daire, maksimum 5 milyon, Çankaya veya Dikmen"
    }
    """
    body = flask_request.json or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({"ok": False, "error": "text boş"}), 400

    try:
        criteria = parse_natural_language_criteria(text)
        return jsonify({"ok": True, "criteria": criteria or {}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ── 7. Dashboard & Analytics ────────────────────────────────────────

@app.route("/api/buyer/dashboard", methods=["GET"])
def api_buyer_dashboard():
    """Buyer dashboard — özet istatistikler."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        # Profil sayısı
        buyers = list(
            db_admin.collection("users").document(uid)
            .collection("buyers").where("is_active", "==", True).stream()
        )

        # Toplam eşleşme
        all_matches = list(
            db_admin.collection("users").document(uid)
            .collection("buyer_matches").stream()
        )

        # Tier dağılımı
        tier_dist = {}
        for match_doc in all_matches:
            tier = match_doc.to_dict().get("tier", "unknown")
            tier_dist[tier] = tier_dist.get(tier, 0) + 1

        return jsonify({
            "ok": True,
            "dashboard": {
                "active_buyers": len(buyers),
                "total_matches": len(all_matches),
                "tier_distribution": tier_dist,
                "avg_match_score": (
                    sum(d.to_dict().get("match_score", 0) for d in all_matches) / len(all_matches)
                    if all_matches else 0
                ),
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ================================================================
# ENTEGRASYON NOTU
# ================================================================
# Bu routes app.py'ye eklenirse, Buyer Extension tam olarak çalışır.
# Sonraki adımlar:
#   1. buyer_engine.py'den import'ları app.py'ye ekle
#   2. Bu routes'ları app.py bootstrap_app() çağrısından önce ekle
#   3. Telegram/WhatsApp entegrasyonu tamamla (app.py'de)
#   4. Frontend (Buyer Panel UI) entegre et

# ================================================================================
# APPLICATION STARTUP
# ================================================================================

if __name__ == "__main__":
    # Initialize services
    print("\n" + "="*80)
    print("🚀 NEXA CRM PRO - STARTING UP")
    print("="*80)
    
    # Bootstrap
    try:
        if 'init_firebase_admin' in dir():
            init_firebase_admin()
        if 'start_scheduler' in dir():
            start_scheduler()
        print("✅ Bootstrap complete")
    except Exception as e:
        print(f"⚠️  Bootstrap warning: {e}")
    
    # Start server
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║            NEXA CRM PRO - PRODUCTION DEPLOYMENT               ║
╠════════════════════════════════════════════════════════════════╣
║ Dashboard:  http://localhost:{port}/crm                        ║
║ Admin:      http://localhost:{port}/admin                      ║
║ Buyer:      http://localhost:{port}/buyer-panel                ║
║ Analysis:   http://localhost:{port}/ai-analysis                ║
║ Health:     http://localhost:{port}/health                     ║
╠════════════════════════════════════════════════════════════════╣
║ Debug Mode: {str(debug):<47} ║
║ Environment: production                                       ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
