"""
Context-Aware Advisor CTA Engine.
Generates tailored value propositions instead of generic 'Bize Ulaşın' links.
"""

from typing import Dict, Any


CTA_TEMPLATES = {
    "BUYER": {
        "headline": "Size En Uygun Güvenli Proje Seçeneklerini Değerlendirelim",
        "cta_text": "Alım Fırsatlarını Danışın",
        "prefill_msg": "Merhaba Yiğit Bey, piyasa analizinizi okudum. Bütçeme ve hedef lokasyona uygun konut alım seçenekleri hakkında danışmak istiyorum."
    },
    "SELLER": {
        "headline": "Mülkünüzün Güncel Piyasa Konumunu ve Gerçek Satış Değerini Analiz Edelim",
        "cta_text": "Mülk Değerleme Analizi Alın",
        "prefill_msg": "Merhaba Yiğit Bey, son piyasa analiziniz doğrultusunda Ankara'daki mülküm için güncel satış ekspertizi ve pazarlama planı almak istiyorum."
    },
    "INVESTOR": {
        "headline": "Bu Gelişmenin Yatırım ve Getiri Stratejinize Etkisini İnceleyelim",
        "cta_text": "Yatırım Getiri Analizi İsteyin",
        "prefill_msg": "Merhaba Yiğit Bey, paylaştığınız gayrimenkul analizindeki getiri ve sermaye artış fırsatları hakkında VIP danışmanlık talep ediyorum."
    },
    "GENERAL": {
        "headline": "Bu Gelişmenin Sizin Gayrimenkul Kararınıza Etkisini Birlikte Değerlendirelim",
        "cta_text": "Yiğit Narin'e Danışın",
        "prefill_msg": "Merhaba Yiğit Bey, son gayrimenkul bülteniniz hakkında görüş ve tavsiyenizi almak istiyorum."
    }
}


class AdvisorCtaEngine:
    """Produces customized CTAs based on article audience and category."""

    def get_cta_for_article(self, category: str, audience: str = "GENERAL", title: str = "") -> Dict[str, str]:
        aud = audience.upper() if audience else "GENERAL"
        if aud not in CTA_TEMPLATES:
            aud = "GENERAL"

        template = dict(CTA_TEMPLATES[aud])
        if title:
            template["prefill_msg"] = f"Merhaba Yiğit Bey, '{title}' analizinizi okudum. Bunun benim için ne anlama geldiği konusunda danışmak istiyorum."

        return template
