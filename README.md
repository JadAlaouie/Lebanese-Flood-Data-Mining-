
# Flood Data Mining — Backend

This document describes the backend service of the Flood Data Mining project. It explains what the service does, how components are organized, how to run it (locally and with Docker), and how to use the API endpoints.

## Project overview

The backend is a Flask-based service that performs the following core tasks:
- Generate strategic search queries (via an AI agent running on Ollama).
- Run web searches (Google scraping with a DuckDuckGo fallback).
- Scrape and parse articles (robust Arabic/English scraper with `newspaper3k` and BeautifulSoup fallbacks).
- Persist scraped articles, images and AI analysis results in a SQLite database.
- Provide endpoints to trigger searches, poll progress, save/delete articles, and export results to Excel (including AI-extracted fields).

Key design goals: good Arabic + English scraping support, robust AI analysis with on-host Ollama integration, and a simple REST API for the frontend.

## Repository layout (backend)

- `backend/app.py` — Main Flask application and API. Orchestrates searches, scraping, AI calls and DB writes.
- `backend/dockerfile` — Dockerfile used by `docker-compose` to build the backend container.
- `backend/README.md` — (this file) backend documentation.
- `backend/src/` — Core modules:
   - `database.py` — SQLite schema + helpers for saving scraped articles, image metadata, AI analysis and saved articles.
   - `scraper.py` — Best-effort article scraper with Arabic/English support, `newspaper3k` integration, image extraction, and robust fallbacks.
   - `ai_agent.py` — Ollama-based agent for flood relevance detection, information extraction and query-generation.
   - `google_search.py` — Performs search by scraping Google result pages with a DuckDuckGo fallback.
   - `export_ai_filtered.py` — Minimal Flask app for transforming AI-filtered JSON into an Excel workbook (optional microservice).

## Important dependencies

Python packages referenced in the codebase (ensure they are installed):
- requests
- beautifulsoup4
- flask
- flask-cors
- python-dotenv
- openpyxl (required for Excel export endpoints)
- newspaper3k (optional, highly recommended for better article extraction)
- httpx (optional fallback for special HTTP cases)

Note: `requirements.txt` currently lists the core dependencies but may need `openpyxl`, `newspaper3k`, and `httpx` added if you use the export or advanced scraping features.

## Setup and running

Two common ways to run the backend: Docker Compose (recommended for the full stack) and local development.

### 1) Full stack with Docker Compose (recommended)

The repository includes `docker-compose.yml` that configures three services:
- `ollama` — runs the Ollama model (exposes `11434`) used by the AI agent.
- `backend` — this Flask backend (exposes `5000`).
- `frontend` — static frontend served by nginx (exposes `8080`).

To run the stack:

```powershell
# From the repository root on Windows PowerShell
docker compose up --build
```

After startup:
- Ollama will be available (container `ollama`) at `http://localhost:11434`.
- Backend API will be available at `http://localhost:5000`.
- Frontend will be served at `http://localhost:8080` (nginx proxies `/api/` to the backend).

Notes:
- The frontend JavaScript sometimes calls `http://localhost:5000` directly; when running via nginx you may prefer changing the frontend to call the proxied `/api/` paths or update `nginx.conf`.
- If you run the frontend static files directly (not through nginx), CORS is enabled on the backend so cross-origin requests are allowed.

### 2) Local development without Docker

Requirements:
- Python 3.10+ and pip
- (Optional) Ollama CLI or an equivalent model server running on `http://localhost:11434`.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
# If you need export or advanced scraping:
python -m pip install openpyxl newspaper3k httpx
```

Run backend:

```powershell
python backend/app.py
```

You can serve the frontend folder quickly using Python HTTP server:

```powershell
cd frontend
python -m http.server 8080
# Open http://localhost:8080 in your browser
```

Alternatively use `run-all.ps1` to open separate windows for Ollama, backend and a static server (Windows only).

## Environment / configuration

- `OLLAMA_URL` (optional): Override default Ollama URL (default: `http://localhost:11434`). When running with Docker Compose the backend is configured to use `http://ollama:11434`.
- `DATABASE_PATH` (optional): Path to the SQLite DB file (default: `flood_data.db`). Docker sets this to `/app/flood_data.db` inside the container.
- `.env`: The project may include `.env` usage for secrets; however the current code does not require Google API keys (it scrapes search HTML). If you switch to Google Custom Search API, add API keys to `.env` and update the search module.

## API endpoints (backend)

Main endpoints exposed by `backend/app.py`:

- GET `/test`
   - Health check. Returns server status.

- POST `/search`
   - Body: JSON with `queries` (string or list) and `analyze_ai` (bool, default true).
   - Behavior: Starts a background thread that runs search -> scrape -> save -> optional AI analysis. Returns 202 Accepted and the client should poll `/search-progress`.

