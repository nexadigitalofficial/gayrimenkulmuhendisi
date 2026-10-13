@echo off
chcp 65001 >nul
title NexaScout - Toplu VIP E-Posta Gonderim Konsolu
echo ===============================================================================
echo      NEXASCOUT - TOPLU VIP E-POSTA VE WORD TEKLİF GÖNDERİM SİSTEMİ
echo      Coldwell Banker VIP Real - Yiğit Narin (0532 451 40 08)
echo ===============================================================================
echo.
cd /d "%~dp0"
python TOPLU_EPOSTA_GONDER.py %*
echo.
pause
