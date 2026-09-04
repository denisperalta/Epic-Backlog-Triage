@echo off
rem ---------------------------------------------------------------------------
rem  Epic Backlog Triage - one-click setup and run.
rem
rem  Double-click this file. It finds Python (offering to install it via
rem  winget if missing), builds a private virtual environment, installs
rem  legendary, checks itself over, walks you through the Epic login the
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
call :detect_python
if defined PY goto :have_python
goto :no_python

:have_python
echo [1/7] Python 3.8+ found
if not exist "epic_steam.py" goto :wrong_folder

rem ------------------------------------------- 2. private virtual environment
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" goto :have_venv
echo [2/7] creating the .venv virtual environment ...
%PY% -m venv .venv
if errorlevel 1 goto :venv_failed

:have_venv
echo [2/7] virtual environment ready

rem -------------------------------------------------------- 3. dependencies
"%VPY%" -c "import legendary" >nul 2>&1
if not errorlevel 1 goto :have_deps
echo [3/7] installing legendary (needs the internet, once) ...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :pip_failed

:have_deps
echo [3/7] legendary installed

rem -------------------------------------------------------- 4. self-check
rem Fast and offline. Running it here means a half-applied edit or a damaged
rem checkout is caught before the Epic login and the Steam fetching,
rem rather than after. Silent unless something is actually wrong.
"%VPY%" -m unittest discover -b >nul 2>&1
if errorlevel 1 goto :tests_failed
echo [4/7] scripts self-checked

rem ------------------------------------------------------- 5. Epic account
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
"%VPY%" -c "from legendary.core import LegendaryCore; u = LegendaryCore().lgd.userdata or {}; print('[5/7] Epic account connected: ' + u.get('displayName', '?'))"

rem ----------------------------------------------------------- 6. the work
echo.
echo [6/7] reading your library and fetching Steam data ...
echo       The first run takes a couple of minutes. Every reply is cached, so
echo       every run after this one finishes in seconds.
echo.
"%VPY%" epic_steam.py %*
if errorlevel 1 goto :run_failed

echo.
echo [6/7] retrying unmatched titles, and settling which are delisted ...
"%VPY%" second_pass.py
if errorlevel 1 goto :run_failed

rem --------------------------------------------------------- 7. the report
echo.
echo [7/7] rendering the report ...
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

where winget >nul 2>&1
if errorlevel 1 goto :no_python_manual

rem winget's exit codes are HRESULTs - large enough that cmd.exe reads them as
rem negative when it stores the value as a signed int. "if not errorlevel 1"
rem tests errorlevel < 1, which a negative code always satisfies, so that
rem style of check reads "not installed" as success. Comparing %errorlevel%
rem itself against 0 is not fooled by the sign.
call winget list --id Python.Python.3.12 -e >nul 2>&1
if %errorlevel% equ 0 goto :winget_installed

set /p "WINGET_CONFIRM=  Install Python 3.12 now via winget? [Y/N] "
if /i not "%WINGET_CONFIRM%"=="Y" goto :no_python_manual

echo.
echo   Installing Python 3.12 via winget ...
call winget install -e --id Python.Python.3.12
if %errorlevel% neq 0 goto :no_python_manual

:winget_installed
rem The installer just wrote a new PATH to the registry, but this process's
rem copy of PATH is still the one it started with - re-reading the registry
rem in-process picks it up without needing a fresh window from Explorer.
echo.
echo   Picking up the updated PATH ...
call :refresh_path
call :detect_python
if defined PY goto :have_python

echo   Python 3.8 or newer still was not found after installing.
echo.
echo   Close this window and run run.bat again - a fresh process from Explorer
echo   will pick up the new PATH even if this one still can't see it. If it
echo   still fails, install it by hand from https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH".
goto :failed

:no_python_manual
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

:tests_failed
echo   The built-in self-check failed, so something in the scripts is wrong.
echo   Nothing was fetched. Run it again to see what broke:
echo       .venv\Scripts\python.exe -m unittest discover
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
:detect_python
rem The py launcher first: on Windows a bare "python" is often the Microsoft
rem Store stub, which is not a Python at all.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY exit /b 0
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=python"
exit /b 0

:refresh_path
rem GetEnvironmentVariable resolves embedded references like %SystemRoot% -
rem the raw registry string does not, so parsing it by hand would leave PATH
rem full of literal, un-expanded percent tokens.
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P"
exit /b 0

:check_auth
rem Exit code 0 when legendary has saved credentials. "legendary status"
rem cannot be used for this: it reports "<not logged in>" and still exits 0.
"%VPY%" -c "import sys; from legendary.core import LegendaryCore; sys.exit(0 if LegendaryCore().lgd.userdata else 1)" >nul 2>&1
exit /b %errorlevel%
