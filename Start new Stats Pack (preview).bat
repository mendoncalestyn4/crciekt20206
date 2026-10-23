@echo off
setlocal
title Cricket Captain Stats Pack - new site (preview)
cd /d "%~dp0"

echo.
echo   ===============================================
echo    CRICKET CAPTAIN 2026  -  STATS PACK  (NEW SITE, PREVIEW)
echo   ===============================================
echo.

rem ---- 1. Find Python (3.10 or newer) ------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto nopython
rem (the Microsoft Store "python" shortcut exists even when Python isn't installed)
%PY% --version >nul 2>nul
if errorlevel 1 goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto oldpython

rem ---- 2. First start: a private copy of the libraries in this folder ----
if not exist ".venv\Scripts\python.exe" (
  echo   First start: setting everything up. This takes a few minutes,
  echo   and only happens once.
  echo.
  %PY% -m venv .venv
  if errorlevel 1 goto fail
  ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
  copy /y requirements.txt ".venv\installed.txt" >nul
)

rem ---- 3. After an update: install anything new -------------------------
fc /b requirements.txt ".venv\installed.txt" >nul 2>nul
if errorlevel 1 (
  echo   Updating libraries for the new version...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
  copy /y requirements.txt ".venv\installed.txt" >nul
)

rem ---- 4. Start the new site (only on this PC); the browser opens by itself
if not exist "web\dist\index.html" (
  echo   The new site's files are missing (the web\dist folder^).
  echo   Download the Stats Pack zip again and extract all of it.
  pause
  goto end
)
echo   Starting the NEW site (a preview)... your browser will open in a few seconds.
echo   The current site is still "Start Stats Pack.bat": both use the same careers.
echo.
echo   Keep this window open while you use it.
echo   Close it (or press Ctrl+C) to stop.
echo.
".venv\Scripts\python.exe" -m server
if errorlevel 1 goto fail
goto end

:nopython
echo   Python isn't installed yet. It's free and takes two minutes:
echo.
echo     1. The Python download page will open now.
echo     2. Download "Python 3.12" (or newer) for Windows and run it.
echo     3. On the first screen, TICK "Add python.exe to PATH", then Install Now.
echo     4. Double-click "Start Stats Pack" again.
echo.
start "" "https://www.python.org/downloads/windows/"
pause
goto end

:oldpython
echo   Your Python is too old (the Stats Pack needs 3.10 or newer).
echo   Install the latest Python from the page that opens now, then try again.
start "" "https://www.python.org/downloads/windows/"
pause
goto end

:fail
echo.
echo   Something went wrong (see the messages above).
echo   Check your internet connection for the first start, then try again.
echo   If it keeps happening, delete the ".venv" folder here and start again.
pause

:end
endlocal
