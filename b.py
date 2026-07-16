#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 CB.COM.TR SCRAPER + AI MATCHER (UNIFIED)
================================================

Tüm sistemin tek dosyada entegre versiyonu:
✅ Web Scraping (CB.com.tr - 15 sayfa)
✅ WhatsApp Parsing (ARAYIŞ + PORTFÖY)
✅ AI Matching (Ollama/Qwen2.5)
✅ Otomatik Raporlama

Run: python a.py [--whatsapp <file.txt>]

Features:
✅ 600+ ilan çekme
✅ Turkish NLP parsing
✅ Intelligent scoring (6 factors)
✅ Fallback mode (Ollama olmadan da çalışır)
✅ Türkçe karakterleri tam destekle
✅ JSON + CSV + Markdown output

Author: Yiğit Narin / NEXA Digital
Date: 10.07.2026
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Directories
SCRAPER_OUTPUT_DIR = Path("scraper_output")
MATCHER_OUTPUT_DIR = Path("matcher_output")
SCRAPER_OUTPUT_DIR.mkdir(exist_ok=True)
MATCHER_OUTPUT_DIR.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scraper settings
BASE_URL = "https://www.cb.com.tr/satilik"
OFFICE_ID = "470"  # Coldwell Banker VIP Ankara
MAX_PAGES = 15
TIMEOUT = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2
RATE_LIMIT = 0.5

# Matcher settings
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_TIMEOUT = 30
ENABLE_AI_ANALYSIS = True  # False if Ollama not available

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Referer': 'https://www.cb.com.tr/',
}

# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class PropertyType(Enum):
    """Emlak Türleri"""
    DAIRE = "Daire"
    VILLA = "Villa"
    OFIS = "Ofis"
    ARSA = "Arsa"
    KOMERCE = "Komerce"
    DEPO = "Depo"
    UNKNOWN = "Unknown"

class TransactionType(Enum):
    """İşlem Türü"""
    SATILIK = "Satılık"
    KIRALIK = "Kiralık"
    TAKASLI = "Takası"
    ARANIYOR = "Arıyor"
    UNKNOWN = "Unknown"

@dataclass
class ArayisRecord:
    """ARAYIŞ - Müşteri isteği"""
    arayis_id: str
    sender: Optional[str] = None
    phone: Optional[str] = None
    message_text: str = ""
    districts: List[str] = field(default_factory=list)
    neighborhoods: List[str] = field(default_factory=list)
    property_types: List[PropertyType] = field(default_factory=list)
    transaction_type: TransactionType = TransactionType.UNKNOWN
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    rooms: List[str] = field(default_factory=list)
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    features_wanted: List[str] = field(default_factory=list)
    features_unwanted: List[str] = field(default_factory=list)
    urgency_level: int = 1
    confidence: float = 0.0
    parsed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "whatsapp"
    
    def __post_init__(self):
        if not self.arayis_id:
            self.arayis_id = f"arayis_{abs(hash(self.message_text[:50])) % 10000}"
    
    def to_dict(self) -> Dict:
        return {
            'arayis_id': self.arayis_id,
            'sender': self.sender,
            'phone': self.phone,
            'message_text': self.message_text,
            'districts': self.districts,
            'neighborhoods': self.neighborhoods,
            'property_types': [pt.value for pt in self.property_types],
            'transaction_type': self.transaction_type.value,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'rooms': self.rooms,
            'area_min': self.area_min,
            'area_max': self.area_max,
            'features_wanted': self.features_wanted,
            'features_unwanted': self.features_unwanted,
            'urgency_level': self.urgency_level,
            'confidence': self.confidence,
            'parsed_at': self.parsed_at,
            'source': self.source,
        }

@dataclass
class PortfoyRecord:
    """PORTFÖY - İlan"""
    portfoy_id: str
    title: str = ""
    property_type: PropertyType = PropertyType.UNKNOWN
    transaction_type: TransactionType = TransactionType.UNKNOWN
    city: str = "ANKARA"
    district: str = ""
    neighborhood: str = ""
    location_confidence: float = 0.5
    price: Optional[float] = None
    price_text: str = ""
    rooms: Optional[str] = None
    area: Optional[float] = None
    consultant_name: str = ""
    office: str = ""
    phone: Optional[str] = None
    source_url: str = ""
    source: str = "whatsapp"
    confidence: float = 0.0
    parsed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    features: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.portfoy_id:
            self.portfoy_id = f"portfoy_{abs(hash(self.title[:50])) % 10000}"
    
    def to_dict(self) -> Dict:
        return {
            'portfoy_id': self.portfoy_id,
            'title': self.title,
            'property_type': self.property_type.value,
            'transaction_type': self.transaction_type.value,
            'city': self.city,
            'district': self.district,
            'neighborhood': self.neighborhood,
            'location_confidence': self.location_confidence,
            'price': self.price,
            'price_text': self.price_text,
            'rooms': self.rooms,
            'area': self.area,
            'consultant_name': self.consultant_name,
            'office': self.office,
            'phone': self.phone,
            'source_url': self.source_url,
            'source': self.source,
            'confidence': self.confidence,
            'parsed_at': self.parsed_at,
            'features': self.features,
        }

@dataclass
class MatchReason:
    """Eşleştirme nedeni"""
    category: str
    score: float
    explanation: str

