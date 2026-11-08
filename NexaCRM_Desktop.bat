@echo off
chcp 65001 > nul
title Nexa CRM Pro - Masaüstü Uygulaması Başlatıcı

echo ======================================================================
echo           🚀 NEXA CRM PRO - MASAÜSTÜ UYGULAMASI BAŞLATILIYOR...
echo ======================================================================
echo.

:: 1. Flask sunucusunun açık olup olmadığını kontrol et
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/crm' -TimeoutSec 1 -UseBasicParsing; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    echo [1/2] Nexa CRM arka plan sunucusu başlatılıyor...
    start /min "" python app.py
    timeout /t 3 /nobreak > nul
) else (
    echo [1/2] Nexa CRM arka plan sunucusu zaten aktif (Port 5000).
)

echo [2/2] Pencereli Masaüstü Uygulama Modu açılıyor...

:: 2. Edge veya Chrome App Modunda Başlat
set "EDGE_EXE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

if exist "%EDGE_EXE%" (
    start "" "%EDGE_EXE%" --app="http://127.0.0.1:5000/crm" --window-size=1366,860
    exit /b 0
)

if exist "%CHROME_EXE%" (
    start "" "%CHROME_EXE%" --app="http://127.0.0.1:5000/crm" --window-size=1366,860
    exit /b 0
)

:: Tarayıcı bulunamazsa varsayılan tarayıcıyla aç
start "" "http://127.0.0.1:5000/crm"
exit /b 0
