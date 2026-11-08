@echo off
rem Lance Retouche IA sans fenêtre noire
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m retouche_ia %*
