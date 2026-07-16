# 🚀 KİRALIK MATCHING OPTİMİZASYON İPUÇLARI

Kiralık ilanları matcher'da daha verimli hale getirmek için öneriler.

---

## 1️⃣ TRANSACTION_TYPE FİLTRELEMESİ

### Problem
Matcher, satılık arayışlarını kiralık ilanlarıyla eşleştiriyor:
- Arayış: "3+1 daire satılık ₺5M bütçe"
- Match: Kiralık 3+1 daire ₺3000/ay ← ❌ YANLIŞ

### Çözüm
Matcher'da transaction_type kontrolü ekle:

```python
# matcher_engine.py'de (matcher_engine.py)

def match_all(self, arayislar, portfoyler):
    """Match with transaction_type filtering"""
    
    for arayis in arayislar:
        # ✅ YENİ: Arayış türünü algıla
        arayis_txn_type = self._detect_transaction_type(arayis)
        
        for portfoy in portfoyler:
            # ✅ YENİ: Transaction type uyumlu mu?
            if not self._transaction_types_compatible(arayis_txn_type, portfoy.transaction_type):
                continue  # Skip mismatch
            
            score = self.calculate_score(arayis, portfoy)
            # ...

def _detect_transaction_type(self, arayis_record):
    """Arayış'ın satılık mı kiralık mı olduğunu algıla"""
    
    description = arayis_record.description.lower()
    
    # Kiralık indicators
    kiralık_keywords = ['kira', 'aylık', '/ay', 'günlük']
    if any(kw in description for kw in kiralık_keywords):
        return TransactionType.KIRALIK
    
    # Satılık indicators (varsayılan)
    return TransactionType.SATILIK

def _transaction_types_compatible(self, arayis_type, portfoy_type):
    """İşlem türleri uyumlu mu?"""
    
    # Satılık arayışı ← Satılık portföy ✅
    # Kiralık arayışı ← Kiralık portföy ✅
    # Satılık arayışı ← Kiralık portföy ❌
    # Kiralık arayışı ← Satılık portföy ❌ (çoğunlukla)
    
    # İstisnai durum: Büyük ihtimal satılık'ı kiralık'la eşleştirme
    if arayis_type == portfoy_type:
        return True
    
    # Cross-matching (opsiyonel): "Her tür mülk ara"
    # return True
    
    return False
```

---

## 2️⃣ FİYAT NORMALIZASYONU

### Problem
Satılık fiyatları TL, kiralık fiyatları aylık:
- Satılık: ₺5.000.000
- Kiralık: ₺3.000/ay

Karşılaştırma imkansız.

### Çözüm
Fiyatları aylık kiralık karşılığına dönüştür:

```python
# matcher_engine.py'de

def normalize_price(self, price: float, transaction_type: str, area: float = None):
    """
    Tüm fiyatları aylık kiralık karşılığına dönüştür
    Satılık: ₺5M → ~₺15.000/ay (0.3% aylık getiri)
    Kiralık: ₺3.000/ay → ₺3.000/ay (olduğu gibi)
    """
    
    if transaction_type == TransactionType.KIRALIK:
        return price  # Zaten aylık
    
    # Satılık → Kiralık aylık karşılığı
    # Kabul: %0.3 aylık getiri (Turkey real estate norm)
    monthly_equivalent = price * 0.003
    
    return monthly_equivalent

# Örnek:
# Satılık: ₺5.000.000 × 0.003 = ₺15.000/ay ✅
# Satılık: ₺2.000.000 × 0.003 = ₺6.000/ay ✅
# Kiralık: ₺3.000 = ₺3.000 ✅
```

**Kullanım:**
```python
arayis_price_normalized = self.normalize_price(
    price=arayis.price,
    transaction_type=arayis.transaction_type,
    area=arayis.area
)

portfoy_price_normalized = self.normalize_price(
    price=portfoy.price,
    transaction_type=portfoy.transaction_type,
    area=portfoy.area
)

# Şimdi karşılaştırılabilir:
price_diff = abs(arayis_price_normalized - portfoy_price_normalized)
```

---

## 3️⃣ SCORING KRİTERLERİ AYARLAMASI

### Satılık için Optimal Weights

```python
SATILLIK_WEIGHTS = {
    'price': 0.25,
    'rooms': 0.25,
    'location': 0.20,
    'type': 0.15,
    'features': 0.10,
    'urgency': 0.05,
}
```

### Kiralık için Optimized Weights

```python
KIRALLIK_WEIGHTS = {
    'price': 0.30,        # ✅ Daha yüksek (aylık ₺ önemli)
    'rooms': 0.25,
    'location': 0.20,
    'type': 0.15,
    'features': 0.07,     # ✅ Biraz düşük
    'availability': 0.03, # ✅ YENİ: Kiralık başlangıç tarihi
}
```

