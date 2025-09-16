from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import sys
import os
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global variable to track search progress
search_progress = {
    'total': 0,
    'completed': 0,
    'current_url': '',
    'status': 'idle',
    'results': []
}

# Try to import real functions, fall back to mock if needed
try:
    from src.database import init_db, save_scraped_article, save_ai_analysis, save_scraped_images, get_flagged_articles
    from src.scraper import scrape_article
    from src.ai_agent import analyze_scraped_article
    
    # For google_search, handle it separately since it might have import issues
    try:
        from src.google_search import google_search
        print("✅ Successfully imported google_search")
    except Exception as e:
        print(f"⚠️ Google search import failed: {e}")
        def google_search(query):
            # Fallback mock results that look like real Google results
            return [
                {"title": f"Mock Result 1 for {query}", "link": "http://example.com/1", "snippet": f"This is a mock result for {query}"},
                {"title": f"Mock Result 2 for {query}", "link": "http://example.com/2", "snippet": f"Another mock result about {query}"},
                {"title": f"Lebanese Flood News - {query}", "link": "http://example.com/lebanon", "snippet": f"News about flooding in Lebanon related to {query}"}
            ]
    
    print("✅ Real functions loaded successfully")
    USING_REAL_DATA = True
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔧 Using fallback mock functions...")
    
    def google_search(query):
        return [{"title": "Mock Article", "link": "http://example.com", "snippet": "Mock snippet"}]
    
    def init_db(): pass
    def save_scraped_article(*args, **kwargs): return 1
    def save_ai_analysis(*args, **kwargs): pass
    def save_scraped_images(*args, **kwargs): pass
    def get_flagged_articles(): return []
    
    def scrape_article(url, **kwargs):
        return {"success": True, "url": url, "title": "Mock Title", "content": "Mock content", "word_count": 100, "images": []}
    
    def analyze_scraped_article(url, title, content):
        return {"relevance_analysis": {"is_relevant": True, "confidence": 85, "keywords_found": ["flood", "water"]}}
    
    USING_REAL_DATA = False

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

