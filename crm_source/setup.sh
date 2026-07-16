#!/bin/bash
# ================================================================
# NEXA CRM Pro — Otomatik Kurulum Script
# ================================================================
# Kullanım:
#   Linux/Mac:   bash setup.sh
#   Windows:     Ayrı setup.bat dosyası kullan
# ================================================================

set -e  # Hata olunca stop et

echo "=========================================="
echo "🚀 NEXA CRM PRO — KURULUM"
echo "=========================================="
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Python versiyon kontrol
echo -e "${YELLOW}1️⃣  Python Versiyonu Kontrol Ediliyor...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
if [[ $python_version < "3.8" ]]; then
    echo -e "${RED}❌ Python 3.8+ gerekli (Şu an: $python_version)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $python_version${NC}"
echo ""

# 2. Virtual Environment oluştur
echo -e "${YELLOW}2️⃣  Virtual Environment Oluşturuluyor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ venv oluşturuldu${NC}"
else
    echo -e "${GREEN}✅ venv zaten var${NC}"
fi
echo ""

# 3. Virtual Environment activate
echo -e "${YELLOW}3️⃣  Virtual Environment Aktivasyon...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ venv aktif${NC}"
echo ""

# 4. pip upgrade
echo -e "${YELLOW}4️⃣  pip Upgrade Ediliyor...${NC}"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo -e "${GREEN}✅ pip güncel${NC}"
echo ""

# 5. Dependencies yükle
echo -e "${YELLOW}5️⃣  Dependencies Yükleniyor (Bu 2-3 dakika alabilir)...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies yüklendi${NC}"
echo ""

# 6. .env dosyası kontrol
echo -e "${YELLOW}6️⃣  Konfigürasyon Dosyası Kontrol Ediliyor...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}✅ .env dosyası oluşturuldu (.env.template'den)${NC}"
        echo -e "${YELLOW}⚠️  .env dosyasını açıp değerleri doldur:${NC}"
        echo -e "   FIREBASE_SERVICE_ACCOUNT=..."
        echo -e "   GEMINI_API_KEY=..."
        echo -e "   EMAIL konfigürasyonu..."
    else
        echo -e "${RED}❌ .env.template bulunamadı${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env dosyası var${NC}"
fi
echo ""

# 7. Syntax kontrolü
echo -e "${YELLOW}7️⃣  Python Syntax Kontrol Ediliyor...${NC}"
python3 -m py_compile app.py buyer_engine.py ai_listing.py 2>&1 | grep -i error && {
    echo -e "${RED}❌ Syntax hatası bulundu${NC}"
    exit 1
} || {
    echo -e "${GREEN}✅ Syntax OK${NC}"
}
echo ""

# 8. Import kontrolü
echo -e "${YELLOW}8️⃣  İmport'lar Kontrol Ediliyor...${NC}"
python3 << 'PYEOF'
import sys
try:
    from app import app
    print("✅ app.py import başarılı")
    
    # Routes kontrol
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    if any('/crm' in r for r in routes):
        print("✅ /crm route tanımlanmış")
    else:
        print("⚠️  /crm route bulunamadı")
        
except Exception as e:
    print(f"❌ İmport hatası: {e}")
    sys.exit(1)
PYEOF
echo ""

# 9. Dosya kontrol
echo -e "${YELLOW}9️⃣  Tüm Dosyalar Kontrol Ediliyor...${NC}"
required_files=(
    "app.py"
    "crm.html"
    "admin.html"
    "buyer_engine.py"
    "ai_listing.py"
    "fsbo_engine.py"
    "requirements.txt"
    ".env"
)

missing=0
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ $file bulunamadı${NC}"
        missing=$((missing + 1))
    else
        echo -e "${GREEN}✅ $file${NC}"
    fi
done

if [ $missing -gt 0 ]; then
    echo -e "${RED}❌ $missing dosya eksik${NC}"
    exit 1
fi
echo ""

# 10. Firebase credential kontrol
echo -e "${YELLOW}🔟 Firebase Credential Kontrol Ediliyor...${NC}"
python3 << 'PYEOF'
import os
from dotenv import load_dotenv

load_dotenv()
sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "service-account.json")

if os.path.exists(sa_path):
    print(f"✅ Firebase credential var: {sa_path}")
else:
    print(f"⚠️  Firebase credential: {sa_path} (şu an bulunamadı)")
    print("   İndirme rehberi: .env.template dosyasına bakın")
PYEOF
echo ""

# 11. Özet
echo "=========================================="
echo -e "${GREEN}✅ KURULUM BAŞARILI!${NC}"
echo "=========================================="
echo ""
echo "Sonraki Adımlar:"
echo "1. .env dosyasını açıp değerleri doldur:"
echo "   nano .env"
echo ""
echo "2. Uygulamayı başlat:"
echo "   python3 app.py"
echo ""
echo "3. Tarayıcıda aç:"
echo "   http://localhost:5000/crm"
echo ""
echo "=========================================="
