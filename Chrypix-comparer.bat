@echo off
rem Chrypix en mode comparaison : Effacer, Remplir et Agrandir calculent chaque proposition avec Flux Fill complet
rem puis avec Flux Fill GGUF Q8 (meme tirage), pour comparer la qualite. Essai seulement.
cd /d "%~dp0"
set CHRYPIX_COMPARER=1
start "" ".venv\Scripts\pythonw.exe" -m chrypix %*
