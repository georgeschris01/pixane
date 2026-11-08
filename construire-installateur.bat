@echo off
rem Fabrique l'installateur de Chrypix : publication\installateur\Chrypix-Setup-<version>.exe
rem Il faut Inno Setup 7 (gratuit) : https://jrsoftware.org/isdl.php
rem La version se change dans chrypix\__init__.py (__version__) avant chaque nouvel installateur.
rem Resultat detaille dans installateur.log.
cd /d "%~dp0"
setlocal

set ISCC=
for %%p in ("%ProgramFiles%\Inno Setup 7\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 7\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe") do (
  if exist %%p set ISCC=%%p
)
if not defined ISCC for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do set ISCC="%%i"

call :work > installateur.log 2>&1

if exist "publication\installateur\Chrypix-Setup-%VERSION%.exe" explorer /select,"publication\installateur\Chrypix-Setup-%VERSION%.exe"
endlocal
goto :eof

:work
echo === Preparation des fichiers (Python, bibliotheques, Chrypix) ===
".venv\Scripts\python.exe" installateur\preparer.py
if errorlevel 1 (
  echo ECHEC de la preparation.
  goto :done
)
set /p VERSION=<publication\version.txt
echo.
echo === Inno Setup, version %VERSION% ===
if not defined ISCC (
  echo Inno Setup est introuvable. Installe-le depuis https://jrsoftware.org/isdl.php puis relance ce fichier.
  goto :done
)
echo Compilateur : %ISCC%
%ISCC% /DAppVersion=%VERSION% installateur\Chrypix.iss
if errorlevel 1 (
  echo ECHEC de l'installateur.
  goto :done
)
echo.
echo Installateur cree : publication\installateur\Chrypix-Setup-%VERSION%.exe
:done
echo.
echo === FIN ===
goto :eof