**Uygulama:**

```python
def calculate_score(self, arayis, portfoy):
    """Score calculation with transaction-specific weights"""
    
    # Weights'i seç
    if portfoy.transaction_type == TransactionType.KIRALIK:
        weights = KIRALLIK_WEIGHTS
    else:
        weights = SATILLIK_WEIGHTS
    
    # Fiyat score (kiralık için normalize edilmiş)
    price_score = self._calculate_price_score(
        arayis.price,
        portfoy.price,
        portfoy.transaction_type
    )
    
    # Diğer scores...
    rooms_score = self._calculate_rooms_score(...)
    location_score = self._calculate_location_score(...)
    
    # Weighted sum
    overall = (
        price_score * weights['price'] +
        rooms_score * weights['rooms'] +
        location_score * weights['location'] +
        # ...
    )
    
    return overall
```

---

## 4️⃣ KIRALAYAN-ÖZGÜ ÖZELLIKLER

### Yeni Fields Ekleme

Kiralık ilanlarında ek bilgiler:

```python
@dataclass
class PortfoyRecord:
    # ... mevcut fields
    
    # ✅ YENİ - Kiralık özgü
    furnished: bool = None          # Mobilyalı mı?
    utilities_included: bool = None # Giderler dahil mi?
    deposit_amount: float = None    # Depozito
    contract_term: str = None       # Sözleşme süresi (3ay, 6ay, 1yıl, vb)
    move_in_date: str = None        # Başlangıç tarihi
    pet_friendly: bool = None       # Evcil hayvan?
    
    @property
    def is_rental(self):
        return self.transaction_type == TransactionType.KIRALIK
```

### WhatsApp Parser'da Kiralık Özellikleri Algılama

```python
# matcher_parser.py'de

def parse_portfoy_record(self, text: str) -> PortfoyRecord:
    """Parse portföy kaydından kiralık özelliklerini çıkar"""
    
    text_lower = text.lower()
    
    # ✅ Mobilyalı mı?
    furnished = any(w in text_lower for w in ['mobilyalı', 'döşemeli', 'furnished'])
    
    # ✅ Giderler dahil mi?
    utilities = any(w in text_lower for w in ['giderleri dahil', 'utilities included', 'tüm giderler'])
    
    # ✅ Evcil hayvan?
    pet_friendly = any(w in text_lower for w in ['hayvan', 'evcil', 'pet'])
    
    # ✅ Depozito
    deposit_match = re.search(r'depozito[:\s]+₺?(\d+)', text_lower)
    deposit = float(deposit_match.group(1)) if deposit_match else None
    
    # ✅ Başlangıç tarihi
    date_patterns = [
        r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',  # 01/01/2026
        r'(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+\d{4}',
    ]
    move_in = None
    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            move_in = match.group(1)
            break
    
    return PortfoyRecord(
        # ... temel alanlar
        furnished=furnished,
        utilities_included=utilities,
        pet_friendly=pet_friendly,
        deposit_amount=deposit,
        move_in_date=move_in,
    )
```

---

## 5️⃣ KİRALIK-ÖZGÜ MATCHING LOGIC

### Kiralık Kriterleri

```python
def calculate_kiralyk_compatibility(self, arayis, portfoy) -> float:
    """0-1 arası kiralık uyumluluk score'u"""
    
    score = 0.0
    
    # 1. Mobilyalı tercihi
    if hasattr(arayis, 'prefer_furnished'):
        if arayis.prefer_furnished == portfoy.furnished:
            score += 0.1
        else:
            score -= 0.05
    
    # 2. Giderleri dahil olma tercihi
    if hasattr(arayis, 'utilities_preference'):
        if arayis.utilities_preference == portfoy.utilities_included:
            score += 0.1
        else:
            score -= 0.05
    
    # 3. Evcil hayvan
    if hasattr(arayis, 'has_pets'):
        if arayis.has_pets and not portfoy.pet_friendly:
            return 0.0  # Deal breaker
        score += 0.1
    
    # 4. Move-in date uyumu
    if arayis.desired_move_in and portfoy.move_in_date:
        date_diff = abs(parse_date(arayis.desired_move_in) - parse_date(portfoy.move_in_date))
        if date_diff <= 7:  # 1 hafta içinde
            score += 0.2
        elif date_diff <= 30:  # 1 ay içinde
            score += 0.1
        else:
            score -= 0.05
    
    return score
```

---

## 6️⃣ AVAILABILITY SCORING

### Problem
Kiralık ilanlar hızlı gidiyor. 2 gün önceki ilan artık yok olabilir.

### Çözüm
Scraped_at timestamp'ine göre eski ilanları penalize et:

