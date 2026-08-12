@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT_DIR=%~dp0"
title MedCipher Studio - Share Package

for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"' ) do set "STAMP=%%I"
set "OUTPUT_DIR=%ROOT_DIR%release"
set "ZIP_PATH=%OUTPUT_DIR%\MedCipherStudio_share_%STAMP%.zip"
set "STAGE_DIR=%TEMP%\MedCipherStudio_share_%STAMP%_%RANDOM%"

echo.
echo ==============================================
echo   MedCipher Studio - Share Package
echo ==============================================
echo.
echo [STEP] Running fresh cleanup with --all...
call "%ROOT_DIR%fresh.bat" --all
if errorlevel 1 (
    echo [ERROR] fresh.bat failed. Packaging aborted.
    exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if exist "%STAGE_DIR%" rd /s /q "%STAGE_DIR%"
mkdir "%STAGE_DIR%"

echo.
echo [STEP] Staging clean project snapshot...
powershell -NoProfile -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$root=(Resolve-Path '%ROOT_DIR%').Path.TrimEnd('\');" ^
    "$stage='%STAGE_DIR%';" ^
    "$zip='%ZIP_PATH%';" ^
    "$excludePrefixes=@('.git','.venv','.cache','.pytest_cache','htmlcov','dist','build','release','frontend\node_modules','frontend\.npm-cache','frontend\dist','frontend\.vite','frontend\coverage','knowledge\raw\uploads','knowledge\processed\chunks\uploads');" ^
    "if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force };" ^
    "New-Item -ItemType Directory -Path $stage -Force | Out-Null;" ^
    "Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object {" ^
    "  $relative=$_.FullName.Substring($root.Length).TrimStart('\');" ^
    "  if (-not $relative) { return $false };" ^
    "  if ($relative -eq '.coverage') { return $false };" ^
    "  if ($_.Extension -in '.pyc','.pyo') { return $false };" ^
    "  foreach ($prefix in $excludePrefixes) {" ^
    "    if ($relative -eq $prefix -or $relative.StartsWith($prefix + '\')) { return $false }" ^
    "  };" ^
    "  return $true" ^
    "} | ForEach-Object {" ^
    "  $relative=$_.FullName.Substring($root.Length).TrimStart('\');" ^
    "  $destination=Join-Path $stage $relative;" ^
    "  $destinationDir=Split-Path -Path $destination -Parent;" ^
    "  if (-not (Test-Path -LiteralPath $destinationDir)) { New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null };" ^
    "  Copy-Item -LiteralPath $_.FullName -Destination $destination -Force;" ^
    "};" ^
    "if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force };" ^
    "Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force;"
if errorlevel 1 (
    echo [ERROR] Failed to create zip package.
    if exist "%STAGE_DIR%" rd /s /q "%STAGE_DIR%"
    exit /b 1
)

if exist "%STAGE_DIR%" rd /s /q "%STAGE_DIR%"

echo.
echo [DONE] Share package created successfully.
echo [FILE] %ZIP_PATH%
echo [NOTE] The zip excludes .git, virtualenvs, node_modules, frontend npm cache,
echo [NOTE] build outputs, local caches, coverage data, and uploaded knowledge artifacts.
echo.
exit /b 0
