"""
Property & Project Linking Engine.
Automatically connects market intelligence articles to actual CB VIP Ankara projects and portfolio listings.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from intelligence.models import RegionEntity, TopicEntity

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DATA = BASE_DIR / "static" / "data"


class PropertyLinker:
    """Matches intelligence events with real active projects and portfolio listings."""

    def __init__(self):
        self.projects_cache: List[Dict[str, Any]] = []
        self.portfolio_cache: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        try:
            proj_path = STATIC_DATA / "projects_map.json"
            if proj_path.exists():
                with open(proj_path, "r", encoding="utf-8") as f:
                    self.projects_cache = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load projects_map.json: {e}")

        try:
            port_path = STATIC_DATA / "portfolio_listing_dashboards.json"
            if port_path.exists():
                with open(port_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.portfolio_cache = list(data.values()) if isinstance(data, dict) else data
        except Exception as e:
            print(f"[WARN] Failed to load portfolio_listing_dashboards.json: {e}")

    def link_article_to_properties(
        self,
        locations: List[RegionEntity],
        topics: List[TopicEntity],
        max_results: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns relevant projects and listings for the given article locations and topics.
        """
        loc_names = [l.name.lower() for l in locations]
        topic_names = [t.name.lower() for t in topics]

        matched_projects = []
        for p in self.projects_cache:
            p_region = (p.get("region") or p.get("location") or "").lower()
            p_title = (p.get("title") or p.get("name") or "").lower()
            
            score = 0
            for l in loc_names:
                if l in p_region or l in p_title:
                    score += 2
            if any(t in p_title for t in topic_names):
                score += 1

            if score > 0:
                matched_projects.append((score, {
                    "id": p.get("id"),
                    "title": p.get("title") or p.get("name"),
                    "region": p.get("region") or p.get("location"),
                    "price_display": p.get("price_display") or p.get("price", "Fiyat Sorunuz"),
                    "image": p.get("image") or (p.get("images", [""])[0] if p.get("images") else "")
                }))

        matched_projects.sort(key=lambda x: x[0], reverse=True)
        top_projects = [p[1] for p in matched_projects[:max_results]]

        # Fallback to first 2 VIP projects if no exact location match
        if not top_projects and self.projects_cache:
            for p in self.projects_cache[:2]:
                top_projects.append({
                    "id": p.get("id"),
                    "title": p.get("title") or p.get("name"),
                    "region": p.get("region") or p.get("location"),
                    "price_display": p.get("price_display") or p.get("price", "Fiyat Sorunuz"),
                    "image": p.get("image") or ""
                })

        return {
            "projects": top_projects,
            "project_ids": [p["id"] for p in top_projects if p.get("id")]
        }
