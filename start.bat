@echo off
setlocal
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title BuildTrust Studio - Fullstack Launcher

echo.
echo ==============================================
echo   BuildTrust Studio - Fullstack Launcher
echo ==============================================
echo.

call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_python || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_poetry || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_node || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_npm || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_backend_deps || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :ensure_frontend_deps || goto :fail
call "%ROOT_DIR%scripts\windows\common_env.bat" :warn_missing_env

echo.
echo [INFO] Starting backend API in a new window...
start "BuildTrust API" cmd /k "cd /d ""%ROOT_DIR%"" && poetry run buildtrust-api"

echo [INFO] Starting React frontend in a new window...
start "BuildTrust Frontend" cmd /k "cd /d ""%ROOT_DIR%frontend"" && npm run dev"

echo.
echo [OK] BuildTrust Studio is starting.
echo      API:      http://127.0.0.1:8000
echo      Frontend: http://127.0.0.1:5173
echo      Swagger:  http://127.0.0.1:8000/docs
echo.
echo [TIP] Use start_streamlit.bat if you want the Streamlit compatibility UI.
echo.
exit /b 0

:fail
echo.
echo [ERROR] Launch aborted.
pause
exit /b 1
