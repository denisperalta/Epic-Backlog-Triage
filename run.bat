@echo off
rem ---------------------------------------------------------------------------
rem  Epic Backlog Triage - one-click setup and run.
rem
rem  Double-click this file. It finds Python, builds a private virtual
rem  environment, installs legendary, walks you through the Epic login the
rem  first time, then produces out\report.html and opens it.
rem
rem  Any arguments are passed through to epic_steam.py, so   run.bat --refresh
rem  re-queries your Epic library instead of reusing the cached copy.
rem ---------------------------------------------------------------------------
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Epic Backlog Triage
set "RC=0"

echo.
echo   Epic Backlog Triage
echo   ===================
echo.

rem ------------------------------------------------------- 1. find a Python
rem The py launcher first: on Windows a bare "python" is often the Microsoft
rem Store stub, which is not a Python at all.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :have_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY goto :no_python

:have_python
echo [1/6] Python 3.8+ found
if not exist "epic_steam.py" goto :wrong_folder

rem ------------------------------------------- 2. private virtual environment
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" goto :have_venv
echo [2/6] creating the .venv virtual environment ...
%PY% -m venv .venv
if errorlevel 1 goto :venv_failed

:have_venv
echo [2/6] virtual environment ready

rem -------------------------------------------------------- 3. dependencies
"%VPY%" -c "import legendary" >nul 2>&1
if not errorlevel 1 goto :have_deps
echo [3/6] installing legendary (needs the internet, once) ...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :pip_failed

:have_deps
echo [3/6] legendary installed

rem ------------------------------------------------------- 4. Epic account
call :check_auth
if not errorlevel 1 goto :have_auth

echo.
echo   ---------------------------------------------------------------------
echo    Your Epic account is not connected yet. A login page is about to
echo    open. Sign in there as you normally would.
echo.
echo    If no page opens, browse to  https://legendary.gl/epiclogin
echo    log in, and paste the "authorizationCode" value from the JSON the
echo    page shows you. The code is single-use and expires within minutes,
echo    so reload that page if it is rejected.
echo   ---------------------------------------------------------------------
echo.
".venv\Scripts\legendary.exe" auth
echo.
call :check_auth
if errorlevel 1 goto :auth_failed

:have_auth
"%VPY%" -c "from legendary.core import LegendaryCore; u = LegendaryCore().lgd.userdata or {}; print('[4/6] Epic account connected: ' + u.get('displayName', '?'))"

rem ----------------------------------------------------------- 5. the work
echo.
echo [5/6] reading your library and fetching Steam data ...
echo       The first run takes roughly an hour - Steam is rate limited, so
echo       requests are throttled and every reply is cached. Every run after
echo       this one finishes in seconds. Leave it going.
echo.
"%VPY%" epic_steam.py %*
if errorlevel 1 goto :run_failed

echo.
echo [5/6] retrying the titles that did not match ...
"%VPY%" second_pass.py
if errorlevel 1 goto :run_failed

rem --------------------------------------------------------- 6. the report
echo.
echo [6/6] rendering the report ...
"%VPY%" build_report.py
if errorlevel 1 goto :run_failed

echo.
echo   Done. Opening out\report.html
start "" "out\report.html"
goto :done

rem ------------------------------------------------------------- failures
:no_python
echo   Python 3.8 or newer was not found.
echo.
echo   Install it from  https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH" in the installer, then run this again.
goto :failed

:wrong_folder
echo   epic_steam.py is not next to this script.
echo   Keep run.bat inside the repository folder it came from.
goto :failed

:venv_failed
echo   Could not create the .venv virtual environment.
echo   On a stock Windows Python this usually means the install is damaged -
echo   reinstalling Python from python.org fixes it.
goto :failed

:pip_failed
echo   Installing legendary failed. Check the internet connection, then
echo   run this again. To see the full error:
echo       .venv\Scripts\python.exe -m pip install -r requirements.txt
goto :failed

:auth_failed
echo   Still not signed in to Epic, so there is no library to read.
echo   Try again by hand to see what went wrong:
echo       .venv\Scripts\legendary.exe auth
goto :failed

:run_failed
echo.
echo   That step failed - the message above says why.
goto :failed

:failed
set "RC=1"
echo.

:done
rem Keep the window open when this was double-clicked, but not when it was
rem started from a console that is going to stay open anyway.
echo %cmdcmdline% | find /i "%~nx0" >nul 2>&1
if not errorlevel 1 pause
exit /b %RC%

rem ---------------------------------------------------------------- helpers
:check_auth
rem Exit code 0 when legendary has saved credentials. "legendary status"
rem cannot be used for this: it reports "<not logged in>" and still exits 0.
"%VPY%" -c "import sys; from legendary.core import LegendaryCore; sys.exit(0 if LegendaryCore().lgd.userdata else 1)" >nul 2>&1
exit /b %errorlevel%
