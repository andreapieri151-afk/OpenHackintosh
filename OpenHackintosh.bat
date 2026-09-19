@echo off
rem OpenHackintosh 2.0.1 Stable - launcher Windows
rem Doppio click oppure: OpenHackintosh.bat [comando] [opzioni]
rem Non usa path assoluti: lavora nella cartella del progetto.

setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1

rem Console in UTF-8: evita errori di encoding con emoji/simboli.
chcp 65001 >nul 2>&1

echo +----------------------------------------------------------+
echo ^|  OpenHackintosh 2.0.1 Stable (Windows)                    ^|
echo ^|  CLI-first - Hardware Detection - EFI con file veri       ^|
echo +----------------------------------------------------------+
echo.

rem --- 1. Python (prima "python", poi il launcher "py") ---------------------
set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    echo Python non trovato.
    echo Installa Python 3.9+ da https://www.python.org/downloads/
    echo IMPORTANTE: spunta "Add python.exe to PATH" durante l'installazione.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo Trovato %%v

rem --- 2. Ambiente virtuale (creato solo se manca) --------------------------
if not exist ".venv\" (
    echo Creo ambiente Python ^(.venv^)...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Impossibile creare .venv.
        echo.
        pause
        exit /b 1
    )
)

set "VENVPY=.venv\Scripts\python.exe"
if not exist "%VENVPY%" (
    echo .venv esiste ma e' incompleto. Elimina la cartella .venv e riprova.
    echo.
    pause
    exit /b 1
)

rem --- 3. Dipendenze ---------------------------------------------------------
"%VENVPY%" -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installo dipendenze ^(requests^)...
    "%VENVPY%" -m pip install -r requirements.txt -q
    if errorlevel 1 "%VENVPY%" -m pip install requests -q
    if errorlevel 1 (
        echo Installazione dipendenze fallita.
        echo.
        pause
        exit /b 1
    )
)

rem --- 4. Avvio --------------------------------------------------------------
echo.
echo Avvio OpenHackintosh...
echo.
"%VENVPY%" main.py %*
set "RC=%ERRORLEVEL%"

echo.
pause
exit /b %RC%
