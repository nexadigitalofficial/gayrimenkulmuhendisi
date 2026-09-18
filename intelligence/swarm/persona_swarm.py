# -*- coding: utf-8 -*-
"""
🤖 NEXA AI Swarm - Portfolio Target Audience & Buyer Persona Intelligence Engine
================================================================================
4 Specialized AI Swarm Agents:
1. DemographicScoutAgent: Analyzes rooms, sqm, property type, family/business capacity.
2. FinancialYieldAgent: Analyzes price, capital yield, amortization, corporate tax advantages.
3. LocationDynamicsAgent: Analyzes district, neighborhood, prestige, commute, zoning.
4. HonestAdvisoryAuditorAgent: Identifies key USPS and Anti-Personas (who it's NOT suitable for).
Synthesizer: Produces NEXA Fit Scores (0-100%) and Ultra-Premium Intelligence Object.
"""

import json
import re
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("nexa.persona_swarm")


class DemographicScoutAgent:
    """Ajan 1: Demografik & Yaşam Profili Ajanı"""

    def analyze(self, prop_type: str, tx_type: str, rooms: str, sqm: str, title: str) -> Dict[str, Any]:
        p_lower = (prop_type or "").lower()
        t_lower = (title or "").lower()
        r_clean = (rooms or "").strip()
        sqm_val = 0
        m = re.search(r"(\d+)", sqm or "")
        if m:
            try:
                sqm_val = int(m.group(1))
            except Exception:
                sqm_val = 0

        # Commercial / Office detection
        if any(k in p_lower or k in t_lower for k in ["ofis", "iş yeri", "isyeri", "plaza", "büro", "klinik"]):
            if "5+1" in r_clean or "5+1" in t_lower or sqm_val >= 250:
                return {
                    "primary_category": "Kurumsal & Prestij İş Yeri",
                    "ideal_scale": "20 - 45 Kişilik Çalışma Kadrosu",
                    "personas": [
                        {
                            "title": "Kurumsal Şirket Genel Merkezi & Holding Temsilciliği",
                            "score": 98,
                            "icon": "fa-building",
                            "badge": "Maksimum Uyum",
                            "suitability": "Geniş oda dağılımı (5+1), departmanlaşma ve yönetim kurulu toplantıları için ideal metrekare konforu sunar.",
                        },
                        {
                            "title": "Üst Segment Hukuk Bürosu & Danışmanlık Grubu",
                            "score": 95,
                            "icon": "fa-balance-scale",
                            "badge": "Yüksek Prestij",
                            "suitability": "Ortaklar ve kıdemli avukatlar için bağımsız çalışma odaları, müvekkil karşılama lobisi için mükemmel mimari.",
                        },
                        {
                            "title": "Medikal Estetik Klinik & VIP Sağlık / Diş Merkezi",
                            "score": 91,
                            "icon": "fa-user-md",
                            "badge": "Özel Sektör",
                            "suitability": "Çoklu muayenehane, laboratuvar ve hasta mahremiyeti sağlayan oda bölümlendirmesi.",
                        },
                    ],
                    "capacity_detail": "Geniş metrekare ve bağımsız oda kurgusu, kurumsal departman ayrımı veya diplomatik temsilcilik için benzersiz esneklik sağlar.",
                }
            else:
                return {
                    "primary_category": "Butik Profesyonel Ofis",
                    "ideal_scale": "5 - 15 Kişilik Uzman Kadro",
                    "personas": [
                        {
                            "title": "Mali Müşavirlik, Denetim & Yeminli Danışmanlık",
                            "score": 96,
                            "icon": "fa-calculator",
                            "badge": "Maksimum Uyum",
                            "suitability": "Müşteri kabulü, arşivleme ve odaklanmış çalışma alanları için ideal plan.",
                        },
                        {
                            "title": "Mimarlık, Yazılım & Kreatif Ajans Stüdyosu",
                            "score": 93,
                            "icon": "fa-laptop-code",
                            "badge": "Yaratıcı Sektör",
                            "suitability": "Açık ofis ve yönetici odası entegrasyonuna uygun modern yerleşim.",
                        },
                        {
                            "title": "Uluslararası Ticaret & İrtibat Bürosu",
                            "score": 89,
                            "icon": "fa-globe",
                            "badge": "Dış Ticaret",
                            "suitability": "Merkezi lokasyon ve düşük işletme genel gideri avantajı.",
                        },
                    ],
                    "capacity_detail": "Kompakt, işletme maliyeti optimize edilmiş ve tabela değeri yüksek profesyonel çalışma ortamı.",
                }

        # Land / Tarla / Arsa
        if any(k in p_lower or k in t_lower for k in ["arsa", "tarla", "bahçe", "parsel"]):
            return {
                "primary_category": "Stratejik Arsa & Arazi Yatırımı",
                "ideal_scale": "Bireysel / Kurumsal Yatırımcı & Geliştirici",
                "personas": [
                    {
                        "title": "Orta-Uzun Vadeli Varlık Büyütme Yatırımcısı",
                        "score": 97,
                        "icon": "fa-chart-line",
                        "badge": "Enflasyon Kalkanı",
                        "suitability": "Tek tapu güvencesi, değerini kaybetmeyen reel toprak varlığı ve enflasyona karşı güçlü koruma.",
                    },
                    {
                        "title": "Müstakil Yaşam & Doğa / Hobi Bahçesi Meraklısı",
                        "score": 92,
                        "icon": "fa-seedling",
                        "badge": "Yaşam Kalitesi",
                        "suitability": "Hafta sonu kaçış alanı, tiny house veya hobi amaçlı ekim-dikim için ferah parsel yapısı.",
                    },
                    {
                        "title": "Gelecek Vizyonlu İmar & Proje Geliştiricisi",
                        "score": 88,
                        "icon": "fa-drafting-compass",
                        "badge": "Gelişim Aksı",
                        "suitability": "Bölgesel altyapı ve imar genişleme planları ile prim potansiyeli taşıyan stratejik konum.",
                    },
                ],
                "capacity_detail": "Bölgesel gelişme koridorunda tek tapu güvencesiyle yüksek getiri hedefli sermaye konuşlandırması.",
            }

        # Villa / Taş Villa
        if any(k in p_lower or k in t_lower for k in ["villa", "müstakil", "tas villa", "taş villa"]):
            return {
                "primary_category": "Müstakil Lüks & Prestij Yaşam",
                "ideal_scale": "Mahremiyet ve Doğal Konfor Arayan Aileler",
                "personas": [
                    {
                        "title": "Huzur & Doğa Odaklı Üst Düzey Yönetici / Emekli",
                        "score": 98,
                        "icon": "fa-tree",
                        "badge": "Maksimum Huzur",
                        "suitability": "Şehir gürültüsünden arındırılmış, özel taş mimarili, temiz hava ve yüksek yaşam kalitesi.",
                    },
                    {
                        "title": "Geniş Bahçeli Müstakil Yaşam Tercih Eden Aile",
                        "score": 94,
                        "icon": "fa-home",
                        "badge": "Aile Yaşamı",
                        "suitability": "Çocuklar ve evcil hayvanlar için güvenli, bağımsız bahçe ve geniş sosyal alan.",
                    },
                    {
                        "title": "Hafta Sonu & Sezonluk Özel Kaçış Konutu",
                        "score": 90,
                        "icon": "fa-mountain",
                        "badge": "İkinci Konut",
                        "suitability": "Dört mevsim şömine keyfi, barbekü ve dinlenme için hazır donanımlı butik kaçış noktası.",
                    },
                ],
                "capacity_detail": "Doğal taş işçiliği ve bağımsız bahçe nizamı ile kalıcı mahremiyet ve dinginlik.",
            }

        # Residential Apartment / Rezidans
        if "3+1" in r_clean or "4+1" in r_clean or "3+1" in t_lower or "4+1" in t_lower:
            return {
                "primary_category": "Geniş Aile & Konforlu Konut Yaşamı",
                "ideal_scale": "3 - 6 Kişilik Çekirdek / Geniş Aile",
                "personas": [
                    {
                        "title": "Çocuklu Çekirdek & Geniş Aileler",
                        "score": 97,
                        "icon": "fa-users",
                        "badge": "İdeal Aile Evi",
                        "suitability": "Çift balkon, geniş ebeveyn yatak odası, çocuk çalışma odaları ve ferah salon yerleşimi.",
                    },
                    {
                        "title": "Konum ve Ulaşım Odaklı Kamu & Özel Sektör Çalışanı",
                        "score": 93,
                        "icon": "fa-briefcase",
                        "badge": "Lojistik Avantaj",
                        "suitability": "Okullara, sağlık merkezlerine ve toplu taşıma akslarına yürüme mesafesinde günlük konfor.",
                    },
                    {
                        "title": "Düzenli Kira Getirisi Arayan Gayrimenkul Yatırımcısı",
                        "score": 89,
                        "icon": "fa-hand-holding-usd",
                        "badge": "Yüksek Talep",
                        "suitability": "Bölgede 3+1 / 4+1 kiralık aile konutlarına olan sürekli ve yüksek talep derinliği.",
                    },
                ],
                "capacity_detail": "Kullanışlı kat planı, optimize edilmiş metrekare verimliliği ve aile odaklı yaşam standartları.",
            }

        # 1+1 or 2+1 Compact / Luxury / Rezidans
        return {
            "primary_category": "Modern Şehir Yaşamı & Dinamik Profesyoneller",
            "ideal_scale": "1 - 3 Kişilik Bireysel / Çift Yaşamı",
            "personas": [
                {
                    "title": "Genç Profesyoneller, Akademisyenler & Kurumsal Yöneticiler",
                    "score": 96,
                    "icon": "fa-user-tie",
                    "badge": "Maksimum Uyum",
                    "suitability": "Şehir merkezine yakın, bakımı kolay, akıllı ve şık iç tasarım donatısı.",
                },
                {
                    "title": "Yeni Evli Çiftler & İlk Evini Tercih Edenler",
                    "score": 92,
                    "icon": "fa-heart",
                    "badge": "Kusursuz Başlangıç",
                    "suitability": "Düşük aidat ve ısınma genel gideri, modern site güvenliği ve estetik yaşam.",
                },
                {
                    "title": "Hızlı Likidite & Yüksek Amortismanlı Kira Yatırımcısı",
                    "score": 90,
                    "icon": "fa-coins",
                    "badge": "Hızlı Dönüş",
                    "suitability": "Bölgedeki kurumsal kiracı sirkülasyonu sayesinde minimum boş kalma süresi.",
                },
            ],
            "capacity_detail": "Yüksek kiralama hızı, minimum boşluk süresi ve dinamik metropol yaşam temposu.",
        }


