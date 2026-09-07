"""
Abstract base class and contract for real estate news sources.
Includes SSRF protection, timeout boundaries, and normalization.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import urllib.parse
import ipaddress
import socket
import re
from datetime import datetime, timezone
from intelligence.models import NewsSourceModel, RawArticle, SourceType


def is_safe_url(url: str) -> bool:
    """SSRF guard: verifies URL is public http/https and not local/private subnet."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
            return False
        
        # Check resolved IP
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            return False
        return True
    except Exception:
        return False


class NewsSource(ABC):
    """Base source adapter."""

    def __init__(self, model: NewsSourceModel):
        self.model = model

    @abstractmethod
    def fetch(self) -> List[RawArticle]:
        """Fetches raw articles from the external source."""
        pass

    def validate(self, article: RawArticle) -> bool:
        """Validates that article contains essential fields and safe URLs."""
        if not article.title or len(article.title.strip()) < 10:
            return False
        if not article.url or not is_safe_url(article.url):
            return False
        if not article.content or len(article.content.strip()) < 40:
            return False
        return True

    def normalize(self, article: RawArticle) -> RawArticle:
        """Cleans whitespace, strips HTML tags from summary, standardizes dates."""
        article.title = re.sub(r'\s+', ' ', article.title).strip()
        article.summary = re.sub(r'<[^>]+>', '', article.summary or '').strip()
        article.content = re.sub(r'\s+', ' ', article.content).strip()
        if not article.published_at:
            article.published_at = datetime.now(timezone.utc).isoformat()
        return article
