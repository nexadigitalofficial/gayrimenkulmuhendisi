@echo off
REM ================================================================
REM NEXA CRM Pro — Windows Otomatik Kurulum Script
REM ================================================================
REM Kullanım:
REM   - setup.bat dosyasına double-click yapı
REM   - Veya: cmd.exe'de "setup.bat" yazı
REM ================================================================

setlocal enabledelayedexpansion

echo ==========================================
echo NEXA CRM PRO - WINDOWS KURULUM
echo ==========================================
echo.

REM 1. Python versiyonu kontrol
echo 1/10 Python Versiyonu Kontrol Ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi. Lutfen Python 3.8+ yukle:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION%
echo.

REM 2. Virtual Environment olustur
echo 2/10 Virtual Environment Olusturuluyor...
if not exist "venv" (
    python -m venv venv
    echo [OK] venv olusturuldu
) else (
    echo [OK] venv zaten var
)
echo.

REM 3. Virtual Environment aktif et
echo 3/10 Virtual Environment Aktivasyonu...
call venv\Scripts\activate.bat
echo [OK] venv aktif
echo.

REM 4. pip upgrade
echo 4/10 pip Upgrade Ediliyor...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo [OK] pip guncellendi
echo.

REM 5. Dependencies yükle
echo 5/10 Dependencies Yukleniyor (2-3 dakika)...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [HATA] Dependencies yuklemede hata
    pause
    exit /b 1
)
echo [OK] Dependencies yuklendi
echo.

REM 6. .env dosyası kontrol
echo 6/10 Konfigurasyon Dosyasi Kontrol Ediliyor...
if not exist ".env" (
    if exist ".env.template" (
        copy .env.template .env
        echo [OK] .env dosyasi olusturuldu
        echo [DIKKAT] .env dosyasini acip degerleri doldur:
        echo   - FIREBASE_SERVICE_ACCOUNT=...
        echo   - GEMINI_API_KEY=...
    ) else (
        echo [HATA] .env.template bulunamadi
        pause
        exit /b 1
    )
) else (
    echo [OK] .env dosyasi var
)
echo.

REM 7. Syntax kontrolü
echo 7/10 Python Syntax Kontrol Ediliyor...
python -m py_compile app.py >nul 2>&1
if errorlevel 1 (
    echo [HATA] app.py'de syntax hatasi
    pause
    exit /b 1
)
python -m py_compile buyer_engine.py >nul 2>&1
if errorlevel 1 (
    echo [HATA] buyer_engine.py'de syntax hatasi
    pause
    exit /b 1
)
echo [OK] Syntax OK
echo.

REM 8. Import kontrolü
echo 8/10 Import'lar Kontrol Ediliyor...
python -c "from app import app; print('[OK] app.py import basarili')" >nul 2>&1
if errorlevel 1 (
    echo [HATA] Import hatasi
    pause
    exit /b 1
)
echo [OK] Import'lar okey
echo.

REM 9. Dosya kontrol
echo 9/10 Tum Dosyalar Kontrol Ediliyor...
set MISSING=0
for %%f in (app.py crm.html admin.html buyer_engine.py ai_listing.py requirements.txt .env) do (
    if not exist "%%f" (
        echo [HATA] %%f bulunamadi
        set /a MISSING=!MISSING!+1
    ) else (
        echo [OK] %%f
    )
)
if !MISSING! gtr 0 (
    echo.
    echo [HATA] !MISSING! dosya eksik
    pause
    exit /b 1
)
echo.

REM 10. Firebase credential kontrol
echo 10/10 Firebase Credential Kontrol Ediliyor...
python << 'PYEOF'
import os
from dotenv import load_dotenv

load_dotenv()
sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "service-account.json")

if os.path.exists(sa_path):
    print(f"[OK] Firebase credential var: {sa_path}")
else:
    print(f"[DIKKAT] Firebase credential: {sa_path}")
    print("   Su an bulunamadi, ama devam edebilirsin")
PYEOF
echo.

REM 11. Özet
echo ==========================================
echo [OK] KURULUM BASARILI!
echo ==========================================
echo.
echo Sonraki Adimlar:
echo.
echo 1. .env dosyasini duzenle:
echo    - notepad .env
echo    - FIREBASE_SERVICE_ACCOUNT ve GEMINI_API_KEY doldur
echo.
echo 2. Uygulamayi basla:
echo    - python app.py
echo.
echo 3. Tarayicida ac:
echo    - http://localhost:5000/crm
echo.
echo ==========================================

REM Otomatik test başlatmak isterseniz:
REM python app.py

pause
