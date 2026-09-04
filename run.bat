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
cd /d "%~dp0"
title Epic Backlog Triage
set "RC=0"

rem --------------------------------------------------- 0. language / idioma
rem Asked before chcp switches the console to UTF-8 (below) - re-pointing the
rem code page right before a redirected/piped read can eat the input, so the
rem plain-ASCII prompt goes first and the code page change comes after.
set "RUNLANG=E"
set /p "RUNLANG=Language / Idioma: [E]nglish or [s]panish? (E/s) "
set "RUNLANG=%RUNLANG:~0,1%"
if /i not "%RUNLANG%"=="S" set "RUNLANG=E"
if /i "%RUNLANG%"=="S" set "RUNLANG=S"

chcp 65001 >nul

if "%RUNLANG%"=="S" goto :msgs_es
goto :msgs_en

:msgs_en
set "M_STEP1=[1/7] Python 3.8+ found"
set "M_STEP2_CREATING=[2/7] creating the .venv virtual environment ..."
set "M_STEP2_READY=[2/7] virtual environment ready"
set "M_STEP3_INSTALLING=[3/7] installing legendary (needs the internet, once) ..."
set "M_STEP3_READY=[3/7] legendary installed"
set "M_STEP4=[4/7] scripts self-checked"
set "M_AUTH_L1=   Your Epic account is not connected yet. A browser tab is about to"
set "M_AUTH_L2=   open to Epic's real login page (epicgames.com). Sign in there as"
set "M_AUTH_L3=   you normally would - email/password, and 2FA if you use it."
set "M_AUTH_L4=   If no tab opens, browse to  https://legendary.gl/epiclogin  yourself."
set "M_AUTH_L5=   After you log in, the tab lands on a plain page of text that"
set "M_AUTH_L6=   starts with a { character. That is correct, not an error - it"
set "M_AUTH_L7=   is the raw code Epic sends back, e.g. {authorizationCode: ...}"
set "M_AUTH_L8=   Select everything on that page (Ctrl+A), copy it (Ctrl+C), switch"
set "M_AUTH_L9=   back to this window, and paste it (Ctrl+V, or right-click Paste)"
set "M_AUTH_L10=   where it says 'Please enter the authorizationCode value...'."
set "M_AUTH_L11=   Paste the WHOLE block of text - no need to pick out just the code"
set "M_AUTH_L12=   by hand, this script's login step figures that part out."
set "M_AUTH_L13=   The code is single-use and expires within a few minutes. If it is"
set "M_AUTH_L14=   rejected, reload  https://legendary.gl/epiclogin  for a fresh one."
set "M_ACCT_CONNECTED=[5/7] Epic account connected: "
set "M_STEP6_FETCHING=[6/7] reading your library and fetching Steam data ..."
set "M_STEP6_NOTE1=      The first run takes a couple of minutes. Every reply is cached, so"
set "M_STEP6_NOTE2=      every run after this one finishes in seconds."
set "M_STEP6_RETRY=[6/7] retrying unmatched titles, and settling which are delisted ..."
set "M_STEP7_RENDER=[7/7] rendering the report ..."
set "M_DONE=  Done. Opening out\report.html"
set "M_NO_PYTHON=  Python 3.8 or newer was not found."
set "M_WINGET_DEFAULT=Y"
set "M_WINGET_PROMPT=  Install Python 3.12 now via winget? [Y/n] "
set "M_WINGET_INSTALLING=  Installing Python 3.12 via winget ..."
set "M_PATH_REFRESH=  Picking up the updated PATH ..."
set "M_STILL_NOT_FOUND=  Python 3.8 or newer still was not found after installing."
set "M_REOPEN_L1=  Close this window and run run.bat again - a fresh process from Explorer"
set "M_REOPEN_L2=  will pick up the new PATH even if this one still can't see it. If it"
set "M_REOPEN_L3=  still fails, install it by hand from https://www.python.org/downloads/"
set "M_REOPEN_L4=  and tick 'Add python.exe to PATH'."
set "M_MANUAL_L1=  Install it from  https://www.python.org/downloads/"
set "M_MANUAL_L2=  and tick 'Add python.exe to PATH' in the installer, then run this again."
set "M_WRONG_FOLDER_L1=  epic_steam.py is not next to this script."
set "M_WRONG_FOLDER_L2=  Keep run.bat inside the repository folder it came from."
set "M_VENV_FAILED_L1=  Could not create the .venv virtual environment."
set "M_VENV_FAILED_L2=  On a stock Windows Python this usually means the install is damaged -"
set "M_VENV_FAILED_L3=  reinstalling Python from python.org fixes it."
set "M_PIP_FAILED_L1=  Installing legendary failed. Check the internet connection, then"
set "M_PIP_FAILED_L2=  run this again. To see the full error:"
set "M_AUTH_FAILED_L1=  Still not signed in to Epic, so there is no library to read."
set "M_AUTH_FAILED_L2=  Try again by hand to see what went wrong:"
set "M_TESTS_FAILED_L1=  The built-in self-check failed, so something in the scripts is wrong."
set "M_TESTS_FAILED_L2=  Nothing was fetched. Run it again to see what broke:"
set "M_RUN_FAILED=  That step failed - the message above says why."
goto :msgs_done

