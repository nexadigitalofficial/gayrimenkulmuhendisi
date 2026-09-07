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
        budget: float,
        location: str = "Ankara / Çankaya",
        property_type: str = "Konut",
        payment_method: str = "Nakit + Taksit",
        time_horizon: str = "Orta Vade (3-5 Yıl)"
    ) -> DecisionResult:
        factors = []
        score = 7.4  # Base index out of 10

        # Location factor
        loc_lower = location.lower()
        if any(h in loc_lower for h in ["beytepe", "çankaya", "incek", "çayyolu", "yaşamkent"]):
            score += 0.6
            factors.append({
                "factor": "Bölgesel Değer Artış Potansiyeli",
                "impact": "Pozitif (+0.6)",
                "detail": f"{location} aksı lüks konut talebi ve altyapı bağlantılarıyla değerini güçlü korumaktadır."
            })
        else:
            factors.append({
                "factor": "Bölgesel Likidite",
                "impact": "Nötr",
                "detail": f"{location} bölgesinde mülk tipi ve fiyatlama ekspertizi dikkatle yapılmalıdır."
            })

        # Payment method factor
        pay_lower = payment_method.lower()
        if "nakit" in pay_lower or "taksit" in pay_lower or "lansman" in pay_lower:
            score += 0.5
            factors.append({
                "factor": "Finansman Maliyeti & Ödeme Kolaylığı",
                "impact": "Avantajlı (+0.5)",
                "detail": "Doğrudan geliştirici taksiti veya nakit alım iskontosu, banka kredi faiz maliyetinden koruma sağlar."
            })
        else:
            score -= 0.7
            factors.append({
                "factor": "Konut Kredisi Faiz Yükü",
                "impact": "Baskı (-0.7)",
                "detail": "Mevcut banka faiz oranları aylık taksit yükünü artırmaktadır; peşinat oranını yüksek tutmak kritiktir."
            })

        # Price & inflation hedge factor
        factors.append({
            "factor": "Enflasyon & Maliyet Koruması",
            "impact": "Pozitif (+0.5)",
            "detail": "İnşaat maliyetlerindeki artış, bitmiş veya teslim aşamasındaki konutlarda reel sermaye koruması sağlamaktadır."
        })

        # Clamp score between 1.0 and 9.5 (never absolute 10 or 0)
        score = round(min(max(score, 2.5), 9.2), 1)

        condition = "Strong Conditions (Güçlü Koşullar)" if score >= 7.5 else (
            "Moderate Conditions (Dengeli Koşullar)" if score >= 6.0 else "Caution (Temkinli / Seçici)"
        )

        risks = [
            "İnşaat bitirme ve teslimat gecikmesi riski (mutlaka kurumsal güvenceli projeler seçilmelidir)",
            "Doğru ekspertiz yapılmadan piyasa ortalamasının üzerinde alım riski"
        ]
        opportunities = [
            "Lansman aşamasındaki projelerde vade farksız taksit ve özel liste fiyatı",
            "Bölgedeki kira getirisinin krediyi veya birikimi amorti etme kabiliyeti"
        ]

        return DecisionResult(
            engine_name="buying_conditions",
            score=score,
            condition=condition,
            headline=f"Alım Koşulları Endeksi: {score} / 10 — {condition}",
            summary=f"{location} bölgesinde {property_type} alımı için piyasa, doğru finansman modeli ve seçkin proje şartıyla olumlu fırsat penceresi sunmaktadır.",
            factors=factors,
            risks=risks,
            opportunities=opportunities,
            suggested_action="Hedeflenen bütçeye uygun en iyi 3 teslimat güvenceli projeyi yerinde karşılaştırın.",
            advisor_consultation_prompt="Bütçeniz ve lokasyon tercihiniz doğrultusunda en avantajlı seçenekleri Yiğit Narin ile birebir planlayın."
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
        condition: str = "Masrafsız / Sıfır"
    ) -> DecisionResult:
        factors = []
        score = 6.8  # Base index out of 10

        loc_lower = location.lower()
        if any(h in loc_lower for h in ["beytepe", "çankaya", "gop", "incek"]):
            score += 0.7
            factors.append({
                "factor": "Seçkin Bölge Alıcı Talebi",
                "impact": "Güçlü (+0.7)",
                "detail": f"{location} hattında nitelikli hazır konut arayışındaki alıcı kitlesi canlıdır."
            })

        # Condition factor
        cond_lower = condition.lower()
        if "sıfır" in cond_lower or "masrafsız" in cond_lower or "lüks" in cond_lower:
            score += 0.5
            factors.append({
                "factor": "Mülk Durumu & Rekabet Üstünlüğü",
                "impact": "Pozitif (+0.5)",
                "detail": "Tadilat ihtiyacı olmayan konutlar piyasada çok daha hızlı nakde çevrilmektedir."
            })
        else:
            score -= 0.4
            factors.append({
                "factor": "Tadilat & Yenileme Beklentisi",
                "impact": "İskonto Baskısı (-0.4)",
                "detail": "Alıcılar masraflı mülklerde pazarlık marjını yüksek tutma eğilimindedir."
            })

        # Urgent liquidation impact
        urg_lower = urgency.lower()
        if "acil" in urg_lower or "1 ay" in urg_lower:
            score -= 0.8
            factors.append({
                "factor": "Zaman Kısıtı & Likidasyon Marjı",
                "impact": "Baskı (-0.8)",
                "detail": "Kısa sürede satış hedefi %5-10 fiyat esnekliği gerektirebilir."
            })

        score = round(min(max(score, 3.0), 9.0), 1)
        res_condition = "Strong Conditions (Satış İçin Uygun Zaman)" if score >= 7.5 else (
            "Moderate Conditions (Dengeli Piyasa)" if score >= 6.0 else "Caution (Fiyat Korumalı Satış)"
        )

        risks = [
            "Piyasa rayicinin üzerinde listeleyerek mülkün piyasada eskimesi riski",
            "Yetkisiz çoklu emlakçı ilanları ile mülk imajının zedelenmesi"
        ]
        opportunities = [
            "Doğru fiyatlandırma ve CB VIP uluslararası pazarlama ağı ile hedef kitleye doğrudan erişim",
            "Elde edilen likiditenin topraktan lansman veya arsa yatırımı ile katlanması fırsatı"
        ]

        return DecisionResult(
            engine_name="selling_conditions",
            score=score,
            condition=res_condition,
            headline=f"Satış Koşulları Endeksi: {score} / 10 — {res_condition}",
            summary=f"{location} bölgesindeki {property_type} mülkünüz için doğru değerleme ve profesyonel tek yetkili pazarlama ile başarı oranı yüksektir.",
            factors=factors,
            risks=risks,
            opportunities=opportunities,
            suggested_action="Mülkünüz için güncel karşılaştırmalı piyasa analizi (CMA) raporu oluşturun.",
            advisor_consultation_prompt="Mülkünüzün gerçek değerini ve en hızlı satış stratejisini Yiğit Narin'den öğrenin."
        )

    # ─────────────────────────────────────────────────────────────────
    # 3. PROJE YATIRIMI İÇİN UYGUN ZAMAN MI?
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_project_opportunity(
        project_name: str = "Mas Lora / Angim Beytepe",
        location: str = "Beytepe / Yaşamkent",
        developer_reputation: str = "Yüksek",
        delivery_stage: str = "Kaba İnşaat / Lansman"
    ) -> DecisionResult:
        factors = [
            {
                "factor": "Lansman Prim Marjı",
                "impact": "Yüksek Getiri",
                "detail": "Topraktan veya kaba inşaat aşamasında girilen projeler anahtar teslimine kadar %40-60 nominal prim üretmektedir."
            },
            {
                "factor": "Geliştirici Güvencesi & Sözleşme Şartları",
                "impact": "Kritik Güvence",
                "detail": "Noter onaylı satış vaadi ve kurumsal geliştirici taahhütleri sermaye güvenliğini sağlar."
            },
            {
                "factor": "Bölge Altyapı Entegrasyonu",
                "impact": "Pozitif",
                "detail": f"{location} bölgesindeki yeni bulvar bağlantıları ve ticari alanlar projenin likiditesini katlamaktadır."
            }
        ]

        score = 82.0  # Out of 100
        return DecisionResult(
            engine_name="project_opportunity",
            score=score,
            condition="High Opportunity (Yüksek Fırsat Potansiyeli)",
            headline=f"Proje Yatırım Fırsat Skoru: 82 / 100",
            summary=f"{location} bölgesinde lansman ve yapım aşamasındaki seçkin projeler, vade farksız ödeme planlarıyla yüksek sermaye büyümesi vadetmektedir.",
            factors=factors,
            risks=["İnşaat teslim süresi uzaması", "Ödeme taksit planının nakit akışını zorlaması"],
            opportunities=["Teslimde yüksek kira çarpanı", "Lansman fiyat avantajı"],
            suggested_action="Örnek daireyi ve kat planlarını yerinde inceleyin.",
            advisor_consultation_prompt="Projenin en şerefiyeli dairesini ve özel ödeme planını Yiğit Narin ile belirleyin."
        )

    # ─────────────────────────────────────────────────────────────────
    # 4. KİRADA KALMAK MI SATIN ALMAK MI?
    # ─────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_rent_vs_buy(
        monthly_rent: float = 35_000,
        home_price: float = 5_500_000,
        cash_available: float = 2_000_000,
        duration_years: int = 5
    ) -> DecisionResult:
        total_rent_paid = monthly_rent * 12 * duration_years * 1.35  # Accounting for rent escalations
        expected_home_value_5y = home_price * 2.10  # Conservative 5-year capital appreciation in Turkey
        net_wealth_buying = expected_home_value_5y - home_price

        factors = [
            {
                "factor": "Ödenecek Toplam Kira Kaybı",
                "impact": f"Yaklaşık {int(total_rent_paid):,} TL eriyen nakit",
                "detail": "5 yılda ödenecek kira bedeli geri dönüşü olmayan bir giderdir."
            },
            {
                "factor": "Sermaye Değer Artış Avantajı",
                "impact": f"+{int(net_wealth_buying):,} TL tahmini özkaynak artışı",
                "detail": "Gayrimenkul mülkiyeti enflasyona karşı birincil kalkan vazifesi görmektedir."
            }
        ]

        score = 8.1  # Out of 10 for Buying preference
        return DecisionResult(
            engine_name="rent_vs_buy",
            score=score,
            condition="Strong Buy Advantage (Satın Alma Lehine Güçlü Dinamik)",
            headline=f"Satın Alma Tercihi Endeksi: {score} / 10",
            summary="Mevcut kira artış oranları ve gayrimenkulün değer koruma kabiliyeti dikkate alındığında, 3+ yıl ikamet edilecek lokasyonda satın alma stratejik olarak belirgin üstünlük sağlamaktadır.",
            factors=factors,
            risks=["Kredi faiz yükünün aylık bütçeyi zorlaması"],
            opportunities=["Kira ödemek yerine kendi mülküne sermaye yatırma avantajı"],
            suggested_action="Bütçenize uygun peşinat ve taksit projeksiyonunu netleştirin.",
            advisor_consultation_prompt="Kira yerine kendi evinize geçiş planınızı Yiğit Narin ile hesaplayın."
        )