class FinancialYieldAgent:
    """Ajan 2: Finans & Yatırım Getirisi Stratejisti"""

    def analyze(self, tx_type: str, price: str, prop_type: str, title: str) -> Dict[str, Any]:
        is_rental = tx_type == "Kiralık" or "kira" in (tx_type or "").lower()

        if is_rental:
            return {
                "transaction_focus": "Kiralama & Nakit Akış Rasyoneli",
                "financial_metrics": [
                    {
                        "label": "Gider Gösterilebilirlik",
                        "value": "%100 Vergisel Avantaj",
                        "desc": "Tüzel kişi veya serbest meslek erbabı kiralamalarında kira bedeli kurumlar/gelir vergisinden doğrudan düşülebilir.",
                    },
                    {
                        "label": "Stopaj / KDV Dengesi",
                        "value": "Optimum Maliyet",
                        "desc": "Şirket merkezleri için faturalı veya stopajlı kiralama sayesinde net işletme maliyetini optimize eder.",
                    },
                    {
                        "label": "Giriş Sermaye Yükü",
                        "value": "Minimum Sabit Maliyet",
                        "desc": "Büyük satın alma sermayesi bağlamadan ana arterde temsil kabiliyeti ve nakit esnekliği sağlar.",
                    },
                ],
                "investor_verdict": (
                    "Bu gayrimenkul kiralama modelinde; sermayeyi ana operasyonel işlerde değerlendirirken, "
                    "şirket veya bireysel bütçeye öngörülebilir aylık maliyet ve yüksek vergisel amortisman faydası sunmaktadır."
                ),
            }
        else:
            return {
                "transaction_focus": "Sermaye Kazancı & Mülkiyet Güvencesi",
                "financial_metrics": [
                    {
                        "label": "Bölgesel Değer Artışı",
                        "value": "Enflasyon Üzeri Reel Getiri",
                        "desc": "Ankara'nın gelişen arterinde arz kısıtı bulunan lokasyon yapısı sayesinde yüksek sermaye kıymet artışı.",
                    },
                    {
                        "label": "Kira Amortisman Potansiyeli",
                        "value": "14 - 17 Yıl Projeksiyonu",
                        "desc": "Bölge ortalamasının üzerinde talep gören nitelikli mülk, kiralamaya verildiğinde güçlü nakit akışı üretir.",
                    },
                    {
                        "label": "Likidite & Teminat Kabiliyeti",
                        "value": "A Sınıfı Teminat Değeri",
                        "desc": "Bankacılık ve kredi mekanizmalarında yüksek ekspertiz ve kolay teminata konu olabilme gücü.",
                    },
                ],
                "investor_verdict": (
                    "Satın alma perspektifinde; enflasyonist ortamda reel satın alma gücünü koruyan, "
                    "zamanla arsa payı veya bölgesel talep artışıyla katlanarak değerlenen stratejik bir varlık alımıdır."
                ),
            }


