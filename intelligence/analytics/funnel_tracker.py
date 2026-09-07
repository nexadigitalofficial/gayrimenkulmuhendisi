"""
Configurable Lead Intent Scoring & Funnel Tracking.
Tracks user engagement and converts reading behavior into actionable CRM lead signals.
"""

from typing import Dict, Any, Optional
from intelligence.db import log_crm_intelligence_event


INTENT_SCORE_MAP = {
    "article_view": 1,
    "related_article_click": 2,
    "property_link_click": 4,
    "decision_tool_run": 5,
    "advisor_cta_click": 10,
    "whatsapp_click": 15,
    "appointment_click": 25
}


class FunnelTracker:
    """Tracks intelligence funnel interactions and updates lead scores."""

    @staticmethod
    def track_interaction(
        event_type: str,
        user_id: Optional[str] = None,
        article_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """Records the event and returns the score delta applied."""
        delta = INTENT_SCORE_MAP.get(event_type, 1)
        log_crm_intelligence_event(
            user_id=user_id,
            article_id=article_id,
            event_type=event_type,
            intent_score_delta=delta,
            context=context or {}
        )
        return delta
