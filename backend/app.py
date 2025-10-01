from flask import send_file
import io
import openpyxl
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
# --- AI Filtering Prompt for Article Extraction ---
GPT_FLOOD_EXTRACTION_PROMPT = '''
I am providing scrapped data from an internet article about a flood event that occurred. I want you to analyze the text of the article and extract key information that I need for my analysis of flood records.

IMPORTANT: You MUST return your response as a valid JSON object with the following exact field names. If information is not available, use empty string "". If the article discusses multiple floods, return a JSON array of objects.

Return format (single event):
{
  "Location": "",
  "River/Wadi": "",
  "Event date": "",
  "Event time": "",
  "Event duration": "",
  "Article date": "",
  "Flood classification": "",
  "Flood depth": "",
  "Flood extent": "",
  "Rainfall depth": "",
  "Casualties/injuries": "",
  "Damage": "",
  "Costs": "",
  "Road closures": "",
  "Emergency services": "",
  "Response services": "",
  "Displacement": "",
  "Affected population": "",
  "Return period": "",
  "Past events": "",
  "Peak Discharge": ""
}

Field descriptions:
- Location: The location of the flood event including all locations that were affected by the flood, provide precise information including names of villages, streets, sites, etc. if available.
- River/Wadi: Name of the river or wadi that flooded (if the case is applicable)
- Event date: Date of the flood event, distinguish between the date of the flood event and the date the article was published online.
- Event time: Timing (during the day) of the flood event. Be precise.
- Event duration: duration of the flood
- Article date: Date of article online publication.
- Flood classification: Type of flood that occurred (coastal, urban, fluvial, groundwater flooding, or lake/pond flood)
- Flood depth: Depth of flood water (if found)
- Flood extent: Flood extent (width of flood)
- Rainfall depth: Rainfall depth recorded (if found)
- Casualties/injuries: Number of deaths and number of injuries
- Damage: List all type of damages (damage to agricultural lands, industries, residential houses, tents, cars, poultry, livestock, infrastructure, etc…). Also list intangible or non-physical damage including affected services such as electricity, disruption of businesses and schools, etc.
- Costs: Estimation of damage cost (if found)
- Road closures: List of road closures or cuts with locations
- Emergency services: Emergency services that responded to the event
- Response services: Type of response and emergency services that were delivered.
- Displacement: Number of displaced populations by the flood event.
- Affected population: Number of affected populations by the flood event
- Return period: the return period of the event or the period since a similar event occurred
- Past events: dates of past events that are mentioned
- Peak Discharge: peak flow of the river if mentioned

If the news is in Arabic, return the output values in Arabic. If it is in English, return the output values in English.
DO NOT include any text before or after the JSON. Return ONLY valid JSON.
'''# Global variable to track search progress and a Lock to protect it
search_progress = {
    'total': 0,
    'completed': 0,
    'current_step': 'Idle', # Renamed from current_url for better progress updates
    'status': 'idle',
    'progress_percentage': 0,
    'final_results': None # To store final result once search is complete
}
search_progress_lock = threading.Lock() # Lock for thread-safe access

# Add the project root to the system path to allow for imports from the src directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all required functions from the src directory
try:
    # NOTE: The ImportError indicates 'save_article_to_saved' is not in database.py. 
    # We rename it on import to 'db_save_article' to prevent the original recursive call error.
    from src.database import init_db, save_scraped_article, save_ai_analysis, save_scraped_images, get_flagged_articles, save_article_to_saved as db_save_article, get_saved_articles, delete_saved_article
    # Use enhanced scraper with Arabic & English support from scraper.py
    from src.scraper import scrape_article
    from src.ai_agent import analyze_scraped_article
    from src.google_search import google_search

    print("✅ All real functions loaded successfully (using enhanced scraper with Arabic & English support)")

except ImportError as e:
    print(f"❌ A required module could not be imported: {e}")
    sys.exit(1)

