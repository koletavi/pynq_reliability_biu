@echo off
setlocal
cd /d "%~dp0"

echo This averages CSVs in data\boards\^<board^>\pynq_run_data
echo and writes data\boards\^<board^>\averages\.
echo It then deletes those raw CSVs and folds that board's logs into one daily log.
echo It does not read data\boards\board_02\groupB\.
echo Copy the raw CSVs somewhere safe before you continue.
echo.
set /p ANSWER=Type YES to continue: 
if /i not "%ANSWER%"=="YES" goto cancelled

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" lab_tools\average_outputs.py
    goto done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 lab_tools\average_outputs.py
    goto done
)
python lab_tools\average_outputs.py

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
