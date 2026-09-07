# -*- coding: utf-8 -*-
"""
NEXA Real Estate Intelligence Swarm Package
Coldwell Banker CB VIP Ankara • Yiğit Narin
"""

from intelligence.swarm.swarm_models import (
    CandidateAction,
    VerificationStatus,
    MarketRegime,
    EvidenceItem,
    ContrarianAnalysis,
    ResearchTask,
    SignalCandidate,
    MarketState,
    EmergingTrend,
    FinalIntelligenceObject
)

from intelligence.swarm.scouts import (
    SourceScoutAgent,
    GovernmentDataAgent,
    NewsDiscoveryAgent
)

from intelligence.swarm.specialists import (
    FinanceAgent,
    EntityResolutionAgent,
    AnkaraAgent,
    InfrastructureZoningAgent,
    ProjectIntelligenceAgent,
    RentalMarketAgent
)

from intelligence.swarm.critical_thinking import (
    ContrarianAgent,
    TrendDetectionAgent
)

from intelligence.swarm.verification import (
    FactCheckerAgent,
    EvidenceGraphBuilder
)

from intelligence.swarm.synthesizer import (
    ContentSynthesizerAgent,
    QAGateAgent
)

from intelligence.swarm.director import IntelligenceDirector

__all__ = [
    "CandidateAction",
    "VerificationStatus",
    "MarketRegime",
    "EvidenceItem",
    "ContrarianAnalysis",
    "ResearchTask",
    "SignalCandidate",
    "MarketState",
    "EmergingTrend",
    "FinalIntelligenceObject",
    "SourceScoutAgent",
    "GovernmentDataAgent",
    "NewsDiscoveryAgent",
    "FinanceAgent",
    "EntityResolutionAgent",
    "AnkaraAgent",
    "InfrastructureZoningAgent",
    "ProjectIntelligenceAgent",
    "RentalMarketAgent",
    "ContrarianAgent",
    "TrendDetectionAgent",
    "FactCheckerAgent",
    "EvidenceGraphBuilder",
    "ContentSynthesizerAgent",
    "QAGateAgent",
    "IntelligenceDirector"
]
