@echo off
rem LCA-Copilot Single-Click Setup & Launcher Script for Windows

echo ================================================================================
echo                    LCA-COPILOT ONE-CLICK INSTALLER & LAUNCHER
echo ================================================================================

cd /d "%~dp0"

rem 1. Create virtual environment if it does not exist
if not exist .venv (
    echo Creating virtual environment ^(.venv^)...
    python -m venv .venv
)

rem 2. Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate

rem 3. Upgrade pip and install dependencies
echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements from requirements.txt...
pip install -r requirements.txt

rem 4. Run system diagnostics
echo Running system diagnostics...
python -m agentic_lca.cli --setup

echo ================================================================================
echo Setup complete! To run the interactive chat CLI, use:
echo   .venv\Scripts\activate.bat ^&^& python run_pipeline.py --chat
echo.
echo To run the Web Dashboard, use:
echo   .venv\Scripts\activate.bat ^&^& python run_pipeline.py --web
echo ================================================================================
pause