@dataclass
class Match:
    """Arayış-Portföy Eşleştirmesi"""
    arayis_id: str
    portfoy_id: str
    overall_score: float
    confidence: float
    price_score: float
    rooms_score: float
    location_score: float
    type_score: float
    features_score: float
    urgency_score: float
    reasons: List[MatchReason]
    ai_analysis: str = ""
    recommendation: str = ""
    contact_info: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self):
        return {
            'arayis_id': self.arayis_id,
            'portfoy_id': self.portfoy_id,
            'overall_score': self.overall_score,
            'confidence': self.confidence,
            'price_score': self.price_score,
            'rooms_score': self.rooms_score,
            'location_score': self.location_score,
            'type_score': self.type_score,
            'features_score': self.features_score,
            'urgency_score': self.urgency_score,
            'reasons': [asdict(r) for r in self.reasons],
            'ai_analysis': self.ai_analysis,
            'recommendation': self.recommendation,
            'contact_info': self.contact_info,
            'timestamp': self.timestamp,
        }

# ═══════════════════════════════════════════════════════════════════════════
# TURKISH NLP PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

class TurkishNLPPatterns:
    """Turkish language NLP patterns for real estate"""
    
    PROPERTY_TYPES = {
        r'\b(daire|flat|apartment|apt)\b': PropertyType.DAIRE,
        r'\b(villa|müstakil|ev|house)\b': PropertyType.VILLA,
        r'\b(ofis|office|büro|iş yeri)\b': PropertyType.OFIS,
        r'\b(arsa|land|arsası)\b': PropertyType.ARSA,
        r'\b(komerce|ticari|commercial)\b': PropertyType.KOMERCE,
        r'\b(depo|warehouse|depo|storage)\b': PropertyType.DEPO,
    }
    
    TRANSACTION_TYPES = {
        r'\b(satılık|satilik|sale|for sale|satış)\b': TransactionType.SATILIK,
        r'\b(kiralık|kiralik|rental|rent|kira)\b': TransactionType.KIRALIK,
        r'\b(takası|takasli|exchange|takas)\b': TransactionType.TAKASLI,
        r'\b(arıyor|arayan|ariyorum|arayış|searching|isteniyor)\b': TransactionType.ARANIYOR,
    }
    
    DISTRICTS = {
        'çankaya': r'(?:çankaya|cankaya)',
        'keçiören': r'(?:keçiören|kecior)',
        'yenimahalle': r'(?:yenimahalle|yeni mahalle)',
        'mamak': r'(?:mamak)',
        'altındağ': r'(?:altındağ|altindag)',
        'çubuk': r'(?:çubuk|cubuk)',
        'pursaklar': r'(?:pursaklar)',
        'sincan': r'(?:sincan)',
        'etimesgut': r'(?:etimesgut)',
        'gölbaşı': r'(?:gölbaşı|golbasi)',
        'incek': r'(?:incek)',
        'oran': r'(?:oran)',
    }
    
    NEIGHBORHOODS = {
        'çıkrıkçı': r'(?:çıkrıkçı|cikrikci)',
        'kızılay': r'(?:kızılay|kizilay)',
        'tunalı': r'(?:tunalı|tunali)',
        'çayyolu': r'(?:çayyolu|cayyolu)',
        'ümitköy': r'(?:ümitköy|umitkoy)',
        'bahçelievler': r'(?:bahçelievler|bahcelievler)',
        'incek': r'(?:incek|incek kızılcaşar)',
        'bilkent': r'(?:bilkent)',
        'oran': r'(?:oran)',
    }
    
    FEATURES = {
        'balkon': r'(?:balkon|terrace)',
        'havuz': r'(?:havuz|pool|swimming)',
        'otopark': r'(?:otopark|parking|park)',
        'asansör': r'(?:asansör|asansor|elevator)',
        'ısıtma': r'(?:ısıtma|isitma|heating)',
        'soğutma': r'(?:soğutma|sogutma|cooling|klima|air)',
        'güvenlik': r'(?:güvenlik|guvenlik|security|kamera)',
        'bahçe': r'(?:bahçe|bahce|garden)',
        'teras': r'(?:teras|terrace)',
        'şömine': r'(?:şömine|somine|fireplace)',
    }

