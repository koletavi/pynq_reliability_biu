@echo off
setlocal
cd /d "%~dp0"

echo This averages CSVs in data\boards\board_02\groupB\pynq_run_data
echo and writes data\boards\board_02\groupB\averages\.
echo The raw CSVs stay in place.
echo That group's logs are folded into one daily log, and those original logs are removed.
echo It does not read the board A folders.
echo.
set /p ANSWER=Type YES to continue: 
if /i not "%ANSWER%"=="YES" goto cancelled

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" lab_tools\average_outputs.py --group groupB
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 lab_tools\average_outputs.py --group groupB
    goto done
)
python lab_tools\average_outputs.py --group groupB

:done
if errorlevel 1 goto fail
echo OK
pause
exit /b 0

:cancelled
echo Stopped. Raw CSVs were not changed.
pause
exit /b 0

:fail
echo FAIL
pause
exit /b 1
