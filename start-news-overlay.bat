@echo off
cd /d "%~dp0"
python news-overlay-server.py %*
pause
