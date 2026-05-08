@echo off
chcp 65001 >nul
title BeamNG 云电脑视觉驾驶员
python vision_driver.py
if errorlevel 1 (
    echo.
    echo  程序发生错误，请查看 error_vision.log
    echo  An error occurred. Check error_vision.log
    pause
)
