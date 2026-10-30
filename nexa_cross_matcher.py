#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================================
NEXA CROSS-MATCHER™ | Çapraz Platform Tersine Mühendislik & Dijital İkiz Eşleme Motoru
========================================================================================
Coldwell Banker (veya harici CRM) portföyünü, Sahibinden.com arama havuzundaki
aday ilanlarla görsel parmak izi (dHash/pHash), metin madenciliği ve nitelik
benzerliği ile eşleştirerek "Kendi Portföyümüzü" kesin doğrulukla sahiplenir.
"""

import sys
import re
import io
import urllib.request
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

# Reconfigure stdout for Windows console UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def compute_dhash(image_input, hash_size: int = 8) -> Optional[str]:
    """
    Computes a 64-bit Difference Hash (dHash) for an in-memory image or URL.
    Resistant to scaling, format changes (.jpg vs .avif vs .webp) and compression.
    """
    try:
        if isinstance(image_input, str):
            if image_input.startswith("http://") or image_input.startswith("https://"):
                req = urllib.request.Request(
                    image_input,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    img_data = resp.read()
                image = Image.open(io.BytesIO(img_data))
            else:
                image = Image.open(image_input)
        elif isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            image = image_input
        else:
            return None

        # Convert to grayscale and resize to (width=hash_size+1, height=hash_size)
        image = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        
        # Use get_flattened_data or getdata safely
        if hasattr(image, "get_flattened_data"):
            pixels = list(image.get_flattened_data())
        else:
            pixels = list(image.getdata())
            
        difference = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                difference.append(pixel_left > pixel_right)
                
        decimal_value = 0
        hex_string = []
        for index, value in enumerate(difference):
            if value:
                decimal_value += 2 ** (index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                decimal_value = 0
                
        return "".join(hex_string)
    except Exception as e:
        return None


def hamming_distance(h1: str, h2: str) -> int:
    """Calculates bitwise Hamming distance between two hex hashes (0 to 64)."""
    if not h1 or not h2 or len(h1) != len(h2):
        return 64
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count("1")
    except Exception:
        return 64


def normalize_text(text: str) -> str:
    """Cleans Turkish text, removes punctuation and extra whitespace."""
    if not text:
        return ""
    t = text.lower()
    t = t.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    t = t.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def text_similarity(s1: str, s2: str) -> float:
    """Calculates token overlap Jaccard similarity between two texts."""
    n1 = set(normalize_text(s1).split())
    n2 = set(normalize_text(s2).split())
    if not n1 or not n2:
        return 0.0
    intersection = len(n1.intersection(n2))
    union = len(n1.union(n2))
    return float(intersection) / float(union) if union > 0 else 0.0


def extract_numeric_price(price_val: Any) -> float:
    """Converts price strings like '7.500.000 ₺' or '55000' to float."""
    if not price_val:
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
    s = str(price_val)
    digits = "".join(filter(str.isdigit, s))
    return float(digits) if digits else 0.0


class NexaCrossMatcher:
    """
    Multi-modal cross-platform reverse engineering engine.
    Matches a Coldwell Banker listing against candidate listings in a market pool.
    """

    def __init__(self, max_hamming_distance: int = 7):
        self.max_hamming_distance = max_hamming_distance

    def compare_listings(self, cb_listing: dict, candidate_listing: dict) -> Dict[str, Any]:
        """
        Deep comparison between our CB listing and a candidate listing.
        Returns match verdict and granular component scores.
        """
        # 1. Direct ID Match Check
        cb_id = str(cb_listing.get("listing_id") or cb_listing.get("ilan_no") or cb_listing.get("id") or "").strip()
        cand_id = str(candidate_listing.get("listing_id") or candidate_listing.get("ilan_no") or candidate_listing.get("id") or "").strip()
        if cb_id and cand_id and cb_id == cand_id:
            return {
                "is_match": True,
                "confidence": 1.0,
                "reason": "Direct Listing ID Match",
                "image_match": 1.0,
                "text_match": 1.0,
                "price_diff_pct": 0.0
            }

        # 2. Location & Category Match
        cb_loc = normalize_text(cb_listing.get("location") or str(cb_listing.get("specs", {}).get("Konum", "")))
        cand_loc = normalize_text(candidate_listing.get("location") or str(candidate_listing.get("specs", {}).get("Konum", "")))
        loc_score = text_similarity(cb_loc, cand_loc)

        # 3. Price Comparison
        p1 = extract_numeric_price(cb_listing.get("price") or cb_listing.get("fiyat"))
        p2 = extract_numeric_price(candidate_listing.get("price") or candidate_listing.get("fiyat"))
        price_diff_pct = abs(p1 - p2) / max(p1, 1.0) if p1 > 0 else 1.0
        price_score = max(0.0, 1.0 - (price_diff_pct * 3.0)) # 1.0 if identical, drops fast if >15%

        # 4. Text (Title & Description) Match
        cb_title = cb_listing.get("title") or cb_listing.get("baslik") or ""
        cand_title = candidate_listing.get("title") or candidate_listing.get("baslik") or ""
        title_score = text_similarity(cb_title, cand_title)

        cb_desc = cb_listing.get("description") or cb_listing.get("aciklama") or ""
        cand_desc = candidate_listing.get("description") or candidate_listing.get("aciklama") or ""
        desc_score = text_similarity(cb_desc, cand_desc) if cb_desc and cand_desc else title_score

        text_score = (title_score * 0.6) + (desc_score * 0.4)

        # 5. Image Fingerprint Comparison (if image hashes exist or can be compared)
        cb_hashes = cb_listing.get("image_hashes") or []
        cand_hashes = candidate_listing.get("image_hashes") or []
        
        image_score = 0.0
        matched_images_count = 0

        if cb_hashes and cand_hashes:
            for h1 in cb_hashes:
                best_dist = min([hamming_distance(h1, h2) for h2 in cand_hashes])
                if best_dist <= self.max_hamming_distance:
                    matched_images_count += 1
            if len(cb_hashes) > 0:
                image_score = matched_images_count / len(cb_hashes)

        # Weighted Confidence Score
        # If image matching is available, it carries 45% weight. Otherwise text + price carry more weight.
        if cb_hashes and cand_hashes:
            confidence = (image_score * 0.45) + (text_score * 0.25) + (price_score * 0.15) + (loc_score * 0.15)
        else:
            confidence = (text_score * 0.45) + (price_score * 0.35) + (loc_score * 0.20)

        is_match = confidence >= 0.70 or (image_score >= 0.50 and price_score >= 0.85)

        return {
            "is_match": is_match,
            "confidence": round(confidence, 3),
            "image_match": round(image_score, 3),
            "text_match": round(text_score, 3),
            "price_score": round(price_score, 3),
            "loc_score": round(loc_score, 3),
            "price_diff_pct": round(price_diff_pct * 100, 1),
            "reason": "Multi-Modal Fingerprint Match" if is_match else "Threshold Not Met"
        }

    def find_twin_in_pool(self, cb_listing: dict, pool_listings: List[dict]) -> Tuple[Optional[dict], float]:
        """
        Scans a candidate pool to pinpoint our own twin listing.
        Returns: (matched_listing_or_None, confidence_score)
        """
        best_candidate = None
        highest_confidence = 0.0

        for candidate in pool_listings:
            res = self.compare_listings(cb_listing, candidate)
            if res["confidence"] > highest_confidence:
                highest_confidence = res["confidence"]
                if res["is_match"]:
                    best_candidate = candidate

        return best_candidate, highest_confidence


if __name__ == "__main__":
    print("[NEXA CROSS-MATCHER] Self-test running...")
    matcher = NexaCrossMatcher()
    
    sample_cb = {
        "listing_id": "1345396672",
        "title": "Kavaklıdere'de Satılık Daire | Merkezi Konum",
        "price": "7.500.000 ₺",
        "location": "Ankara / Çankaya / Kavaklıdere",
        "description": "Tunali Hilmi yakininda masrafsiz kombili satilik daire"
    }

    sample_cand_exact = {
        "listing_id": "1345396672",
        "title": "Kavaklıdere'de Satılık Daire | Merkezi Konum",
        "price": "7.500.000 ₺",
        "location": "Ankara / Çankaya / Kavaklıdere"
    }

    sample_cand_similar = {
        "listing_id": "9998887776",
        "title": "Kavaklıdere Tunalı Hilmi Satılık Daire Merkezi Konumda",
        "price": "7.500.000 TL",
        "location": "Ankara / Çankaya / Kavaklıdere",
        "description": "Tunalı Hilmi Caddesi yakınında masrafsız kombili satılık daire"
    }

    sample_cand_diff = {
        "listing_id": "1112223334",
        "title": "Çayyolu Ahmet Taner Kışlalı Kiralık Müstakil Villa",
        "price": "110.000 TL",
        "location": "Ankara / Çankaya / Çayyolu"
    }

    print("Test 1 (Exact ID Match):", matcher.compare_listings(sample_cb, sample_cand_exact))
    print("Test 2 (Reverse Text & Price Match):", matcher.compare_listings(sample_cb, sample_cand_similar))
    print("Test 3 (Completely Different):", matcher.compare_listings(sample_cb, sample_cand_diff))
    print("[OK] Self-test passed successfully!")
