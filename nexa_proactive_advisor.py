#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
NEXA PROACTIVE ADVISOR™ | Otonom Yapay Zekâ Piyasa Stratejisti & Tavsiye Motoru
========================================================================================
Piyasadaki delta olaylarını (fiyat indirimi, yeni rakip girişi, satılan/kalkan emsaller)
yalnızca kuru bir bildirim olarak bırakmaz; portföyümüzün rekabet şerefiyesini,
DOM satış hızını ve kâr marjını koruyacak eyleme dönüştürülebilir stratejik tavsiyeler üretir.
"""

import sys
from typing import Dict, Any, Optional

# Reconfigure stdout for Windows console UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class NexaProactiveAdvisor:
    """
    Generates executive-grade strategic commentary and proactive advice
    for market delta events based on valuation rules and competitive positioning.
    """

    def generate_advice(
        self,
        event_type: str,
        competitor_listing: dict,
        our_listing: Optional[dict],
        old_price: float,
        new_price: float,
        change_pct: float
    ) -> Dict[str, str]:
        """
        Analyzes the delta event against our own portfolio and returns:
          - ai_strategic_comment: Derin piyasa etkisi ve analiz yorumu
          - recommended_action: Danışmanın hemen atması gereken somut adım
        """
        comp_title = competitor_listing.get("title") or "Rakip İlan"
        comp_m2 = competitor_listing.get("m2_gross") or competitor_listing.get("m2") or 0
        our_price = float(our_listing.get("current_price") or our_listing.get("price") or 0) if our_listing else 0.0

        if event_type == "PRICE_DROP":
            diff_tl = abs(old_price - new_price)
            # Evaluate price positioning relative to our portfolio
            if our_price > 0 and new_price < our_price:
                pct_below = round(((our_price - new_price) / our_price) * 100, 1)
                comment = (
                    f"🚨 DİKKAT: Rakip ilan ({comp_title}) fiyatını {old_price:,.0f} TL'den "
                    f"{new_price:,.0f} TL'ye düşürdü (%{change_pct:.1f} indirim, -{diff_tl:,.0f} TL). "
                    f"Bu indirimle birlikte rakip portföy, sizin mülkünüzün %{pct_below:.1f} altına indi. "
                    f"Alıcıların filtre aramalarında rakip ilan öne çıkacaktır."
                )
                action = (
                    f"Fiyat kırmak yerine şerefiye farkınızı öne çıkarın. Portföyünüzün kat/konum, "
                    f"arsa büyüklüğü veya lüks donatı avantajlarını ilan başlığında vurgulayın. "
                    f"Pazarlık marjınızı en fazla %{min(5.0, pct_below):.1f} esnetmeye hazır olun."
                )
            elif our_price > 0 and new_price >= our_price:
                comment = (
                    f"📊 Rakip ilan ({comp_title}) fiyatını {old_price:,.0f} TL'den {new_price:,.0f} TL'ye "
                    f"düşürdü (%{change_pct:.1f} indirim), ancak portföyünüz hâlâ rakibe göre "
                    f"{((new_price - our_price) / our_price * 100):.1f}% daha avantajlı fiyat seviyesinde."
                )
                action = (
                    f"Mevcut fiyatınızı kesinlikle koruyun. Rakibin fiyat kırması bölgede genel bir "
                    f"talep hareketi yaratacaktır; bu durum sizin portföyünüze daha hızlı talep çekecektir."
                )
            else:
                comment = (
                    f"🚨 Pazardaki rakip ilan ({comp_title}) fiyatını %{change_pct:.1f} kırdı "
                    f"({old_price:,.0f} ➔ {new_price:,.0f} TL)."
                )
                action = "Pazar emsal medyanı aşağı yönlü esnedi. Portföy ekspertiz değerini güncelleyin."

        elif event_type == "NEW_ENTRY":
            comment = (
                f"🆕 BÖLGEYE YENİ RAKİP GİRDİ: '{comp_title}' başlıklı yeni bir ilan "
                f"{new_price:,.0f} TL liste fiyatıyla pazara dahil oldu. "
            )
            if our_price > 0:
                if new_price > our_price:
                    comment += f"Yeni rakip sizin portföyünüzden %{((new_price - our_price)/our_price*100):.1f} daha pahalı girdi."
                    action = "Fiyat avantajınızı koruyun. Yeni ilanı inceleyen alıcılar sizin portföyünüzü daha cazip bulacaktır."
                else:
                    comment += f"Yeni rakip sizin portföyünüzden %{((our_price - new_price)/our_price*100):.1f} daha uygun fiyatla girdi."
                    action = "Yeni rakibin donatı ve tadilat durumunu inceleyin; şerefiye üstünlüklerinizi CRM ilan kartında belirginleştirin."
            else:
                action = "Yeni rakibin emsal değerleme puanını ve DOM beklentisini inceleyin."

        elif event_type == "DELISTED_OR_SOLD":
            comment = (
                f"🏁 RAKİP İLAN PAZARDAN ÇIKTI: '{comp_title}' ({old_price:,.0f} TL) yayından kalktı. "
                f"Bu mülk ya satıldı/kiralandı ya da mal sahibi tarafından çekildi. Bölgedeki aktif arz azaldı!"
            )
            action = (
                "Piyasa arzı daraldı, pazarlık gücünüz arttı! Mevcut portföyünüzde indirim taleplerine karşı "
                "daha dirençli durun ve acil alıcıları portföyünüze yönlendirin."
            )

        elif event_type == "PRICE_HIKE":
            diff_tl = abs(new_price - old_price)
            comment = (
                f"📈 RAKİP FİYAT ARTIRDI: '{comp_title}' fiyatını {old_price:,.0f} TL'den "
                f"{new_price:,.0f} TL'ye yükseltti (+%{change_pct:.1f}, +{diff_tl:,.0f} TL)."
            )
            action = "Rakip fiyat artışı sizin portföyünüzün pazar cazibesini doğrudan yükseltti. Satış hızınız artacaktır."

        else:
            comment = f"Piyasa güncellemesi: {comp_title} ilanı güncellendi."
            action = "İlan parametrelerini inceleyin."

        return {
            "ai_strategic_comment": comment,
            "recommended_action": action
        }


if __name__ == "__main__":
    advisor = NexaProactiveAdvisor()
    res = advisor.generate_advice(
        event_type="PRICE_DROP",
        competitor_listing={"title": "Çankaya Kavaklıdere 3+1 Prestijli Daire", "m2_gross": 140},
        our_listing={"title": "Kavaklıdere Satılık Daire", "current_price": 7500000},
        old_price=8200000,
        new_price=7100000,
        change_pct=13.4
    )
    print("Advisor Test Comment:\n", res["ai_strategic_comment"])
    print("Advisor Test Action:\n", res["recommended_action"])
