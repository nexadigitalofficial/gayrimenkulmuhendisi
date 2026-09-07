# -*- coding: utf-8 -*-
"""
Critical Thinking, Contrarian & Trend Detection Agents
NEXA Real Estate Intelligence Swarm
"""

from typing import Dict, Any, List
from intelligence.swarm.swarm_models import ContrarianAnalysis, EmergingTrend


class ContrarianAgent:
    """Confirmation bias destroyer. Formulates counter-hypotheses and downside stress tests."""

    CONTRARIAN_SCENARIOS = {
        "faiz_indirimi": {
            "counter": "Faiz indirimleri beklendiği kadar hızlı başlamaz veya mevduat faizleri yüksek kalmaya devam ederse nakit akışı gayrimenkule dönmekte gecikebilir.",
            "indicators": ["Enflasyon katılığının sürmesi", "Merkez bankalarının temkinli duruşu"],
            "risks": ["Finansman maliyetinin uzun süre yüksek kalması", "İkinci el likiditesinde yavaşlama"]
        },
        "fiyat_artisi": {
            "counter": "Nominal fiyat artışları enflasyondan arındırıldığında reel bazda getiri sağlamayabilir; seçici bölge analizi şarttır.",
            "indicators": ["Alım gücünün baskılanması", "Kredi hacmindeki daralma"],
            "risks": ["Emsal üstü aşırı fiyatlama sonucu uzun satış süreleri", "Kira çarpanının bozulması"]
        },
        "ulasim_projesi": {
            "counter": "Altyapı ve raylı sistem projelerinde ihale ve inşaat süreçleri hedeflenen süreden 1-2 yıl daha uzun sürebilir; prim beklentisi erken fiyatlanmış olabilir.",
            "indicators": ["Belediye bütçe kısıtları", "Kamulaştırma itirazları"],
            "risks": ["Kısa vadede inşaat tozu/gürültü baskısı", "Spekülatif köpük oluşumu"]
        },
        "general": {
            "counter": "Piyasadaki iyimser senaryolar makroekonomik dalgalanmalar ve alternatif finansal araçların getirileri karşısında test edilecektir.",
            "indicators": ["Alternatif sabit getirili enstrümanların cazibesi", "Seçici alıcı davranışı"],
            "risks": ["Likidite sıkışıklığı", "Zamanlama hatası"]
        }
    }

    def stress_test(self, title: str, content: str) -> ContrarianAnalysis:
        text = f"{title} {content}".lower()

        if any(w in text for w in ["faiz", "kredi", "gevşeme", "indirim"]):
            scenario = self.CONTRARIAN_SCENARIOS["faiz_indirimi"]
        elif any(w in text for w in ["fiyat", "rekor", "prim", "artış"]):
            scenario = self.CONTRARIAN_SCENARIOS["fiyat_artisi"]
        elif any(w in text for w in ["metro", "raylı", "ulaşım", "otoyol"]):
            scenario = self.CONTRARIAN_SCENARIOS["ulasim_projesi"]
        else:
            scenario = self.CONTRARIAN_SCENARIOS["general"]

        return ContrarianAnalysis(
            counter_hypothesis=scenario["counter"],
            contrary_indicators=scenario["indicators"],
            downside_risks=scenario["risks"],
            confidence_discount=0.05,
            verdict="Piyasa fırsatı mevcut olmakla birlikte, kontra göstergeler ve likidite zamanlaması mutlaka göz önünde bulundurulmalıdır."
        )


class TrendDetectionAgent:
    """Monitors topic velocity and detects multi-day emerging trends."""

    @staticmethod
    def evaluate_trend(topic: str, region: str, occurrence_count: int = 1) -> EmergingTrend:
        velocity = 1.0 + (occurrence_count - 1) * 0.4
        
        if occurrence_count >= 3:
            summary = f"{region} bölgesinde {topic} konusunda son 14 günde yoğunlaşan güçlü bir piyasa trendi tespit edildi."
        else:
            summary = f"{topic} başlığında yeni bir sinyal izleniyor."

        return EmergingTrend(
            trend_id=f"tr_{abs(hash(topic + region)) % 100000:05d}",
            topic=topic,
            region=region,
            period_days=14,
            velocity=round(velocity, 2),
            signal_count=occurrence_count,
            summary=summary
        )

    @classmethod
    def detect_emerging_trends(cls, articles_or_items: List[Dict[str, Any]]) -> List[EmergingTrend]:
        """Scans articles, groups by topic/region, calculates velocity and returns active trends."""
        from collections import Counter
        counts = Counter()
        for it in articles_or_items:
            title = it.get("title", "")
            content = it.get("content", "")
            text = f"{title} {content}".lower()

            region = "Ankara"
            for r in ["Beytepe", "İncek", "Çayyolu", "Çankaya", "Gölbaşı"]:
                if r.lower() in text:
                    region = r
                    break

            topic = "Konut Piyasası"
            if "arsa" in text or "tarla" in text or "parsel" in text:
                topic = "Arsa & Arazi Gelişimi"
            elif "villa" in text or "müstakil" in text:
                topic = "Lüks Villa Talebi"
            elif "faiz" in text or "kredi" in text or "finans" in text:
                topic = "Finansman & Faiz Eğilimi"
            elif "kira" in text:
                topic = "Kira Getiri Hacmi"

            counts[(topic, region)] += 1

        trends = []
        for (topic, region), count in counts.items():
            trends.append(cls.evaluate_trend(topic, region, occurrence_count=count))

        trends.sort(key=lambda tr: tr.velocity, reverse=True)
        return trends
