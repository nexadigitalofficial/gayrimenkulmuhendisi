"""
Interactive 'Danışmana Sor' Flow.
Generates instant personalized briefs based on user query category and generates direct WhatsApp link.
"""

import urllib.parse
from typing import Dict, Any


class AdvisorFlow:
    """Processes 'Danışmana Sor' inquiries and prepares consultation payloads."""

    WHATSAPP_PHONE = "905324514008"

    OPTIONS_MAP = {
        "impact": "Beni nasıl etkiler?",
        "buy": "Ev almak için uygun zaman mı?",
        "sell": "Mülkümü satmalı mıyım?",
        "invest": "Yatırım ve getiri fırsatı var mı?",
        "region": "Bölgemdeki fiyatları nasıl etkiler?"
    }

    def process_inquiry(
        self,
        article_title: str,
        article_slug: str,
        option_key: str,
        user_name: str = "",
        user_phone: str = ""
    ) -> Dict[str, Any]:
        option_desc = self.OPTIONS_MAP.get(option_key, "Genel Piyasa Değerlendirmesi")

        # Briefing summary based on selected choice
        if option_key == "buy":
            brief = "Mevcut piyasada alım yaparken nakit iskontoları ve doğrudan müteahhit taksitli projeler öncelikli değerlendirilmelidir."
        elif option_key == "sell":
            brief = "Mülkünüz için doğru değerleme yapıldığında alıcı kitlesine hızlı ulaşmak mümkündür; gerçekçi ekspertiz esastır."
        elif option_key == "invest":
            brief = "Özellikle gelişen batı/güneybatı aksındaki altyapılı bölgeler enflasyona karşı yüksek getiri ve sermaye koruması vadetmektedir."
        else:
            brief = "Piyasadaki arz-talep ve finansman dengeleri dikkate alınarak kişisel hedeflerinize özel bir yol haritası çizilmelidir."

        # WhatsApp Message
        wa_text = f"Merhaba Yiğit Bey,\n\n'{article_title}' konulu piyasa analizinizi inceledim.\nÖzellikle şu konuda danışmak istiyorum: *{option_desc}*\n"
        if user_name:
            wa_text += f"\nAdım: {user_name}"
        if user_phone:
            wa_text += f"\nİletişim: {user_phone}"
        wa_text += "\n\nSizinle kısa bir telefon veya kahve randevusu planlayabilir miyiz?"

        wa_url = f"https://wa.me/{self.WHATSAPP_PHONE}?text={urllib.parse.quote(wa_text)}"

        return {
            "option_selected": option_desc,
            "brief_summary": brief,
            "whatsapp_url": wa_url,
            "advisor_name": "Yiğit Narin",
            "advisor_title": "Coldwell Banker CB VIP Ankara Lüks Konut & Yatırım Danışmanı"
        }
