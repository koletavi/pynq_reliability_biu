@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" run\process_main.py
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import minimalmodbus, paramiko, pandas, matplotlib" >nul 2>&1
    if not errorlevel 1 (
        py -3 run\process_main.py
        goto done
    )
)
python run\process_main.py

:done
if errorlevel 1 goto fail
echo OK
exit /b 0

:fail
echo FAIL
pause
exit /b 1