- GET `/search-progress`
   - Returns JSON progress state: total, completed, current_step, progress_percentage and `final_results` once completed. Frontend polls this to update the progress bar.

- POST `/generate-queries`
   - Body: JSON with `keywords`, `context`, `num_queries`, `language`, `model`.
   - Generates strategic search queries using the Ollama agent; includes robust parsing and algorithmic fallbacks.

- POST `/filter-articles-ai`
   - Body: JSON with `articles` (array). Runs an AI extraction prompt for each article and returns `filtered_results`.

- GET `/flagged`
   - Returns articles flagged as relevant by the AI (based on keyword detection and ai_analysis table).

- POST `/save-article`
   - Save an article to `saved_articles` table. Body fields: `url`, `title`, `snippet`, `full_content`, `word_count`, `image_count`, `images`, `flagged`.

- GET `/saved-articles`
   - Retrieve all saved articles.

- DELETE `/delete-saved-article`
   - Body: `{ "url": "..." }` – deletes article by URL.

- GET `/export-saved-articles`
   - Exports saved articles to an Excel workbook and returns it as a download using `openpyxl`.

- GET `/export-saved-articles-ai`
   - Runs AI extraction/classification for saved articles and returns an Excel workbook containing AI-extracted fields.

Note: `export_ai_filtered.py` provides an alternative microservice endpoint (`/export-ai-filtered`) which accepts POSTed `filtered_results` and returns an Excel workbook; useful for decoupling export logic.

## Database schema (high level)

Created by `init_db()` in `backend/src/database.py` (SQLite default `flood_data.db`):

- `queries` — saved generated queries (id, keyword, query, created_at).
- `search_results` — raw search results returned from scraping (url, title, snippet, scraped flag).
- `scraped_articles` — scraped article content and metadata (url, title, content, word_count, image_count, scraped_at, source_query).
- `scraped_images` — image metadata for scraped articles (article_id, image_url, alt_text, caption, title, width, height, local_path, file_size).
- `ai_analysis` — AI results stored per article (article_id, url, is_relevant, confidence, keywords_found JSON, summary, category, location, flood_type, severity, key_facts).
- `saved_articles` — user-saved articles with `images` stored as JSON text and `saved_at` timestamp.

Use `view_db.py` from the repo root to print a quick DB summary and recent AI results.

## AI agent (Ollama) details

- The AI agent (`src/ai_agent.py`) prefers a local Ollama server (`/api/generate` and `/api/chat`). It attempts multiple fallbacks and parsing heuristics to return valid JSON.
- The agent includes a large Lebanese + flood keyword list used for quick relevance detection and priority flagging (Arabic + English).
- The flood extraction is driven by a strict prompt (`GPT_FLOOD_EXTRACTION_PROMPT`) which asks the model to return a JSON object with exact field names (Location, Event date, Flood classification, etc.). The backend expects valid JSON from that prompt.
- Ensure Ollama is running and the model (e.g., `gpt-oss:20b`) is available before using query generation or AI extraction endpoints.

## Frontend notes and integration

- The frontend static site (folder `frontend/`) contains `index.html`, `script.js` and `styles.css`.
- The frontend communicates with the backend endpoints described above; some JS requests use `http://localhost:5000` while the Docker/nginx setup expects `/api/` to be proxied. When deploying with Docker Compose:
   - Either update the frontend to call `/api/` endpoints (recommended), or
   - Keep JS pointing to `http://localhost:5000` and expose backend port directly (less ideal in Docker).

## Troubleshooting and tips

- Missing Python packages: If you see import errors for `openpyxl`, `newspaper`, or `httpx`, install them:

```powershell
python -m pip install openpyxl newspaper3k httpx
```

- Ollama not found: the stack expects an Ollama server. To run locally you can use the `run-all.ps1` or start Ollama separately. In Docker Compose the `ollama` service is included.
- Google search scraping can be blocked or return different HTML over time. Consider switching to the Google Custom Search API for more reliable results (if you have API credits) and update `src/google_search.py` accordingly.

## Development notes and suggestions

- Add `openpyxl`, `newspaper3k`, and `httpx` to `requirements.txt` so Docker builds include them if you use those features.
- Update frontend API base URLs to use `/api/` to match the nginx proxy used in the Docker setup.
- Consider running the Flask backend behind a production WSGI server (gunicorn) for concurrency and stability in production, especially when the service runs background threads.
- Add a small `README.md` at the repository root that documents how to run the full stack and where to find the main entry points.

## License & contact

This repository contains research tooling; include your preferred license file (e.g., `LICENSE`) and contact information here. If you want, I can add a template MIT or Apache license and a short `CONTRIBUTING.md`.

---

If you want I can also:
- Add this documentation as a top-level `PROJECT_DOCUMENTATION.md` (or update the repo root README).
- Update `requirements.txt` to include recommended packages.
- Modify frontend calls to use `/api/` for Docker compatibility.
