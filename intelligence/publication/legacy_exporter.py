"""
Backward compatibility exporter.
Ensures static/data/latest_news.json is always synced with intelligence.db
so any legacy scripts continue to work without breaking.
"""

import os
import json
from pathlib import Path
from typing import List
from intelligence.models import IntelligenceArticle

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DATA = BASE_DIR / "static" / "data"
LEGACY_PATH = STATIC_DATA / "latest_news.json"


def export_to_legacy_json(articles: List[IntelligenceArticle]) -> bool:
    """Exports articles in the legacy JSON format."""
    try:
        os.makedirs(STATIC_DATA, exist_ok=True)
        payload = []
        for art in articles:
            payload.append({
                "id": art.id,
                "title": art.title,
                "summary": art.summary,
                "content": art.content,
                "image": art.image_url,
                "category": art.category,
                "readTime": art.read_time,
                "published": True,
                "createdAt": art.created_at,
                "updatedAt": art.updated_at,
                "slug": art.slug,
                "what_we_know": getattr(art, "what_we_know", ""),
                "what_we_infer": getattr(art, "what_we_infer", ""),
                "what_we_suspect": getattr(art, "what_we_suspect", ""),
                "what_we_dont_know": getattr(art, "what_we_dont_know", ""),
                "contrarian_view": getattr(art, "contrarian_view", {}),
                "why_this_news": getattr(art, "why_this_news", {}),
                "quality_score": getattr(art, "quality_score", 90),
                "confidence_score": getattr(art, "confidence_score", 0.9)
            })

        # Atomic file write
        temp_path = str(LEGACY_PATH) + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, str(LEGACY_PATH))
        print(f"[OK] Exported {len(payload)} articles to {LEGACY_PATH}")
        return True
    except Exception as e:
        print(f"[ERROR] export_to_legacy_json failed: {e}")
        return False
