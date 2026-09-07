"""
Normalizer for raw text, dates, and Turkish slug generation.
"""

import re
import html
from datetime import datetime, timezone


def clean_text(text: str) -> str:
    """Removes HTML, unescapes entities, collapses whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def title_to_slug(title: str) -> str:
    """Generates SEO-friendly Turkish URL slug."""
    s = title.strip().lower()
    # Turkish char replacements
    tr_map = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'İ': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'
    }
    for k, v in tr_map.items():
        s = s.replace(k, v)
    # Remove non-alphanumeric except hyphen
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s).strip('-')
    return s or "haber"
