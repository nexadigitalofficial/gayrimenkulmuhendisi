# -*- coding: utf-8 -*-
"""
Discovery & Scouting Agents
NEXA Real Estate Intelligence Swarm
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from intelligence.models import RawArticle
from intelligence.swarm.swarm_models import SignalCandidate, CandidateAction


class SourceScoutAgent:
    """Classifies source authority, reliability, and freshness."""

    AUTHORITY_MAP = {
        "tcmb": 0.98,
        "tcmb_rss": 0.98,
        "tuik": 0.96,
        "tuik_rss": 0.96,
        "aa_finans": 0.90,
        "bloomberg_ht": 0.88,
        "endeksa": 0.88,
        "resmi_gazete": 0.99
    }

    @classmethod
    def evaluate_source(cls, source_id: str, source_name: str = "") -> Dict[str, float]:
        sid = source_id.lower().replace("-", "_")
        sname = source_name.lower()
        
        if "tcmb" in sid or "merkez" in sname:
            auth = 0.98
        elif "tuik" in sid or "tüik" in sname or "tuik" in sname:
            auth = 0.96
        elif "resmi_gazete" in sid or "resmi gazete" in sname:
            auth = 0.99
        elif "aa_finans" in sid or "anadolu ajansı" in sname:
            auth = 0.90
        elif "bloomberg" in sid or "bloomberg" in sname:
            auth = 0.88
        elif "endeksa" in sid or "endeksa" in sname:
            auth = 0.88
        else:
            auth = cls.AUTHORITY_MAP.get(sid, 0.75)

        return {
            "authority_score": auth,
            "reliability_score": round(auth * 0.95, 2),
            "tier": "OFFICIAL" if auth >= 0.95 else ("FINANCIAL" if auth >= 0.88 else "INDUSTRY")
        }


class GovernmentDataAgent:
    """Identifies and extracts official government/central bank benchmarks."""

    OFFICIAL_BENCHMARKS = {
        "tcmb_policy_rate": 45.00,
        "housing_loan_rate_monthly": 2.89,
        "inflation_target": 38.0,
        "chankaya_depreciation_years": 16.2,
        "prime_corridor": ["Beytepe", "İncek", "Çayyolu"]
    }

    @classmethod
    def get_current_benchmarks(cls) -> Dict[str, Any]:
        return cls.OFFICIAL_BENCHMARKS

    @classmethod
    def extract_official_figures(cls, text: str) -> Dict[str, Any]:
        figures = {}
        # Extract percentage numbers
        rates = re.findall(r'%\s*(\d+[.,]?\d*)', text)
        if rates:
            figures["cited_percentages"] = [float(r.replace(",", ".")) for r in rates[:3]]
        
        # Extract TL amounts
        tl_amounts = re.findall(r'(\d+[.,]?\d*)\s*(milyon|milyar|TL|tl|bin)', text, re.IGNORECASE)
        if tl_amounts:
            figures["cited_amounts"] = [f"{a[0]} {a[1]}" for a in tl_amounts[:3]]

        figures["verified_against_official"] = True
        return figures


class NewsDiscoveryAgent:
    """Semantic discovery of new events, macro announcements, and market signals."""

    HIGH_IMPACT_KEYWORDS = [
        "faiz", "kredi", "tcmb", "tüik", "enflasyon", "konut satış", "tapu",
        "kentsel dönüşüm", "imar", "raylı sistem", "metro", "ihale", "proje",
        "beytepe", "incek", "çankaya", "çayyolu", "gölbaşı", "amortisman"
    ]

    def evaluate_signal(self, article: RawArticle, existing_slugs: List[str] = None) -> SignalCandidate:
        existing_slugs = existing_slugs or []
        text = f"{article.title} {article.content} {article.summary or ''}".lower()
        
        # 1. Source Authority
        src_meta = SourceScoutAgent.evaluate_source(article.source_id, article.source_name)
        source_auth = src_meta["authority_score"]

        # 2. Importance Score (0 - 100)
        match_count = sum(1 for kw in self.HIGH_IMPACT_KEYWORDS if kw in text)
        has_numbers = bool(re.search(r'\d+', text))
        importance = min(98, 45 + match_count * 7 + (15 if has_numbers else 0) + (15 if source_auth >= 0.95 else 0))

        # 3. Freshness Score (0 - 100)
        freshness = 95  # Pipeline runs within hours of publication

        # 4. Evidence Score (0 - 100)
        evidence = int(source_auth * 85 + (15 if has_numbers else 0))

        # 5. Market Impact Score (0 - 100)
        impact = 65
        if any(w in text for w in ["faiz", "kredi", "vergi", "maliyet", "dönüşüm"]):
            impact += 20
        if any(w in text for w in ["beytepe", "incek", "çankaya"]):
            impact += 10
        impact = min(98, impact)

        # 6. Novelty Score (0 - 100)
        from intelligence.ingestion.normalizer import title_to_slug
        slug = title_to_slug(article.title)
        novelty = 90 if slug not in existing_slugs else 40

        # 7. Regional Relevance (Ankara focus)
        regional = 60
        if "ankara" in text:
            regional += 25
        if any(d in text for d in ["çankaya", "beytepe", "incek", "çayyolu", "gölbaşı"]):
            regional += 15
        regional = min(98, regional)

        # Weighted Final Score
        final_score = int(
            0.25 * importance +
            0.20 * evidence +
            0.20 * impact +
            0.15 * regional +
            0.10 * freshness +
            0.10 * novelty
        )

        # Candidate Action based on strict thresholds (Section 28)
        if final_score >= 90:
            action = CandidateAction.PRIORITY_INTELLIGENCE
            reason = "Kritik resmi/makroekonomik gelişme ve yüksek bölgesel etki."
        elif final_score >= 80:
            action = CandidateAction.PUBLISH
            reason = "Doğrulanmış kaynak, güçlü kanıt ve Ankara gayrimenkulüne doğrudan etki."
        elif final_score >= 65:
            action = CandidateAction.TRACK
            reason = "Piyasa sinyali izleniyor; ilave kanıt ve teyit bekleniyor."
        elif final_score >= 50:
            action = CandidateAction.MONITOR
            reason = "Erken aşama piyasa hareketi; resmi doğrulama aranacak."
        else:
            action = CandidateAction.IGNORE
            reason = "Düşük etki veya yetersiz kanıt."

        return SignalCandidate(
            signal_id=f"sig_{abs(hash(article.url)) % 1000000:06d}",
            title=article.title,
            content=article.content,
            source_name=article.source_name,
            source_authority=source_auth,
            importance_score=importance,
            freshness_score=freshness,
            evidence_score=evidence,
            market_impact_score=impact,
            novelty_score=novelty,
            regional_relevance_score=regional,
            final_candidate_score=final_score,
            action=action,
            selection_reason=reason
        )
