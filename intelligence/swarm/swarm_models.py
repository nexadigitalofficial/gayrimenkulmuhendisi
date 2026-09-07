# -*- coding: utf-8 -*-
"""
NEXA Real Estate Intelligence Swarm - Data Models & Ontologies
Coldwell Banker CB VIP Ankara • Yiğit Narin
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class CandidateAction(str, Enum):
    IGNORE = "IGNORE"                        # < 50 score
    MONITOR = "MONITOR"                      # 50 - 64 score (early signal, watch)
    TRACK = "TRACK"                          # 65 - 79 score (evidence gathering)
    PUBLISH = "PUBLISH"                      # 80 - 89 score (verified publication)
    PRIORITY_INTELLIGENCE = "PRIORITY"       # 90+ score (urgent market briefing)


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"


class MarketRegime(str, Enum):
    EXPANSION = "EXPANSION"     # Strong demand, growing supply, rising price pressure
    STABLE = "STABLE"           # Balanced supply-demand, steady yields
    COOLING = "COOLING"         # Rate pressure, slower transactions, buyer advantage
    STRESS = "STRESS"           # High financing costs, low transaction volume
    RECOVERY = "RECOVERY"       # Emerging demand pickup, early cycle opportunities


@dataclass
class EvidenceItem:
    claim: str
    source_id: str
    source_name: str
    authority_score: float = 0.85
    reliability_score: float = 0.80
    url: str = ""
    corroborating_sources: List[str] = field(default_factory=list)
    status: VerificationStatus = VerificationStatus.VERIFIED


@dataclass
class ContrarianAnalysis:
    counter_hypothesis: str
    contrary_indicators: List[str] = field(default_factory=list)
    downside_risks: List[str] = field(default_factory=list)
    confidence_discount: float = 0.05
    verdict: str = "Piyasa etkisi teyit edildi ancak risk marjı dikkate alınmalı."


@dataclass
class ResearchTask:
    task_id: str
    priority: int  # 0 - 100
    topic: str
    region: str
    key_questions: List[str] = field(default_factory=list)
    assigned_agents: List[str] = field(default_factory=list)
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SignalCandidate:
    signal_id: str
    title: str
    content: str
    source_name: str
    source_authority: float = 0.85
    importance_score: int = 70
    freshness_score: int = 90
    evidence_score: int = 75
    market_impact_score: int = 70
    novelty_score: int = 70
    regional_relevance_score: int = 75
    final_candidate_score: int = 74
    action: CandidateAction = CandidateAction.TRACK
    selection_reason: str = ""


@dataclass
class MarketState:
    demand: float = 72.0
    supply: float = 54.0
    credit: float = 62.0
    rental: float = 78.0
    price_pressure: float = 66.0
    investment_appetite: float = 74.0
    regime: MarketRegime = MarketRegime.STABLE
    regional_indices: Dict[str, Dict[str, float]] = field(default_factory=dict)
    daily_diff: Dict[str, float] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EmergingTrend:
    trend_id: str
    topic: str
    region: str
    period_days: int = 14
    velocity: float = 1.0  # rate of acceleration
    signal_count: int = 1
    summary: str = ""
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FinalIntelligenceObject:
    id: str
    title: str
    slug: str
    category: str
    importance: int
    confidence: int
    freshness: int
    global_impact: int
    regional_impact: int
    buyer_impact: int
    seller_impact: int
    investor_impact: int
    developer_impact: int
    risk_score: int
    opportunity_score: int
    locations: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    claims: List[EvidenceItem] = field(default_factory=list)
    
    # 4-Part Epistemological Model
    what_we_know: str = ""       # Verified facts, citations, data
    what_we_infer: str = ""      # Logical economic deductions
    what_we_suspect: str = ""    # Unverified early signals under watch
    what_we_dont_know: str = ""  # Data gaps, unknowns, pending decisions
    
    contrarian_view: Optional[ContrarianAnalysis] = None
    why_this_news: Dict[str, Any] = field(default_factory=dict)
    decision_context: Dict[str, Any] = field(default_factory=dict)
    advisor_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
