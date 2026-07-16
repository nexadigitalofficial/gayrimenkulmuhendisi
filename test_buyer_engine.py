"""
================================================================
test_buyer_engine.py
Buyer Extension'ın tüm fonksiyonlarını test et
================================================================

Kullanım:
  python test_buyer_engine.py

Gereklilik:
  - buyer_engine.py aynı dizinde olmalı
  - sentence-transformers yüklü olmalı
  - GEMINI_API_KEY (opsiyonel, NL parsing için)

================================================================
"""

import os
import json
from datetime import datetime, timezone
from buyer_engine import (
    BuyerProfile,
    BuyerMatcher,
    ListingMatch,
    MatchingTier,
    buyer_engine_status,
    parse_natural_language_criteria,
)


def print_section(title):
    """Bölüm başlığı yazdır."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_buyer_engine_status():
    """Test: Engine durumu."""
    print_section("Test 1: Engine Status")
    status = buyer_engine_status()
    print(f"Status: {json.dumps(status, indent=2)}")
    assert status["ok"], "Engine status hatalı"
    print("✅ PASSED")


def test_buyer_profile_creation():
    """Test: Buyer profili oluşturma."""
    print_section("Test 2: Buyer Profile Creation")

    profile_dict = {
        "id": "buyer_001",
        "uid": "user_123",
        "name": "Ahmet Yılmaz",
        "email": "ahmet@example.com",
        "phone": "05324514008",
        "telegram_id": "123456789",
        "whatsapp_phone": "905324514008",
        "criteria": {
            "min_price": 3_000_000,
            "max_price": 6_000_000,
            "min_area": 80,
            "max_area": 150,
            "neighborhoods": ["Çankaya", "Dikmen"],
            "property_types": ["Daire", "Dubleks"],
            "min_rooms": 2,
            "max_rooms": 4,
            "natural_language": "Ankara'da yeni ve güzel, balkonlu, otopark",
        },
        "preferences": {
            "notification_channels": ["email", "crm_task"],
            "auto_match": True,
            "priority_level": "high",
        },
        "is_active": True,
    }

    profile = BuyerProfile(profile_dict)
    assert profile.name == "Ahmet Yılmaz", "Profil adı hatalı"
    assert profile.min_price == 3_000_000, "Min fiyat hatalı"
    assert "Çankaya" in profile.neighborhoods, "Mahalle eklenmemiş"
    assert profile.auto_match == True, "Auto match hatalı"

    # to_dict test
    profile_out = profile.to_dict()
    assert profile_out["name"] == "Ahmet Yılmaz", "to_dict() hatalı"

    print(f"Profil: {profile.name}")
    print(f"Fiyat aralığı: {profile.min_price:,} - {profile.max_price:,} TL")
    print(f"Alan aralığı: {profile.min_area} - {profile.max_area} m²")
    print(f"Semtler: {', '.join(profile.neighborhoods)}")
    print("✅ PASSED")

    return profile


def test_listing_match_creation(profile):
    """Test: İlan-alıcı eşleşmesi oluşturma."""
    print_section("Test 3: Listing Match Creation")

    listing = {
        "id": "listing_001",
        "property_type": "Daire",
        "location": "Çankaya, Ankara",
        "price": 4_500_000,
        "area": 110,
        "rooms": 3,
        "age": 5,
        "amenities": ["Asansör", "Otopark", "Balkon"],
    }

    match = ListingMatch(
        buyer_id=profile.buyer_id,
        listing_id=listing["id"],
        listing_data=listing,
        match_score=85.5,
        match_details={
            "price": "4.500.000 TL (85%)",
            "area": "110 m² (88%)",
            "location": "Çankaya (100%)",
            "property_type": "Daire (100%)",
        },
    )

    assert match.tier == MatchingTier.EXCELLENT.value, "Tier hatalı"
    assert match.match_score == 85.5, "Skor hatalı"

    print(f"Eşleşme Skoru: {match.match_score:.1f}%")
    print(f"Tier: {match.tier.upper()}")
    print(f"İlan: {listing['property_type']} @ {listing['location']}")
    print(f"Fiyat: {listing['price']:,} TL")
    print(f"Alan: {listing['area']} m²")
    print("✅ PASSED")

    return match


def test_matching_engine(profile):
    """Test: Matching engine."""
    print_section("Test 4: Matching Engine")

    matcher = BuyerMatcher()

    # Test case 1: Perfect match
    perfect_listing = {
        "id": "perfect_001",
        "property_type": "Daire",
        "location": "Çankaya",
        "price": 4_500_000,
        "area": 110,
        "rooms": 3,
        "age": 5,
        "amenities": ["Asansör", "Otopark", "Balkon"],
        "description": "Yeni, güzel konum",
    }

    match = matcher.match_listing(profile, perfect_listing)
    assert match is not None, "Perfect match bulunamadı"
    assert match.match_score > 80, f"Skor çok düşük: {match.match_score}"
    print(f"✅ Perfect Match: {match.match_score:.1f}% ({match.tier})")

    # Test case 2: Price out of range
    expensive_listing = {
        "id": "expensive_001",
        "property_type": "Daire",
        "location": "Çankaya",
        "price": 10_000_000,  # ← Out of range
        "area": 110,
        "rooms": 3,
    }

    match = matcher.match_listing(profile, expensive_listing)
    assert match is None, "Pahalı ilan eşleşmemesi gerekiyordu"
    print("✅ Out of Range Check: Correctly rejected")

    # Test case 3: Wrong neighborhood
    wrong_location_listing = {
        "id": "wrong_loc_001",
        "property_type": "Daire",
        "location": "Keçiören",  # ← Not in neighborhoods
        "price": 4_500_000,
        "area": 110,
        "rooms": 3,
    }

    match = matcher.match_listing(profile, wrong_location_listing)
    assert match is None, "Yanlış mahalle eşleşmemesi gerekiyordu"
    print("✅ Wrong Location Check: Correctly rejected")

    # Test case 4: Weak match (area too small)
    small_listing = {
        "id": "small_001",
        "property_type": "Daire",
        "location": "Dikmen",
        "price": 3_500_000,
        "area": 50,  # ← Below min
        "rooms": 2,
    }

    match = matcher.match_listing(profile, small_listing)
    assert match is None, "Küçük ilan eşleşmemesi gerekiyordu"
    print("✅ Area Range Check: Correctly rejected")

    print("✅ PASSED")


def test_matching_tiers():
    """Test: Matching tier'ları."""
    print_section("Test 5: Matching Tiers")

    tiers = [
        (95, MatchingTier.PERFECT.value, "🟢 HARIKA"),
        (80, MatchingTier.EXCELLENT.value, "🔵 MÜKEMMELiyen"),
        (65, MatchingTier.GOOD.value, "🟡 İYİ"),
        (50, MatchingTier.FAIR.value, "🟠 ORTA"),
        (35, MatchingTier.WEAK.value, "🔴 ZAYIF"),
        (15, MatchingTier.POOR.value, "⚪ ZAYIF"),
    ]

    for score, expected_tier, emoji in tiers:
        match = ListingMatch(
            buyer_id="test",
            listing_id="test",
            listing_data={},
            match_score=score,
            match_details={},
        )
        assert match.tier == expected_tier, f"Tier {score} için hatalı"
        print(f"  {emoji}: {score}% → {expected_tier}")

    print("✅ PASSED")


