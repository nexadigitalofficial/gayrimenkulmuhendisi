"""
Explainable Multi-Audience Impact Engine.
Calculates transparent 0-100 scores for Buyers, Sellers, Investors, and Developers.
"""

from typing import Dict, Any, List
from intelligence.models import ImpactScore, MarketDirection, TopicEntity, RegionEntity


class ImpactEngine:
    """Calculates multi-dimensional impact scores with clear explainability."""

    def evaluate_impacts(
        self,
        title: str,
        content: str,
        topics: List[TopicEntity],
        locations: List[RegionEntity],
        ai_data: Dict[str, Any] = None
    ) -> ImpactScore:
        text = f"{title} {content}".lower()
        ai_data = ai_data or {}

        # If AI provided scores and valid rationales, use as base
        b_score = ai_data.get("buyer_score")
        s_score = ai_data.get("seller_score")
        i_score = ai_data.get("investor_score")
        d_score = ai_data.get("developer_score")

        topic_names = [t.name for t in topics]

        # 1. Buyer Scoring logic
        if b_score is None:
            b_score = 65
            if "kredi" in topic_names or "faiz" in topic_names:
                b_score = 80 if ("indirim" in text or "düşüş" in text or "fırsat" in text) else 45
            elif "ulaşım" in topic_names or "proje" in topic_names:
                b_score = 75
        b_rationale = ai_data.get("buyer_rationale") or self._generate_buyer_rationale(text, b_score, topic_names)

        # 2. Seller Scoring logic
        if s_score is None:
            s_score = 60
            if "talep" in text or "artış" in text or "prim" in text:
                s_score = 78
            elif "arz" in text or "yavaşlama" in text:
                s_score = 48
        s_rationale = ai_data.get("seller_rationale") or self._generate_seller_rationale(text, s_score, topic_names)

        # 3. Investor Scoring logic
        if i_score is None:
            i_score = 70
            if "kira" in topic_names or "amortisman" in text or "arsa" in topic_names:
                i_score = 88
            elif "enflasyon" in text or "değerleme" in text:
                i_score = 82
        i_rationale = ai_data.get("investor_rationale") or self._generate_investor_rationale(text, i_score, topic_names)

        # 4. Developer Scoring logic
        if d_score is None:
            d_score = 55
            if "kentsel dönüşüm" in topic_names or "maliyet" in text:
                d_score = 74
        d_rationale = ai_data.get("developer_rationale") or self._generate_developer_rationale(text, d_score, topic_names)

        # Trends
        price_trend = MarketDirection.UP if ("artış" in text or "yüksel" in text or "prim" in text) else MarketDirection.NEUTRAL
        rent_trend = MarketDirection.UP if ("kira" in text and ("artış" in text or "getiri" in text)) else MarketDirection.NEUTRAL
        credit_cond = MarketDirection.DOWN if ("yüksek faiz" in text or "sıkılaşma" in text) else MarketDirection.NEUTRAL

        return ImpactScore(
            buyer_score=min(max(int(b_score), 0), 100),
            buyer_rationale=b_rationale,
            seller_score=min(max(int(s_score), 0), 100),
            seller_rationale=s_rationale,
            investor_score=min(max(int(i_score), 0), 100),
            investor_rationale=i_rationale,
            developer_score=min(max(int(d_score), 0), 100),
            developer_rationale=d_rationale,
            price_trend=price_trend,
            rent_trend=rent_trend,
            credit_conditions=credit_cond
        )

    def _generate_buyer_rationale(self, text: str, score: int, topics: List[str]) -> str:
        if score >= 75:
            return "Nakit ve peşin alımlarda lansman iskontoları ve vadeli proje seçenekleri avantaj sunuyor."
        elif score <= 50:
            return "Mevcut kredi faiz maliyetleri nedeniyle doğrudan geliştirici taksitli seçenekler önceliklendirilmeli."
        return "Piyasa dengelenme sürecinde doğru lokasyon ve teslim garantili projeler tercih edilmelidir."

    def _generate_seller_rationale(self, text: str, score: int, topics: List[str]) -> str:
        if score >= 75:
            return "Bölgedeki güçlü alıcı ilgisi ve arz kısıtı, mülkün gerçek piyasa değerinde hızlı satışını destekliyor."
        return "Fiyatlamada gerçekçi ekspertiz ve kurumsal pazarlama alıcı karar sürecini hızlandıracaktır."

    def _generate_investor_rationale(self, text: str, score: int, topics: List[str]) -> str:
        if score >= 80:
            return "Yüksek kira çarpanı ve altyapı gelişim potansiyeli orta/uzun vadeli reel sermaye büyümesi sağlıyor."
        return "Enflasyona karşı koruma sağlayan seçkin lokasyonlardaki taşınmazlar düzenli getiri vadediyor."

    def _generate_developer_rationale(self, text: str, score: int, topics: List[str]) -> str:
        if score >= 70:
            return "Kentsel dönüşüm teşvikleri ve yeni imar hatları proje geliştirme marjlarını destekliyor."
        return "İnşaat maliyet endeksi ve arz dengesi yakından izlenerek aşamalı lansman kurgulanmalı."
