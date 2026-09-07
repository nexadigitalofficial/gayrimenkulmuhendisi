"""
Dynamic topic classification engine.
Categories: Konut, Arsa, Faiz, Kredi, Ekonomi, Yatırım, Proje, Kentsel Dönüşüm, Ulaşım, Mevzuat, Kira, Fiyat, Talep, Arz.
"""

import re
from typing import List
from intelligence.models import TopicEntity


TOPIC_KEYWORDS = {
    "Konut": ["konut", "daire", "ev", "villa", "rezidans", "apartman", "yaşam"],
    "Arsa": ["arsa", "parsel", "tarla", "imar", "ifraz", "müstakil arsa"],
    "Faiz": ["faiz", "politika faizi", "tcmb", "merkez bankası", "parasal sıkılaşma"],
    "Kredi": ["kredi", "konut kredisi", "mortgage", "finansman", "taksit", "peşinat", "banka kredisi"],
    "Yatırım": ["yatırım", "getiri", "amortisman", "portföy", "fon", "gayrimenkul yatırımı", "prim"],
    "Proje": ["proje", "lansman", "inşaat", "müteahhit", "teslim", "şantiye", "markalı konut"],
    "Kentsel Dönüşüm": ["kentsel dönüşüm", "deprem", "riskli yapı", "güçlendirme", "kentsel yenileme"],
    "Ulaşım": ["ulaşım", "metro", "bulvar", "otoyol", "yol", "bağlantı yolu", "istasyon"],
    "Kira": ["kira", "kiralık", "kira getirisi", "kiracı", "tüfe kira", "amortisman süresi"],
    "Mevzuat": ["mevzuat", "yönetmelik", "resmi gazete", "tapu", "harç", "vergi", "kanun"]
}


class TopicEngine:
    """Classifies real estate articles into structured topic entities."""

    def classify(self, text: str) -> List[TopicEntity]:
        text_lower = text.lower()
        results: List[TopicEntity] = []

        for topic, keywords in TOPIC_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                matches += len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower))

            if matches > 0:
                # Calculate normalized relevance
                relevance = min(0.40 + (matches * 0.15), 1.0)
                results.append(TopicEntity(name=topic, relevance=round(relevance, 2)))

        # Sort by relevance descending
        results.sort(key=lambda t: t.relevance, reverse=True)
        return results if results else [TopicEntity(name="Piyasa Analizi", relevance=0.85)]