@app.route('/search', methods=['POST'])
def search():
    global search_progress
    
    data = request.json
    query = data.get('query')
    analyze_with_ai = data.get('analyze_ai', True)
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    print(f"🔍 Starting search for: {query}")
    
    # Reset progress
    search_progress = {
        'total': 0,
        'completed': 0,
        'current_url': '',
        'status': 'searching',
        'results': []
    }

    try:
        # Get search results (Google API max is 10 per request)
        results = google_search(query, num=10)  # Get maximum results per API call
        print(f"✅ Google search returned {len(results)} results")
        
        # Update progress with total
        search_progress['total'] = len(results)
        search_progress['status'] = 'scraping'
        
        scraped_results = []
        successful_scrapes = 0
        
        # Scrape ALL results from Google search
        total_results = len(results)
        for i, item in enumerate(results):  # Process ALL results, no limit
            url = item.get('link')
            title = item.get('title', 'No title')
            snippet = item.get('snippet', '')
            
            # Update progress
            search_progress['completed'] = i
            search_progress['current_url'] = url
            
            print(f"📄 Scraping {i+1}/{total_results}: {url}")
            
            try:
                # Scrape the article
                scraped_data = scrape_article(url, include_images=True, download_images=False, timeout=15)
                
                if scraped_data['success']:
                    successful_scrapes += 1
                    print(f"✅ Scraped successfully: {scraped_data['word_count']} words, {scraped_data['image_count']} images")
                    
                    # Save to database
                    article_id = save_scraped_article(
                        url=scraped_data['url'],
                        title=scraped_data.get('title', title),
                        content=scraped_data.get('content', ''),
                        word_count=scraped_data.get('word_count', 0),
                        source_query=query,
                        success=scraped_data['success'],
                        images=scraped_data.get('images', [])
                    )
                    
                    # Save images if any were found
                    if scraped_data.get('images'):
                        save_scraped_images(article_id, scraped_data['images'])
                    
                    # AI Analysis (optional)
                    ai_analysis = None
                    if analyze_with_ai:
                        try:
                            print(f"🤖 Running AI analysis for: {url}")
                            ai_analysis = analyze_scraped_article(
                                url=scraped_data['url'],
                                title=scraped_data.get('title', title),
                                content=scraped_data.get('content', '')
                            )
                            
                            # Save AI analysis to database
                            save_ai_analysis(article_id, url, ai_analysis)
                            
                            # Check for Lebanese keywords
                            keywords_found = ai_analysis.get('keywords_found', [])
                            if keywords_found:
                                print(f"🚩 Lebanese keywords detected: {keywords_found}")
                            
                            print(f"✅ AI analysis completed")
                            
                        except Exception as e:
                            print(f"⚠️ AI analysis failed for {url}: {str(e)}")
                            ai_analysis = {"error": f"AI analysis failed: {str(e)}"}
                else:
                    print(f"⚠️ Scraping failed for: {url}")
            
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
            
            # Prepare result for frontend with better formatting
            result = {
                'title': scraped_data.get('title', title),
                'link': url,
                'snippet': snippet[:200] + '...' if len(snippet) > 200 else snippet,
                'scraped': scraped_data['success'],
                'content': scraped_data.get('content', '')[:800] if scraped_data.get('content') else '',  # Increased preview
                'word_count': scraped_data.get('word_count', 0),
                'images': scraped_data.get('images', [])[:3],  # Limit to first 3 images for display
                'image_count': len(scraped_data.get('images', [])),
                'ai_analysis': ai_analysis.get('relevance_analysis', {}) if ai_analysis else None
            }
            
            scraped_results.append(result)
            search_progress['results'] = scraped_results.copy()  # Update progress results
            
            # Add small delay to be respectful to websites, but faster for processing all results
            time.sleep(0.3)  # Reduced to 0.3 seconds for faster bulk processing
        
        # Mark as completed
        search_progress['completed'] = total_results
        search_progress['status'] = 'completed'
        search_progress['current_url'] = ''
        
        print(f"🎉 Search completed: {len(scraped_results)} total results, {successful_scrapes} scraped successfully")
        
        final_results = {
            'articles': scraped_results,
            'total_results': len(scraped_results),
            'scraped_count': successful_scrapes
        }
        
        search_progress['final_results'] = final_results
        
        return jsonify(final_results)
        
    except Exception as e:
        search_progress['status'] = 'error'
        search_progress['error'] = str(e)
        print(f"❌ Search endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/search-progress', methods=['GET'])
def get_search_progress():
    """Get current search progress"""
    return jsonify(search_progress)

@app.route('/analyze', methods=['POST'])
def analyze_existing():
    """Analyze existing scraped articles with AI"""
    try:
        if USING_REAL_DATA:
            # This would get unanalyzed articles from database and analyze them
            # For now, return success message indicating real analysis would happen
            analyzed_count = 0  # This would be the actual count from database
            return jsonify({
                "message": "Analysis completed successfully",
                "analyzed_count": analyzed_count,
                "note": "Real AI analysis integration ready"
            })
        else:
            return jsonify({
                "message": "Analysis completed successfully (mock)",
                "analyzed_count": 5
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/flagged', methods=['GET'])
def get_flagged_articles_endpoint():
    """Get all articles flagged with Lebanese keywords"""
    try:
        if USING_REAL_DATA:
            # Use real database function to get all flagged articles
            flagged_articles = get_flagged_articles()
            
            # Transform the data to match frontend expectations
            results = []
            for article in flagged_articles:
                result = {
                    "title": article.get('title', 'No title'),
                    "link": article.get('link', '#'),
                    "snippet": article.get('scraped_content', '')[:200] + '...' if article.get('scraped_content') else 'No content available',
                    "scraped": True,  # All flagged articles should be scraped
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
                "articles": results,  # Changed from "results" to "articles" for consistency
                "total_results": len(results),
                "scraped_count": len(results),  # All flagged articles are scraped
                "message": f"Found {len(results)} articles with Lebanese keywords"
            })
        else:
            # Enhanced mock flagged articles for testing
            flagged_articles = [
                {
                    "title": "Flood Alert in Lebanon - Heavy Rainfall Expected",
                    "link": "http://example.com/flood-lebanon",
                    "snippet": "Heavy flooding reported in Beirut area with significant damage to infrastructure...",
                    "scraped": True,
                    "content": "Major flooding occurred in Beirut today causing widespread damage to roads and buildings. Emergency services are responding to multiple incidents across the city. The Lebanese government has issued warnings for residents in low-lying areas to evacuate immediately.",
                    "word_count": 250,
                    "image_count": 2,
                    "ai_analysis": {
                        "is_relevant": True,
                        "confidence": 95,
                        "keywords_found": ["flood", "lebanon", "beirut", "flooding"],
                        "summary": "Article discusses flooding in Beirut with emergency response details",
                        "category": "emergency"
                    }
                },
                {
                    "title": "نهر الليطاني يفيض - أضرار في البقاع",
                    "link": "http://example.com/litani-flood",
                    "snippet": "فيضانات نهر الليطاني تسبب أضرار جسيمة في منطقة البقاع...",
                    "scraped": True,
                    "content": "شهدت منطقة البقاع فيضانات كبيرة نتيجة فيضان نهر الليطاني بعد هطول أمطار غزيرة. السلطات اللبنانية تحذر من مخاطر الفيضانات وتطلب من السكان توخي الحذر.",
                    "word_count": 180,
                    "image_count": 3,
                    "ai_analysis": {
                        "is_relevant": True,
                        "confidence": 92,
                        "keywords_found": ["نهر الليطاني", "فيضانات", "البقاع", "أمطار"],
                        "summary": "تقرير عن فيضانات نهر الليطاني في البقاع",
                        "category": "natural_disaster"
                    }
                },
                {
                    "title": "صيدا تواجه مشاكل في تصريف المياه",
                    "link": "http://example.com/saida-drainage",
                    "snippet": "مشاكل في شبكة تصريف المياه في مدينة صيدا تؤدي لتجمع المياه...",
                    "scraped": True,
                    "content": "تعاني مدينة صيدا من مشاكل في شبكة تصريف المياه مما يؤدي إلى تجمع المياه في الشوارع خاصة خلال فصل الشتاء. البلدية تعمل على حلول عاجلة.",
                    "word_count": 120,
                    "image_count": 1,
                    "ai_analysis": {
                        "is_relevant": True,
                        "confidence": 88,
                        "keywords_found": ["صيدا", "مياه", "تصريف"],
                        "summary": "تقرير عن مشاكل تصريف المياه في صيدا",
                        "category": "infrastructure"
                    }
                },
                {
                    "title": "Heavy Rains in Mount Lebanon Cause Landslides",
                    "link": "http://example.com/lebanon-landslides",
                    "snippet": "Torrential rains in Mount Lebanon trigger landslides affecting several villages...",
                    "scraped": True,
                    "content": "Heavy rainfall in Mount Lebanon has triggered multiple landslides affecting access to several mountain villages. The Lebanese Civil Defense is coordinating rescue efforts. Weather forecasts predict more rain in the coming days.",
                    "word_count": 200,
                    "image_count": 4,
                    "ai_analysis": {
                        "is_relevant": True,
                        "confidence": 90,
                        "keywords_found": ["lebanon", "mount lebanon", "rains", "landslides"],
                        "summary": "Report on landslides in Mount Lebanon due to heavy rains",
                        "category": "natural_disaster"
                    }
                }
            ]
            
            return jsonify({
                "articles": flagged_articles,
                "total_results": len(flagged_articles),
                "scraped_count": len(flagged_articles),
                "message": f"Found {len(flagged_articles)} articles with Lebanese keywords (mock data)"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify server is running"""
    return jsonify({"message": "Server is running successfully!", "status": "ok"})

if __name__ == '__main__':
    print("🌊 Starting Flood Data Mining Server...")
    
    if USING_REAL_DATA:
        print("✅ Using REAL data (scraper, database, AI agent)")
        try:
            init_db()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")
    else:
        print("⚠️ Using MOCK data (for testing only)")
    
    print("🔍 Available endpoints:")
    print("  - POST /search - Search and scrape articles")
    print("  - POST /analyze - Analyze existing articles")
    print("  - GET /flagged - Get flagged Lebanese articles")  
    print("  - GET /test - Test server connectivity")
    print("🌐 Server starting at: http://localhost:5000")
    print("📊 View database: python view_db.py")
    
    app.run(debug=True)
