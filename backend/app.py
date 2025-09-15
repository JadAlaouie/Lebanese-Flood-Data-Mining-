from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.src.google_search import google_search
from backend.src.database import init_db, save_search_result, save_scraped_article, save_ai_analysis
from backend.src.scraper import scrape_article
from backend.src.ai_agent import FloodAnalysisAgent
import sqlite3
import json


app = Flask(__name__)
CORS(app)
init_db()

# Initialize AI agent
ai_agent = FloodAnalysisAgent()

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
            article_id = save_scraped_article(
                url=item.get('link'),
                title=article_data['title'] or item.get('title'),
                content=article_data['content'],
                word_count=article_data['word_count'],
                source_query=query,
                success=True
            )
            
            # Perform AI analysis on the scraped content
            try:
                print(f"Analyzing content with AI for: {item.get('title')}")
                analysis_result = ai_agent.analyze_article(article_data['content'])
                
                # Save AI analysis to database
                save_ai_analysis(article_id, item.get('link'), analysis_result)
                print(f"AI analysis completed for: {item.get('title')}")
            except Exception as e:
                print(f"AI analysis failed for {item.get('title')}: {str(e)}")
                analysis_result = None
            
            # Also save to original articles table for backward compatibility
            conn = sqlite3.connect('flood_data.db')
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO articles (search_result_id, url, content)
                VALUES (?, ?, ?)
            """, (search_result_id, item.get('link'), article_data['content']))
            conn.commit()
            conn.close()
            
            # Add scraped content and AI analysis to the response
            article_response = {
                'title': article_data['title'] or item.get('title'),
                'link': item.get('link'),
                'snippet': item.get('snippet'),
                'content': article_data['content'][:500] + '...' if len(article_data['content']) > 500 else article_data['content'],
                'word_count': article_data['word_count'],
                'scraped': True
            }
            
            # Add AI analysis results to response if available
            if analysis_result:
                relevance = analysis_result.get('relevance_analysis', {})
                article_response['ai_analysis'] = {
                    'is_relevant': relevance.get('is_relevant', False),
                    'confidence': relevance.get('confidence', 0),
                    'category': relevance.get('category', 'unknown'),
                    'summary': relevance.get('summary', ''),
                    'keywords_found': relevance.get('keywords_found', [])
                }
            
            scraped_articles.append(article_response)
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

@app.route('/analyze', methods=['POST'])
def analyze_articles():
    """Run AI analysis on existing scraped articles"""
    try:
        data = request.json
        limit = data.get('limit', 10)
        
        conn = sqlite3.connect('flood_data.db')
        c = conn.cursor()
        
        # Get unanalyzed scraped articles
        c.execute("""
            SELECT sa.id, sa.url, sa.title, sa.content 
            FROM scraped_articles sa
            LEFT JOIN ai_analysis aa ON sa.id = aa.article_id
            WHERE aa.id IS NULL AND sa.success = 1 AND sa.content IS NOT NULL
            LIMIT ?
        """, (limit,))
        
        unanalyzed = c.fetchall()
        conn.close()
        
        if not unanalyzed:
            return jsonify({'message': 'No unanalyzed articles found', 'analyzed_count': 0})
        
        analyzed_count = 0
        results = []
        
        for article_id, url, title, content in unanalyzed:
            try:
                print(f"Analyzing: {title} - {url}")
                analysis_result = ai_agent.analyze_article(content)
                
                # Save AI analysis to database
                save_ai_analysis(article_id, url, analysis_result)
                analyzed_count += 1
                
                relevance = analysis_result.get('relevance_analysis', {})
                results.append({
                    'article_id': article_id,
                    'url': url,
                    'title': title,
                    'is_relevant': relevance.get('is_relevant', False),
                    'confidence': relevance.get('confidence', 0),
                    'category': relevance.get('category', 'unknown'),
                    'success': True
                })
                
            except Exception as e:
                print(f"AI analysis failed for {title}: {str(e)}")
                results.append({
                    'article_id': article_id,
                    'url': url,
                    'title': title,
                    'success': False,
                    'error': str(e)
                })
            
            # Small delay between analyses
            import time
            time.sleep(0.5)
        
        return jsonify({
            'message': f'Analyzed {analyzed_count} articles',
            'analyzed_count': analyzed_count,
            'total_processed': len(unanalyzed),
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flagged', methods=['GET'])
def get_flagged_articles():
    """Get articles flagged with Lebanese keywords or high relevance scores"""
    try:
        conn = sqlite3.connect('flood_data.db')
        c = conn.cursor()
        
        # Get flagged articles (Lebanese keywords or high confidence)
        c.execute("""
            SELECT 
                sa.id,
                sa.url,
                sa.title,
                sa.content,
                sa.word_count,
                sa.scraped_at,
                sa.source_query,
                aa.is_relevant,
                aa.confidence,
                aa.keywords_found,
                aa.category,
                aa.summary
            FROM scraped_articles sa
            LEFT JOIN ai_analysis aa ON sa.id = aa.article_id
            WHERE (
                aa.category = 'lebanese_flood_content' OR 
                aa.confidence >= 70 OR
                aa.keywords_found LIKE '%شاطئ%' OR
                aa.keywords_found LIKE '%فيضان%' OR
                aa.keywords_found LIKE '%نهر%' OR
                aa.keywords_found LIKE '%سيل%' OR
                aa.keywords_found LIKE '%امطار%'
            )
            ORDER BY aa.confidence DESC, sa.scraped_at DESC
            LIMIT 50
        """)
        
        flagged_articles = []
        for row in c.fetchall():
            article_id, url, title, content, word_count, scraped_at, source_query, is_relevant, confidence, keywords_found, category, summary = row
            
            # Parse keywords
            try:
                keywords = json.loads(keywords_found) if keywords_found else []
            except:
                keywords = []
            
            flagged_articles.append({
                'id': article_id,
                'url': url,
                'title': title,
                'content_preview': content[:300] + '...' if content and len(content) > 300 else content,
                'word_count': word_count,
                'scraped_at': scraped_at,
                'source_query': source_query,
                'is_relevant': bool(is_relevant),
                'confidence': confidence or 0,
                'keywords_found': keywords,
                'category': category,
                'summary': summary,
                'flagged': True
            })
        
        conn.close()
        
        return jsonify({
            'flagged_articles': flagged_articles,
            'total_flagged': len(flagged_articles),
            'message': f'Found {len(flagged_articles)} flagged articles'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
