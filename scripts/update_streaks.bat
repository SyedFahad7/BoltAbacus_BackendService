@echo off
REM Script to update user streaks based on activity
REM This should be run daily via Windows Task Scheduler

REM Change to the Django project directory
cd /d "%~dp0.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the management commands
echo Updating streaks from activity...
python manage.py update_streaks_from_activity --days=7

echo Resetting inactive streaks...
python manage.py reset_inactive_streaks

echo Streak update completed at %date% %time%
