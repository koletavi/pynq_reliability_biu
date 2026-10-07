@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" run\oven_run.py --check --boards board_01
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 run\oven_run.py --check --boards board_01
    goto done
)
python run\oven_run.py --check --boards board_01

:done
if errorlevel 1 goto fail
echo OK
exit /b 0

:fail
echo FAIL
pause
exit /b 1