:msgs_es
set "M_STEP1=[1/7] Python 3.8+ encontrado"
set "M_STEP2_CREATING=[2/7] creando el entorno virtual .venv ..."
set "M_STEP2_READY=[2/7] entorno virtual listo"
set "M_STEP3_INSTALLING=[3/7] instalando legendary (necesita conexión a internet, una vez) ..."
set "M_STEP3_READY=[3/7] legendary instalado"
set "M_STEP4=[4/7] scripts autoverificados"
set "M_AUTH_L1=   Tu cuenta de Epic aún no está conectada. Está a punto de abrirse una"
set "M_AUTH_L2=   pestaña con el login real de Epic (epicgames.com). Inicia sesión ahí"
set "M_AUTH_L3=   como de costumbre - email/contraseña, y 2FA si lo usas."
set "M_AUTH_L4=   Si no se abre ninguna pestaña, entra tú mismo en  https://legendary.gl/epiclogin"
set "M_AUTH_L5=   Tras iniciar sesión, la pestaña llega a una página de texto plano que"
set "M_AUTH_L6=   empieza con un carácter {. Eso es correcto, no un error - es el"
set "M_AUTH_L7=   código en bruto que envía Epic, p.ej. {authorizationCode: ...}"
set "M_AUTH_L8=   Selecciona todo en esa página (Ctrl+A), cópialo (Ctrl+C), vuelve"
set "M_AUTH_L9=   a esta ventana y pégalo (Ctrl+V, o clic derecho > Pegar)"
set "M_AUTH_L10=   donde dice 'Please enter the authorizationCode value...'."
set "M_AUTH_L11=   Pega el bloque COMPLETO de texto - no hace falta extraer el código"
set "M_AUTH_L12=   a mano, este paso del script se encarga de eso."
set "M_AUTH_L13=   El código es de un solo uso y caduca en pocos minutos. Si es"
set "M_AUTH_L14=   rechazado, recarga  https://legendary.gl/epiclogin  para conseguir uno nuevo."
set "M_ACCT_CONNECTED=[5/7] Cuenta de Epic conectada: "
set "M_STEP6_FETCHING=[6/7] leyendo tu biblioteca y descargando datos de Steam ..."
set "M_STEP6_NOTE1=      La primera vez tarda un par de minutos. Cada respuesta queda en"
set "M_STEP6_NOTE2=      caché, así que las siguientes ejecuciones terminan en segundos."
set "M_STEP6_RETRY=[6/7] reintentando títulos sin match y viendo cuáles están descatalogados ..."
set "M_STEP7_RENDER=[7/7] generando el informe ..."
set "M_DONE=  Listo. Abriendo out\report.html"
set "M_NO_PYTHON=  No se encontró Python 3.8 o superior."
set "M_WINGET_DEFAULT=S"
set "M_WINGET_PROMPT=  ¿Instalar Python 3.12 ahora con winget? [S/n] "
set "M_WINGET_INSTALLING=  Instalando Python 3.12 con winget ..."
set "M_PATH_REFRESH=  Recogiendo el PATH actualizado ..."
set "M_STILL_NOT_FOUND=  Python 3.8 o superior seguía sin encontrarse tras la instalación."
set "M_REOPEN_L1=  Cierra esta ventana y vuelve a ejecutar run.bat - un proceso nuevo desde"
set "M_REOPEN_L2=  el Explorador recogerá el PATH nuevo aunque este no lo vea. Si sigue"
set "M_REOPEN_L3=  fallando, instálalo a mano desde https://www.python.org/downloads/"
set "M_REOPEN_L4=  y marca 'Add python.exe to PATH'."
set "M_MANUAL_L1=  Instálalo desde  https://www.python.org/downloads/"
set "M_MANUAL_L2=  y marca 'Add python.exe to PATH' en el instalador; luego ejecuta esto de nuevo."
set "M_WRONG_FOLDER_L1=  epic_steam.py no está junto a este script."
set "M_WRONG_FOLDER_L2=  Mantén run.bat dentro de la carpeta del repositorio del que vino."
set "M_VENV_FAILED_L1=  No se pudo crear el entorno virtual .venv."
set "M_VENV_FAILED_L2=  En un Python de Windows normal esto suele significar que la instalación"
set "M_VENV_FAILED_L3=  está dañada - reinstalar Python desde python.org lo soluciona."
set "M_PIP_FAILED_L1=  La instalación de legendary falló. Comprueba la conexión a internet,"
set "M_PIP_FAILED_L2=  y ejecuta esto de nuevo. Para ver el error completo:"
set "M_AUTH_FAILED_L1=  Sigues sin iniciar sesión en Epic, así que no hay biblioteca que leer."
set "M_AUTH_FAILED_L2=  Inténtalo a mano para ver qué falló:"
set "M_TESTS_FAILED_L1=  La autoverificación falló, así que algo en los scripts está mal."
set "M_TESTS_FAILED_L2=  No se descargó nada. Ejecuta esto de nuevo para ver qué se rompió:"
set "M_RUN_FAILED=  Ese paso falló - el mensaje de arriba explica por qué."

