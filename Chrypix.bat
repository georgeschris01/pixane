@echo off
rem Lance Chrypix sans fenêtre noire
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m chrypix %*
