@echo off
title Neural TTS Studio - Servidor Local
cd /d "%~dp0"
echo Iniciando Neural TTS Studio en http://127.0.0.1:7860 ...
start "" "http://127.0.0.1:7860"
"%USERPROFILE%\.local\bin\uv.exe" run python app.py
pause
