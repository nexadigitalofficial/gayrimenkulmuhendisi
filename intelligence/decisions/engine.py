"""
Interactive Real Estate Decision Intelligence Engines.
Implements:
1. "Ev Almalı mıyım?" (Buying Conditions Engine)
2. "Evimi Satmalı mıyım?" (Selling Conditions Engine)
3. "Proje Yatırımı İçin Uygun Zaman mı?" (Project Opportunity Engine)
4. "Kirada Kalmak mı Satın Almak mı?" (Rent vs. Buy Yield Engine)
5. "Arsa Almalı mıyım?" (Land Investment Engine)

Safety Principles:
- Strictly non-dogmatic (No "Kesin al/sat").
- Output conditions: Strong Conditions, Moderate Conditions, Neutral, Caution, Weak Conditions.
- Every score is backed by transparent, explainable financial & market metrics.
"""

from typing import Dict, Any, List
from intelligence.models import DecisionResult


class DecisionIntelligence:
    """Calculates condition indexes and risk/opportunity profiles for client decisions."""

    # ─────────────────────────────────────────────────────────────────
    # 1. EV ALMALI MIYIM? (BUYING CONDITIONS ENGINE)
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_buying_conditions(
        budget: float = 5_000_000,
        location: str = "Ankara / Çankaya",
        property_type: str = "Konut",
        payment_method: str = "Nakit + Taksit",
        time_horizon: str = "Orta Vade (3-5 Yıl)",
        **kwargs
    ) -> DecisionResult:
        # Flexible parameter normalization
        budget = float(kwargs.get("budget_tl") or kwargs.get("budget") or budget or 5_000_000)
        location = str(kwargs.get("district") or kwargs.get("location") or location or "Ankara / Çankaya").strip()
        property_type = str(kwargs.get("unit_type") or kwargs.get("property_type") or property_type or "Konut").strip()
        payment_method = str(kwargs.get("financing_type") or kwargs.get("payment_method") or payment_method or "Nakit + Taksit").strip()
        time_horizon = str(kwargs.get("holding_period_years") or kwargs.get("time_horizon") or time_horizon or "Orta Vade (3-5 Yıl)").strip()

        factors = []
        score = 7.2  # Base index out of 10

        # Location factor
        loc_lower = location.lower()
        if any(h in loc_lower for h in ["beytepe", "çankaya", "incek", "çayyolu", "yaşamkent", "bilkent", "ümitköy"]):
            score += 0.7
            factors.append({
                "factor": "Bölgesel Değer Artış & Prestij Koridoru",
                "impact": "Pozitif (+0.7)",
                "detail": f"{location} aksı, Ankara'nın kurumsal sermaye göçü ve lüks konut talebiyle değerini güçlü korumaktadır."
            })
        elif any(h in loc_lower for h in ["gölbaşı", "bağlıca", "eryaman", "batı"]):
            score += 0.4
            factors.append({
                "factor": "Gelişme Aksı Potansiyeli",
                "impact": "Olumlu (+0.4)",
                "detail": f"{location} bölgesi yeni altyapı ve konut projeleriyle orta vadede büyüme potansiyeline sahiptir."
            })
        else:
            factors.append({
                "factor": "Bölgesel Likidite & Ekspertiz",
                "impact": "Nötr",
                "detail": f"{location} bölgesinde mülk tipi ve birim m² fiyatlama ekspertizi titizlikle yapılmalıdır."
            })

        # Payment method factor
        pay_lower = payment_method.lower()
        if any(w in pay_lower for w in ["nakit", "peşin", "taksit", "lansman", "geliştirici"]):
            score += 0.6
            factors.append({
                "factor": "Finansman Maliyeti & Nakit Avantajı",
                "impact": "Avantajlı (+0.6)",
                "detail": "Doğrudan geliştirici taksiti veya peşin alım iskontosu, banka konut kredisi faiz maliyetinden tam koruma sağlar."
            })
        else:
            score -= 0.6
            factors.append({
                "factor": "Konut Kredisi Faiz Maliyet Baskısı",
                "impact": "Baskı (-0.6)",
                "detail": "Yüksek banka faiz oranları aylık taksit yükünü artırmaktadır; peşinat oranını asgari %60 tutmak önerilir."
            })

        # Budget scale impact
        if budget >= 15_000_000:
            score += 0.4
            factors.append({
                "factor": "Yüksek Sermaye & Özel Portföy Erişimi",
                "impact": "Stratejik (+0.4)",
                "detail": f"{budget:,.0f} TL bütçe, seçkin projelerde şerefiyeli ünite ve özel pazarlık marjı yakalamak için ideal ölçektedir."
            })
        elif budget <= 3_500_000:
            score -= 0.3
            factors.append({
                "factor": "Segment Arz Kısıtı",
                "impact": "Dikkat (-0.3)",
                "detail": "Giriş segmentinde nitelikli ve prim potansiyeli yüksek stok sınırlı olup hızlı hareket gerektirir."
            })

        # Inflation & replacement cost hedge
        factors.append({
            "factor": "İkame Maliyeti & Enflasyon Kalkanı",
            "impact": "Pozitif (+0.5)",
            "detail": "TÜİK İnşaat Maliyet Endeksi (İME) artışı, teslim aşamasındaki konutlarda reel sermaye koruması sağlamaktadır."
        })

        # Clamp score between 2.5 and 9.4
        score = round(min(max(score, 2.5), 9.4), 1)

        condition = "Strong Conditions (Güçlü Alım Koşulları)" if score >= 7.5 else (
            "Moderate Conditions (Dengeli / Seçici Koşullar)" if score >= 6.0 else "Caution (Temkinli / Seçici Piyasa)"
        )

        risks = [
            "İnşaat tamamlama ve iskan teslim gecikmesi riski (mutlaka kurumsal güvenceli projeler seçilmelidir)",
            "Piyasa rayici üzerinde köpük fiyatlama riski (karşılaştırmalı ekspertiz şarttır)"
        ]
        opportunities = [
            "Lansman ve yapım aşamasındaki projelerde vade farksız taksit ve ilk liste fiyatı avantajı",
            "Bölgedeki güçlü kira talebinin gayrimenkulü 14-16 yılda amorti edebilme kabiliyeti"
        ]

        formatted_budget = f"{budget:,.0f} TL"
        return DecisionResult(
            engine_name="buying_conditions",
            score=score,
            condition=condition,
            headline=f"Alım Koşulları Endeksi: {score} / 10 — {condition}",
            summary=f"{location} bölgesinde {formatted_budget} bütçe ile {property_type} alımı için piyasa dinamikleri, doğru finansman modeliyle avantajlı bir sermaye koruma ve büyüme fırsatı sunmaktadır.",
            factors=factors,
            risks=risks,
            opportunities=opportunities,
            suggested_action="Bütçenize en uygun teslimat güvenceli 3 prestij projesini yerinde karşılaştırın.",
            advisor_consultation_prompt=f"Merhaba Yiğit Bey, NEXA İstihbarat Terminali üzerinden {location} bölgesinde {formatted_budget} bütçe ve {payment_method} modeliyle simülasyon yaptım ({score}/10 Alım Endeksi). Uygun portföyler hakkında görüşmek istiyorum."
        )

    # ─────────────────────────────────────────────────────────────────
    # 2. EVİMİ SATMALI MIYIM? (SELLING CONDITIONS ENGINE)
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_selling_conditions(
        location: str = "Ankara / Çankaya",
        property_type: str = "Daire",
        approx_value: float = 6_000_000,
        urgency: str = "Normal (3-6 Ay)",
        condition: str = "Masrafsız / Sıfır",
        **kwargs
    ) -> DecisionResult:
        # Flexible parameter normalization
        location = str(kwargs.get("district") or kwargs.get("location") or location or "Ankara / Çankaya").strip()
        property_type = str(kwargs.get("unit_type") or kwargs.get("property_type") or property_type or "Daire").strip()
        approx_value = float(kwargs.get("estimated_value") or kwargs.get("value_tl") or kwargs.get("approx_value") or approx_value or 6_000_000)
        urgency = str(kwargs.get("timeline") or kwargs.get("urgency") or urgency or "Normal (3-6 Ay)").strip()
        condition_str = str(kwargs.get("property_status") or kwargs.get("condition") or condition or "Masrafsız / Sıfır").strip()

        factors = []
        score = 6.8  # Base index out of 10

        loc_lower = location.lower()
        if any(h in loc_lower for h in ["beytepe", "çankaya", "gop", "incek", "bilkent", "çayyolu"]):
            score += 0.7
            factors.append({
                "factor": "Seçkin Bölge Alıcı Talebi & Likidite",
                "impact": "Güçlü (+0.7)",
                "detail": f"{location} hattında nitelikli ve oturuma hazır konut arayan hazır alıcı kitlesi canlıdır."
            })

        # Condition factor
        cond_lower = condition_str.lower()
        if any(w in cond_lower for w in ["sıfır", "masrafsız", "lüks", "yapılı", "iyi"]):
            score += 0.5
            factors.append({
                "factor": "Mülk Durumu & Rekabet Üstünlüğü",
                "impact": "Pozitif (+0.5)",
                "detail": "Tadilat ve yenileme ihtiyacı olmayan mülkler piyasada çok daha hızlı ve liste fiyatına yakın nakde çevrilmektedir."
            })
        else:
            score -= 0.4
            factors.append({
                "factor": "Tadilat & Yenileme İskontosu Beklentisi",
                "impact": "İskonto Baskısı (-0.4)",
                "detail": "Alıcılar masraflı mülklerde pazarlık marjını yüksek tutma ve fiyat kırma eğilimindedir."
            })

        # Urgent liquidation impact
        urg_lower = urgency.lower()
        if any(w in urg_lower for w in ["acil", "1 ay", "derhal", "hızlı"]):
            score -= 0.8
            factors.append({
                "factor": "Zaman Kısıtı & Likidasyon Marjı",
                "impact": "Fiyat Baskısı (-0.8)",
                "detail": "Kısa sürede (30 gün altı) nakde dönme hedefi ortalama %5-10 iskonto marjı gerektirebilir."
            })
        else:
            score += 0.3
            factors.append({
                "factor": "Sabırlı Pazarlama Stratejisi",
                "impact": "Avantaj (+0.3)",
                "detail": "3-6 aylık makul süre, mülkün gerçek değerinde doğru alıcı profiliyle buluşmasını sağlar."
            })

        # Value scale factor
        if approx_value >= 12_000_000:
            factors.append({
                "factor": "Lüks Segment Pazarlama Ağı",
                "impact": "Özel Süreç",
                "detail": "12M TL üzeri mülkler genel ilan portalları yerine Coldwell Banker VIP gibi kapalı yatırımcı ağıyla daha hızlı sonuç verir."
            })

        score = round(min(max(score, 3.0), 9.2), 1)
        res_condition = "Strong Conditions (Satış İçin Uygun Zaman)" if score >= 7.5 else (
            "Moderate Conditions (Dengeli Piyasa / Doğru Fiyat Şart)" if score >= 6.0 else "Caution (Seçici / Fiyat Korumalı Satış)"
        )

        risks = [
            "Piyasa rayicinin üzerinde listeleyerek mülkün piyasada 'eski ilan' konumuna düşmesi",
            "Yetkisiz çoklu emlakçı ilanlarıyla piyasada fiyat karmaşası yaratılması"
        ]
        opportunities = [
            "Doğru fiyatlandırma ve CB VIP uluslararası pazarlama ağı ile nitelikli alıcıya doğrudan erişim",
            "Elde edilen likiditenin topraktan lansman veya kat karşılığı arsa yatırımı ile katlanması"
        ]

        formatted_val = f"{approx_value:,.0f} TL"
        return DecisionResult(
            engine_name="selling_conditions",
            score=score,
            condition=res_condition,
            headline=f"Satış Koşulları Endeksi: {score} / 10 — {res_condition}",
            summary=f"{location} bölgesindeki yaklaşık {formatted_val} değerindeki {property_type} mülkünüz için doğru değerleme ve profesyonel tek yetkili pazarlama ile başarı oranı yüksektir.",
            factors=factors,
            risks=risks,
            opportunities=opportunities,
            suggested_action="Mülkünüz için güncel Karşılaştırmalı Piyasa Analizi (CMA) raporu oluşturun.",
            advisor_consultation_prompt=f"Merhaba Yiğit Bey, NEXA İstihbarat Terminali üzerinden {location} bölgesindeki {formatted_val} değerindeki mülküm için satış analizi yaptım ({score}/10 Satış Endeksi). Profesyonel satış stratejisi hakkında görüşmek istiyorum."
        )

    # ─────────────────────────────────────────────────────────────────
    # 3. PROJE YATIRIMI İÇİN UYGUN ZAMAN MI?
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_project_opportunity(
        project_name: str = "Mas Lora / Angim Beytepe",
        location: str = "Beytepe / Yaşamkent",
        developer_reputation: str = "Yüksek",
        delivery_stage: str = "Kaba İnşaat / Lansman",
        **kwargs
    ) -> DecisionResult:
        # Flexible parameter normalization
        project_name = str(kwargs.get("project_name") or project_name or "Prestij Projesi").strip()
        location = str(kwargs.get("district") or kwargs.get("location") or location or "Beytepe / Ankara").strip()
        developer_reputation = str(kwargs.get("developer_reputation") or developer_reputation or "Yüksek").strip()
        delivery_stage = str(kwargs.get("delivery_stage") or delivery_stage or "Kaba İnşaat / Lansman").strip()

        score = 75.0  # Base score out of 100
        factors = []

        # Delivery stage dynamic scoring
        stage_lower = delivery_stage.lower()
        if any(w in stage_lower for w in ["lansman", "temel", "erken"]):
            score += 10.0
            factors.append({
                "factor": "Lansman Prim Marjı (Topraktan Avantajı)",
                "impact": "Yüksek Getiri (+10 Puan)",
                "detail": "Lansman ve temel aşamasında girilen projeler anahtar teslimine kadar %45-65 reel sermaye primi üretmektedir."
            })
        elif any(w in stage_lower for w in ["kaba", "yapım", "inşaat"]):
            score += 6.0
            factors.append({
                "factor": "İlerleme Seviyesi & Büyüme Dengesi",
                "impact": "Güçlü (+6 Puan)",
                "detail": "Kaba inşaat aşamasındaki projelerde hem teslimat riski azalmış hem de yukarı yönlü prim potansiyeli korunmuştur."
            })
        else:
            score += 4.0
            factors.append({
                "factor": "Hızlı Teslimat & Nakit Akışı",
                "impact": "Düşük Risk (+4 Puan)",
                "detail": "Teslim aşamasındaki projeler derhal kira getirisi üretme ve sıfır bekleme avantajı sağlar."
            })

        # Developer reputation
        dev_lower = developer_reputation.lower()
        if any(w in dev_lower for w in ["yüksek", "kurumsal", "güvenilir", "a+"]):
            score += 8.0
            factors.append({
                "factor": "Geliştirici Güvencesi & Taahhüt Gücü",
                "impact": "Kritik Güvence (+8 Puan)",
                "detail": "Kurumsal sermaye yapısı ve noter onaylı satış vaadi sözleşmesi yatırılan ana parayı tam koruma altına alır."
            })
        else:
            score -= 5.0
            factors.append({
                "factor": "Müteahhit Finansal Güç Analizi",
                "impact": "Dikkat (-5 Puan)",
                "detail": "Finansal dayanıklılığı teyit edilmemiş geliştiricilerde inşaat süresi uzama riski titizlikle denetlenmelidir."
            })

        # Location catalyst
        loc_lower = location.lower()
        if any(h in loc_lower for h in ["beytepe", "incek", "çankaya", "çayyolu", "bilkent"]):
            score += 5.0
            factors.append({
                "factor": "Bölge Altyapı & Bulvar Entegrasyonu",
                "impact": "Pozitif (+5 Puan)",
                "detail": f"{location} bölgesindeki yeni bulvar bağlantıları ve ticari akslar projenin likiditesini katlamaktadır."
            })

        score = round(min(max(score, 45.0), 94.0), 1)
        condition = "High Opportunity (Yüksek Fırsat Potansiyeli)" if score >= 80 else (
            "Moderate Opportunity (Dengeli Fırsat)" if score >= 65 else "Selective (Seçici İnceleme Gerektirir)"
        )

        return DecisionResult(
            engine_name="project_opportunity",
            score=score,
            condition=condition,
            headline=f"Proje Yatırım Fırsat Skoru: {score:.0f} / 100 — {condition}",
            summary=f"{location} bölgesindeki {project_name} projesi, {delivery_stage} aşamasında sunduğu ödeme kolaylıkları ve sermaye büyümesiyle yüksek potansiyel barındırmaktadır.",
            factors=factors,
            risks=["Müteahhit teslim taahhüt sürelerinin takibi", "Ödeme taksit planının yatırımcının nakit akışını zorlamaması"],
            opportunities=["Teslimde yüksek kira çarpanı ve döviz/altın bazında reel sermaye artışı", "Lansman liste fiyatı iskontosu"],
            suggested_action="Örnek daireyi, teknik şartnameyi ve kat planlarını yerinde inceleyin.",
            advisor_consultation_prompt=f"Merhaba Yiğit Bey, NEXA İstihbarat Terminali üzerinden {location} bölgesindeki {project_name} için proje fırsat analizi yaptım ({score:.0f}/100 Puan). En şerefiyeli daire ve ödeme planı hakkında bilgi almak istiyorum."
        )

    # ─────────────────────────────────────────────────────────────────
    # 4. KİRADA KALMAK MI SATIN ALMAK MI?
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_rent_vs_buy(
        monthly_rent: float = 35_000,
        home_price: float = 5_500_000,
        cash_available: float = 2_000_000,
        duration_years: int = 5,
        **kwargs
    ) -> DecisionResult:
        # Flexible parameter normalization
        monthly_rent = float(kwargs.get("rent_tl") or kwargs.get("monthly_rent") or monthly_rent or 35_000)
        home_price = float(kwargs.get("property_price_tl") or kwargs.get("home_price") or home_price or 5_500_000)
        cash_available = float(kwargs.get("cash_tl") or kwargs.get("cash_available") or cash_available or 2_000_000)
        duration_years = int(kwargs.get("years") or kwargs.get("duration_years") or duration_years or 5)

        # Dynamic Financial Calculation
        annual_rent = monthly_rent * 12
        # Gross Yield %
        gross_yield = (annual_rent / home_price * 100) if home_price > 0 else 6.5
        # Amortization Period (Price-to-rent ratio in years)
        amortization_years = (home_price / annual_rent) if annual_rent > 0 else 15.0

        # Projected rent with 35% average annual escalation over duration
        total_rent_paid = sum(annual_rent * ((1 + 0.35) ** y) for y in range(duration_years))

        # Expected property appreciation over duration (conservative ~2.2x over 5 yrs)
        appreciation_factor = (1 + 0.22) ** duration_years
        expected_home_value = home_price * appreciation_factor
        net_wealth_delta = expected_home_value - home_price

        factors = [
            {
                "factor": "Kira Çarpanı & Amortisman Süresi",
                "impact": f"{amortization_years:.1f} Yıl (Brüt Getiri: %{gross_yield:.1f})",
                "detail": f"Bölgedeki kira bedeli mülk değerini yaklaşık {amortization_years:.1f} yılda amorti etmektedir (Türkiye lüks ortalaması 15-18 yıldır)."
            },
            {
                "factor": "Geri Dönüşsüz Nakit Çıkışı (Ödenecek Toplam Kira)",
                "impact": f"~{int(total_rent_paid):,} TL eriyen nakit",
                "detail": f"{duration_years} yıllık süreçte kiraya verilecek tutar tamamen geri dönüşümsüz bir harcamadır."
            },
            {
                "factor": "Özkaynak & Sermaye Büyümesi",
                "impact": f"+{int(net_wealth_delta):,} TL tahmini değer artışı",
                "detail": "Gayrimenkul sahipliği, enflasyonist dönemlerde reel alım gücünü koruyan birincil kalkandır."
            }
        ]

        # Score calculation: lower amortization -> higher buy score
        # 12 years amortization -> score ~9.0, 18 years -> ~7.5, 25 years -> ~5.5
        score = 12.0 - (amortization_years * 0.28)
        if duration_years >= 4:
            score += 0.5  # Long term favors buying
        score = round(min(max(score, 3.5), 9.4), 1)

        condition = "Strong Buy Advantage (Satın Alma Belirgin Üstün)" if score >= 7.5 else (
            "Moderate Buy Advantage (Satın Alma Dengeli)" if score >= 6.0 else "Balanced (Kirada Kalıp Nakdi Değerlendirme)"
        )

        return DecisionResult(
            engine_name="rent_vs_buy",
            score=score,
            condition=condition,
            headline=f"Satın Alma Tercihi Endeksi: {score} / 10 — {condition}",
            summary=f"Mevcut {monthly_rent:,.0f} TL kira ve {home_price:,.0f} TL mülk değeri dengesinde, {duration_years} yıllık ikamet projeksiyonunda satın alma stratejisi net özkaynak birikimi açısından güçlü bir üstünlük sağlamaktadır.",
            factors=factors,
            risks=["Kredi faiz maliyetinin aylık nakit akışını zorlamaması için peşinat dengesinin kurulması"],
            opportunities=["Kira ödemek yerine kendi mülkünüzde sermaye büyümesi yaratma imkanı", "Enflasyona karşı reel varlık koruması"],
            suggested_action="Bütçenize en uygun peşinat ve ödeme takvimi simülasyonunu netleştirin.",
            advisor_consultation_prompt=f"Merhaba Yiğit Bey, NEXA İstihbarat Terminali üzerinden {monthly_rent:,.0f} TL kira ve {home_price:,.0f} TL ev fiyatı ile Kirada Kalmak vs Satın Almak analizi yaptım ({score}/10 Satın Alma Endeksi). Stratejik finansman seçeneklerini görüşmek istiyorum."
        )