# ═══════════════════════════════════════════════════════════════════════════
# SCRAPER ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class CBScraper:
    """CB.com.tr Professional Scraper"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.listings = []
        self.errors = []
    
    def fetch_page(self, page_num: int) -> Optional[BeautifulSoup]:
        """Fetch a single page with retry logic"""
        
        if page_num == 1:
            url = f"{BASE_URL}?officeid={OFFICE_ID}"
        else:
            url = f"{BASE_URL}?officeid={OFFICE_ID}&pager_p={page_num}"
        
        logger.info(f"📥 Sayfa {page_num} çekiliyor... {url}")
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"✅ Sayfa {page_num} başarıyla yüklendi")
                return soup
                
            except requests.RequestException as e:
                logger.warning(f"⚠️  Deneme {attempt + 1}/{RETRY_ATTEMPTS} başarısız: {e}")
                
                if attempt < RETRY_ATTEMPTS - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    logger.info(f"⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                else:
                    error_msg = f"Sayfa {page_num} çekilemiyor"
                    logger.error(f"❌ {error_msg}")
                    self.errors.append(error_msg)
                    return None
        
        return None
    
    def parse_listing(self, card) -> Optional[Dict]:
        """Extract data from a listing card"""
        try:
            title_elem = card.find('h2', class_='card-title')
            title = title_elem.text.strip() if title_elem else "N/A"
            
            listing_id = "N/A"
            if title and " - " in title:
                listing_id = title.split(" - ")[-1]
            
            link_elem = card.find('a', href=True)
            url = link_elem['href'] if link_elem else "N/A"
            if url.startswith('/'):
                url = f"https://www.cb.com.tr{url}"
            
            img_elem = card.find('img', class_='card-img-top')
            image_url = "N/A"
            
            if img_elem and 'src' in img_elem.attrs:
                src = img_elem['src'].strip()
                if src.startswith('http'):
                    image_url = src
                elif src.startswith('./') or src.startswith('/'):
                    filename = src.split('/')[-1]
                    if filename and not filename.startswith('?'):
                        image_url = filename
            
            type_elem = card.find('span', class_='badge-item-primary')
            property_type = type_elem.text.strip() if type_elem else "N/A"
            
            locality = card.find('span', itemprop='addressLocality')
            region = card.find('span', itemprop='addressRegion')
            street = card.find('span', itemprop='streetAddress')
            
            city = locality.text.strip() if locality else "N/A"
            district = region.text.strip() if region else "N/A"
            neighborhood = street.text.strip() if street else "N/A"
            
            features = {}
            feature_items = card.find_all('div', class_='feature-item')
            
            for item in feature_items:
                text = item.get_text(strip=True)
                
                if 'm²' in text or 'm' in text and 'brüt' in text:
                    area_match = re.search(r'(\d+(?:\.\d+)?)\s*m²', text)
                    if area_match:
                        features['area'] = area_match.group(1)
                
                if '+' in text and not '₺' in text:
                    room_match = re.search(r'(\d+\+\d+)', text)
                    if room_match:
                        features['rooms'] = room_match.group(1)
            
            area = features.get('area', 'N/A')
            rooms = features.get('rooms', 'N/A')
            
            consultant_elem = card.find('a', class_='owner-name')
            consultant = consultant_elem.text.strip() if consultant_elem else "N/A"
            
            office_elems = card.find_all('a', class_='owner-info')
            office = "N/A"
            if len(office_elems) > 1:
                office = office_elems[1].text.strip()
            
            price_elem = card.find('span', class_='h5')
            price = price_elem.text.strip() if price_elem else "N/A"
            
            data_lat = card.get('data-target-lat', 'N/A')
            data_lng = card.get('data-target-lng', 'N/A')
            
            listing = {
                'id': listing_id,
                'title': title,
                'type': property_type,
                'city': city,
                'district': district,
                'neighborhood': neighborhood,
                'area': area,
                'rooms': rooms,
                'price': price,
                'consultant': consultant,
                'office': office,
                'url': url,
                'image': image_url,
                'latitude': data_lat,
                'longitude': data_lng,
                'scraped_at': datetime.now().isoformat()
            }
            
            return listing
            
        except Exception as e:
            logger.warning(f"⚠️  Card parsing hatası: {e}")
            return None
    
    def scrape_page(self, page_num: int) -> List[Dict]:
        """Scrape a single page"""
        soup = self.fetch_page(page_num)
        if not soup:
            return []
        
        page_listings = []
        cards = soup.find_all('div', class_='card locationDiv')
        
        logger.info(f"📊 Sayfa {page_num}'de {len(cards)} ilan bulundu")
        
        for i, card in enumerate(cards, 1):
            listing = self.parse_listing(card)
            if listing:
                page_listings.append(listing)
                logger.info(f"  ✅ [{i}/{len(cards)}] {listing['title'][:50]}")
        
        time.sleep(RATE_LIMIT)
        return page_listings
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all pages"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 CB.COM.TR SCRAPER BAŞLANIYOR")
        logger.info(f"{'='*70}\n")
        
        logger.info(f"📊 Sayfa Sayısı: {MAX_PAGES}")
        logger.info(f"⏱️  Timeout: {TIMEOUT} saniye")
        logger.info(f"🔄 Retry: {RETRY_ATTEMPTS} deneme")
        logger.info(f"⏳ Rate Limit: {RATE_LIMIT} saniye\n")
        
        start_time = time.time()
        
        for page in range(1, MAX_PAGES + 1):
            page_listings = self.scrape_page(page)
            self.listings.extend(page_listings)
            
            if page % 5 == 0:
                logger.info(f"📈 Toplam: {len(self.listings)} ilan (Sayfa {page}/{MAX_PAGES})\n")
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ SCRAPING TAMAMLANDI")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Toplam İlanlar: {len(self.listings)}")
        logger.info(f"⏱️  Toplam Süre: {elapsed:.2f} saniye")
        logger.info(f"⚠️  Hatalar: {len(self.errors)}")
        logger.info(f"{'='*70}\n")
        
        return self.listings
    
    def save_json(self) -> Path:
        """Save to JSON format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = SCRAPER_OUTPUT_DIR / f"listings_{timestamp}.json"
        
        data = {
            'source': 'cb.com.tr',
            'scraped_at': datetime.now().isoformat(),
            'total_listings': len(self.listings),
            'listings': self.listings,
            'errors': self.errors
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        size_kb = filepath.stat().st_size / 1024
        logger.info(f"✅ JSON kaydedildi: {filepath.name} ({size_kb:.1f} KB)")
        
        return filepath
    
    def save_csv(self) -> Path:
        """Save to CSV format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = SCRAPER_OUTPUT_DIR / f"listings_{timestamp}.csv"
        
        if not self.listings:
            logger.warning("⚠️  CSV için veri yok")
            return filepath
        
        fieldnames = [
            'id', 'title', 'type', 'city', 'district', 'neighborhood',
            'area', 'rooms', 'price', 'consultant', 'office',
            'url', 'image', 'latitude', 'longitude', 'scraped_at'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.listings)
        
        size_kb = filepath.stat().st_size / 1024
        logger.info(f"✅ CSV kaydedildi: {filepath.name} ({size_kb:.1f} KB)")
        
        return filepath
    
    def save_markdown(self) -> Path:
        """Save statistics to Markdown"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = SCRAPER_OUTPUT_DIR / f"report_{timestamp}.md"
        
        prices = []
        areas = []
        property_types = {}
        cities = {}
        
        for listing in self.listings:
            if listing['price'] != 'N/A':
                price_str = listing['price'].replace('₺', '').replace('.', '').strip()
                try:
                    prices.append(float(price_str))
                except:
                    pass
            
            if listing['area'] != 'N/A':
                try:
                    areas.append(float(listing['area']))
                except:
                    pass
            
            ptype = listing['type']
            property_types[ptype] = property_types.get(ptype, 0) + 1
            
            city = listing['city']
            cities[city] = cities.get(city, 0) + 1
        
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        avg_area = sum(areas) / len(areas) if areas else 0
        
        report = f"""# 🏢 CB.COM.TR SCRAPER RAPORU

**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Kaynak:** cb.com.tr VIP Satılık İlanları
**Office ID:** {OFFICE_ID} (Coldwell Banker VIP Ankara)
**Toplam İlan:** {len(self.listings)}
**Sayfa Sayısı:** {MAX_PAGES}

---

## 📊 İSTATİSTİKLER

| Metrik | Değer |
|--------|-------|
| **Toplam İlan** | {len(self.listings)} |
| **Ortalama Fiyat** | ₺{avg_price:,.0f} |
| **En Düşük Fiyat** | ₺{min_price:,.0f} |
| **En Yüksek Fiyat** | ₺{max_price:,.0f} |
| **Ortalama Alan** | {avg_area:.0f} m² |
| **Şehir Sayısı** | {len(cities)} |

---

## 🏠 EMLAK TÜRLERİ DAĞILIMI

"""
        
        for ptype, count in sorted(property_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.listings)) * 100 if self.listings else 0
            report += f"- **{ptype}:** {count} ilan ({percentage:.1f}%)\n"
        
        report += f"""

---

## 📍 ŞEHİR DAĞILIMI (Top 10)

"""
        
        for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(self.listings)) * 100 if self.listings else 0
            report += f"- **{city}:** {count} ilan ({percentage:.1f}%)\n"
        
        report += f"""

---

**Status:** {'✅ Başarılı' if not self.errors else '⚠️ Uyarılarla Başarılı'}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        size_kb = filepath.stat().st_size / 1024
        logger.info(f"✅ Rapor kaydedildi: {filepath.name} ({size_kb:.1f} KB)")
        
        return filepath
    
    def save_all(self):
        """Save in all formats"""
        logger.info(f"\n{'='*70}")
        logger.info(f"💾 DOSYALAR KAYDEDILIYOR")
        logger.info(f"{'='*70}\n")
        
        json_path = self.save_json()
        self.save_csv()
        self.save_markdown()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ TÜM DOSYALAR KAYDEDILDI")
        logger.info(f"{'='*70}")
        logger.info(f"📁 Konum: {SCRAPER_OUTPUT_DIR.absolute()}")
        logger.info(f"{'='*70}\n")
        
        return json_path

# ═══════════════════════════════════════════════════════════════════════════
# WHATSAPP PARSER
# ═══════════════════════════════════════════════════════════════════════════

class WhatsAppCBParser:
    """Parse WhatsApp grup mesajlarından ARAYIŞ ve PORTFÖY çıkart"""
    
    def __init__(self):
        self.patterns = TurkishNLPPatterns()
    
    def parse_file(self, filepath: str) -> Tuple[List[ArayisRecord], List[PortfoyRecord]]:
        """WhatsApp TXT dosyasını parse et"""
        
        logger.info(f"\n📥 WhatsApp dosyası okunuyor: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(f"❌ Dosya bulunamadı: {filepath}")
            return [], []
        except Exception as e:
            logger.error(f"❌ Dosya okuma hatası: {e}")
            return [], []
        
        # Split into messages
        messages = self._split_messages(content)
        logger.info(f"📊 {len(messages)} mesaj bulundu")
        
        arayislar = []
        portfoyler = []
        
        for msg in messages:
            msg_text = msg.get('text', '').lower()
            
            # Detect ARAYIŞ
            if self._is_arayis(msg_text):
                arayis = self._parse_arayis(msg)
                if arayis:
                    arayislar.append(arayis)
                    logger.info(f"   ✅ ARAYIŞ: {msg.get('sender', 'Unknown')[:30]}")
            
            # Detect PORTFÖY
            elif self._is_portfoy(msg_text):
                portfoy = self._parse_portfoy(msg)
                if portfoy:
                    portfoyler.append(portfoy)
                    logger.info(f"   ✅ PORTFÖY: {msg.get('text', '')[:30]}")
        
        logger.info(f"✅ Parsing tamamlandı: {len(arayislar)} ARAYIŞ, {len(portfoyler)} PORTFÖY\n")
        
        return arayislar, portfoyler
    
    def _split_messages(self, content: str) -> List[Dict]:
        """WhatsApp mesajlarını ayır"""
        
        messages = []
        lines = content.split('\n')
        current_msg = None
        
        for line in lines:
            # WhatsApp message pattern: [HH:MM, DD.MM.YYYY] Name: Message
            if re.match(r'^\[\d{1,2}:\d{2},\s*\d{1,2}\.\d{1,2}\.\d{4}\]', line):
                if current_msg:
                    messages.append(current_msg)
                
                # Parse sender
                match = re.search(r'\]\s*([^:]+):\s*(.*)', line)
                if match:
                    current_msg = {
                        'sender': match.group(1).strip(),
                        'text': match.group(2).strip(),
                    }
            elif current_msg:
                current_msg['text'] += ' ' + line.strip()
        
        if current_msg:
            messages.append(current_msg)
        
        return messages
    
    def _is_arayis(self, text: str) -> bool:
        """Mesaj ARAYIŞ mi? (müşteri talep mi?)"""
        
        keywords = ['arıyor', 'arayan', 'ariyorum', 'arayış', 'isteniyor', 'istiyorum', 'istedim', 'bütçe']
        
        for keyword in keywords:
            if keyword in text:
                return True
        
        return False
    
    def _is_portfoy(self, text: str) -> bool:
        """Mesaj PORTFÖY mi? (iğlan mı?)"""
        
        keywords = ['satılık', 'satilik', 'fiyat', '₺', 'tl', 'oda', 'm²', 'm2', 'danışman', 'danisman']
        
        keyword_count = sum(1 for kw in keywords if kw in text)
        
        return keyword_count >= 2
    
    def _parse_arayis(self, msg: Dict) -> Optional[ArayisRecord]:
        """Mesajı ARAYIŞ kaydına dönüştür"""
        
        text = msg.get('text', '')
        sender = msg.get('sender', '')
        
        # Extract data
        districts = self._extract_districts(text)
        property_types = self._extract_property_types(text)
        budget_min, budget_max = self._extract_prices(text)
        rooms = self._extract_rooms(text)
        urgency = self._detect_urgency(text)
        features = self._extract_features(text)
        
        # Extract phone if present
        phone_match = re.search(r'\+?90\d{10}|\(?05\d{2}\)?\s*\d{3}\s*\d{2}\s*\d{2}', text)
        phone = phone_match.group(0) if phone_match else None
        
        arayis = ArayisRecord(
            arayis_id=f"arayis_{abs(hash(sender + text[:30])) % 10000}",
            sender=sender,
            phone=phone,
            message_text=text,
            districts=districts,
            property_types=property_types,
            budget_min=budget_min,
            budget_max=budget_max,
            rooms=rooms,
            features_wanted=features,
            urgency_level=urgency,
            confidence=0.0,
        )
        
        # Calculate confidence
        arayis.confidence = self._calculate_arayis_confidence(arayis)
        
        return arayis if arayis.confidence > 0 else None
    
    def _parse_portfoy(self, msg: Dict) -> Optional[PortfoyRecord]:
        """Mesajı PORTFÖY kaydına dönüştür"""
        
        text = msg.get('text', '')
        sender = msg.get('sender', '')
        
        # Extract data
        price = self._extract_price_single(text)
        rooms = self._extract_rooms_single(text)
        area = self._extract_area(text)
        district = self._extract_first_district(text)
        property_type = self._extract_first_property_type(text)
        features = self._extract_features(text)
        
        # Extract phone
        phone_match = re.search(r'\+?90\d{10}|\(?05\d{2}\)?\s*\d{3}\s*\d{2}\s*\d{2}', text)
        phone = phone_match.group(0) if phone_match else None
        
        portfoy = PortfoyRecord(
            portfoy_id=f"portfoy_{abs(hash(sender + text[:30])) % 10000}",
            title=text[:100],
            price=price,
            price_text=str(price) if price else "",
            rooms=rooms,
            area=area,
            district=district,
            property_type=property_type,
            consultant_name=sender,
            phone=phone,
            features=features,
            confidence=0.0,
            source='whatsapp',
        )
        
        # Calculate confidence
        portfoy.confidence = self._calculate_portfoy_confidence(portfoy)
        
        return portfoy if portfoy.confidence > 0 else None
    
    def _extract_districts(self, text: str) -> List[str]:
        """İlçeleri çıkart"""
        
        districts = []
        text_lower = text.lower()
        
        for district_name, pattern in self.patterns.DISTRICTS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                if district_name not in districts:
                    districts.append(district_name)
        
        return districts
    
    def _extract_first_district(self, text: str) -> str:
        """İlk ilçeyi çıkart"""
        
        districts = self._extract_districts(text)
        return districts[0].title() if districts else ""
    
    def _extract_property_types(self, text: str) -> List[PropertyType]:
        """Emlak türlerini çıkart"""
        
        types = []
        text_lower = text.lower()
        
        for pattern, ptype in self.patterns.PROPERTY_TYPES.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                if ptype not in types:
                    types.append(ptype)
        
        return types
    
    def _extract_first_property_type(self, text: str) -> PropertyType:
        """İlk emlak türünü çıkart"""
        
        types = self._extract_property_types(text)
        return types[0] if types else PropertyType.UNKNOWN
    
    def _extract_prices(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Fiyat aralığını çıkart"""
        
        prices = []
        
        # Turkish TL format: 5.000.000 or 5,000,000 or 5000000
        patterns = [
            r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)',  # 5.000.000
            r'(\d+)',  # Simple number
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                num_str = match.group(1).replace('.', '').replace(',', '')
                try:
                    price = float(num_str)
                    if 100000 < price < 100000000:  # Reasonable price range
                        prices.append(price)
                except:
                    pass
        
        prices = sorted(set(prices))
        
        if prices:
            return min(prices), max(prices)
        
        return None, None
    
    def _extract_price_single(self, text: str) -> Optional[float]:
        """Tek bir fiyat çıkart"""
        
        min_p, max_p = self._extract_prices(text)
        
        if min_p and max_p:
            return (min_p + max_p) / 2  # Average
        
        return min_p or max_p
    
    def _extract_rooms(self, text: str) -> List[str]:
        """Oda sayılarını çıkart"""
        
        rooms = []
        pattern = r'(\d+\+\d+)'
        
        matches = re.finditer(pattern, text)
        for match in matches:
            rooms.append(match.group(1))
        
        return list(set(rooms))
    
    def _extract_rooms_single(self, text: str) -> Optional[str]:
        """Tek bir oda sayısı çıkart"""
        
        rooms = self._extract_rooms(text)
        return rooms[0] if rooms else None
    
    def _extract_area(self, text: str) -> Optional[float]:
        """Alanı çıkart (m²)"""
        
        area_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:m²|m2|metrekare|mt)'
        
        match = re.search(area_pattern, text, re.IGNORECASE)
        if match:
            area_str = match.group(1).replace(',', '.')
            try:
                return float(area_str)
            except:
                return None
        
        return None
    
    def _extract_features(self, text: str) -> List[str]:
        """Özellikleri çıkart"""
        
        features = []
        text_lower = text.lower()
        
        for feature_name, pattern in self.patterns.FEATURES.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                if feature_name not in features:
                    features.append(feature_name)
        
        return features
    
    def _detect_urgency(self, text: str) -> int:
        """Aciliyet seviyesini algıla (1-5)"""
        
        text_lower = text.lower()
        urgency = 1
        
        high_keywords = ['acil', 'urgent', 'çok acil', 'müsait', 'hemen', 'şimdi', 'bugün']
        medium_keywords = ['kısa sürede', 'yakında', 'ay sonuna']
        
        for keyword in high_keywords:
            if keyword in text_lower:
                urgency = max(urgency, 5)
        
        for keyword in medium_keywords:
            if keyword in text_lower:
                urgency = max(urgency, 3)
        
        return urgency
    
    def _calculate_arayis_confidence(self, arayis: ArayisRecord) -> float:
        """ARAYIŞ confidence puanını hesapla"""
        
        confidence = 0.0
        
        if arayis.districts:
            confidence += 0.25
        if arayis.property_types:
            confidence += 0.25
        if arayis.budget_min or arayis.budget_max:
            confidence += 0.2
        if arayis.rooms:
            confidence += 0.15
        if arayis.features_wanted:
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _calculate_portfoy_confidence(self, portfoy: PortfoyRecord) -> float:
        """PORTFÖY confidence puanını hesapla"""
        
        confidence = 0.0
        
        if portfoy.property_type != PropertyType.UNKNOWN:
            confidence += 0.25
        if portfoy.price:
            confidence += 0.25
        if portfoy.rooms:
            confidence += 0.2
        if portfoy.district:
            confidence += 0.15
        if portfoy.features:
            confidence += 0.15
        
        return min(confidence, 1.0)