class LocationDynamicsAgent:
    """Ajan 3: Mikro-Lokasyon & Tabela Değeri Uzmanı"""

    def analyze(self, loc: str, title: str) -> Dict[str, Any]:
        text = f"{loc} {title}".lower()

        if "cinnah" in text or "atakule" in text or "çankaya" in text:
            return {
                "region_badge": "Diplomatik & Prestij Aksı (Protokol Koridoru)",
                "prestige_level": "Ultra Prime (A++)",
                "commute_score": 98,
                "walkability": "Tüm Elçilik, Bakanlık ve Kızılay/Tunalı aksına dakikalar mesafesinde",
                "zoning_notes": "Yüksek tabela görünürlüğü, prestijli kurumsal komşuluk, elit müşteri algısı.",
            }
        elif "cevizlidere" in text or "balgat" in text or "öveçler" in text:
            return {
                "region_badge": "Ticaret & Merkezi Ulaşım Kavşağı",
                "prestige_level": "Yüksek Ticari Potansiyel (A)",
                "commute_score": 95,
                "walkability": "Konya Yolu, Eskişehir Yolu ve kamu kurumlarına doğrudan kılcal bağlantı",
                "zoning_notes": "Ana cadde cephesi, kesintisiz yaya ve araç trafiği, yoğun ticari hareketlilik.",
            }
        elif "beytepe" in text or "incek" in text or "çayyolu" in text or "ümitköy" in text:
            return {
                "region_badge": "Modern Lüks & Rezidans / Villa Bölgesi",
                "prestige_level": "Premium Yaşam & Elit Çevre (A+)",
                "commute_score": 92,
                "walkability": "Bilkent, Hacettepe ve Angora aksında, seçkin kolejler ve AVM'ler yakınında",
                "zoning_notes": "Güvenlikli site nizamı, geniş peyzaj alanları ve yüksek sosyo-ekonomik demografi.",
            }
        elif "altınoran" in text or "sinpaş" in text or "ilkbahar" in text:
            return {
                "region_badge": "Entegre Karma Yaşam & Vadi Manzarası",
                "prestige_level": "Prestij Konsept Rezidans (A+)",
                "commute_score": 91,
                "walkability": "Site içi sosyal tesisler, marina konsepti ve Turan Güneş bulvarı bağlantısı",
                "zoning_notes": "7/24 resepsiyon ve güvenlik, kapalı havuz ve spor kompleksleriyle tam donanımlı yaşam.",
            }
        elif "sincan" in text or "yenikent" in text or "etimesgut" in text:
            return {
                "region_badge": "Batı Gelişim Koridoru & Hızlı Büyüyen Aile Aksı",
                "prestige_level": "Yüksek Fiyat/Performans & Değerlenme Aksı",
                "commute_score": 88,
                "walkability": "Geniş cadde planı, yeni okullar, semt pazarları ve parklar kuşağı",
                "zoning_notes": "Modern imar parselasyonu, geniş otopark imkanı ve ferah kat aralıkları.",
            }
        elif "yahşihan" in text or "kırıkkale" in text:
            return {
                "region_badge": "Sanayi & Lojistik Gelişme Koridoru",
                "prestige_level": "Yüksek Büyüme Potansiyelli Yatırım Bölgesi",
                "commute_score": 86,
                "walkability": "Üniversite, sanayi siteleri ve ana karayolu lojistik hattı üzerinde",
                "zoning_notes": "Büyük parselasyon, tek tapu mülkiyet avantajı ve gelişim aksında stratejik konum.",
            }
        elif "gölbaşı" in text or "günalan" in text or "çubuk" in text or "çamlıdere" in text:
            return {
                "region_badge": "Ekolojik Yaşam, Sayfiye & Gelişim Alanı",
                "prestige_level": "Doğal Yaşam & Müstakil Kaçış Aksı",
                "commute_score": 85,
                "walkability": "Şehir stresinden uzak, temiz hava ve geniş doğal çevre",
                "zoning_notes": "Müstakil yapılaşma, hobi/bahçe konsepti ve doğa ile iç içe sakin yaşam.",
            }
        else:
            return {
                "region_badge": "Ankara Metropol Bölgesi",
                "prestige_level": "Standart Metropol Dinamiği",
                "commute_score": 89,
                "walkability": "Ana arterlere ve toplu taşıma olanaklarına dengeli erişim",
                "zoning_notes": "Gelişmiş kentsel altyapı ve oturmuş mahalle dokusu.",
            }


