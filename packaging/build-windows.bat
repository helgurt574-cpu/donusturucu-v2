@echo off
cd /d "%~dp0.."
py -3 packaging\build_native.py %*
if errorlevel 1 pause
