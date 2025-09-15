
import sqlite3

def init_db(db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Table for queries generated
    c.execute('''CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        query TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Table for search results (links from Google API)
    c.execute('''CREATE TABLE IF NOT EXISTS search_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        link TEXT UNIQUE,
        snippet TEXT
    )''')
    # Table for scraped articles
    c.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_result_id INTEGER,
        url TEXT NOT NULL,
        content TEXT,
        filtered INTEGER DEFAULT 0,
        is_relevant INTEGER,
        FOREIGN KEY(search_result_id) REFERENCES search_results(id)
    )''')
    # New table for independent scraped articles
    c.execute('''CREATE TABLE IF NOT EXISTS scraped_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        title TEXT,
        content TEXT,
        word_count INTEGER DEFAULT 0,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_query TEXT,
        success INTEGER DEFAULT 1
    )''')
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
        c.execute("""
            INSERT OR IGNORE INTO search_results (title, link, snippet)
            VALUES (?, ?, ?)
        """, (title, link, snippet))
        conn.commit()
        print(f"Saved to DB: {title} | {link}")
    finally:
        conn.close()

def save_article(url, content, db_path='flood_data.db'):
    pass

def update_article_filter(article_id, is_relevant, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('UPDATE articles SET filtered=1, is_relevant=? WHERE id=?', (is_relevant, article_id))
    conn.commit()
    conn.close()

def save_scraped_article(url, title, content, word_count, source_query, success=True, db_path='flood_data.db'):
    """Save scraped article to independent scraped_articles table"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO scraped_articles (url, title, content, word_count, source_query, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url, title, content, word_count, source_query, 1 if success else 0))
        article_id = c.lastrowid
        conn.commit()
        print(f"Saved scraped article: {title} | Words: {word_count}")
        return article_id
    finally:
        conn.close()
