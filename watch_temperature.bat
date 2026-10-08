@echo off
setlocal
cd /d "%~dp0"

rem Live oven-temperature plot. Does not open the oven port.
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" lab_tools\animate_example_prev.py
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 lab_tools\animate_example_prev.py
    goto done
)
python lab_tools\animate_example_prev.py

:done
if errorlevel 1 goto fail
echo OK
pause
exit /b 0

:fail
echo FAIL
pause
exit /b 1
