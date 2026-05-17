@echo off
setlocal
cd /d "%~dp0"

echo.
echo ================================================
echo  Vision_Control - Dependency Setup
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://www.python.org
    echo Make sure to tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

python --version
echo.

set MIRROR=-i https://pypi.org/simple/ --trusted-host pypi.org

echo [1/5] Upgrading pip ...
python -m pip install --upgrade pip %MIRROR%
echo.

echo [2/5] Installing runtime requirements ...
python -m pip install -r requirements.txt %MIRROR%
echo.

echo [3/5] Installing vision_control package (editable mode) ...
rem  This is what makes `python -m vision_control.main` work from any cwd.
rem  Without it the package sits inside src\ and Python can't find it.
python -m pip install -e . %MIRROR%
if errorlevel 1 (
    echo.
    echo   WARN  Editable install failed. Falling back to PYTHONPATH at launch.
    echo         You may need to upgrade pip + setuptools manually:
    echo           python -m pip install --upgrade pip setuptools wheel
    echo.
)
echo.

echo [4/5] Verifying core packages ...
python -c "import dxcam;          print('  OK  dxcam          ', dxcam.__version__ if hasattr(dxcam,'__version__') else '')"
python -c "import cv2;            print('  OK  opencv-python  ', cv2.__version__)"
python -c "import numpy;          print('  OK  numpy          ', numpy.__version__)"
python -c "import onnxruntime;    print('  OK  onnxruntime    ', onnxruntime.__version__, '| providers:', onnxruntime.get_available_providers())"
python -c "import vgamepad;       print('  OK  vgamepad       ', vgamepad.__version__ if hasattr(vgamepad,'__version__') else '')"
python -c "import PIL, win32api;  print('  OK  Pillow + pywin32')"
python -c "import vision_control; print('  OK  vision_control ', vision_control.__version__)"
echo.

echo [5/5] ViGEmBus driver check ...
sc query ViGEmBus >nul 2>&1
if errorlevel 1 (
    echo   WARN  ViGEmBus driver is NOT installed.
    echo         Vision_Control will fall back to keyboard ^(SendInput^).
    echo         For best results, install:
    echo           https://github.com/ViGEm/ViGEmBus/releases
) else (
    echo   OK    ViGEmBus driver detected.
)
echo.

echo ================================================
echo Done. Run launch.bat to start, or try:
echo     python -m vision_control.main --selftest
echo ================================================
echo.
pause
endlocal
