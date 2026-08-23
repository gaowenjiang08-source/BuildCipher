@echo off
setlocal
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title BuildCipher Studio - Frontend Launcher

echo.
echo ==============================================
echo   BuildCipher Studio - Frontend Launcher
echo ==============================================
echo.

call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_node || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_npm || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_frontend_deps || goto :fail

echo.
echo [INFO] Starting React frontend...
echo       URL: http://127.0.0.1:5173
echo       API base: http://127.0.0.1:8000
echo.
pushd "%ROOT_DIR%frontend" >nul
call npm run dev
set "BUILDCIPHER_FRONTEND_EXIT=%ERRORLEVEL%"
popd >nul
exit /b %BUILDCIPHER_FRONTEND_EXIT%

:fail
echo.
echo [ERROR] Frontend launch aborted.
pause
exit /b 1
