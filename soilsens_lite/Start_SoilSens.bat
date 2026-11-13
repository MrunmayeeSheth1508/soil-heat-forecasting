@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py run_soilsens.py) || (python run_soilsens.py)
pause
