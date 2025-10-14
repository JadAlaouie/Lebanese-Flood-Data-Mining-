
# PowerShell script to run Ollama model, backend, and serve frontend with error handling

# Function to check if Python is installed
function Test-Python {
	$python = Get-Command python -ErrorAction SilentlyContinue
	if (-not $python) {
		Write-Host "Python is not installed or not in PATH. Please install Python 3.x and try again." -ForegroundColor Red
		exit 1
	}
}

Test-Python

# Start Ollama model (gpt-oss:20b) in a new terminal window and keep it open
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'ollama run gpt-oss:20b'

# Start backend (Flask API) in a new terminal window and keep it open
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd backend; python app.py'

# Serve frontend using Python HTTP server on port 8080 in a new terminal window and keep it open
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd frontend; python -m http.server 8080'

Write-Host "All services started. If you see errors in any window, please copy them here for troubleshooting."
Write-Host "Access the frontend at http://localhost:8080"
