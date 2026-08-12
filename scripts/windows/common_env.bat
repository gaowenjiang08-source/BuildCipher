@echo off
if "%~1"=="" goto :eof
goto %~1

:ensure_python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo         Install Python 3.10+ and try again.
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}')"' ) do set "BUILDTRUST_PYTHON_VERSION=%%v"
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python %BUILDTRUST_PYTHON_VERSION% is too old.
    echo         BuildTrust Studio requires Python 3.10 or newer.
    exit /b 1
)

echo [OK] Python %BUILDTRUST_PYTHON_VERSION%
exit /b 0

:ensure_poetry
poetry --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Poetry was not found in PATH.
    echo         Install Poetry first: https://python-poetry.org/docs/
    exit /b 1
)

for /f "delims=" %%v in ('poetry --version') do set "BUILDTRUST_POETRY_VERSION=%%v"
echo [OK] %BUILDTRUST_POETRY_VERSION%
exit /b 0

:ensure_node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found in PATH.
    echo         Install Node.js 18+ and try again.
    exit /b 1
)

for /f "delims=" %%v in ('node --version') do set "BUILDTRUST_NODE_VERSION=%%v"
node -e "const major = Number(process.versions.node.split('.')[0]); process.exit(major >= 18 ? 0 : 1)"
if errorlevel 1 (
    echo [ERROR] Node.js %BUILDTRUST_NODE_VERSION% is too old.
    echo         BuildTrust Studio requires Node.js 18 or newer.
    exit /b 1
)

echo [OK] Node.js %BUILDTRUST_NODE_VERSION%
exit /b 0

:ensure_npm
call npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found in PATH.
    exit /b 1
)

for /f "delims=" %%v in ('cmd /c npm --version') do set "BUILDTRUST_NPM_VERSION=%%v"
echo [OK] npm %BUILDTRUST_NPM_VERSION%
exit /b 0

:ensure_backend_deps
poetry run python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if not errorlevel 1 (
    echo [OK] Backend dependencies already available.
    exit /b 0
)

echo [INFO] Backend dependencies missing. Running poetry install...
poetry install
if errorlevel 1 (
    echo [ERROR] poetry install failed.
    exit /b 1
)

echo [OK] Backend dependencies installed.
exit /b 0

:ensure_frontend_deps
if exist "%ROOT_DIR%frontend\node_modules\vite\package.json" (
    echo [OK] Frontend dependencies already available.
    exit /b 0
)

echo [INFO] Frontend dependencies missing. Running npm install...
pushd "%ROOT_DIR%frontend" >nul
call npm install
set "BUILDTRUST_NPM_EXIT=%ERRORLEVEL%"
popd >nul
if not "%BUILDTRUST_NPM_EXIT%"=="0" (
    echo [ERROR] npm install failed.
    exit /b 1
)

echo [OK] Frontend dependencies installed.
exit /b 0

:warn_missing_env
if exist "%ROOT_DIR%.env" exit /b 0
echo [WARN] .env was not found. Copy .env.example to .env if you need real LLM keys.
exit /b 0