:msgs_done

echo.
echo   Epic Backlog Triage
echo   ===================
echo.

rem ------------------------------------------------------- 1. find a Python
call :detect_python
if defined PY goto :have_python
goto :no_python

:have_python
echo %M_STEP1%
if not exist "epic_steam.py" goto :wrong_folder

rem ------------------------------------------- 2. private virtual environment
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" goto :have_venv
echo %M_STEP2_CREATING%
%PY% -m venv .venv
if errorlevel 1 goto :venv_failed

:have_venv
echo %M_STEP2_READY%

rem -------------------------------------------------------- 3. dependencies
"%VPY%" -c "import legendary" >nul 2>&1
if not errorlevel 1 goto :have_deps
echo %M_STEP3_INSTALLING%
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :pip_failed

:have_deps
echo %M_STEP3_READY%

rem -------------------------------------------------------- 4. self-check
rem Fast and offline. Running it here means a half-applied edit or a damaged
rem checkout is caught before the Epic login and the Steam fetching, rather
rem than after. Silent unless something is actually wrong. The release zip
rem ships without test_*.py (dev-only, not needed to run) - unittest
rem discover finding zero tests exits nonzero ("NO TESTS RAN"), which would
rem read as a broken checkout when there is really just nothing to check.
if not exist "test_*.py" goto :self_checked
"%VPY%" -m unittest discover -b >nul 2>&1
if errorlevel 1 goto :tests_failed
:self_checked
echo %M_STEP4%

rem ------------------------------------------------------- 5. Epic account
call :check_auth
if not errorlevel 1 goto :have_auth

echo.
echo   ---------------------------------------------------------------------
echo %M_AUTH_L1%
echo %M_AUTH_L2%
echo %M_AUTH_L3%
echo.
echo %M_AUTH_L4%
echo.
echo %M_AUTH_L5%
echo %M_AUTH_L6%
echo %M_AUTH_L7%
echo.
echo %M_AUTH_L8%
echo %M_AUTH_L9%
echo %M_AUTH_L10%
echo %M_AUTH_L11%
echo %M_AUTH_L12%
echo.
echo %M_AUTH_L13%
echo %M_AUTH_L14%
echo   ---------------------------------------------------------------------
echo.
".venv\Scripts\legendary.exe" auth
echo.
call :check_auth
if errorlevel 1 goto :auth_failed

