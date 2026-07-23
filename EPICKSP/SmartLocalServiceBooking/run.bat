@echo off
echo Initializing database...
call ".\.venv\Scripts\python.exe" init_db.py
echo.
echo Starting Flask application...
call ".\.venv\Scripts\python.exe" app.py
pause
