@echo off
echo ============================================================
echo FMEA Generator API Server
echo ============================================================
echo.
echo Checking dependencies...
pip install flask flask-cors --quiet
echo.
echo Starting API server...
echo Server will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.
python api.py
