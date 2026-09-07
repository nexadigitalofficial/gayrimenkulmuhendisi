# -*- coding: utf-8 -*-
"""
Intelligence Director - The Central Brain of the Swarm
NEXA Real Estate Intelligence Swarm
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from intelligence.models import RawArticle
from intelligence.swarm.swarm_models import (
    ResearchTask, SignalCandidate, CandidateAction, FinalIntelligenceObject
)
from intelligence.swarm.scouts import NewsDiscoveryAgent, SourceScoutAgent
from intelligence.swarm.specialists import FinanceAgent, AnkaraAgent, EntityResolutionAgent
from intelligence.swarm.critical_thinking import ContrarianAgent, TrendDetectionAgent
from intelligence.swarm.verification import FactCheckerAgent, EvidenceGraphBuilder
from intelligence.swarm.synthesizer import ContentSynthesizerAgent, QAGateAgent
from intelligence.ingestion.normalizer import title_to_slug


class IntelligenceDirector:
    """The central brain orchestrating research cycles, priority queue, and multi-agent synthesis."""

    def __init__(self):
        self.discovery_agent = NewsDiscoveryAgent()
        self.contrarian_agent = ContrarianAgent()
        self.qa_gate = QAGateAgent()
        self.research_queue: List[ResearchTask] = []

    def plan_daily_research(self, raw_articles: List[RawArticle]) -> List[ResearchTask]:
        """Examines the world, identifies signals, and forms the Research Priority Queue."""
        self.research_queue = []
        
        # Formulate core investigative questions for today
        topics_seen = set()
        for idx, art in enumerate(raw_articles, 1):
            cand = self.discovery_agent.evaluate_signal(art)
            if cand.action in [CandidateAction.PUBLISH, CandidateAction.PRIORITY_INTELLIGENCE, CandidateAction.TRACK]:
                entities = EntityResolutionAgent.resolve_entities(art.title + " " + art.content)
                primary_region = entities["primary_entity"]["neighborhood"]
                
                # Determine investigative questions
                questions = [
                    f"Bu gelişmenin birincil ve bağımsız kaynakları teyit edildi mi?",
                    f"{primary_region} bölgesindeki konut ve arsa fiyatlarına doğrudan etkisi nedir?",
                    f"Mevcut faiz ve finansman ortamında alıcı ve satıcı dengesini nasıl değiştirir?",
                    f"Bu analizin aksini gösteren karşıt piyasa göstergeleri (contrarian) nelerdir?"
                ]

                task = ResearchTask(
                    task_id=f"task_{idx:03d}_{cand.signal_id}",
                    priority=cand.final_candidate_score,
                    topic=entities["primary_entity"]["segment"],
                    region=primary_region,
                    key_questions=questions,
                    assigned_agents=[
                        "NewsDiscoveryAgent",
                        "SourceScoutAgent",
                        "FinanceAgent",
                        "AnkaraAgent",
                        "ContrarianAgent",
                        "FactCheckerAgent",
                        "ContentSynthesizerAgent"
                    ],
                    status="QUEUED"
                )
                self.research_queue.append(task)

        # Sort priority queue descending
        self.research_queue.sort(key=lambda t: t.priority, reverse=True)
        return self.research_queue

    def execute_swarm_investigation(self, raw_articles: List[RawArticle]) -> Dict[str, Any]:
        """Runs the multi-agent investigation across all candidates and produces verified intelligence."""
        # 1. Plan Research Queue
        self.plan_daily_research(raw_articles)

        scanned_count = len(raw_articles)
        evaluated_candidates: List[SignalCandidate] = []
        published_intelligence: List[FinalIntelligenceObject] = []
        monitored_signals: List[Dict[str, Any]] = []

        for art in raw_articles:
            cand = self.discovery_agent.evaluate_signal(art)
            evaluated_candidates.append(cand)

            # Extract and verify factual claims
            claims = FactCheckerAgent.extract_and_verify_claims(
                title=art.title,
                content=art.content,
                source_id=art.source_id,
                source_name=art.source_name,
                source_url=art.url
            )
            evidence_graph = EvidenceGraphBuilder.build_graph(claims)

            # Contrarian stress-test
            contrarian = self.contrarian_agent.stress_test(art.title, art.content)

            # Entity resolution
            entities = EntityResolutionAgent.resolve_entities(art.title + " " + art.content)
            region_name = entities["primary_entity"]["neighborhood"]
            district_meta = AnkaraAgent.evaluate_district(region_name)

            # Finance context
            finance_meta = FinanceAgent.analyze_financing(art.content)

            # Epistemological synthesis
            epistemic = ContentSynthesizerAgent.synthesize_epistemology(
                title=art.title,
                content=art.content,
                claims=claims,
                contrarian=contrarian
            )

            # QA Gate: Zero-Fill Rule check
            qa_res = self.qa_gate.evaluate_publication_readiness(
                candidate_score=cand.final_candidate_score,
                confidence_score=evidence_graph["overall_authority_score"],
                claims=claims
            )

            slug = title_to_slug(art.title)

            # 4-way impact calculations
            b_score = min(95, max(40, cand.market_impact_score + 5))
            s_score = min(90, max(45, cand.market_impact_score - 8))
            i_score = min(98, max(50, cand.importance_score + 3))
            d_score = min(88, max(40, cand.market_impact_score - 12))

            intelligence_obj = FinalIntelligenceObject(
                id=f"intel_{abs(hash(slug)) % 1000000:06d}",
                title=art.title,
                slug=slug,
                category=entities["primary_entity"]["segment"],
                importance=cand.importance_score,
                confidence=int(evidence_graph["overall_authority_score"] * 100),
                freshness=cand.freshness_score,
                global_impact=cand.market_impact_score,
                regional_impact=cand.regional_relevance_score,
                buyer_impact=b_score,
                seller_impact=s_score,
                investor_impact=i_score,
                developer_impact=d_score,
                risk_score=38,
                opportunity_score=82,
                locations=[region_name, "Ankara"],
                topics=[cand.selection_reason, entities["primary_entity"]["segment"]],
                sources=[{
                    "source_id": art.source_id,
                    "source_name": art.source_name,
                    "url": art.url,
                    "authority": cand.source_authority
                }],
                claims=claims,
                what_we_know=epistemic["what_we_know"],
                what_we_infer=epistemic["what_we_infer"],
                what_we_suspect=epistemic["what_we_suspect"],
                what_we_dont_know=epistemic["what_we_dont_know"],
                contrarian_view=contrarian,
                why_this_news={
                    "importance_score": cand.importance_score,
                    "evidence_score": cand.evidence_score,
                    "market_impact_score": cand.market_impact_score,
                    "regional_relevance_score": cand.regional_relevance_score,
                    "final_score": cand.final_candidate_score,
                    "selection_reason": cand.selection_reason
                },
                decision_context={
                    "district_metrics": district_meta,
                    "finance_outlook": finance_meta
                },
                advisor_context={
                    "advisor_name": "Yiğit Narin",
                    "advisor_phone": "+905324514008",
                    "target_topic": entities["primary_entity"]["segment"],
                    "suggested_wa_prompt": f"Merhaba Yiğit Bey, '{art.title}' analizi ve {region_name} bölgesindeki etkileri hakkında görüşünüzü rica ediyorum."
                }
            )

            if qa_res["is_ready_for_publish"]:
                published_intelligence.append(intelligence_obj)
            else:
                monitored_signals.append({
                    "title": art.title,
                    "score": cand.final_candidate_score,
                    "reason": qa_res["reasons"]
                })

        # Summary statement
        verified_count = len(published_intelligence)
        summary_text = (
            f"Bugün {scanned_count} piyasa sinyali tarandı, {len(evaluated_candidates)} sinyal analiz edildi, "
            f"{verified_count} doğrulanmış yüksek etkili piyasa istihbaratı yayımlandı."
        )

        return {
            "summary_statement": summary_text,
            "scanned_signals_count": scanned_count,
            "evaluated_signals_count": len(evaluated_candidates),
            "published_intelligence_count": verified_count,
            "monitored_signals_count": len(monitored_signals),
            "research_queue": [
                {"id": t.task_id, "priority": t.priority, "region": t.region, "topic": t.topic}
                for t in self.research_queue
            ],
            "published_articles": published_intelligence,
            "monitored_signals": monitored_signals
        }
