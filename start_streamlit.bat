@echo off
setlocal
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title BuildTrust Studio - Streamlit Compatibility Launcher

echo.
echo ==================================================
echo   BuildTrust Studio - Streamlit Compatibility UI
echo ==================================================
echo.

call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_python || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_poetry || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_backend_deps || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :warn_missing_env

echo.
echo [INFO] Starting Streamlit compatibility UI...
echo       URL: http://127.0.0.1:8503
echo.
poetry run streamlit run streamlit\web_app.py --server.port=8503 --server.headless=true --global.developmentMode=false
exit /b %ERRORLEVEL%

:fail
echo.
echo [ERROR] Streamlit launch aborted.
pause
exit /b 1
