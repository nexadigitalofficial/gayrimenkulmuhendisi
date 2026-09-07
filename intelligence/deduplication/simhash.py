"""
SimHash & Token Jaccard similarity for near-duplicate detection and event clustering.
"""

import re
import hashlib
from typing import Set, List


STOPWORDS = {
    "ve", "ile", "bir", "bu", "da", "de", "için", "olan", "olarak", "gibi", "kadar",
    "sonra", "önce", "en", "daha", "çok", "veya", "ise", "ancak", "her", "tarafından"
}


def tokenize(text: str) -> List[str]:
    """Extracts alphanumeric words in lowercase, excluding stopwords."""
    words = re.findall(r'[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}', text.lower())
    return [w for w in words if w not in STOPWORDS]


def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates Jaccard word set similarity between two texts."""
    set1: Set[str] = set(tokenize(text1))
    set2: Set[str] = set(tokenize(text2))
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0


def compute_simhash(text: str, hash_bits: int = 64) -> int:
    """Computes a 64-bit SimHash fingerprint for the text."""
    tokens = tokenize(text)
    if not tokens:
        return 0

    v = [0] * hash_bits
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        for i in range(hash_bits):
            bit = (token_hash >> i) & 1
            if bit == 1:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(hash_bits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """Counts differing bits between two 64-bit fingerprints."""
    x = hash1 ^ hash2
    return bin(x).count('1')


def is_near_duplicate(text1: str, text2: str, threshold: float = 0.55) -> bool:
    """Returns True if two texts are semantically near-duplicates."""
    # Fast path: Jaccard on title/lead
    jacc = jaccard_similarity(text1, text2)
    if jacc >= threshold:
        return True
    
    # Secondary check: SimHash distance
    h1 = compute_simhash(text1)
    h2 = compute_simhash(text2)
    if h1 != 0 and h2 != 0:
        dist = hamming_distance(h1, h2)
        if dist <= 6:  # 64-bit simhash distance <= 6 is very high similarity
            return True
    return False