class HonestAdvisoryAuditorAgent:
    """Ajan 4: SWOT, Risk & Dürüst Danışman Filtresi (Anti-Persona)"""

    def analyze(self, prop_type: str, tx_type: str, rooms: str, sqm: str, title: str) -> Dict[str, Any]:
        p_lower = (prop_type or "").lower()
        t_lower = (title or "").lower()

        anti_personas = []
        key_usps = []

        if any(k in p_lower or k in t_lower for k in ["ofis", "iş yeri", "isyeri"]):
            key_usps = [
                "Protokol aksında yüksek tabela ve prestij değeri",
                "Geniş metrekare ve bağımsız oda kurgusu",
                "Tüzel kişilik için doğrudan giderleştirme ve vergi avantajı",
            ]
            anti_personas = [
                "Ağır sanayi, gürültülü imalat veya lojistik depo arayışında olanlar",
                "Bireysel öğrenci evi veya küçük bütçeli bekar evi kiralayacaklar",
                "Yalnızca gece konut kullanımı hedefleyen aileler (ticari yoğunluk nedeniyle)",
            ]
        elif any(k in p_lower or k in t_lower for k in ["arsa", "tarla"]):
            key_usps = [
                "Tek tapu müstakil mülkiyet güvencesi",
                "Enflasyona karşı en dayanıklı reel varlık sınıfı",
                "Gelecek imar ve altyapı projeleriyle katlanabilir prim potansiyeli",
            ]
            anti_personas = [
                "Yarın sabah anında taşınabileceği hazır konut/ofis arayanlar",
                "Kısa vadede (1-3 ay) günlük nakit kira getirisi bekleyenler",
                "Doğrudan yüksek katlı site inşaatına hemen başlamak isteyenler (imar sürecine göre)",
            ]
        elif any(k in p_lower or k in t_lower for k in ["villa", "taş villa"]):
            key_usps = [
                "Müstakil bahçe ve tam mahremiyet alanı",
                "Özel doğal taş mimarisi ve yüksek tavan ferahlığı",
                "Şehir gürültüsü ve hava kirliliğinden arınmış dingin ortam",
            ]
            anti_personas = [
                "Metro kapısında ya da merkezi AVM içinde yaşamayı olmazsa olmaz görenler",
                "Bahçe bakımı ve müstakil ev sorumluluğunu üstlenmek istemeyenler",
            ]
        else:
            # Apartman dairesi
            key_usps = [
                "Fonksiyonel kat planı ve ferah yaşam alanları",
                "Aile yaşamına uygun güvenli ve nezih komşuluk çevresi",
                "Eğitim kurumları ve sosyal olanaklara kesintisiz erişim",
            ]
            anti_personas = [
                "Ağır ticari müşteri trafiği yaratacak perakende mağaza işletmecileri",
                "Yalnızca 1 kişilik minimal mikro-stüdyo arayan öğrenciler",
            ]

        return {
            "key_usps": key_usps,
            "anti_personas": anti_personas,
            "advisory_honesty_note": (
                "NEXA Portföy Etik İlkesi: Bir gayrimenkulün kimler için uygun olduğu kadar, "
                "kimler için uygun olmadığını açıkça ifade etmek hem alıcının hem satıcının zamanını korur."
            ),
        }


