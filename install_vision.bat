@echo off
chcp 65001 >nul
title BeamNG 云电脑视觉驾驶员 - 安装依赖

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   BeamNG 云电脑视觉驾驶员 - 依赖安装         ║
echo  ║   Cloud Vision Driver - Dependency Installer  ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  正在检测 Python 环境...
echo  Detecting Python environment...
echo.

:: 检测 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [错误] 未检测到 Python！
    echo  [Error] Python not found!
    echo.
    echo  请先安装 Python 3.9 或更高版本：
    echo  Please install Python 3.9 or higher:
    echo  https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  检测到 / Found: %PYVER%
echo.

:: 升级 pip
echo  [1/2] 升级 pip / Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  完成 / Done
echo.

:: 安装依赖
echo  [2/2] 安装视觉驾驶员依赖 / Installing vision driver dependencies...
echo  （首次安装约需 1-5 分钟，请勿关闭窗口）
echo  (First install takes ~1-5 min, do not close this window)
echo.

python -m pip install -r requirements_vision.txt

if errorlevel 1 (
    echo.
    echo  [警告] 部分包安装失败，尝试逐一安装...
    echo  [Warning] Some packages failed, trying one by one...
    echo.
    python -m pip install opencv-python
    python -m pip install mss
    python -m pip install Pillow
    python -m pip install numpy
    python -m pip install pynput
    python -m pip install pygetwindow
    python -m pip install ultralytics
)

echo.
echo  ══════════════════════════════════════════════
echo  [验证] 检查安装结果 / Verifying installation...
echo  ══════════════════════════════════════════════
echo.

python -c "import cv2; print('  ✓ OpenCV', cv2.__version__)"
python -c "import mss; print('  ✓ mss', mss.__version__)"
python -c "from PIL import Image; import PIL; print('  ✓ Pillow', PIL.__version__)"
python -c "import numpy; print('  ✓ NumPy', numpy.__version__)"
python -c "import pynput; print('  ✓ pynput OK')"
python -c "import pygetwindow; print('  ✓ pygetwindow OK')" 2>nul || echo   ⚠  pygetwindow 安装失败（非致命，窗口检测功能受限）
python -c "from ultralytics import YOLO; print('  ✓ YOLOv8 (ultralytics) OK')" 2>nul || echo   ⚠  ultralytics 安装失败（可选，障碍物检测不可用）

echo.
echo  ══════════════════════════════════════════════
echo  安装完成！/ Installation complete!
echo.
echo  现在可以双击 launch_vision.bat 启动视觉驾驶员
echo  Now run launch_vision.bat to start the vision driver
echo  ══════════════════════════════════════════════
echo.
pause