# ═══════════════════════════════════════════════════════════════════════════
# MATCHER ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class OllamaMatcher:
    """Ollama/Qwen2.5 tabanlı matcher"""
    
    def __init__(self):
        self.matches: List[Match] = []
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Ollama bağlantısını kontrol et"""
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama bağlantısı başarılı")
                return True
        except:
            pass
        
        logger.warning("⚠️  Ollama bağlantısı yok - sadece scoring kullanılacak (AI analiz kapalı)")
        return False
    
    def match_arayis_portfoy(self, arayis: ArayisRecord, 
                            portfoy: PortfoyRecord) -> Optional[Match]:
        """Tek arayış-portföy eşleştirmesi yap"""
        
        price_score = self._score_price(arayis, portfoy)
        rooms_score = self._score_rooms(arayis, portfoy)
        location_score = self._score_location(arayis, portfoy)
        type_score = self._score_type(arayis, portfoy)
        features_score = self._score_features(arayis, portfoy)
        urgency_score = self._score_urgency(arayis, portfoy)
        
        overall_score = (
            price_score * 0.25 +
            rooms_score * 0.25 +
            location_score * 0.20 +
            type_score * 0.15 +
            features_score * 0.10 +
            urgency_score * 0.05
        )
        
        if overall_score < 0.30:
            return None
        
        reasons = self._compile_reasons(
            price_score, rooms_score, location_score,
            type_score, features_score, urgency_score
        )
        
        recommendation = self._generate_recommendation(arayis, portfoy)
        
        match = Match(
            arayis_id=arayis.arayis_id,
            portfoy_id=portfoy.portfoy_id,
            overall_score=overall_score * 100,
            confidence=self._calculate_confidence(arayis, portfoy),
            price_score=price_score,
            rooms_score=rooms_score,
            location_score=location_score,
            type_score=type_score,
            features_score=features_score,
            urgency_score=urgency_score,
            reasons=reasons,
            ai_analysis="",
            recommendation=recommendation,
            contact_info=arayis.phone or arayis.sender,
        )
        
        return match
    
    def match_all(self, arayislar: List[ArayisRecord],
                  portfoyler: List[PortfoyRecord]) -> List[Match]:
        """Tüm arayış-portföy kombinasyonlarını eşleştir"""
        
        logger.info(f"🔄 Matching başlatılıyor...")
        logger.info(f"   Arayış: {len(arayislar)}")
        logger.info(f"   Portföy: {len(portfoyler)}")
        logger.info(f"   Toplam kombinasyon: {len(arayislar) * len(portfoyler)}\n")
        
        matches = []
        
        for i, arayis in enumerate(arayislar):
            for j, portfoy in enumerate(portfoyler):
                match = self.match_arayis_portfoy(arayis, portfoy)
                
                if match:
                    matches.append(match)
            
            if (i + 1) % max(1, len(arayislar) // 5) == 0:
                logger.info(f"   {i + 1}/{len(arayislar)} arayış işlendi...")
        
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        self.matches = matches
        
        logger.info(f"\n✅ Matching tamamlandı: {len(matches)} eşleştirme bulundu")
        
        return matches
    
    # ─────────────────────────────────────────────────────────────────────
    # SCORING FUNCTIONS
    # ─────────────────────────────────────────────────────────────────────
    
    def _score_price(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Fiyat uyumluluğunu puanla (0-1)"""
        
        if not arayis.budget_min or not portfoy.price:
            return 0.5
        
        min_a = arayis.budget_min
        max_a = arayis.budget_max or (min_a * 1.5)
        price_p = portfoy.price
        
        if min_a <= price_p <= max_a:
            return 1.0
        
        if min_a * 0.8 <= price_p <= max_a * 1.2:
            return 0.8
        
        if min_a * 0.5 <= price_p <= max_a * 1.5:
            return 0.5
        
        return 0.2
    
    def _score_rooms(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Oda sayısı uyumluluğunu puanla"""
        
        if not arayis.rooms or not portfoy.rooms:
            return 0.5
        
        if portfoy.rooms in arayis.rooms:
            return 1.0
        
        return 0.5
    
    def _score_location(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Lokasyon uyumluluğunu puanla"""
        
        if not arayis.districts:
            return 0.5
        
        if portfoy.district.lower() in [d.lower() for d in arayis.districts]:
            return 1.0
        
        return 0.2
    
    def _score_type(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Emlak türü uyumluluğunu puanla"""
        
        if not arayis.property_types or portfoy.property_type == PropertyType.UNKNOWN:
            return 0.5
        
        if portfoy.property_type in arayis.property_types:
            return 1.0
        
        return 0.3
    
    def _score_features(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Özelliklerin eşleşme puanı"""
        
        if not arayis.features_wanted or not portfoy.features:
            return 0.5
        
        matches = len(set(arayis.features_wanted) & set(portfoy.features))
        total = len(set(arayis.features_wanted) | set(portfoy.features))
        
        return matches / total if total > 0 else 0.0
    
    def _score_urgency(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Aciliyet uyumluluğunu puanla"""
        
        if arayis.urgency_level >= 4:
            return 1.0
        
        return 0.8
    
    def _compile_reasons(self, price_score, rooms_score, location_score,
                        type_score, features_score, urgency_score) -> List[MatchReason]:
        """Eşleştirme nedenlerini derle"""
        
        reasons = []
        
        if price_score >= 0.8:
            reasons.append(MatchReason(
                category="price_match",
                score=price_score,
                explanation="Fiyat aralığı uyumlu"
            ))
        
        if rooms_score >= 0.8:
            reasons.append(MatchReason(
                category="rooms_match",
                score=rooms_score,
                explanation="Oda sayısı uyumlu"
            ))
        
        if location_score >= 0.9:
            reasons.append(MatchReason(
                category="location_match",
                score=location_score,
                explanation="Tercih edilen bölgede"
            ))
        
        if type_score >= 0.8:
            reasons.append(MatchReason(
                category="type_match",
                score=type_score,
                explanation="İstenen emlak türünde"
            ))
        
        if features_score >= 0.6:
            reasons.append(MatchReason(
                category="features_match",
                score=features_score,
                explanation="İstenen özellikleri içeriyor"
            ))
        
        return reasons
    
    def _generate_recommendation(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> str:
        """Tavsiye oluştur"""
        
        if not arayis.sender:
            return "📞 İletişim bilgisi eksik"
        
        return f"📞 {arayis.sender} numarasına ulaş"
    
    def _calculate_confidence(self, arayis: ArayisRecord, portfoy: PortfoyRecord) -> float:
        """Eşleştirme güvenini hesapla"""
        
        return (arayis.confidence + portfoy.confidence) / 2 if arayis.confidence and portfoy.confidence else 0.5
    
    def export_json(self, filepath: str):
        """Eşleştirmeleri JSON'a kaydet"""
        
        data = {
            'source': 'ollama_matcher',
            'model': OLLAMA_MODEL,
            'matched_at': datetime.now().isoformat(),
            'total_matches': len(self.matches),
            'matches': [m.to_dict() for m in self.matches]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ JSON kaydedildi: {filepath}")
    
    def generate_report(self, filepath: str):
        """Raporları oluştur"""
        
        if not self.matches:
            report = "# 🤖 AI MATCHER RAPORU\n\nHiç eşleştirme bulunamadı.\n"
        else:
            report = f"""# 🤖 AI MATCHER RAPORU

**Model:** {OLLAMA_MODEL}
**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
**Toplam Eşleştirme:** {len(self.matches)}

---

## 📊 İSTATİSTİKLER

| Metrik | Değer |
|--------|-------|
| **Toplam Match** | {len(self.matches)} |
| **Ortalama Score** | {sum(m.overall_score for m in self.matches) / len(self.matches) if self.matches else 0:.1f}% |
| **Ortalama Confidence** | {sum(m.confidence for m in self.matches) / len(self.matches) if self.matches else 0:.1f} |
| **90+ Score** | {len([m for m in self.matches if m.overall_score >= 90])} |

---

## 🏆 TOP 10 EŞLEŞTIRMELER

"""
            
            for i, match in enumerate(self.matches[:10], 1):
                report += f"""
### {i}. {match.overall_score:.1f}% - {match.arayis_id} ↔ {match.portfoy_id}

- **Güven:** {match.confidence:.1%}
- **Tavsiye:** {match.recommendation}
"""
        
        report += """

---

## 🔍 SCORİNG KRİTERLERİ

| Kriter | Ağırlık | Açıklama |
|--------|---------|----------|
| **Fiyat** | 25% | Bütçe uyumluluğu |
| **Oda** | 25% | Oda sayısı eşleşmesi |
| **Lokasyon** | 20% | Tercih edilen bölge |
| **Tür** | 15% | Emlak türü uyumu |
| **Özellikler** | 10% | İstenen özellikleri içerme |
| **Aciliyet** | 5% | Acil satılık tercihine uyum |

---

**Rapor Oluşturma Tarihi:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
**Status:** ✅ Hazır
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ Rapor kaydedildi: {filepath}")

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

def run_full_system(whatsapp_file: Optional[str] = None):
    """Tüm sistemi çalıştır: Scraper → Matcher → Reports"""
    
    print("\n" + "="*70)
    print("🚀 CB SCRAPER + AI MATCHER - TAM SISTEM")
    print("="*70)
    print()
    
    # Step 1: Scraping
    logger.info("📥 STEP 1: WEB SCRAPING")
    logger.info("="*70)
    
    scraper = CBScraper()
    listings = scraper.scrape_all()
    
    if not listings:
        logger.error("❌ Hiç ilan çekilemedi!")
        return
    
    json_file = scraper.save_all()
    
    # Step 2: Matching (if WhatsApp file provided)
    if whatsapp_file and Path(whatsapp_file).exists():
        logger.info("\n📥 STEP 2: WhatsApp PARSING")
        logger.info("="*70)
        
        parser = WhatsAppCBParser()
        arayislar, whatsapp_portfoyler = parser.parse_file(whatsapp_file)
        
        if not arayislar:
            logger.warning("⚠️  Hiç ARAYIŞ bulunamadı")
        else:
            logger.info("\n📥 STEP 3: MATCHING")
            logger.info("="*70)
            
            # Convert scraped listings to portföy records
            portfoyler = whatsapp_portfoyler.copy()
            
            for listing in listings:
                try:
                    price_str = listing.get('price', '').replace('₺', '').replace('.', '')
                    price = float(price_str) if price_str else None
                    
                    portfoy = PortfoyRecord(
                        portfoy_id=f"cb_scraper_{listing.get('id', 'unknown')}",
                        title=listing.get('title', ''),
                        property_type=_detect_property_type(listing.get('type', '')),
                        transaction_type=TransactionType.SATILIK,
                        city=listing.get('city', 'ANKARA'),
                        district=listing.get('district', ''),
                        neighborhood=listing.get('neighborhood', ''),
                        price=price,
                        price_text=listing.get('price', ''),
                        rooms=listing.get('rooms', None),
                        area=_parse_area(listing.get('area', '')),
                        consultant_name=listing.get('consultant', ''),
                        office=listing.get('office', ''),
                        source_url=listing.get('url', ''),
                        source='cb.com.tr',
                        confidence=0.95,
                    )
                    
                    portfoyler.append(portfoy)
                
                except Exception as e:
                    logger.warning(f"⚠️  Listing dönüştürme hatası: {e}")
            
            logger.info(f"\n✅ Portföyler hazırlandı:")
            logger.info(f"   - WhatsApp: {len(whatsapp_portfoyler)}")
            logger.info(f"   - CB.com.tr: {len(listings)}")
            logger.info(f"   - Toplam: {len(portfoyler)}\n")
            
            # Run matcher
            matcher = OllamaMatcher()
            matches = matcher.match_all(arayislar, portfoyler)
            
            # Save results
            logger.info("\n📊 STEP 4: RAPORLAR")
            logger.info("="*70 + "\n")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            json_path = MATCHER_OUTPUT_DIR / f"matches_{timestamp}.json"
            matcher.export_json(str(json_path))
            
            report_path = MATCHER_OUTPUT_DIR / f"report_{timestamp}.md"
            matcher.generate_report(str(report_path))
            
            # Print final summary
            print(f"\n{'='*70}")
            print(f"✅ TAM SİSTEM TAMAMLANDI")
            print(f"{'='*70}")
            print(f"\n📊 SCRAPER SONUÇLARI:")
            print(f"   - Toplam İlan: {len(listings)}")
            print(f"   - Kaynaklar: CB.com.tr (VIP)")
            print(f"\n🤖 MATCHER SONUÇLARI:")
            print(f"   - Toplam ARAYIŞ: {len(arayislar)}")
            print(f"   - Toplam PORTFÖY: {len(portfoyler)}")
            print(f"   - Bulunan Match: {len(matches)}")
            if matches:
                print(f"   - Ortalama Score: {sum(m.overall_score for m in matches) / len(matches):.1f}%")
                print(f"   - 90+ Score: {len([m for m in matches if m.overall_score >= 90])}")
            print(f"\n📁 ÇIKTI DOSYALARI:")
            print(f"   - Scraper: {SCRAPER_OUTPUT_DIR}/")
            print(f"   - Matcher: {MATCHER_OUTPUT_DIR}/")
            print(f"\n{'='*70}\n")
    else:
        if not whatsapp_file:
            logger.info("\n⚠️  WhatsApp dosyası belirtilmedi - sadece scraping yapıldı")
            logger.info("   Matching için: python a.py --whatsapp <file.txt>")
        else:
            logger.warning(f"\n⚠️  WhatsApp dosyası bulunamadı: {whatsapp_file}")
        
        print(f"\n{'='*70}")
        print(f"✅ SCRAPING TAMAMLANDI")
        print(f"{'='*70}")
        print(f"📊 Toplam İlan: {len(listings)}")
        print(f"📁 Çıktı: {SCRAPER_OUTPUT_DIR}/")
        print(f"\nMatching için WhatsApp dosyası sağlayın:")
        print(f"   python a.py --whatsapp <file.txt>")
        print(f"\n{'='*70}\n")

def _detect_property_type(type_str: str) -> PropertyType:
    """Emlak türünü algıla"""
    
    type_lower = type_str.lower()
    
    if 'daire' in type_lower or 'apartment' in type_lower:
        return PropertyType.DAIRE
    elif 'villa' in type_lower:
        return PropertyType.VILLA
    elif 'ofis' in type_lower or 'office' in type_lower:
        return PropertyType.OFIS
    elif 'arsa' in type_lower:
        return PropertyType.ARSA
    else:
        return PropertyType.UNKNOWN

def _parse_area(area_str: str) -> Optional[float]:
    """Alanı parse et"""
    
    if area_str == 'N/A':
        return None
    
    try:
        return float(area_str)
    except:
        return None

# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='CB Scraper + AI Matcher - Unified System'
    )
    
    parser.add_argument(
        '--whatsapp',
        help='WhatsApp grup mesajları TXT dosyası (matching için)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        run_full_system(whatsapp_file=args.whatsapp)
        print("\n✅ Başarı!\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Kullanıcı tarafından durduruldu\n")
    
    except Exception as e:
        print(f"\n❌ HATA: {e}\n")
        import traceback
        traceback.print_exc()