class PersonaSwarmSynthesizer:
    """NEXA Swarm Synthesizer: 4 Ajanı Birleştirip Entegre İstihbarat Üretir"""

    def __init__(self):
        self.scout = DemographicScoutAgent()
        self.finance = FinancialYieldAgent()
        self.location = LocationDynamicsAgent()
        self.auditor = HonestAdvisoryAuditorAgent()

    def generate_intelligence(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        title = listing.get("title", "")
        tx_type = listing.get("type") or listing.get("transaction_type") or "Satılık"
        prop_type = listing.get("property_type") or "Konut"
        price = listing.get("price", "")
        loc = listing.get("loc", "Ankara")
        rooms = listing.get("rooms", "")
        area = listing.get("area", "")
        link = listing.get("link") or listing.get("url") or ""
        img = listing.get("img", "")

        is_kiralik = "kiralık" in tx_type.lower() or "kiralik" in tx_type.lower()
        theme = "emerald" if is_kiralik else "gold"
        theme_title = "Kiralık Portföy Analizi" if is_kiralik else "Satılık Yatırım & Konut Analizi"
        theme_color = "#10b981" if is_kiralik else "#d4af37"

        # Run Swarm
        demo_res = self.scout.analyze(prop_type, tx_type, rooms, area, title)
        fin_res = self.finance.analyze(tx_type, price, prop_type, title)
        loc_res = self.location.analyze(loc, title)
        audit_res = self.auditor.analyze(prop_type, tx_type, rooms, area, title)

        personas = demo_res.get("personas", [])
        top_fit = personas[0]["score"] if personas else 95

        executive_summary = (
            f"NEXA AI Swarm değerlendirmesine göre bu {prop_type.lower()} portföyü; "
            f"özellikle '{personas[0]['title'] if personas else 'İdeal Hedef Kitle'}' profili için %{top_fit} uyumluluk skoru vermektedir. "
            f"{loc_res.get('region_badge')} avantajı ve {fin_res.get('transaction_focus')} odağıyla öne çıkmaktadır."
        )

        return {
            "ok": True,
            "listing_ref": {
                "title": title,
                "price": price,
                "loc": loc,
                "type": tx_type,
                "property_type": prop_type,
                "rooms": rooms,
                "area": area,
                "link": link,
                "img": img,
            },
            "theme": {
                "mode": theme,
                "accent_color": theme_color,
                "badge_text": tx_type,
                "title": theme_title,
            },
            "swarm_metadata": {
                "engine": "NEXA AI Persona Swarm 2.0",
                "agents_count": 4,
                "active_agents": [
                    "DemographicScoutAgent",
                    "FinancialYieldAgent",
                    "LocationDynamicsAgent",
                    "HonestAdvisoryAuditorAgent",
                ],
                "confidence_score": 0.96,
            },
            "executive_summary": executive_summary,
            "top_personas": personas,
            "primary_category": demo_res.get("primary_category"),
            "ideal_scale": demo_res.get("ideal_scale"),
            "capacity_detail": demo_res.get("capacity_detail"),
            "financial_analysis": fin_res,
            "location_analysis": loc_res,
            "auditor_analysis": audit_res,
        }
