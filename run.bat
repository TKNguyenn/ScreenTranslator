@echo off
setlocal
cd /d %~dp0
set PYTHONUNBUFFERED=1

if not exist .venv (
    echo [SETUP] Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :fatal
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fatal

python -m pip install -r requirements.txt
if errorlevel 1 goto :fatal

if not exist config.json copy /Y config.example.json config.json >nul
if not exist providers.json copy /Y providers.example.json providers.json >nul
if not exist prompts.json copy /Y prompts.example.json prompts.json >nul
if not exist .env copy /Y .env.example .env >nul

echo.
echo [START] AI Screen Translator
python main.py
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Application exited with code %EXIT_CODE%.
    echo Check data\logs\app.log for details.
    pause
)
endlocal
exit /b %EXIT_CODE%

:fatal
echo.
echo Failed to prepare the application.
echo Check Python installation and internet/package access.
pause
endlocal
exit /b 1
