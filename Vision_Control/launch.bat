@echo off
setlocal
cd /d "%~dp0"

rem  Belt-and-braces: if the editable install didn't take, fall back to
rem  PYTHONPATH so `python -m vision_control.main` still finds the package.
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

rem  Default (no args): open the GUI control panel.
rem  Pass `--selftest`, `--headless --window TITLE`, etc. through verbatim.
python -m vision_control.main %*
set "EC=%ERRORLEVEL%"

if not "%EC%"=="0" (
    echo.
    echo An error occurred. Exit code: %EC%
    echo Quick checks:
    echo   python -m vision_control.main --selftest
    echo   See logs in vision_control.log ^(once logging is wired up^).
    echo.
    pause
)
endlocal
