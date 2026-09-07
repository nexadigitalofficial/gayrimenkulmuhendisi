# -*- coding: utf-8 -*-
"""
NEXA Real Estate Intelligence Network - Daily Crawler & Pipeline Runner
Coldwell Banker CB VIP Ankara • Yiğit Narin

Executes the end-to-end multi-source ingestion, deduplication, verification,
scoring, and publication pipeline.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def run_pipeline():
    print("=" * 60)
    print("NEXA REAL ESTATE INTELLIGENCE NETWORK - PIPELINE EXECUTION")
    print("=" * 60)
    
    from intelligence.pipeline import IntelligencePipeline
    pipeline = IntelligencePipeline()
    result = pipeline.run()
    
    print(f"\nPipeline Finished Successfully:")
    print(f"  Items Found: {result.items_found}")
    print(f"  Articles Published: {result.published_count}")
    print(f"  Duplicates Merged: {result.duplicates_merged}")
    print(f"  Facts Verified: {result.verified_count}")
    print(f"  Execution Time: {result.latency_ms} ms")
    return True

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
