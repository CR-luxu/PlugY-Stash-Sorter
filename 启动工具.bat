@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PlugY 大箱子整理器
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
    goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    goto :end
)
echo.
echo 没有找到 Python 3。请先安装 Python 3.9 或更高版本。
echo 下载地址：https://www.python.org/downloads/
echo.
pause
:end
if errorlevel 1 pause
