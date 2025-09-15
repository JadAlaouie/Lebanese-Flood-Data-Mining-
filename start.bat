@echo off
echo Starting Flood Data Mining System with AI Analysis...
echo.

echo Checking Python environment...
"C:/Users/PC/Desktop/flood data mining/.venv/Scripts/python.exe" -c "import sys; print('Python version:', sys.version[:5])"

echo.
echo Starting Flask backend server...
echo Server will start at http://localhost:5000
echo.
echo After the server starts:
echo 1. Open frontend/index.html in your browser
echo 2. Search for flood-related terms
echo 3. Watch as articles are scraped and analyzed with AI
echo.
echo Press Ctrl+C to stop the server
echo.

"C:/Users/PC/Desktop/flood data mining/.venv/Scripts/python.exe" backend/app.py