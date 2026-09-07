"""
Domain models and dataclasses for NEXA Real Estate Intelligence Network.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
import json


class SourceType(str, Enum):
    OFFICIAL = "official"          # TCMB, TÜİK, BDDK, Emlak Konut
    GOVERNMENT = "government"      # Resmî Gazete, Çevre ve Şehircilik Bakanlığı
    FINANCIAL = "financial"        # AA Finans, Bloomberg HT, Dünya/Ekonomim
    SECTOR = "sector"              # Endeksa, Gayrimenkul sektörel raporları
    RSS = "rss"                    # Sektörel RSS ve haber toplayıcıları


class ContentStatus(str, Enum):
    DISCOVERED = "discovered"
    PROCESSING = "processing"
    VERIFIED = "verified"
    DRAFT = "draft"
    QUALITY_CHECK = "quality_check"
    PUBLISHED = "published"
    UPDATED = "updated"
    ARCHIVED = "archived"


class MarketDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


@dataclass
class NewsSourceModel:
    id: str
    name: str
    url: str
    type: SourceType
    authority_score: int = 80          # 1 - 100
    reliability_score: int = 80        # 1 - 100
    enabled: bool = True
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RawArticle:
    source_id: str
    source_name: str
    title: str
    url: str
    content: str
    summary: str = ""
    author: str = ""
    published_at: Optional[str] = None
    image_url: Optional[str] = None
    raw_html: str = ""
    guid: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactClaim:
    claim_text: str
    source_name: str
    source_url: str
    source_date: str
    verification_status: str = "verified"   # verified, unverified, disputed
    confidence: float = 0.90               # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactScore:
    buyer_score: int = 50           # 0 - 100
    buyer_rationale: str = ""
    seller_score: int = 50          # 0 - 100
    seller_rationale: str = ""
    investor_score: int = 50        # 0 - 100
    investor_rationale: str = ""
    developer_score: int = 50       # 0 - 100
    developer_rationale: str = ""

    # Directional indicators
    price_trend: MarketDirection = MarketDirection.NEUTRAL
    rent_trend: MarketDirection = MarketDirection.NEUTRAL
    credit_conditions: MarketDirection = MarketDirection.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["price_trend"] = self.price_trend.value
        d["rent_trend"] = self.rent_trend.value
        d["credit_conditions"] = self.credit_conditions.value
        return d


@dataclass
class RegionEntity:
    name: str                       # e.g. "Beytepe", "Çankaya", "Ankara"
    type: str = "district"          # province, district, neighborhood
    relevance: float = 1.0          # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TopicEntity:
    name: str                       # Konut, Arsa, Faiz, Kredi, etc.
    relevance: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EventCluster:
    id: str
    title: str
    summary: str
    start_time: str
    updated_time: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    locations: List[RegionEntity] = field(default_factory=list)
    topics: List[TopicEntity] = field(default_factory=list)
    importance: str = "medium"      # critical, high, medium, low
    confidence: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "start_time": self.start_time,
            "updated_time": self.updated_time,
            "sources": self.sources,
            "locations": [loc.to_dict() if isinstance(loc, RegionEntity) else loc for loc in self.locations],
            "topics": [top.to_dict() if isinstance(top, TopicEntity) else top for top in self.topics],
            "importance": self.importance,
            "confidence": self.confidence,
        }


@dataclass
class IntelligenceArticle:
    id: str
    slug: str
    title: str
    summary: str
    content: str
    image_url: str
    category: str
    read_time: str
    status: ContentStatus = ContentStatus.PUBLISHED

    # Intelligence & Deep Context
    what_happened: str = ""
    why_it_matters: str = ""
    who_is_affected: str = ""
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    time_horizon: str = "Orta Vade (3-6 Ay)"

    # Structured Data
    impacts: ImpactScore = field(default_factory=ImpactScore)
    facts: List[FactClaim] = field(default_factory=list)
    locations: List[RegionEntity] = field(default_factory=list)
    topics: List[TopicEntity] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)

    # Related Data & Linking
    related_article_ids: List[str] = field(default_factory=list)
    related_project_ids: List[str] = field(default_factory=list)
    related_portfolio_ids: List[str] = field(default_factory=list)

    # Advisor CTA Context
    target_audience: str = "GENERAL"  # BUYER, SELLER, INVESTOR, GENERAL
    advisor_headline: str = "Bu Gelişmenin Sizin İçin Ne Anlama Geldiğini Danışmanınıza Sorun"
    advisor_cta_text: str = "Yiğit Narin'e Danışın"
    advisor_phone: str = "+905324514008"

    # Epistemological Model & Swarm Context
    what_we_know: str = ""
    what_we_infer: str = ""
    what_we_suspect: str = ""
    what_we_dont_know: str = ""
    contrarian_view: Dict[str, Any] = field(default_factory=dict)
    why_this_news: Dict[str, Any] = field(default_factory=dict)

    # Quality & Lifecycle
    quality_score: int = 90
    confidence_score: float = 0.90
    event_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "image": self.image_url,
            "category": self.category,
            "readTime": self.read_time,
            "status": self.status.value,
            "what_happened": self.what_happened,
            "why_it_matters": self.why_it_matters,
            "who_is_affected": self.who_is_affected,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "time_horizon": self.time_horizon,
            "impacts": self.impacts.to_dict() if isinstance(self.impacts, ImpactScore) else self.impacts,
            "facts": [f.to_dict() if isinstance(f, FactClaim) else f for f in self.facts],
            "locations": [loc.to_dict() if isinstance(loc, RegionEntity) else loc for loc in self.locations],
            "topics": [top.to_dict() if isinstance(top, TopicEntity) else top for top in self.topics],
            "sources": self.sources,
            "related_article_ids": self.related_article_ids,
            "related_project_ids": self.related_project_ids,
            "related_portfolio_ids": self.related_portfolio_ids,
            "target_audience": self.target_audience,
            "advisor_headline": self.advisor_headline,
            "advisor_cta_text": self.advisor_cta_text,
            "advisor_phone": self.advisor_phone,
            "what_we_know": self.what_we_know,
            "what_we_infer": self.what_we_infer,
            "what_we_suspect": self.what_we_suspect,
            "what_we_dont_know": self.what_we_dont_know,
            "contrarian_view": self.contrarian_view,
            "why_this_news": self.why_this_news,
            "quality_score": self.quality_score,
            "confidence_score": self.confidence_score,
            "event_id": self.event_id,
            "published": self.status == ContentStatus.PUBLISHED,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class DecisionResult:
    engine_name: str                # buying_conditions, selling_conditions, etc.
    score: float                    # e.g. 7.4 / 10 or 82 / 100
    condition: str                  # Strong, Moderate, Neutral, Caution, Weak
    headline: str
    summary: str
    factors: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    suggested_action: str = ""
    advisor_consultation_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserInterestVector:
    user_id: str
    topics: Dict[str, float] = field(default_factory=dict)       # {"Konut": 0.88, "Faiz": 0.74}
    locations: Dict[str, float] = field(default_factory=dict)    # {"Beytepe": 0.92, "Çankaya": 0.85}
    intent_score: int = 0
    viewed_articles: List[str] = field(default_factory=list)
    viewed_projects: List[str] = field(default_factory=list)
    decision_tools_used: List[str] = field(default_factory=list)
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntelligenceRun:
    run_id: str
    started_at: str
    ended_at: Optional[str] = None
    sources_checked: int = 0
    items_found: int = 0
    duplicates_merged: int = 0
    verified_count: int = 0
    published_count: int = 0
    rejected_count: int = 0
    errors: List[str] = field(default_factory=list)
    latency_ms: int = 0
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
