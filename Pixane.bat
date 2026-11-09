@echo off
rem Lance Pixane sans fenêtre noire
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m pixane %*
