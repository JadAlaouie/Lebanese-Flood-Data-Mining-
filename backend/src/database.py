import sqlite3
import json
from datetime import datetime

def init_db(db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Original tables
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  keyword TEXT NOT NULL,
                  query TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS search_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query_id INTEGER,
                  url TEXT NOT NULL,
                  title TEXT,
                  snippet TEXT,
                  scraped INTEGER DEFAULT 0,
                  FOREIGN KEY (query_id) REFERENCES queries (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  search_result_id INTEGER,
                  url TEXT NOT NULL,
                  content TEXT,
                  filtered INTEGER DEFAULT 0,
                  is_relevant INTEGER,
                  FOREIGN KEY (search_result_id) REFERENCES search_results (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS scraped_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT NOT NULL,
                  title TEXT,
                  content TEXT,
                  word_count INTEGER,
                  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source_query TEXT,
                  success INTEGER DEFAULT 1)''')
    
    # New table for AI analysis
    c.execute('''CREATE TABLE IF NOT EXISTS ai_analysis
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_id INTEGER,
                  url TEXT NOT NULL,
                  is_relevant INTEGER,
                  confidence INTEGER,
                  keywords_found TEXT,
                  summary TEXT,
                  category TEXT,
                  location TEXT,
                  flood_type TEXT,
                  severity TEXT,
                  key_facts TEXT,
                  analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (article_id) REFERENCES scraped_articles (id))''')
    
    conn.commit()
    conn.close()

def save_ai_analysis(article_id: int, url: str, analysis_result: dict, db_path='flood_data.db'):
    """Save AI analysis results to database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    relevance = analysis_result.get('relevance_analysis', {})
    detailed = analysis_result.get('detailed_info', {})
    
    c.execute('''INSERT INTO ai_analysis 
                 (article_id, url, is_relevant, confidence, keywords_found, summary, category, 
                  location, flood_type, severity, key_facts)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (article_id, url,
               relevance.get('is_relevant', 0),
               relevance.get('confidence', 0),
               json.dumps(relevance.get('keywords_found', [])),
               relevance.get('summary', ''),
               relevance.get('category', ''),
               json.dumps(detailed.get('location', [])),
               detailed.get('flood_type', ''),
               detailed.get('severity', ''),
               json.dumps(detailed.get('key_facts', []))))
    
    conn.commit()
    conn.close()

# Example save functions for each table
def save_query(keyword, query, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('INSERT INTO queries (keyword, query) VALUES (?, ?)', (keyword, query))
    query_id = c.lastrowid
    conn.commit()
    conn.close()
    return query_id

def save_search_result(title, link, snippet, db_path="flood_data.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        print(f"Saving to DB: {title} | {link}")
        c.execute('''INSERT OR IGNORE INTO search_results (url, title, snippet)
                     VALUES (?, ?, ?)''', (link, title, snippet))
        conn.commit()
        print(f"Saved to DB: {title} | {link}")
    finally:
        conn.close()

def save_scraped_article(url, title, content, word_count, source_query, success, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''INSERT INTO scraped_articles 
                 (url, title, content, word_count, source_query, success)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (url, title, content, word_count, source_query, success))
    article_id = c.lastrowid
    conn.commit()
    conn.close()
    return article_id

def save_article(url, content, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('INSERT INTO articles (url, content) VALUES (?, ?)', (url, content))
    conn.commit()
    conn.close()
