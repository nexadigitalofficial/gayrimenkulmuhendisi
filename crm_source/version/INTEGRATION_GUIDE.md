"""
================================================================
BUYER EXTENSION — ENTEGRASYON REHBERİ
Nexa CRM AI Buyer Extension — Adım Adım Kurulum
================================================================

Bu rehber, Buyer Extension'ı mevcut app.py'ye nasıl entegre 
edeceğinizi gösterir.

ADIMLAR:
  1. buyer_engine.py'i projeye ekle
  2. app.py'ye buyer_engine import'larını ekle
  3. app.py'ye buyer API routes'larını ekle
  4. crm.html'e buyer_panel.html'i entegre et
  5. .env'e gerekli variables'ları ekle
  6. Test et

DOSYALAR:
  ✅ buyer_engine.py — Matching logic + data models
  ✅ app_buyer_routes.py — API routes (app.py'ye copy-paste)
  ✅ buyer_panel.html — Frontend UI (crm.html'e entegre)
  ✅ INTEGRATION_GUIDE.md — Bu dosya

================================================================
"""

# ================================================================
# ADIM 1: buyer_engine.py'i projeye ekle
# ================================================================
# Dosya: /project/buyer_engine.py
# Kaynak: buyer_engine.py (Tam dosya — değişiklik yapma)


# ================================================================
# ADIM 2: app.py'nin başına şu import'ları ekle
# ================================================================

"""
Var olan import'ların altına ekle (satır ~42 civarı):

from buyer_engine import (
    BuyerProfile, BuyerMatcher, ListingMatch, NotificationEngine,
    NotificationChannel, MatchingTier, buyer_engine_status, 
    parse_natural_language_criteria
)
"""


# ================================================================
# ADIM 3: app.py'ye buyer API routes'larını ekle
# ================================================================

"""
Aşağıdaki tüm route'ları app.py'nin sonuna ekle 
(bootstrap_app() çağrısından ÖNCE).
"""


# ── BUYER EXTENSION API ROUTES ─────────────────────────────────

@app.route("/api/buyer/status")
def api_buyer_status():
    """Buyer Engine durumu."""
    return jsonify(buyer_engine_status())


@app.route("/api/buyer/profile/create", methods=["POST"])
def api_buyer_create():
    """Yeni alıcı profili oluştur."""
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


@app.route("/api/buyer/match-listing", methods=["POST"])
def api_buyer_match_listing():
    """Tek bir ilanı buyer profillerine göre eşleştir."""
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
                # Firebase'e kaydet
                match_ref = (
                    db_admin.collection("users").document(uid)
                    .collection("buyer_matches").document()
                )
                match_ref.set(match.to_dict())

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


@app.route("/api/buyer/matches/list", methods=["GET"])
def api_buyer_matches_list():
    """Buyer'ın tüm eşleşmelerini listele."""
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


@app.route("/api/buyer/notify", methods=["POST"])
def api_buyer_notify():
    """Eşleşme için manual notification tetikle."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    body = flask_request.json or {}
    uid = body.get("uid")
    buyer_id = body.get("buyer_id")
    channels = body.get("channels", ["email", "crm_task"])

    if not uid or not buyer_id:
        return jsonify({"ok": False, "error": "uid ve buyer_id gerekli"}), 400

    try:
        buyer_doc = (
            db_admin.collection("users").document(uid)
            .collection("buyers").document(buyer_id).get()
        )
        if not buyer_doc.exists:
            return jsonify({"ok": False, "error": "Buyer profili bulunamadı"}), 404

        buyer_dict = buyer_doc.to_dict()
        buyer = BuyerProfile(buyer_dict)

        result = {}
        if "email" in channels and buyer.email:
            subject, text, html = build_lead_confirmation_email(
                name=buyer.name,
                phone=buyer.phone,
                notes=f"Yeni eşleşme bulundu - Skor: {body.get('match_score', 0):.0f}%"
            )
            result["email"] = send_transactional_email(buyer.email, subject, text, html)

        if "whatsapp" in channels and buyer.whatsapp_phone:
            result["whatsapp"] = send_whatsapp(
                buyer.whatsapp_phone,
                f"🏠 Yeni eşleşme bulundu! Skor: {body.get('match_score', 0):.0f}%"
            )

        if "crm_task" in channels:
            # CRM'e görev aç (opsiyonel — kendi task sisteminizle entegre edin)
            result["crm_task"] = {"ok": True}

        return jsonify({"ok": True, "notifications": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/buyer/parse-criteria", methods=["POST"])
def api_buyer_parse_criteria():
    """Natural language kriterleri parse et (Gemini)."""
    body = flask_request.json or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({"ok": False, "error": "text boş"}), 400

    try:
        criteria = parse_natural_language_criteria(text)
        return jsonify({"ok": True, "criteria": criteria or {}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/buyer/dashboard", methods=["GET"])
def api_buyer_dashboard():
    """Buyer dashboard — özet istatistikler."""
    if not _fb_initialized:
        return jsonify({"ok": False, "error": "Firebase bağlı değil"}), 503

    uid = flask_request.args.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "uid gerekli"}), 400

    try:
        buyers = list(
            db_admin.collection("users").document(uid)
            .collection("buyers").where("is_active", "==", True).stream()
        )

        all_matches = list(
            db_admin.collection("users").document(uid)
            .collection("buyer_matches").stream()
        )

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
# ADIM 4: crm.html'e buyer_panel.html'i entegre et
# ================================================================

"""
crm.html içinde, mevcut tab'lardan sonra şunu ekle:

<!-- BUYER PANEL TAB -->
<div id="buyerPanelContainer" style="display: none;">
  <!-- buyer_panel.html içeriğini burada include et -->
</div>

Sonra crm.html'in script kısmında:

<script>
  // Buyer panel initialization
  function switchToBuyerPanel(uid) {
    // Diğer tab'ları gizle
    document.querySelectorAll('[id$="Container"]').forEach(el => el.style.display = "none");
    document.getElementById("buyerPanelContainer").style.display = "block";
    
    // Panel'i initialize et
    initBuyerPanel(uid);
  }
</script>

Veya daha basit: buyer_panel.html'in başında <div id="buyerPanel">...</div> 
ve sonunda </div>, bunu crm.html'e copy-paste yap.
"""


# ================================================================
# ADIM 5: .env dosyasına ekle (opsiyonel)
# ================================================================

"""
BUYER_MIN_MATCH_SCORE=50
BUYER_VECTOR_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_BUYER_NOTIFICATIONS=true
"""


# ================================================================
# ADIM 6: Test et
# ================================================================

"""
1. Flask sunucuyu başlat:
   python app.py

2. API status'unu kontrol et:
   curl http://localhost:5000/api/buyer/status

3. Test edici yüklü mi kontrol et:
   pip install sentence-transformers

4. Buyer profili oluştur:
   curl -X POST http://localhost:5000/api/buyer/profile/create \
     -H "Content-Type: application/json" \
     -d '{
       "uid": "test_user_123",
       "name": "Ahmet Yılmaz",
       "email": "ahmet@example.com",
       "phone": "05324514008",
       "criteria": {
         "min_price": 3000000,
         "max_price": 6000000,
         "neighborhoods": ["Çankaya", "Dikmen"]
       }
     }'

5. Dashboard'ı aç:
   http://localhost:5000/crm.html
   (Buyer tab'ını ekledikten sonra)
"""


# ================================================================
# FIREBASE AYARLARI
# ================================================================

"""
Firestore Collection Structure:

users/{uid}/
  ├── buyers/{buyerID}/
  │   ├── id: string
  │   ├── name: string
  │   ├── email: string
  │   ├── phone: string
  │   ├── criteria: {
  │   │   min_price, max_price, min_area, max_area,
  │   │   neighborhoods[], property_types[],
  │   │   natural_language: string
  │   }
  │   ├── preferences: {
  │   │   notification_channels[], auto_match: bool,
  │   │   priority_level: string
  │   }
  │   └── is_active: bool
  │
  └── buyer_matches/{matchID}/
      ├── buyer_id: string
      ├── listing_id: string
      ├── listing_data: object
      ├── match_score: number
      ├── match_details: object
      ├── tier: string
      ├── created_at: timestamp
      └── notification_sent: bool
"""


# ================================================================
# ENTEGRASYON AKIŞI
# ================================================================

"""
1. ADMIN: Buyer profile oluşturur
   /api/buyer/profile/create
   → Firebase: users/{uid}/buyers/{buyerID}

2. SİSTEM: Yeni ilan geldiğinde
   /api/buyer/match-listing
   → BuyerMatcher tüm buyers'ı kontrol eder
   → Eşleşenleri Firebase'e kaydeder

3. ADMIN/SYSTEM: Eşleşmeleri görür
   /api/buyer/dashboard
   /api/buyer/matches/list
   → Dashboard: Stats + Tier dağılımı

4. ADMIN: Eşleşme hakkında bildir
   /api/buyer/notify
   → Email, Telegram, WhatsApp, CRM task

5. REPEATING: Eski ilanları taramak için
   (Cron job aracılığıyla)
   /api/buyer/match-batch
"""


# ================================================================
# TROUBLESHOOTING
# ================================================================

"""
❌ "Firebase bağlı değil" hatası
  → app.py'de init_firebase_admin() çağrılıyor mu?
  → .env'de FIREBASE_SERVICE_ACCOUNT var mı?

❌ Vector model yüklenmedi
  → pip install sentence-transformers
  → Veya buyer_engine.py'de _SENTENCE_TRANSFORMER = False

❌ Gemini API hatası (Natural Language parsing)
  → .env'de GEMINI_API_KEY var mı?
  → API key valid mi?

❌ Email gönderilemedi
  → mailer.py status kontrol et: /api/mailer/status
  → SMTP credentials doğru mu?

✅ Başarılı entegrasyon işareti:
  - /api/buyer/status → {"ok": true}
  - /api/buyer/dashboard → {"ok": true, "dashboard": {...}}
  - crm.html'de Buyer tab'ı görünüyor
"""

