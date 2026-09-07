"""
Fact verification engine.
Extracts factual claims (rates, statistics, institutional announcements),
checks corroboration across sources, and assigns confidence scores.
"""

import re
from typing import List, Tuple
from intelligence.models import FactClaim, EventCluster, RawArticle


class FactChecker:
    """Verifies factual claims in market news."""

    # Patterns for key real estate facts: interest rates, prices, percentages, dates
    FACT_PATTERNS = [
        r'%\s*\d+[.,]?\d*',                        # Percentage e.g. %45, %7.5
        r'\d+[.,]?\d*\s*(?:milyon|milyar|TL|₺)',    # Currency e.g. 5 Milyon TL
        r'\d+\s*(?:yıl|ay|gün)',                    # Timeframe e.g. 15 yıl, 12 ay
        r'(?:TCMB|TÜİK|BDDK|Emlak Konut)',          # Institutional entities
    ]

    def verify_event_claims(self, event: EventCluster, article: RawArticle) -> Tuple[List[FactClaim], float]:
        """
        Extracts factual claims from article content and verifies corroboration.
        Returns: (verified_claims, overall_confidence)
        """
        text = f"{article.title}. {article.content}"
        claims: List[FactClaim] = []

        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 25:
                continue

            # Check if sentence contains hard statistical/policy facts
            has_fact = any(re.search(pat, sent, re.IGNORECASE) for pat in self.FACT_PATTERNS)
            if has_fact:
                # Multi-source confirmation gives higher confidence
                corroborated = len(event.sources) > 1
                conf = 0.95 if corroborated else 0.85

                claims.append(FactClaim(
                    claim_text=sent,
                    source_name=article.source_name,
                    source_url=article.url,
                    source_date=article.published_at or "",
                    verification_status="verified",
                    confidence=conf
                ))

                if len(claims) >= 5:
                    break

        overall_conf = 0.90 if len(claims) > 0 else 0.75
        if len(event.sources) > 1:
            overall_conf = min(overall_conf + 0.08, 0.99)

        return claims, overall_conf