def test_natural_language_parsing():
    """Test: Natural language parsing (Gemini)."""
    print_section("Test 6: Natural Language Parsing")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("⚠️  GEMINI_API_KEY tanımlanmamış — test atlanıyor")
        return

    text = "Ankara'da 2+1 daire, maksimum 5 milyon, Çankaya veya Dikmen, 100 m² minimum"
    criteria = parse_natural_language_criteria(text)

    if criteria:
        print(f"Metin: {text}")
        print(f"Parse edilen kriterler: {json.dumps(criteria, indent=2, ensure_ascii=False)}")
        print("✅ PASSED")
    else:
        print("⚠️  Parsing başarısız — API hatası olabilir")


def test_vector_similarity():
    """Test: Vector similarity."""
    print_section("Test 7: Vector Similarity")

    try:
        from sentence_transformers import SentenceTransformer
        print("✅ sentence-transformers yüklü")

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("✅ Model yüklendi")

        # Test encoding
        texts = [
            "Ankara'da daire",
            "Istanbul'da villa",
            "Ankara'da yeni ev",
        ]

        embeddings = model.encode(texts)
        print(f"✅ {len(texts)} metin encode edildi")

        # Similarity test
        similarity = (embeddings[0] @ embeddings[2].T)
        print(f"✅ Benzerlik (Ankara daire vs Ankara ev): {similarity:.2f}")

        print("✅ PASSED")

    except ImportError:
        print("⚠️  sentence-transformers yüklü değil — test atlanıyor")
        print("   Kurulum: pip install sentence-transformers")


