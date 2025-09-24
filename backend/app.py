from flask import Flask, request, jsonify
import requests as pyrequests
from flask_cors import CORS
import time
import sys
import os
import threading
import re
import json
import ast
import traceback

# --- Global variable and initial setup ---

# Global variable to track search progress
search_progress = {
    'total': 0,
    'completed': 0,
    'current_url': '',
    'status': 'idle',
    'results': []
}

# Add the project root to the system path to allow for imports from the src directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all required functions from the src directory
try:
    from src.database import init_db, save_scraped_article, save_ai_analysis, save_scraped_images, get_flagged_articles
    from src.scraper import scrape_article
    from src.ai_agent import analyze_scraped_article
    from src.google_search import google_search

    print("✅ All real functions loaded successfully")

except ImportError as e:
    print(f"❌ A required module could not be imported: {e}")
    print("This script requires the following modules in the 'src' directory:")
    print(" - database.py")
    print(" - scraper.py")
    print(" - ai_agent.py")
    print(" - google_search.py")
    print("Please ensure all dependencies are in place before running.")
    sys.exit(1) # Exit if essential modules are not found

# Initialize the Flask app and CORS ONCE
app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# --- Endpoint Definitions ---

@app.route('/search-progress', methods=['GET'])
def get_search_progress():
    """Return the current search progress for frontend polling"""
    return jsonify(search_progress)

