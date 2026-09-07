# -*- coding: utf-8 -*-
"""
Domain & Regional Specialist Agents
NEXA Real Estate Intelligence Swarm
"""

from typing import Dict, Any, List


class FinanceAgent:
    """Specialist on monetary policy, mortgage terms, deposit yields, and financing costs."""

    @staticmethod
    def analyze_financing(text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        has_rate_cut = any(w in text_lower for w in ["indirim", "gevşeme", "düşüş", "ucuz"])
        has_tightening = any(w in text_lower for w in ["sıkı", "artış", "yüksek", "tavan"])

        if has_rate_cut:
            buyer_sentiment = "Fırsat Penceresi (Ertelenen talep piyasaya dönebilir)"
            mortgage_cost_outlook = "Aşağı yönlü baskı; refinansman imkanı"
        elif has_tightening:
            buyer_sentiment = "Nakit Ağırlıklı (Kredi yerine takas veya vadeli alım)"
            mortgage_cost_outlook = "Yüksek borçlanma maliyeti; özkaynak önceliği"
        else:
            buyer_sentiment = "Stabil / Seçici Yaklaşım"
            mortgage_cost_outlook = "Mevcut seviyelerde yatay seyir"

        return {
            "buyer_sentiment": buyer_sentiment,
            "mortgage_cost_outlook": mortgage_cost_outlook,
            "capital_preservation_index": 88
        }


class EntityResolutionAgent:
    """Normalizes locations, neighborhoods, and projects into hierarchical entity nodes."""

    LOCATION_HIERARCHY = {
        "beytepe": {"city": "Ankara", "district": "Çankaya", "neighborhood": "Beytepe", "segment": "Lüks Rezidans"},
        "incek": {"city": "Ankara", "district": "Gölbaşı", "neighborhood": "İncek", "segment": "Villa & Müstakil"},
        "çayyolu": {"city": "Ankara", "district": "Çankaya", "neighborhood": "Çayyolu", "segment": "Aile & Prestij"},
        "alacaatlı": {"city": "Ankara", "district": "Çankaya", "neighborhood": "Alacaatlı", "segment": "Prestij Konut"},
        "gölbaşı": {"city": "Ankara", "district": "Gölbaşı", "neighborhood": "Gölbaşı Merkez", "segment": "Arsa & Villa"},
        "çankaya": {"city": "Ankara", "district": "Çankaya", "neighborhood": "Çankaya Merkez", "segment": "Diplomatik & Dönüşüm"}
    }

    @classmethod
    def resolve_entities(cls, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        matched = []
        for key, entity in cls.LOCATION_HIERARCHY.items():
            if key in text_lower:
                matched.append(entity)

        if not matched:
            matched.append({"city": "Ankara", "district": "Ankara Geneli", "neighborhood": "Genel", "segment": "Karma"})

        return {
            "primary_entity": matched[0],
            "all_entities": matched
        }


class AnkaraAgent:
    """Micro-level intelligence specialist for Ankara metropolitan prime districts."""

    DISTRICT_METRICS = {
        "Beytepe": {"depreciation_years": 16.8, "annual_growth": "+%68", "liquidity": "Yüksek", "target_audience": "Rezidans / Genç Profesyonel / Bürokrat"},
        "İncek": {"depreciation_years": 17.4, "annual_growth": "+%62", "liquidity": "Orta-Yüksek", "target_audience": "Büyükelçilik / Aile / Müstakil Yaşam"},
        "Çayyolu": {"depreciation_years": 15.9, "annual_growth": "+%58", "liquidity": "Çok Yüksek", "target_audience": "Köklü Aile / Doktor / Akademisyen"},
        "Çankaya": {"depreciation_years": 15.2, "annual_growth": "+%55", "liquidity": "Kesintisiz", "target_audience": "Diplomatik / Dönüşüm / Yatırım"},
        "Gölbaşı": {"depreciation_years": 18.5, "annual_growth": "+%78", "liquidity": "Orta", "target_audience": "Arsa Yatırımcısı / Villa Geliştirici"}
    }

    @classmethod
    def evaluate_district(cls, district_name: str) -> Dict[str, Any]:
        for d_key, metrics in cls.DISTRICT_METRICS.items():
            if d_key.lower() in district_name.lower():
                return {"district": d_key, **metrics}
        return {"district": "Ankara Geneli", "depreciation_years": 16.5, "annual_growth": "+%60", "liquidity": "Normal", "target_audience": "Genel"}


class InfrastructureZoningAgent:
    """Specialist analyzing roads, transit lines, zoning plans, and urban renewal."""

    @staticmethod
    def analyze_infrastructure(text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        has_transit = any(w in text_lower for w in ["metro", "raylı", "ulaşım", "otoyol", "bulvar", "istasyon"])
        has_zoning = any(w in text_lower for w in ["imar", "parsel", "plan", "emsal", "kat irtifakı", "ruhsat"])

        multiplier = 1.0
        if has_transit:
            multiplier += 0.25
        if has_zoning:
            multiplier += 0.15

        return {
            "has_transit_impact": has_transit,
            "has_zoning_impact": has_zoning,
            "estimated_prime_multiplier": round(multiplier, 2)
        }


class ProjectIntelligenceAgent:
    """Specialist inspecting residential projects, launches, stages, and developer integrity."""

    @staticmethod
    def evaluate_project_context(text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        is_launch = "lansman" in text_lower or "ön talep" in text_lower
        is_turnkey = "hemen teslim" in text_lower or "iskan" in text_lower

        return {
            "stage": "Lansman" if is_launch else ("Hemen Teslim" if is_turnkey else "Yapım Aşaması"),
            "bargain_margin": "Yüksek (Nakit iskontosu var)" if is_launch else "Dengeli",
            "developer_risk": "Düşük (CB VIP denetimli)"
        }


class RentalMarketAgent:
    """Specialist analyzing rent dynamics, yields, occupancy rates, and tenant demand."""

    @staticmethod
    def evaluate_rental_state(text: str) -> Dict[str, Any]:
        return {
            "gross_yield_range": "%6.5 - %7.8",
            "occupancy_rate": "%98.2 (Çankaya - Beytepe Aksı)",
            "demand_strength": "Güçlü (Memur, diplomat ve üniversite rotasyonu)",
            "rent_increase_trend": "Enflasyonla paralel dengeli artış"
        }
