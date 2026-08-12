@echo off
setlocal
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title BuildTrust Studio - API Launcher

echo.
echo ==============================================
echo   BuildTrust Studio - API Launcher
echo ==============================================
echo.

call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_python || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_poetry || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_backend_deps || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :warn_missing_env

echo.
echo [INFO] Starting FastAPI backend...
echo       URL: http://127.0.0.1:8000
echo       Docs: http://127.0.0.1:8000/docs
echo.
poetry run buildtrust-api
exit /b %ERRORLEVEL%

:fail
echo.
echo [ERROR] API launch aborted.
pause
exit /b 1
