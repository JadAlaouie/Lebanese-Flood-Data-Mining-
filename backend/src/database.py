import sqlite3
import json
from datetime import datetime

# Helper function to convert SQLite rows to dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def init_db(db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Original tables
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  keyword TEXT NOT NULL,
                  query TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Drop and recreate search_results table to fix schema issues
    c.execute('''DROP TABLE IF EXISTS search_results''')
    c.execute('''CREATE TABLE search_results
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
                  image_count INTEGER DEFAULT 0,
                  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source_query TEXT,
                  success INTEGER DEFAULT 1)''')
    
    # New table for storing image data
    c.execute('''CREATE TABLE IF NOT EXISTS scraped_images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_id INTEGER,
                  image_url TEXT NOT NULL,
                  alt_text TEXT,
                  caption TEXT,
                  title TEXT,
                  width INTEGER,
                  height INTEGER,
                  local_path TEXT,
                  file_size INTEGER,
                  downloaded INTEGER DEFAULT 0,
                  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (article_id) REFERENCES scraped_articles (id))''')
    
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

    # New table for saved articles
    c.execute('''CREATE TABLE IF NOT EXISTS saved_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT NOT NULL UNIQUE,
                  title TEXT,
                  snippet TEXT,
                  full_content TEXT,
                  word_count INTEGER,
                  image_count INTEGER DEFAULT 0,
                  images TEXT,
                  flagged INTEGER DEFAULT 0,
                  saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# --- MISSING FUNCTIONS ADDED HERE ---

def save_article_to_saved(url, title, snippet, full_content, word_count, image_count, images, flagged, db_path='flood_data.db'):
    """Save an article to the saved_articles table."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    images_json = json.dumps(images) if images else '[]'
    
    try:
        c.execute('''INSERT INTO saved_articles 
                     (url, title, snippet, full_content, word_count, image_count, images, flagged)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT(url) DO UPDATE SET
                     title=excluded.title, 
                     full_content=excluded.full_content,
                     flagged=excluded.flagged,
                     saved_at=CURRENT_TIMESTAMP
                  ''', 
                  (url, title, snippet, full_content, word_count, image_count, images_json, flagged))
        conn.commit()
        return {"success": True, "message": "Article saved/updated successfully."}
    except sqlite3.IntegrityError as e:
        print(f"[DB] IntegrityError saving article: {url}\nError: {e}\nData: title={title}, snippet={snippet}, full_content={full_content}, word_count={word_count}, image_count={image_count}, images={images_json}, flagged={flagged}")
        return {"success": False, "message": f"Integrity Error: {e}"}
    except Exception as e:
        print(f"[DB] General DB Error saving article: {url}\nError: {e}\nData: title={title}, snippet={snippet}, full_content={full_content}, word_count={word_count}, image_count={image_count}, images={images_json}, flagged={flagged}")
        return {"success": False, "message": f"Database Error: {e}"}
    finally:
        conn.close()

def get_saved_articles(db_path='flood_data.db'):
    """Retrieve all articles from the saved_articles table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory  # Use dict_factory for easier JSON conversion
    c = conn.cursor()
    
    c.execute('SELECT * FROM saved_articles ORDER BY saved_at DESC')
    articles = c.fetchall()
    
    # Process images field from JSON string back to list/dict
    for article in articles:
        try:
            article['images'] = json.loads(article['images'])
        except (json.JSONDecodeError, TypeError):
            article['images'] = []
            
    conn.close()
    return articles

def delete_saved_article(url, db_path='flood_data.db'):
    """Delete an article from the saved_articles table by URL."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('DELETE FROM saved_articles WHERE url = ?', (url,))
    
    if c.rowcount > 0:
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Article deleted: {url}"}
    else:
        conn.close()
        return {"success": False, "message": f"Article not found: {url}"}

# --- EXISTING FUNCTIONS BELOW ---

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

def save_scraped_article(url, title, content, word_count, source_query, success, images=None, db_path='flood_data.db'):
    """Save scraped article with optional images"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    image_count = len(images) if images else 0
    
    c.execute('''INSERT INTO scraped_articles 
                 (url, title, content, word_count, image_count, source_query, success)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
             (url, title, content, word_count, image_count, source_query, success))
    
    article_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Save images if provided
    if images:
        save_scraped_images(article_id, images, db_path)
    
    return article_id

def save_scraped_images(article_id, images, db_path='flood_data.db'):
    """Save scraped images to database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    for img in images:
        c.execute('''INSERT INTO scraped_images 
                     (article_id, image_url, alt_text, caption, title, width, height, 
                      local_path, file_size, downloaded)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (article_id, img.get('url'), img.get('alt_text'), img.get('caption'), 
                  img.get('title'), img.get('width'), img.get('height'), img.get('local_path'), 
                  img.get('file_size'), img.get('downloaded', 0)))
    
    conn.commit()
    conn.close()

def save_article(url, content, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('INSERT INTO articles (url, content) VALUES (?, ?)', (url, content))
    conn.commit()
    conn.close()

def get_unanalyzed_articles(limit=10, db_path='flood_data.db'):
    """Get articles that haven't been analyzed yet"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        SELECT sa.id, sa.url, sa.title, sa.content 
        FROM scraped_articles sa 
        LEFT JOIN ai_analysis aa ON sa.id = aa.article_id 
        WHERE aa.id IS NULL AND sa.success = 1 AND sa.content IS NOT NULL 
        LIMIT ?
    ''', (limit,))
    
    articles = []
    for row in c.fetchall():
        articles.append({
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'content': row[3]
        })
    
    conn.close()
    return articles

def get_flagged_articles(db_path='flood_data.db'):
    """Get articles flagged with Lebanese keywords"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        SELECT sa.url, sa.title, sa.content, sa.image_count, 
               aa.keywords_found, aa.confidence, aa.summary, aa.category, aa.is_relevant
        FROM scraped_articles sa 
        JOIN ai_analysis aa ON sa.id = aa.article_id 
        WHERE aa.keywords_found IS NOT NULL 
        AND aa.keywords_found != '[]' 
        AND aa.keywords_found != ''
        ORDER BY aa.confidence DESC
    ''', )
    
    articles = []
    for row in c.fetchall():
        try:
            keywords = json.loads(row[4]) if row[4] else []
        except:
            keywords = []
            
        articles.append({
            'link': row[0],
            'title': row[1],
            'scraped_content': row[2][:500] if row[2] else '',
            'image_count': row[3] or 0,
            'ai_analysis': {
                'keywords_found': keywords,
                'confidence': row[5],
                'summary': row[6],
                'category': row[7],
                'is_relevant': bool(row[8])
            }
        })
    
    conn.close()
    return articles