# Backend Setup and Features

## Structure
- `app.py`: Flask API for search and database
- `src/`: Contains modules for Google search and database

## Features Implemented
- Receives search queries from frontend via POST `/search`
- Uses Google Custom Search API to get results (filtered for year >= 2024)
- Saves filtered results to SQLite database
- Returns filtered results to frontend

## How to Run
1. Install dependencies:
   ```
   pip install flask python-dotenv requests
   ```
2. Run the backend:
   ```
   python backend/app.py
   ```
3. Make sure `.env` is set up with your API key and CSE ID.

## Main Files
- `backend/app.py`: Flask API
- `src/google_search.py`: Google search and filtering
- `src/database.py`: Database setup and save functions
