#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 SCRAPER + MATCHER INTEGRATED
================================
a.py (scraper) + matcher_orchestrator entegrasyonu
Scraper tamamlandıktan sonra otomatik olarak matching çalıştır
"""

import os
import glob
import logging
from pathlib import Path
from datetime import datetime

# Import from a.py
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Try to import existing modules
try:
    from a import CBScraper
except ImportError:
    print("❌ a.py dosyası bulunamadı")
    sys.exit(1)

# Import matcher modules
from matcher_orchestrator import MatcherOrchestrator

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# Setup logging
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATED SCRAPER + MATCHER
# ═══════════════════════════════════════════════════════════════════════════

class ScraperWithMatcher:
    """
    CB Scraper + AI Matcher entegrasyonu
    
    Workflow:
    1. Run scraper (a.py)
    2. Scraper outputs JSON
    3. Automatically run matcher
    4. Generate reports
    5. Export results
    """
    
    def __init__(self, whatsapp_txt: str = None, 
                 scraper_output_dir: str = "scraper_output",
                 matcher_output_dir: str = "matcher_output"):
        """
        Args:
            whatsapp_txt: WhatsApp grup mesajları dosyası
            scraper_output_dir: a.py scraper çıktı klasörü
            matcher_output_dir: Matcher çıktı klasörü
        """
        
        self.whatsapp_txt = whatsapp_txt or self._find_whatsapp_file()
        self.scraper_output_dir = Path(scraper_output_dir)
        self.matcher_output_dir = Path(matcher_output_dir)
        
        logger.info(f"🔗 Scraper + Matcher Entegrasyonu başlatıldı")
        logger.info(f"   WhatsApp: {self.whatsapp_txt}")
        logger.info(f"   Scraper Output: {self.scraper_output_dir}")
        logger.info(f"   Matcher Output: {self.matcher_output_dir}\n")
    
    def _find_whatsapp_file(self) -> str:
        """WhatsApp TXT dosyasını bul"""
        
        patterns = [
            "*WhatsApp*.txt",
            "*Coldwell*.txt",
            "*CB*.txt",
            "*grup*.txt",
        ]
        
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                return files[0]
        
        # Default location
        default = "_Coldwell_Banker_Ankara_ile_WhatsApp_Sohbeti.txt"
        if os.path.exists(default):
            return default
        
        return None
    
    def run_full_pipeline(self) -> bool:
        """
        Tam pipeline'ı çalıştır:
        1. Scraper
        2. Matcher
        3. Reports
        """
        
        print(f"\n{'='*70}")
        print(f"🚀 CB SCRAPER + AI MATCHER - TAM PIPELINE")
        print(f"{'='*70}\n")
        
        # Step 1: Run scraper
        logger.info(f"{'='*70}")
        logger.info(f"📥 STEP 1: WEB SCRAPING")
        logger.info(f"{'='*70}\n")
        
        scraper = CBScraper()
        listings = scraper.scrape_all()
        scraper.save_all()
        
        # Get latest JSON file
        latest_json = self._get_latest_scraper_json()
        
        if not latest_json:
            logger.error("❌ Scraper JSON dosyası bulunamadı")
            return False
        
        logger.info(f"\n✅ Scraper tamamlandı")
        logger.info(f"   Dosya: {latest_json}")
        logger.info(f"   İlanlar: {len(listings)}\n")
        
        # Step 2: Check WhatsApp file
        if not self.whatsapp_txt or not os.path.exists(self.whatsapp_txt):
            logger.warning(f"⚠️  WhatsApp dosyası bulunamadı")
            logger.warning(f"   Kontrol et: {self.whatsapp_txt}")
            logger.warning(f"   Matcher olmadan scraper sonuçları kaydedildi\n")
            return True
        
        # Step 3: Run matcher
        logger.info(f"\n{'='*70}")
        logger.info(f"🤖 STEP 2: AI MATCHING")
        logger.info(f"{'='*70}\n")
        
        try:
            orchestrator = MatcherOrchestrator(
                output_dir=str(self.matcher_output_dir)
            )
            
            matches, stats = orchestrator.run_full_pipeline(
                listings_json=str(latest_json),
                whatsapp_txt=str(self.whatsapp_txt)
            )
            
            # Print summary
            self._print_final_summary(listings, matches, stats)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Matcher hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_latest_scraper_json(self) -> str:
        """En son scraper JSON dosyasını getir"""
        
        json_files = list(self.scraper_output_dir.glob("listings_*.json"))
        
        if not json_files:
            return None
        
        # Sort by modification time (latest first)
        json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return str(json_files[0])
    
    def _print_final_summary(self, listings, matches, stats):
        """Final özet bastır"""
        
        print(f"\n{'='*70}")
        print(f"✅ TAM PIPELINE TAMAMLANDI")
        print(f"{'='*70}\n")
        
        print(f"📊 SCRAPER SONUÇLARI:")
        print(f"   - Toplam İlan: {len(listings)}")
        print(f"   - Kaynaklar: CB.com.tr (VIP)")
        print(f"   - Format: JSON, CSV, Markdown")
        
        if matches:
            print(f"\n🤖 MATCHER SONUÇLARI:")
            print(f"   - Toplam Match: {stats['total_matches']}")
            print(f"   - Ortalama Score: {stats['avg_score']:.1f}%")
            print(f"   - 90+ Score: {stats['high_quality']}")
            print(f"   - 70-89 Score: {stats['good_quality']}")
            print(f"   - 50-69 Score: {stats['medium_quality']}")
        
        print(f"\n📁 ÇIKTI DOSYALARI:")
        print(f"   - Scraper: {self.scraper_output_dir}/")
        print(f"   - Matcher: {self.matcher_output_dir}/")
        
        print(f"\n{'='*70}\n")

# ═══════════════════════════════════════════════════════════════════════════
# USAGE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

def example_usage():
    """Kullanım örnekleri"""
    
    # Pattern 1: Default paths
    pipeline = ScraperWithMatcher()
    pipeline.run_full_pipeline()
    
    # Pattern 2: Custom paths
    # pipeline = ScraperWithMatcher(
    #     whatsapp_txt="path/to/whatsapp.txt",
    #     scraper_output_dir="custom_scraper_output",
    #     matcher_output_dir="custom_matcher_output"
    # )
    # pipeline.run_full_pipeline()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='CB Scraper + AI Matcher'
    )
    parser.add_argument(
        '--whatsapp',
        help='WhatsApp grup mesajları dosyası',
        default=None
    )
    parser.add_argument(
        '--scraper-output',
        help='Scraper çıktı klasörü',
        default='scraper_output'
    )
    parser.add_argument(
        '--matcher-output',
        help='Matcher çıktı klasörü',
        default='matcher_output'
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = ScraperWithMatcher(
        whatsapp_txt=args.whatsapp,
        scraper_output_dir=args.scraper_output,
        matcher_output_dir=args.matcher_output
    )
    
    success = pipeline.run_full_pipeline()
    
    exit(0 if success else 1)
