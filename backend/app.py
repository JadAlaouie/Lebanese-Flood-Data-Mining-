from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.src.google_search import google_search
from backend.src.database import init_db, save_search_result, save_scraped_article
from backend.src.scraper import scrape_article
import sqlite3


app = Flask(__name__)
CORS(app)
init_db()

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Get search results from Google
    results = google_search(query)
    scraped_articles = []
    
    # Save and scrape each result immediately
    for item in results:
        # Save search result to database
        conn = sqlite3.connect('flood_data.db')
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO search_results (title, link, snippet)
            VALUES (?, ?, ?)
        """, (item.get('title'), item.get('link'), item.get('snippet')))
        search_result_id = c.lastrowid or c.execute(
            "SELECT id FROM search_results WHERE link = ?", 
            (item.get('link'),)
        ).fetchone()[0]
        conn.commit()
        conn.close()
        
        # Scrape the article immediately
        print(f"Scraping: {item.get('title')} - {item.get('link')}")
        article_data = scrape_article(item.get('link'))
        
        if article_data['success']:
            # Save scraped content to the new independent scraped_articles table
            save_scraped_article(
                url=item.get('link'),
                title=article_data['title'] or item.get('title'),
                content=article_data['content'],
                word_count=article_data['word_count'],
                source_query=query,
                success=True
            )
            
            # Also save to original articles table for backward compatibility
            conn = sqlite3.connect('flood_data.db')
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO articles (search_result_id, url, content)
                VALUES (?, ?, ?)
            """, (search_result_id, item.get('link'), article_data['content']))
            conn.commit()
            conn.close()
            
            # Add scraped content to the response
            scraped_articles.append({
                'title': article_data['title'] or item.get('title'),
                'link': item.get('link'),
                'snippet': item.get('snippet'),
                'content': article_data['content'][:500] + '...' if len(article_data['content']) > 500 else article_data['content'],
                'word_count': article_data['word_count'],
                'scraped': True
            })
        else:
            # Save failed scrape attempt
            save_scraped_article(
                url=item.get('link'),
                title=item.get('title'),
                content=None,
                word_count=0,
                source_query=query,
                success=False
            )
            
            scraped_articles.append({
                'title': item.get('title'),
                'link': item.get('link'),
                'snippet': item.get('snippet'),
                'content': None,
                'error': article_data.get('error'),
                'scraped': False
            })
        
        # Small delay between scrapes
        import time
        time.sleep(0.5)
    
    return jsonify({
        'query': query,
        'total_results': len(results),
        'scraped_count': len([a for a in scraped_articles if a['scraped']]),
        'articles': scraped_articles
    })

@app.route('/scrape', methods=['POST'])
def scrape_saved_links():
    """Scrape articles from saved search results"""
    try:
        conn = sqlite3.connect('flood_data.db')
        c = conn.cursor()
        
        # Get unscraped search results
        c.execute("""
            SELECT sr.id, sr.link, sr.title 
            FROM search_results sr 
            LEFT JOIN articles a ON sr.id = a.search_result_id 
            WHERE a.id IS NULL 
            LIMIT 10
        """)
        
        unscraped = c.fetchall()
        conn.close()
        
        if not unscraped:
            return jsonify({'message': 'No unscraped links found', 'scraped_count': 0})
        
        scraped_count = 0
        results = []
        
        for result_id, url, title in unscraped:
            print(f"Scraping: {title} - {url}")
            article_data = scrape_article(url)
            
            if article_data['success']:
                # Save to articles table
                conn = sqlite3.connect('flood_data.db')
                c = conn.cursor()
                c.execute("""
                    INSERT INTO articles (search_result_id, url, content)
                    VALUES (?, ?, ?)
                """, (result_id, url, article_data['content']))
                conn.commit()
                conn.close()
                scraped_count += 1
                
            results.append({
                'url': url,
                'title': title,
                'success': article_data['success'],
                'word_count': article_data.get('word_count', 0),
                'error': article_data.get('error')
            })
            
            # Add delay between requests to be respectful
            import time
            time.sleep(1)
        
        return jsonify({
            'message': f'Scraped {scraped_count} articles',
            'scraped_count': scraped_count,
            'total_processed': len(unscraped),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