def test_firestore_serialization():
    """Test: Firebase serileştirme."""
    print_section("Test 8: Firebase Serialization")

    profile_dict = {
        "id": "buyer_002",
        "uid": "user_456",
        "name": "Fatma Demir",
        "email": "fatma@example.com",
        "criteria": {
            "min_price": 2_000_000,
            "neighborhoods": ["Keçiören", "Yenimahalle"],
        },
    }

    profile = BuyerProfile(profile_dict)
    firebase_dict = profile.to_dict()

    # Doğrulama
    assert firebase_dict["name"] == "Fatma Demir", "Ad kaydedilmemiş"
    assert "updated_at" in firebase_dict, "updated_at kaydedilmemiş"
    assert isinstance(firebase_dict["is_active"], bool), "is_active boolean olmalı"

    print(f"Profil UID: {firebase_dict['uid']}")
    print(f"updated_at: {firebase_dict['updated_at']}")
    print(f"is_active: {firebase_dict['is_active']}")
    print("✅ PASSED")


def test_batch_matching():
    """Test: Batch matching (birden fazla listing)."""
    print_section("Test 9: Batch Matching")

    profile_dict = {
        "id": "buyer_batch",
        "uid": "user_batch",
        "name": "Batch Test",
        "email": "batch@test.com",
        "criteria": {
            "min_price": 3_000_000,
            "max_price": 5_000_000,
            "neighborhoods": ["Çankaya"],
            "min_area": 80,
            "max_area": 120,
        },
    }

    profile = BuyerProfile(profile_dict)
    matcher = BuyerMatcher()

    listings = [
        {
            "id": "listing_1",
            "property_type": "Daire",
            "location": "Çankaya",
            "price": 4_000_000,
            "area": 100,
        },
        {
            "id": "listing_2",
            "property_type": "Daire",
            "location": "Keçiören",  # Wrong location
            "price": 4_000_000,
            "area": 100,
        },
        {
            "id": "listing_3",
            "property_type": "Daire",
            "location": "Çankaya",
            "price": 6_000_000,  # Too expensive
            "area": 100,
        },
        {
            "id": "listing_4",
            "property_type": "Daire",
            "location": "Çankaya",
            "price": 4_200_000,
            "area": 95,
        },
    ]

    matches = []
    for listing in listings:
        match = matcher.match_listing(profile, listing)
        if match:
            matches.append((listing["id"], match.match_score, match.tier))

    print(f"İlanlar: {len(listings)}")
    print(f"Eşleşmeler: {len(matches)}")
    for listing_id, score, tier in matches:
        print(f"  ✅ {listing_id}: {score:.1f}% ({tier})")

    assert len(matches) == 2, f"2 eşleşme bekleniyordu, {len(matches)} bulundu"
    print("✅ PASSED")


def main():
    """Tüm testleri çalıştır."""
    print("\n" + "=" * 70)
    print("  BUYER ENGINE TEST SUITE")
    print("=" * 70)

    try:
        test_buyer_engine_status()
        profile = test_buyer_profile_creation()
        match = test_listing_match_creation(profile)
        test_matching_engine(profile)
        test_matching_tiers()
        test_natural_language_parsing()
        test_vector_similarity()
        test_firestore_serialization()
        test_batch_matching()

        print_section("✅ TÜM TESTLER BAŞARILI")
        print("\nBuyer Extension kuruluma hazır!")
        print("Sonraki adım: app.py'ye entegrasyonu tamamla")
        print(f"Rehber: INTEGRATION_GUIDE.md")

    except AssertionError as e:
        print_section("❌ TEST BAŞARISIZ")
        print(f"Hata: {e}")
        return 1
    except Exception as e:
        print_section("❌ BEKLENMEDIK HATA")
        print(f"Hata: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
