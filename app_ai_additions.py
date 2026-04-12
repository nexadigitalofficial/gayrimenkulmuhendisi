# ================================================================
# app.py'ye EKLENECEK BÖLÜMLER
# ================================================================
# 1. Dosyanın üstüne, diğer from ... import satırlarının yanına:
#
#    from ai_listing import scrape_listing, analyze_listing, ai_listing_status
#
# 2. Aşağıdaki route'ları app.py'nin sonuna (bootstrap_app() çağrısından önce) ekle.
# ================================================================


# ── AI Analiz Sayfası ─────────────────────────────────────────────────────────

@app.route("/ai-analysis")
def ai_analysis_page():
    """AI Gayrimenkul Analiz sayfası."""
    try:
        return send_file("ai_analysis.html")
    except Exception as e:
        return f"ai_analysis.html bulunamadı: {e}", 404


# ── API: İlan Scrape ──────────────────────────────────────────────────────────

@app.route("/api/ai/scrape", methods=["POST"])
def api_ai_scrape():
    """
    İlan URL'sini scrape eder.
    Body: {"url": "https://www.sahibinden.com/ilan/..."}
    Döner: {"ok": true, "data": {...}} veya {"ok": false, "error": "..."}
    """
    body = flask_request.json or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"ok": False, "error": "url boş olamaz"}), 400

    # Basit URL doğrulama
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        result = scrape_listing(url)
        return jsonify({"ok": result.get("ok", False), "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── API: Tam Analiz ───────────────────────────────────────────────────────────

@app.route("/api/ai/analyze", methods=["POST"])
def api_ai_analyze():
    """
    Gemini ile tam gayrimenkul analizi üretir.

    Body (JSON):
    {
      "listing_data":    { ... }  // /api/ai/scrape çıktısı (opsiyonel)
      "manual_data": {            // Manuel giriş alanları (opsiyonel)
        "manual_price":    "5.500.000 TL",
        "manual_area":     "120 m²",
        "manual_rooms":    "3+1",
        "manual_floor":    "5/8",
        "manual_age":      "10 yıl",
        "manual_location": "Çankaya, Ankara",
        "manual_notes":    "Notlar...",
        "listing_type":    "Satılık"
      },
      "uploaded_images": ["data:image/jpeg;base64,...", ...]   // opsiyonel
    }

    Döner:
    {
      "ok": true,
      "report": {
        "property_summary": {...},
        "price_analysis":   {...},
        "investment_analysis": {...},
        "photo_analysis":   {...},
        "swot":             {...},
        "location_analysis":{...},
        "advisor_notes":    {...},
        "recommendation":   {...},
        "generated_at": "...",
        ...
      }
    }
    """
    body = flask_request.json or {}

    listing_data    = body.get("listing_data")
    manual_data     = body.get("manual_data")
    uploaded_images = body.get("uploaded_images", [])

    # En az bir girdi gerekli
    if not listing_data and not manual_data and not uploaded_images:
        return jsonify({"ok": False, "error": "En az bir girdi gerekli (listing_data, manual_data veya uploaded_images)"}), 400

    try:
        result = analyze_listing(
            listing_data    = listing_data,
            manual_data     = manual_data,
            uploaded_images = uploaded_images,
        )
        status = 200 if result.get("ok") else 500
        return jsonify(result), status
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── API: AI Sistem Durumu ─────────────────────────────────────────────────────

@app.route("/api/ai/status")
def api_ai_status():
    """Gemini AI listing modülünün konfigürasyon durumunu döner."""
    return jsonify(ai_listing_status())


# ── API: Analizi Firebase'e Kaydet ───────────────────────────────────────────

@app.route("/api/ai/save-to-crm", methods=["POST"])
def api_ai_save_to_crm():
    """
    Üretilen analiz raporunu Firebase'e kaydeder.

    Body: {
      "uid":    "kullanici_id",        // firebase auth uid
      "report": { ... },              // analyze_listing() raporu
      "url":    "ilan_url",            // (opsiyonel)
      "contact_id": "..."             // CRM'deki lead ID (opsiyonel)
    }
    """
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
            "report":     report,
            "url":        url,
            "contactId":  contact_id,
            "createdAt":  datetime.now(timezone.utc).isoformat(),
            "source":     report.get("data_source", ""),
            "verdict":    report.get("recommendation", {}).get("verdict", ""),
        })
        return jsonify({"ok": True, "id": doc_ref.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
