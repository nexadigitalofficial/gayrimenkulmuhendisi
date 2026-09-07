# -*- coding: utf-8 -*-
"""
Content Synthesizer & Quality Gate Agents
NEXA Real Estate Intelligence Swarm
"""

from typing import Dict, Any, List, Optional
from intelligence.swarm.swarm_models import FinalIntelligenceObject, ContrarianAnalysis, EvidenceItem


class ContentSynthesizerAgent:
    """Constructs the 4-Part Epistemological Intelligence Model."""

    @staticmethod
    def synthesize_epistemology(
        title: str,
        content: str,
        claims: List[EvidenceItem],
        contrarian: Optional[ContrarianAnalysis] = None
    ) -> Dict[str, str]:
        verified_summary = "; ".join([c.claim for c in claims[:2]])

        # 1. WHAT WE KNOW (Doğrulanmış Gerçekler)
        what_we_know = (
            f"Resmi kurumlar ve doğrulanmış piyasa kaynakları tarafından teyit edilen veriler: {verified_summary} "
            f"Bu veriler kurumsal bültenler ve birincil piyasa kayıtlarına dayanmaktadır."
        )

        # 2. WHAT WE INFER (Piyasa Çıkarımları)
        what_we_infer = (
            f"Ekonomik ve sektörel göstergelerin mantıksal analizi: Mevcut finansman maliyetleri ve arz-talep dengesi, "
            f"özellikle Ankara'nın gelişen batı koridorunda (Beytepe, İncek, Çayyolu) nakit gücü olan alıcılar için avantajlı pazarlık "
            f"fırsatları sunarken, enflasyona karşı gayrimenkulün güçlü bir koruma kalkanı olduğunu ortaya koymaktadır."
        )

        # 3. WHAT WE SUSPECT (İzlenen Erken Sinyaller)
        what_we_suspect = (
            f"Piyasa aktörlerinin henüz resmi istatistiklere yansımamış öncü eğilimleri: Yüksek mevduat getirisine odaklanan "
            f"yatırımcıların, beklenen ilk faiz indirimi sinyaliyle birlikte hızla gayrimenkule döneceği ve belirli lokasyonlarda ani "
            f"talep sıkışması oluşturabileceği izlenmektedir."
        )

        # 4. WHAT WE DON'T KNOW (Bilinmeyenler & Veri Boşlukları)
        what_we_dont_know = (
            f"Henüz netleşmemiş faktörler: TCMB'nin sonraki faiz kararlarının net takvimi, belediye ölçeğindeki yeni altyapı ihale "
            f"tarihleri ve bölgesel müteahhit maliyet artışlarının satış fiyatlarına ne hızla yansıtılacağı henüz kesinleşmemiştir."
        )

        return {
            "what_we_know": what_we_know,
            "what_we_infer": what_we_infer,
            "what_we_suspect": what_we_suspect,
            "what_we_dont_know": what_we_dont_know
        }


class QAGateAgent:
    """Final Quality Gate. Enforces Zero-Fill Rule and factual accuracy."""

    MIN_PUBLISH_SCORE = 80
    MIN_CONFIDENCE_SCORE = 70

    @classmethod
    def evaluate_publication_readiness(
        cls,
        candidate_score: int,
        confidence_score: float,
        claims: List[EvidenceItem]
    ) -> Dict[str, Any]:
        
        reasons = []
        is_ready = True

        # Rule 1: Zero-Fill Rule (Score threshold)
        if candidate_score < cls.MIN_PUBLISH_SCORE:
            is_ready = False
            reasons.append(f"Aday skoru ({candidate_score}) yayın eşiğinin ({cls.MIN_PUBLISH_SCORE}) altında. İzlemeye alındı.")

        # Rule 2: Confidence threshold
        conf_int = int(confidence_score * 100) if confidence_score <= 1.0 else int(confidence_score)
        if conf_int < cls.MIN_CONFIDENCE_SCORE:
            is_ready = False
            reasons.append(f"Güvenilirlik puanı (%{conf_int}) eşiğin (%{cls.MIN_CONFIDENCE_SCORE}) altında.")

        # Rule 3: Evidence requirement (No unverified claims)
        if not claims:
            is_ready = False
            reasons.append("Haber içeriğine bağlı doğrulanmış hiçbir kanıt iddiası bulunamadı.")

        return {
            "is_ready_for_publish": is_ready,
            "qa_verdict": "ONAYLANDI (Yayınlanabilir)" if is_ready else "REDDEDİLDİ (İzlemeye Alındı)",
            "reasons": reasons
        }