# Initialize the Flask app and CORS ONCE
app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# --- Export AI-Filtered Saved Articles to Excel ---
@app.route('/export-saved-articles-ai', methods=['GET'])
def export_saved_articles_ai():
    try:
        saved_articles = get_saved_articles()
        from src.ai_agent import analyze_scraped_article
        from src.scraper import scrape_article
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "AI Filtered Saved Articles"
        fields = [
            "Location", "River/Wadi", "Event date", "Event time", "Event duration", "Article date",
            "Flood classification", "Flood depth", "Flood extent", "Rainfall depth", "Casualties/injuries",
            "Damage", "Costs", "Road closures", "Emergency services", "Response services", "Displacement",
            "Affected population", "Return period", "Past events", "Peak Discharge"
        ]
        ws.append(fields)
        print(f"[DEBUG] Processing {len(saved_articles)} saved articles for AI classification")
        
        for idx, article in enumerate(saved_articles, 1):
            url = article.get("url", "")
            title = article.get("title", "")
            content = article.get("full_content", "") or article.get("content", "")
            
            print(f"\n[DEBUG] Article {idx}/{len(saved_articles)}: {title[:50]}...")
            print(f"[DEBUG] Content length: {len(content)} chars")
            
            # If content is missing or too short, re-scrape the article
            if not content or len(content) < 100:
                print(f"[DEBUG] Content is empty/short, re-scraping from: {url}")
                try:
                    scraped_data = scrape_article(url, timeout=20)
                    if scraped_data.get('success') and scraped_data.get('content'):
                        content = scraped_data['content']
                        title = scraped_data.get('title', title)
                        print(f"[DEBUG] ✓ Re-scraped! New content length: {len(content)} chars")
                    else:
                        print(f"[DEBUG] ✗ Re-scraping failed or returned no content")
                except Exception as e:
                    print(f"[DEBUG] ✗ Re-scraping error: {str(e)}")
            
            # Skip if still no content
            if not content or len(content) < 50:
                print(f"[DEBUG] ⚠ Skipping article {idx} - insufficient content")
                continue
            
            # Use the AI agent to extract/classify info
            result = analyze_scraped_article(url=url, title=title, content=content, context=GPT_FLOOD_EXTRACTION_PROMPT)
            print(f"[DEBUG] AI Result type: {type(result)}")
            print(f"[DEBUG] AI Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
            
            info = result.get('extracted_info', {})
            print(f"[DEBUG] Extracted info type: {type(info)}")
            print(f"[DEBUG] Extracted info: {str(info)[:200]}...")
            
            # Try to parse string output as JSON
            if isinstance(info, str):
                print(f"[DEBUG] Info is string, attempting JSON parse")
                try:
                    info = json.loads(info)
                    print(f"[DEBUG] JSON parse successful")
                except Exception as e:
                    print(f"[DEBUG] JSON parse failed: {e}")
                    info = {f: '' for f in fields}
            
            # If info is a list of events, write each as a row
            if isinstance(info, list):
                print(f"[DEBUG] Info is list with {len(info)} events")
                for event in info:
                    if not isinstance(event, dict):
                        continue
                    row = [event.get(f, '') for f in fields]
                    ws.append(row)
                    print(f"[DEBUG] Added row from event")
            # If info is a dict, write as a single row
            elif isinstance(info, dict):
                print(f"[DEBUG] Info is dict, adding as single row")
                row = [info.get(f, '') for f in fields]
                print(f"[DEBUG] Row data: {row[:3]}...")
                ws.append(row)
            # Otherwise, skip
            else:
                print(f"[DEBUG] Info type not recognized, skipping")
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="ai_filtered_saved_articles.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Export Saved Articles to Excel ---
@app.route('/export-saved-articles', methods=['GET'])
def export_saved_articles():
    """Export all saved articles to an Excel file"""
    try:
        saved_articles = get_saved_articles()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Saved Articles"
        # Write header
        headers = [
            "Title", "URL", "Snippet", "Full Content", "Word Count", "Image Count", "Flagged", "Saved At", "Images", "Source Query"
        ]
        ws.append(headers)
        # Write data rows
        for article in saved_articles:
            # Defensive: ensure images is a list of strings
            images = article.get("images", [])
            if not isinstance(images, list):
                try:
                    images = json.loads(images)
                except Exception:
                    images = []
            images_str = ", ".join(str(img) for img in images if img)
            # Try to get the source_query for this article
            source_query = article.get("source_query", "")
            if not source_query:
                # Try to fetch from scraped_articles if not present
                import sqlite3
                conn = sqlite3.connect('flood_data.db')
                c = conn.cursor()
                c.execute("SELECT source_query FROM scraped_articles WHERE url = ? LIMIT 1", (article.get("url", ""),))
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    source_query = row[0]
            ws.append([
                article.get("title", ""),
                article.get("url", ""),
                article.get("snippet", ""),
                article.get("full_content", ""),
                article.get("word_count", 0),
                article.get("image_count", 0),
                article.get("flagged", False),
                article.get("saved_at", ""),
                images_str,
                source_query
            ])
        # Save to a bytes buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="saved_articles.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Worker Function for Threading (The core fix) ---

def run_search_and_scrape(queries, analyze_with_ai):
    """
    This function runs in a separate thread and handles the long-running search process.
    It updates the global search_progress variable safely.
    """
    global search_progress
    
    with search_progress_lock:
        # Reset and initial state setup
        search_progress.update({
            'total': 0,
            'completed': 0,
            'current_step': 'Initializing search...',
            'status': 'searching',
            'progress_percentage': 0,
            'final_results': None,
            'error': None
        })

    grouped_results = []
    all_articles = []
    
    try:
        # Step 1: Initial Google Search for all queries to get total count
        search_results_list = []
        with search_progress_lock:
            search_progress['current_step'] = 'Fetching all Google search results...'

        for query in queries:
            results = google_search(query, num=10)
            search_results_list.append({'query': query, 'articles': results})
            search_progress['total'] += len(results)
        
        # Total articles to process is now known
        total_articles_to_process = search_progress['total']
        
        with search_progress_lock:
            search_progress['status'] = 'scraping'
        
        # Step 2: Iterate through all results and process
        for query_group in search_results_list:
            query = query_group['query']
            results = query_group['articles']
            scraped_results_for_query = []
            successful_scrapes = 0

            for i, item in enumerate(results):
                url = item.get('link')
                title = item.get('title', 'No title')
                snippet = item.get('snippet', '')
                
                # Update progress
                with search_progress_lock:
                    search_progress['completed'] += 1
                    search_progress['current_step'] = f"Scraping & Analyzing: {title} ({search_progress['completed']}/{total_articles_to_process})"
                    if total_articles_to_process > 0:
                        search_progress['progress_percentage'] = int((search_progress['completed'] / total_articles_to_process) * 100)
                
                print(f"📄 Scraping: {url}")
                
                article_id = None
                ai_analysis = None
                scraped_data = {
                    'success': False, 'url': url, 'title': title, 'content': '', 'word_count': 0, 'images': [], 'image_count': 0
                }
                
                try:
                    # Scrape Article
                    scraped_data = scrape_article(url, include_images=True, download_images=False, timeout=15)
                    
                    if scraped_data['success']:
                        successful_scrapes += 1
                        
                        # Save Scraped Data to DB
                        article_id = save_scraped_article(
                            url=scraped_data['url'],
                            title=scraped_data.get('title', title),
                            content=scraped_data.get('content', ''),
                            word_count=scraped_data.get('word_count', 0),
                            source_query=query,
                            success=scraped_data['success'],
                            images=scraped_data.get('images', [])
                        )
                        if scraped_data.get('images') and article_id:
                            save_scraped_images(article_id, scraped_data['images'])
                            
                        # Run AI Analysis
                        if analyze_with_ai and article_id:
                            try:
                                print(f"🤖 Running AI analysis for: {url}")
                                ai_analysis = analyze_scraped_article(
                                    url=scraped_data['url'],
                                    title=scraped_data.get('title', title),
                                    content=scraped_data.get('content', ''),
                                    context=GPT_FLOOD_EXTRACTION_PROMPT
                                )
                                save_ai_analysis(article_id, url, ai_analysis)
                            except Exception as e:
                                print(f"⚠️ AI analysis failed for {url}: {str(e)}")
                                ai_analysis = {"error": f"AI analysis failed: {str(e)}"}
                    
                    else:
                        print(f"⚠️ Scraping failed for: {url}")
                
                except Exception as e:
                    print(f"❌ Error processing {url}: {str(e)}")
                    traceback.print_exc()

                # Build result for frontend display
                result = {
                    'id': article_id, 
                    'title': scraped_data.get('title', title),
                    'link': url,
                    'snippet': snippet[:200] + '...' if len(snippet) > 200 else snippet,
                    'scraped': scraped_data['success'],
                    'full_content': scraped_data.get('content', ''), # Pass full content for saving
                    'word_count': scraped_data.get('word_count', 0),
                    'images': scraped_data.get('images', [])[:3],
                    'image_count': len(scraped_data.get('images', [])),
                    'ai_analysis': ai_analysis.get('relevance_analysis', {}) if ai_analysis and 'relevance_analysis' in ai_analysis else None
                }
                scraped_results_for_query.append(result)
                all_articles.append(result)
                time.sleep(0.1) # Small delay to be gentle

            # Group the results by query for final output
            grouped_results.append({
                'query': query,
                'articles': scraped_results_for_query,
                'total_results': len(scraped_results_for_query),
                'scraped_count': successful_scrapes
            })

        # Step 3: Final state update
        final_results = {
            'results': grouped_results,
            'total_articles': len([a for a in all_articles if a['scraped']]), # Count only successfully scraped
            'total_queries': len(queries)
        }
        
        with search_progress_lock:
            search_progress['completed'] = total_articles_to_process
            search_progress['progress_percentage'] = 100
            search_progress['status'] = 'completed'
            search_progress['current_step'] = 'Search completed!'
            search_progress['final_results'] = final_results
            print(f"🎉 Search completed and final results stored in progress.")
        
    except Exception as e:
        with search_progress_lock:
            search_progress['status'] = 'error'
            search_progress['error'] = str(e)
            search_progress['current_step'] = f"Search failed: {str(e)}"
        print(f"❌ Search thread error: {str(e)}")
        traceback.print_exc()

# --- Endpoint Definitions ---

@app.route('/search-progress', methods=['GET'])
def get_search_progress():
    """Return the current search progress for frontend polling"""
    with search_progress_lock:
        # Return a copy of the progress to avoid race conditions
        return jsonify(search_progress.copy())

@app.route('/search', methods=['POST'])
def search_endpoint():
    """
    Start the search process in a new thread and return an immediate 202 response.
    The client must poll /search-progress for results.
    """
    data = request.json
    queries = data.get('queries')
    
    if isinstance(queries, str):
        queries = [q.strip() for q in re.split(r',|;|\|', queries) if q.strip()]
        
    analyze_with_ai = data.get('analyze_ai', True)

    if not queries or not isinstance(queries, list):
        return jsonify({'error': 'No queries provided or invalid format.'}), 400

    print(f"🔍 Initiating background search for {len(queries)} queries...")

    # Start the worker function in a new thread
    search_thread = threading.Thread(
        target=run_search_and_scrape, 
        args=(queries, analyze_with_ai)
    )
    search_thread.start()

    # Immediately return a 202 Accepted response
    return jsonify({
        'message': 'Search started in background. Poll /search-progress for updates.',
        'status': 'accepted'
    }), 202 # 202 Accepted status code

# --- AI Filtering Endpoint for Frontend Button ---
@app.route('/filter-articles-ai', methods=['POST'])
def filter_articles_ai():
    try:
        data = request.get_json()
        articles = data.get('articles', [])
        from src.ai_agent import analyze_scraped_article
        filtered_results = []
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', '')
            content = article.get('content', '')
            # Use the user's extraction/classification prompt
            result = analyze_scraped_article(url=url, title=title, content=content, context=GPT_FLOOD_EXTRACTION_PROMPT)
            filtered_results.append(result.get('extracted_info', result))
        return jsonify({'filtered_results': filtered_results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Rest of the endpoints (No change needed) ---

@app.route('/generate-queries', methods=['POST'])
def generate_queries():
    # ... (No changes here, it's correct) ...
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
                # Find the start and end of a code block list
                start = next(i for i, l in enumerate(lines) if l.startswith('['))
                end = next(i for i, l in enumerate(lines) if l.endswith(']'))
                list_str = '\n'.join(lines[start:end + 1])
                parsed = ast.literal_eval(list_str)
                if isinstance(parsed, list):
                    queries = [str(q).strip() for q in parsed if str(q).strip()]
            except Exception as e:
                print(f"[Ollama] Failed to parse as list from code block: {e}")
        
        if not queries:
            # Fallback 1: Try to parse the entire text as a list
            if text.startswith('[') and text.endswith(']'):
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, list):
                        queries = [str(q).strip() for q in parsed if str(q).strip()]
                except Exception as e:
                    print(f"[Ollama] Failed to parse as list: {e}")
            
            # Fallback 2: Parse line-by-line (e.g., numbered list)
            if not queries:
                for line in text.split('\n'):
                    cleaned = line.lstrip('1234567890.- ').strip()
                    if cleaned:
                        queries.append(cleaned)
                queries = [q for q in dict.fromkeys(queries) if q]
        
        print(f"[Ollama] Parsed queries: {queries}")
        return jsonify({'queries': queries, 'model_used': model, 'language_preference': language}) # Added model info for frontend
        
    except Exception as e:
        print("[Ollama] Exception:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
                "full_content": article.get('scraped_content', ''), # Use full_content for saving logic
                "word_count": len(article.get('scraped_content', '').split()) if article.get('scraped_content') else 0,
                "image_count": article.get('image_count', 0),
                "images": article.get('images', []), # Added images list
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

@app.route('/save-article', methods=['POST'])
def save_article_endpoint():
    """Save an article to the saved articles table"""
    try:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title')
        snippet = data.get('snippet')
        full_content = data.get('full_content')
        word_count = data.get('word_count', 0)
        image_count = data.get('image_count', 0)
        images = data.get('images', [])
        flagged = data.get('flagged', 0)
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
            
        result = db_save_article(
            url=url, 
            title=title, 
            snippet=snippet, 
            full_content=full_content, 
            word_count=word_count, 
            image_count=image_count, 
            images=images, 
            flagged=flagged
        )
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Error in /save-article: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/saved-articles', methods=['GET'])
def get_saved_articles_endpoint():
    """Get all saved articles"""
    try:
        saved_articles = get_saved_articles()
        return jsonify({
            "articles": saved_articles,
            "total_count": len(saved_articles),
            "message": f"Found {len(saved_articles)} saved articles"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-saved-article', methods=['DELETE'])
def delete_saved_article_endpoint():
    """Delete a saved article by URL"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
            
        result = delete_saved_article(url)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
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
    print("  - POST /search - Start search and scraping (runs in background)")
    print("  - GET /flagged - Get flagged Lebanese articles")
    print("  - POST /save-article - Save a searched article")
    print("  - GET /saved-articles - Get all saved articles")
    print("  - DELETE /delete-saved-article - Delete a saved article")
    print("  - GET /test - Test server connectivity")
    print("🌐 Server starting at: http://localhost:5000")
    print("📊 View database: python view_db.py")
    
    # Set use_reloader=False when using threads in debug mode to prevent multiple threads
    # However, since Flask's debug mode can cause issues with threading, 
    # it's usually better to run with debug=False in production. 
    # For development, we'll keep it simple but acknowledge the limitation.
    app.run(debug=True, threaded=False)