@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo Starting SUMO GUI for IIT (ISM) Dhanbad Campus Simulation
echo ====================================================================

REM 1. Check if SUMO_HOME is set and valid
if defined SUMO_HOME (
    if exist "%SUMO_HOME%\bin\sumo-gui.exe" (
        set "DETECTED_SUMO_HOME=%SUMO_HOME%"
        goto :FOUND
    )
)

REM 2. Check native installation at Program Files (x86)\SUMO
if exist "C:\Program Files (x86)\SUMO\bin\sumo-gui.exe" (
    set "DETECTED_SUMO_HOME=C:\Program Files (x86)\SUMO"
    goto :FOUND
)

REM 3. Check 64-bit Program Files\SUMO
if exist "C:\Program Files\SUMO\bin\sumo-gui.exe" (
    set "DETECTED_SUMO_HOME=C:\Program Files\SUMO"
    goto :FOUND
)

REM 4. Check user AppData Python site-packages fallback
for /d %%P in ("%USERPROFILE%\AppData\Roaming\Python\Python*\site-packages\sumo") do (
    if exist "%%P\bin\sumo-gui.exe" (
        set "DETECTED_SUMO_HOME=%%P"
        goto :FOUND
    )
)

REM 5. Check if sumo-gui is on system PATH
where sumo-gui.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Located sumo-gui.exe on system PATH.
    cd /d "%~dp0"
    sumo-gui.exe -c campus.sumocfg --gui-settings-file gui-settings.cfg
    goto :EOF
)

echo ERROR: Eclipse SUMO installation could not be found!
echo Please ensure Eclipse SUMO (v1.20+) is installed or set SUMO_HOME.
echo Checked locations:
echo   - %%SUMO_HOME%%\bin\sumo-gui.exe
echo   - C:\Program Files (x86)\SUMO\bin\sumo-gui.exe
echo   - C:\Program Files\SUMO\bin\sumo-gui.exe
echo   - %%USERPROFILE%%\AppData\Roaming\Python\Python*\site-packages\sumo\bin\sumo-gui.exe
pause
exit /b 1

:FOUND
echo Detected SUMO installation at: %DETECTED_SUMO_HOME%
set "SUMO_HOME=%DETECTED_SUMO_HOME%"
set "PATH=%DETECTED_SUMO_HOME%\bin;%PATH%"

cd /d "%~dp0"
if not exist "campus.sumocfg" (
    echo ERROR: campus.sumocfg not found in "%CD%"!
    pause
    exit /b 1
)

echo Launching SUMO GUI...
"%DETECTED_SUMO_HOME%\bin\sumo-gui.exe" -c campus.sumocfg --gui-settings-file gui-settings.cfg
endlocal