:have_auth
"%VPY%" -c "from legendary.core import LegendaryCore; u = LegendaryCore().lgd.userdata or {}; print('%M_ACCT_CONNECTED%' + u.get('displayName', '?'))"

rem ----------------------------------------------------------- 6. the work
echo.
echo %M_STEP6_FETCHING%
echo %M_STEP6_NOTE1%
echo %M_STEP6_NOTE2%
echo.
"%VPY%" epic_steam.py %*
if errorlevel 1 goto :run_failed

echo.
echo %M_STEP6_RETRY%
"%VPY%" second_pass.py
if errorlevel 1 goto :run_failed

rem --------------------------------------------------------- 7. the report
echo.
echo %M_STEP7_RENDER%
"%VPY%" build_report.py
if errorlevel 1 goto :run_failed

echo.
echo %M_DONE%
start "" "out\report.html"
goto :done

rem ------------------------------------------------------------- failures
:no_python
echo %M_NO_PYTHON%
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

rem Pre-set the default so WINGET_CONFIRM is always defined: set /p leaves an
rem existing value untouched on empty input, but leaves it flat-out undefined
rem if there was no prior value - and %VAR:~0,1% on an undefined variable
rem corrupts the rest of the line instead of expanding to nothing.
set "WINGET_CONFIRM=%M_WINGET_DEFAULT%"
set /p "WINGET_CONFIRM=%M_WINGET_PROMPT%"
if /i "%WINGET_CONFIRM:~0,1%"=="n" goto :no_python_manual

echo.
echo %M_WINGET_INSTALLING%
call winget install -e --id Python.Python.3.12
if %errorlevel% neq 0 goto :no_python_manual

:winget_installed
rem The installer just wrote a new PATH to the registry, but this process's
rem copy of PATH is still the one it started with - re-reading the registry
rem in-process picks it up without needing a fresh window from Explorer.
echo.
echo %M_PATH_REFRESH%
call :refresh_path
call :detect_python
if defined PY goto :have_python

echo %M_STILL_NOT_FOUND%
echo.
echo %M_REOPEN_L1%
echo %M_REOPEN_L2%
echo %M_REOPEN_L3%
echo %M_REOPEN_L4%
goto :failed

:no_python_manual
echo %M_MANUAL_L1%
echo %M_MANUAL_L2%
goto :failed

:wrong_folder
echo %M_WRONG_FOLDER_L1%
echo %M_WRONG_FOLDER_L2%
goto :failed

:venv_failed
echo %M_VENV_FAILED_L1%
echo %M_VENV_FAILED_L2%
echo %M_VENV_FAILED_L3%
goto :failed

:pip_failed
echo %M_PIP_FAILED_L1%
echo %M_PIP_FAILED_L2%
echo       .venv\Scripts\python.exe -m pip install -r requirements.txt
goto :failed

:auth_failed
echo %M_AUTH_FAILED_L1%
echo %M_AUTH_FAILED_L2%
echo       .venv\Scripts\legendary.exe auth
goto :failed

:tests_failed
echo %M_TESTS_FAILED_L1%
echo %M_TESTS_FAILED_L2%
echo       .venv\Scripts\python.exe -m unittest discover
goto :failed

:run_failed
echo.
echo %M_RUN_FAILED%
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

rem winget's per-user Python install doesn't reliably register the py
rem launcher, and its own python.exe can land *behind* the Microsoft Store's
rem stub in PATH order - "where python" would pick the stub, which prints an
rem install nag and exits nonzero, over the real interpreter sitting right
rem next to it. Check the known python.org/winget install locations by exact
rem path instead of trusting PATH search to find the right one. These are
rem plain single-line loops, not do-(...)-blocks: %ProgramFiles(x86)% has
rem literal parentheses in the name, which breaks cmd's block parser inside
rem a parenthesized for/if body.
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :_try_pydir "%%D"
if defined PY exit /b 0
for /d %%D in ("%ProgramFiles%\Python3*") do call :_try_pydir "%%D"
if defined PY exit /b 0
for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :_try_pydir "%%D"
if defined PY exit /b 0

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=python"
exit /b 0

:_try_pydir
if defined PY exit /b 0
if not exist "%~1\python.exe" exit /b 0
"%~1\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set "PY="%~1\python.exe""
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