```python
def calculate_availability_score(self, listing_age_days: int) -> float:
    """Listin kaç gün önceki olduğuna göre penalize et"""
    
    if listing_age_days <= 1:
        return 1.0  # Yeni ilan
    elif listing_age_days <= 3:
        return 0.9  # 3 gün
    elif listing_age_days <= 7:
        return 0.7  # 1 hafta
    elif listing_age_days <= 14:
        return 0.5  # 2 hafta
    else:
        return 0.2  # Eski, muhtemelen rented already
```

**Matching'e dahil et:**

```python
from datetime import datetime, timedelta

listing_age = (datetime.now() - portfoy.scraped_at).days
availability_score = self.calculate_availability_score(listing_age)

# Ana scoring'e ekle
overall_score = (
    # ... mevcut scores
    + availability_score * 0.05  # 5% weight
)
```

---

## 7️⃣ BULK KIRALYK ARAYIŞLARI

### Problem
Bir kurumsal müşteri 100 adet kiralık arıyorsa?

### Çözüm

```python
@dataclass
class BulkKiralikArayis:
    """Kurumsal kiralık arayışı"""
    company_name: str
    property_type: PropertyType
    quantity: int           # Kaç adet?
    location: str
    price_range: tuple      # (min, max)
    move_in_date: str
    contract_duration: str  # 6ay, 1yıl, vb
    furnish_requirement: str

# Parser'da
def parse_bulk_arayis(self, text: str) -> Optional[BulkKiralikArayis]:
    """Kurumsal arayışları parse et"""
    
    if '100 adet' in text or '50 adet' in text:
        quantity_match = re.search(r'(\d+)\s+adet', text)
        # ...
        return BulkKiralikArayis(...)
    
    return None
```

---

## 8️⃣ GERÇEKLEŞTİRME ÖRNEĞİ

### Adım 1: Matcher'da Transaction Type Kontrolü

```python
# matcher_engine.py

def is_compatible(self, arayis, portfoy):
    """İlk filtre: transaction type uyumluluğu"""
    
    if arayis.transaction_type == portfoy.transaction_type:
        return True
    
    # Cross-matching (opsiyonel)
    # return True
    
    return False
```

### Adım 2: Fiyat Normalizasyonu

```python
def score_price(self, arayis_price, arayis_type, 
                portfoy_price, portfoy_type):
    """Fiyat score'u (normalize edilmiş)"""
    
    arayis_normalized = self.normalize_price(arayis_price, arayis_type)
    portfoy_normalized = self.normalize_price(portfoy_price, portfoy_type)
    
    # Normal price matching logic
    return self._price_similarity(arayis_normalized, portfoy_normalized)
```

### Adım 3: Kiralık Bonus'ları

```python
def score_overall(self, arayis, portfoy):
    """Final score"""
    
    score = self._base_score(arayis, portfoy)
    
    # Kiralık özgü bonuslar
    if portfoy.is_rental:
        # Mobilyalı bonus
        if arayis.prefer_furnished == portfoy.furnished:
            score += 0.05
        
        # Giderleri dahil bonus
        if arayis.utilities_preference == portfoy.utilities_included:
            score += 0.05
        
        # Eski ilan penalty
        age_penalty = 1.0 - (portfoy.age_days * 0.02)
        score *= age_penalty
    
    return score
```

---

## 🎯 IMPLEMENTATION CHECKLIST

- [ ] `_detect_transaction_type()` ekle
- [ ] `_transaction_types_compatible()` ekle
- [ ] `normalize_price()` ekle (0.3% rule)
- [ ] `KIRALLIK_WEIGHTS` define et
- [ ] `calculate_kiralyk_compatibility()` ekle
- [ ] `calculate_availability_score()` ekle
- [ ] Kiralık fields (furnished, utilities, pet_friendly) ekle
- [ ] Parser'da kiralık field'larını algıla
- [ ] Test with real kiralık data

---

## 📊 BEKLENEN SONUÇLAR

**BEFORE** (Transaction type fark etmiyor):
```
❌ Satılık arayışı + Kiralık matching
  - "3+1 daire ₺5M satılık" → "Kiralık 3+1 daire ₺3000/ay" (85% match!)
```

**AFTER** (Transaction type kontrolü):
```
✅ Satılık arayışı + Kiralık filtered out
  - "3+1 daire ₺5M satılık" → Sadece satılık 3+1 daireler

✅ Kiralık arayışı + Kiralık matching
  - "3+1 daire ₺3500 kiralık" → "Kiralık 3+1 daire ₺3000-3500/ay" (95% match!)
```

---

**Versiyon:** 2.1 - Kiralık Optimizasyonları  
**Zorluk:** Orta  
**Zaman:** 2-4 saat  

🚀 **İyi şanslar!**
