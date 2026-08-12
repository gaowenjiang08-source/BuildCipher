@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title MedCipher Studio - Fresh Cleanup

set "AUTO_ALL=0"
if /I "%~1"=="--all" set "AUTO_ALL=1"

set /a CLEAN_COUNT=0
set /a SKIP_COUNT=0

echo.
echo ==============================================
echo   MedCipher Studio - Fresh Cleanup
echo ==============================================
echo.
echo [INFO] Default cleanup removes local caches, build outputs,
echo [INFO] sandbox traces, and uploaded knowledge artifacts.
echo [INFO] It keeps .env, .git, source code, docs, benchmarks,
echo [INFO] templates, and built-in static data.
echo.

call :remove_dir ".pytest_cache"
call :remove_dir "htmlcov"
call :remove_dir "frontend\dist"
call :remove_dir "frontend\.vite"
call :remove_dir "frontend\coverage"
call :remove_dir "frontend\.npm-cache"
call :remove_dir "dist"
call :remove_dir "build"
call :remove_dir ".cache\case_memory"
call :remove_dir ".cache\sandbox"
call :remove_dir ".cache\llm"
call :remove_dir "knowledge\raw\uploads"
call :remove_dir "knowledge\processed\chunks\uploads"
call :remove_file ".coverage"
call :remove_recursive_dir "__pycache__"
call :remove_recursive_file "*.pyc"
call :remove_recursive_file "*.pyo"

if "%AUTO_ALL%"=="1" (
    set "REMOVE_NODE_MODULES=Y"
    set "REMOVE_CACHE=Y"
    set "REMOVE_VENV=Y"
) else (
    call :ask_yes_no "Remove frontend\\node_modules (large, recreated by npm install)?" REMOVE_NODE_MODULES
    call :ask_yes_no "Remove .cache (clears remaining download/build cache)?" REMOVE_CACHE
    call :ask_yes_no "Remove .venv if present (recreated by poetry install)?" REMOVE_VENV
)

if /I "!REMOVE_NODE_MODULES!"=="Y" call :remove_dir "frontend\node_modules"
if /I "!REMOVE_CACHE!"=="Y" call :remove_dir ".cache"
if /I "!REMOVE_VENV!"=="Y" call :remove_dir ".venv"

echo.
echo [DONE] Fresh cleanup finished.
echo [STAT] Removed !CLEAN_COUNT! item(s), skipped !SKIP_COUNT! item(s).
echo [KEEP] .env, .git, source code, docs, data\benchmarks,
echo [KEEP] data\report_templates, and data\skills were preserved.
echo [TIP] You can relaunch with start.bat / start_api.bat / start_frontend.bat.
echo.
exit /b 0

:ask_yes_no
set "%~2=N"
set "MEDCIPHER_REPLY="
set /p "MEDCIPHER_REPLY=%~1 [y/N]: "
if /I "!MEDCIPHER_REPLY!"=="Y" set "%~2=Y"
if /I "!MEDCIPHER_REPLY!"=="YES" set "%~2=Y"
exit /b 0

:remove_dir
if exist "%ROOT_DIR%%~1" (
    echo [CLEAN] %~1
    rd /s /q "%ROOT_DIR%%~1"
    set /a CLEAN_COUNT+=1
) else (
    echo [SKIP] %~1
    set /a SKIP_COUNT+=1
)
exit /b 0

:remove_file
if exist "%ROOT_DIR%%~1" (
    echo [CLEAN] %~1
    del /f /q "%ROOT_DIR%%~1" >nul 2>&1
    set /a CLEAN_COUNT+=1
) else (
    echo [SKIP] %~1
    set /a SKIP_COUNT+=1
)
exit /b 0

:remove_recursive_dir
set "FOUND_MATCH=0"
for /d /r "%ROOT_DIR%" %%D in (%~1) do (
    if exist "%%~fD" (
        echo [CLEAN] %%~fD
        rd /s /q "%%~fD"
        set /a CLEAN_COUNT+=1
        set "FOUND_MATCH=1"
    )
)
if "!FOUND_MATCH!"=="0" (
    echo [SKIP] Recursive directory pattern %~1
    set /a SKIP_COUNT+=1
)
exit /b 0

:remove_recursive_file
set "FOUND_MATCH=0"
for /r "%ROOT_DIR%" %%F in (%~1) do (
    if exist "%%~fF" (
        echo [CLEAN] %%~fF
        del /f /q "%%~fF" >nul 2>&1
        set /a CLEAN_COUNT+=1
        set "FOUND_MATCH=1"
    )
)
if "!FOUND_MATCH!"=="0" (
    echo [SKIP] Recursive file pattern %~1
    set /a SKIP_COUNT+=1
)
exit /b 0
