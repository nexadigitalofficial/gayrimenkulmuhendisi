@echo off
chcp 65001 >nul
title NexaScout - Google Gmail API Yetkilendirme
echo ===============================================================================
echo      NEXASCOUT - YİĞİT NARİN (CB.COM.TR) GMAIL API BAĞLANTISI
echo ===============================================================================
echo.
echo [BİLGİ] Google yetkilendirme penceresi varsayılan tarayıcınızda açılıyor...
echo [BİLGİ] Açılan ekranda yigit.narin@cb.com.tr hesabınızı seçip "İzin Ver" deyiniz.
echo.
cd /d "%~dp0"
python google_auth_setup.py
echo.
pause
