@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" run\board_only.py --board board_02 --group groupB
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 run\board_only.py --board board_02 --group groupB
    goto done
)
python run\board_only.py --board board_02 --group groupB

:done
if errorlevel 1 goto fail
echo OK
exit /b 0

:fail
echo FAIL
pause
exit /b 1
