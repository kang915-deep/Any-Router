@echo off
REM Any-Router 快捷启动脚本 (Windows)
REM 用法: run.bat "今天午饭花了38元"

setlocal
set PYTHONPATH=%~dp0
python %~dp0run.py %*
endlocal
