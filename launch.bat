@echo off
setlocal
cd /d "%~dp0"

REM Default: run from source (.venv) so the version always matches the code you just edited.
REM Packaged dist\ exe is used only when:
REM   - SEKIKIT_USE_EXE=1, or
REM   - no .venv exists (then fall back to dist if built).
REM Force source even without that logic: SEKIKIT_USE_SOURCE=1

if /I "%SEKIKIT_USE_SOURCE%"=="1" goto :run_source
if /I "%SEKIKIT_USE_EXE%"=="1" goto :run_exe

if exist "%~dp0.venv\Scripts\pythonw.exe" goto :run_source
if exist "%~dp0.venv\Scripts\python.exe" goto :run_source

:run_exe
if exist "%~dp0dist\Sekikit\Sekikit.exe" (
  start "" "%~dp0dist\Sekikit\Sekikit.exe"
  exit /b 0
)
if exist "%~dp0dist\Sekikit.exe" (
  start "" "%~dp0dist\Sekikit.exe"
  exit /b 0
)

:run_source
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv. Is Python installed and on PATH?
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -c "import customtkinter, pypdf, tkinterdnd2" 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
  )
)

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "%~dp0run.py"
) else (
  start "" ".venv\Scripts\python.exe" "%~dp0run.py"
)
exit /b 0
