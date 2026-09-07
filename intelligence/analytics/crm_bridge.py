"""
CRM Bridge: Links intelligence signals directly into the CRM pipeline.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from intelligence.db import get_db_connection


class CrmBridge:
    """Retrieves high-intent prospects and intelligence signals for CRM display."""

    @staticmethod
    def get_prospects_summary(min_intent: int = 5) -> List[Dict[str, Any]]:
        """Retrieves users who crossed lead intent thresholds."""
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT user_id, intent_score, last_active, topics_json, locations_json
                FROM user_interest_vectors
                WHERE intent_score >= ?
                ORDER BY intent_score DESC
                LIMIT 20;
            """, (min_intent,))
            
            prospects = []
            for r in cursor.fetchall():
                prospects.append({
                    "user_id": r["user_id"],
                    "intent_score": r["intent_score"],
                    "last_active": r["last_active"]
                })
            return prospects
        finally:
            conn.close()

    @staticmethod
    def get_funnel_stats() -> Dict[str, Any]:
        """Calculates conversion metrics across the intelligence funnel."""
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT event_type, COUNT(*) as count, SUM(intent_score_delta) as total_points
                FROM crm_intelligence_events
                GROUP BY event_type
                ORDER BY count DESC;
            """)
            stats = {r["event_type"]: {"count": r["count"], "points": r["total_points"]} for r in cursor.fetchall()}
            return stats
        finally:
            conn.close()
