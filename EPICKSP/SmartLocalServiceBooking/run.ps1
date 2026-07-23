# Smart Local Service Booking - Startup Script
Write-Host "Initializing database..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" init_db.py

Write-Host "`nStarting Flask application..." -ForegroundColor Cyan
Write-Host "Access the app at: http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Press CTRL+C to stop`n" -ForegroundColor Yellow

& ".\.venv\Scripts\python.exe" app.py
