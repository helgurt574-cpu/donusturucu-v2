@echo off
setlocal
cd /d "%~dp0"
set "PYTHONHOME=%~dp0runtime"
set "PYTHONPATH=%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "PATH=%~dp0runtime\Library\bin;%~dp0runtime\Scripts;%~dp0runtime;%PATH%"
if not exist "%~dp0runtime\python.exe" (
 echo Yerel Python motoru eksik. Kurulumu yeniden calistirin.
 echo Local Python runtime is missing. Run the installer again.
 exit /b 1
)
"%~dp0runtime\python.exe" -B "%~dp0launch.py" %* >> "%~dp0startup.log" 2>&1
if errorlevel 1 (
 echo Donusturucu acilamadi. Hata kaydi / Error log:
 echo %~dp0startup.log
 type "%~dp0startup.log"
 exit /b 1
)
