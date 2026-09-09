"""
Configurable Lead Intent Scoring & Funnel Tracking.
Tracks user engagement and converts reading behavior into actionable CRM lead signals.
"""

from typing import Dict, Any, Optional
from intelligence.db import log_crm_intelligence_event


INTENT_SCORE_MAP = {
    "article_view": 5,
    "filter_change": 10,
    "related_article_click": 8,
    "property_link_click": 25,
    "decision_tool_run": 20,
    "advisor_cta_click": 35,
    "whatsapp_click": 50,
    "whatsapp_inquiry": 50,
    "appointment_click": 50
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