@app.route('/generate-queries', methods=['POST'])
def generate_queries():
    data = request.get_json()
    keywords = data.get('keywords', '')
    context = data.get('context', '')
    num_queries = data.get('num_queries', 3)
    language = data.get('language', 'mixed')
    model = data.get('model', 'gpt-oss:20b')
    try:
        num_queries = int(num_queries)
    except Exception:
        num_queries = 3

    prompt = f"""
You are an expert search query generation agent.
Generate {num_queries} distinct, strategic search queries about flooding using the following keywords: {keywords}.
Context: {context}
Language: {language}
Return only the queries as a Python list of strings. Do not include any explanation, just the list.
"""
    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt
    }
    try:
        print(f"[Ollama] Sending payload: {payload}")
        response = pyrequests.post(ollama_url, json=payload, timeout=60)
        print(f"[Ollama] Status code: {response.status_code}")
        print(f"[Ollama] Raw response: {response.text}")
        response.raise_for_status()

        responses = []
        for line in response.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                resp = obj.get('response', '')
                if resp:
                    responses.append(resp)
            except Exception as e:
                print(f"[Ollama] Failed to parse line: {line}\nError: {e}")
        
        text = ''.join(responses).strip()
        if not text:
            print("[Ollama] No generated text found in Ollama output.")
            return jsonify({'error': "No generated text found in Ollama output."}), 500
        
        queries = []
        lines = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('```')]
        
        if any(l.startswith('[') for l in lines) and any(l.endswith(']') for l in lines):
            try:
                start = next(i for i, l in enumerate(lines) if l.startswith('['))
                end = next(i for i, l in enumerate(lines) if l.endswith(']'))
                list_str = '\n'.join(lines[start:end + 1])
                parsed = ast.literal_eval(list_str)
                if isinstance(parsed, list):
                    queries = [str(q).strip() for q in parsed if str(q).strip()]
            except Exception as e:
                print(f"[Ollama] Failed to parse as list from code block: {e}")
        
        if not queries:
            if text.startswith('[') and text.endswith(']'):
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, list):
                        queries = [str(q).strip() for q in parsed if str(q).strip()]
                except Exception as e:
                    print(f"[Ollama] Failed to parse as list: {e}")
            
            if not queries:
                for line in text.split('\n'):
                    cleaned = line.lstrip('1234567890.- ').strip()
                    if cleaned:
                        queries.append(cleaned)
                queries = [q for q in dict.fromkeys(queries) if q]
        
        print(f"[Ollama] Parsed queries: {queries}")
        return jsonify({'queries': queries})
        
    except Exception as e:
        print("[Ollama] Exception:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    global search_progress

    data = request.json
    queries = data.get('queries')
    
    if isinstance(queries, str):
        queries = [q.strip() for q in re.split(r',|;|\|', queries) if q.strip()]
        
    analyze_with_ai = data.get('analyze_ai', True)

    grouped_results = []
    if not queries or not isinstance(queries, list):
        print("No queries provided or invalid format. Returning empty results.")
        final_results = {
            'results': grouped_results,
            'total_queries': 0
        }
        search_progress['final_results'] = final_results
        return jsonify(final_results)

    print(f"🔍 Starting search for queries: {queries}")
    search_progress = {
        'total': 0,
        'completed': 0,
        'current_url': '',
        'status': 'searching',
        'results': []
    }

    try:
        for query in queries:
            print(f"🔎 Processing query: {query}")
            results = google_search(query, num=10)
            print(f"✅ Google search returned {len(results)} results for query '{query}'")
            search_progress['total'] += len(results)
            search_progress['status'] = 'scraping'

            scraped_results = []
            successful_scrapes = 0
            total_results = len(results)
            for i, item in enumerate(results):
                url = item.get('link')
                title = item.get('title', 'No title')
                snippet = item.get('snippet', '')
                search_progress['completed'] += 1
                search_progress['current_url'] = url
                print(f"📄 Scraping {i+1}/{total_results}: {url}")
                try:
                    scraped_data = scrape_article(url, include_images=True, download_images=False, timeout=15)
                    if scraped_data['success']:
                        successful_scrapes += 1
                        print(f"✅ Scraped successfully: {scraped_data['word_count']} words, {scraped_data.get('image_count', 'N/A')} images")
                        article_id = save_scraped_article(
                            url=scraped_data['url'],
                            title=scraped_data.get('title', title),
                            content=scraped_data.get('content', ''),
                            word_count=scraped_data.get('word_count', 0),
                            source_query=query,
                            success=scraped_data['success'],
                            images=scraped_data.get('images', [])
                        )
                        if scraped_data.get('images'):
                            save_scraped_images(article_id, scraped_data['images'])
                        ai_analysis = None
                        if analyze_with_ai:
                            try:
                                print(f"🤖 Running AI analysis for: {url}")
                                ai_analysis = analyze_scraped_article(
                                    url=scraped_data['url'],
                                    title=scraped_data.get('title', title),
                                    content=scraped_data.get('content', '')
                                )
                                save_ai_analysis(article_id, url, ai_analysis)
                                keywords_found = ai_analysis.get('keywords_found', [])
                                if keywords_found:
                                    print(f"🚩 Lebanese keywords detected: {keywords_found}")
                                print(f"✅ AI analysis completed")
                            except Exception as e:
                                print(f"⚠️ AI analysis failed for {url}: {str(e)}")
                                ai_analysis = {"error": f"AI analysis failed: {str(e)}"}
                    else:
                        print(f"⚠️ Scraping failed for: {url}")
                        ai_analysis = None
                except Exception as e:
                    print(f"❌ Error processing {url}: {str(e)}")
                    scraped_data = {
                        'success': False,
                        'url': url,
                        'title': title,
                        'content': '',
                        'word_count': 0,
                        'images': [],
                        'image_count': 0
                    }
                    ai_analysis = None
                
                result = {
                    'title': scraped_data.get('title', title),
                    'link': url,
                    'snippet': snippet[:200] + '...' if len(snippet) > 200 else snippet,
                    'scraped': scraped_data['success'],
                    'content': scraped_data.get('content', '')[:800] if scraped_data.get('content') else '',
                    'word_count': scraped_data.get('word_count', 0),
                    'images': scraped_data.get('images', [])[:3],
                    'image_count': len(scraped_data.get('images', [])),
                    'ai_analysis': ai_analysis.get('relevance_analysis', {}) if ai_analysis else None
                }
                scraped_results.append(result)
                search_progress['results'] = scraped_results.copy()
                time.sleep(0.3)
            
            grouped_results.append({
                'query': query,
                'articles': scraped_results,
                'total_results': len(scraped_results),
                'scraped_count': successful_scrapes
            })
        
        search_progress['completed'] = search_progress['total']
        search_progress['status'] = 'completed'
        search_progress['current_url'] = ''
        print(f"🎉 Search completed for all queries.")
        
        final_results = {
            'results': grouped_results,
            'total_queries': len(queries)
        }
        search_progress['final_results'] = final_results
        return jsonify(final_results)
        
    except Exception as e:
        search_progress['status'] = 'error'
        search_progress['error'] = str(e)
        print(f"❌ Search endpoint error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/flagged', methods=['GET'])
def get_flagged_articles_endpoint():
    """Get all articles flagged with Lebanese keywords"""
    try:
        flagged_articles = get_flagged_articles()
        results = []
        for article in flagged_articles:
            result = {
                "title": article.get('title', 'No title'),
                "link": article.get('link', '#'),
                "snippet": article.get('scraped_content', '')[:200] + '...' if article.get('scraped_content') else 'No content available',
                "scraped": True,
                "content": article.get('scraped_content', ''),
                "word_count": len(article.get('scraped_content', '').split()) if article.get('scraped_content') else 0,
                "image_count": article.get('image_count', 0),
                "ai_analysis": {
                    "is_relevant": article['ai_analysis']['is_relevant'],
                    "confidence": article['ai_analysis']['confidence'],
                    "keywords_found": article['ai_analysis']['keywords_found'],
                    "summary": article['ai_analysis'].get('summary', ''),
                    "category": article['ai_analysis'].get('category', 'flood')
                }
            }
            results.append(result)
        return jsonify({
            "articles": results,
            "total_results": len(results),
            "scraped_count": len(results),
            "message": f"Found {len(results)} articles with Lebanese keywords"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify server is running"""
    return jsonify({"message": "Server is running successfully!", "status": "ok"})

if __name__ == '__main__':
    print("🌊 Starting Flood Data Mining Server...")
    print("✅ Using REAL data (scraper, database, AI agent)")
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        print("Please check your database configuration and try again.")
        sys.exit(1)
    
    print("🔍 Available endpoints:")
    print("  - GET /search-progress - Get real-time search progress")
    print("  - POST /generate-queries - Generate search queries")
    print("  - POST /search - Search and scrape articles")
    print("  - GET /flagged - Get flagged Lebanese articles")
    print("  - GET /test - Test server connectivity")
    print("🌐 Server starting at: http://localhost:5000")
    print("📊 View database: python view_db.py")
    
    app.run(debug=True)