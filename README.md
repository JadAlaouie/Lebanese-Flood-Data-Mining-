# Flood Data Mining Project

A comprehensive web scraping and data mining system for flood-related news and information.

## Features

- **Google Custom Search Integration**: Search for flood-related content using Google Custom Search API
- **Automatic Web Scraping**: Scrapes article content from search results automatically
- **Database Storage**: Stores search results and scraped articles in SQLite database
- **Modern Web Interface**: Clean, responsive frontend for searching and viewing results
- **Real-time Processing**: Search and scrape articles in one seamless workflow

## Project Structure

```
flood-data-mining/
├── backend/
│   ├── app.py                 # Flask API server
│   └── src/
│       ├── google_search.py   # Google Search API integration
│       ├── scraper.py         # Web scraping utilities
│       ├── database.py        # Database operations
│       └── filter.py          # Content filtering (optional)
├── frontend/
│   ├── index.html            # Main web interface
│   └── styles.css            # CSS styling
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (API keys)
└── README.md                # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here
```

### 3. Run the Backend

```bash
python -m backend.app
```

### 4. Open Frontend

Open `frontend/index.html` in your web browser.

## Database Schema

The system uses SQLite with these tables:

- **search_results**: Google search results
- **scraped_articles**: Individual scraped articles with metadata
- **articles**: Legacy article storage (for compatibility)
- **queries**: Search query history

## API Endpoints

- `POST /search`: Search for content and scrape articles automatically
- `POST /scrape`: Manual scraping of saved links (optional)

## Technologies Used

- **Backend**: Flask, BeautifulSoup4, Requests
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: SQLite
- **APIs**: Google Custom Search API

## License

MIT License