import sqlite3
import json

def print_table(table_name, db_path='flood_data.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get column names
    c.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in c.fetchall()]
    
    print(f"\nContents of table: {table_name}")
    print(f"Columns: {', '.join(columns)}")
    print("-" * 80)
    
    for row in c.execute(f'SELECT * FROM {table_name}'):
        for i, value in enumerate(row):
            # Pretty print JSON fields
            if columns[i] in ['keywords_found', 'key_facts', 'location'] and value:
                try:
                    value = json.loads(value)
                except:
                    pass
            print(f"{columns[i]}: {value}")
        print("-" * 40)
    conn.close()

def print_ai_summary(db_path='flood_data.db'):
    """Print summary of AI analysis results"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("\n" + "="*60)
    print("AI ANALYSIS SUMMARY")
    print("="*60)
    
    # Count total analyses
    c.execute("SELECT COUNT(*) FROM ai_analysis")
    total = c.fetchone()[0]
    print(f"Total articles analyzed: {total}")
    
    # Count relevant vs non-relevant
    c.execute("SELECT COUNT(*) FROM ai_analysis WHERE is_relevant = 1")
    relevant = c.fetchone()[0]
    print(f"Flood-relevant articles: {relevant}")
    print(f"Non-relevant articles: {total - relevant}")
    
    if total > 0:
        print(f"Relevance rate: {relevant/total*100:.1f}%")
    
    # Show categories
    c.execute("SELECT category, COUNT(*) FROM ai_analysis GROUP BY category")
    categories = c.fetchall()
    print(f"\nCategories found:")
    for cat, count in categories:
        print(f"  {cat}: {count}")
    
    # Show recent relevant articles
    print(f"\nRecent relevant articles:")
    c.execute("""
        SELECT sa.title, sa.url, aa.category, aa.confidence, aa.summary 
        FROM ai_analysis aa
        JOIN scraped_articles sa ON aa.article_id = sa.id
        WHERE aa.is_relevant = 1
        ORDER BY aa.analyzed_at DESC
        LIMIT 5
    """)
    
    for title, url, category, confidence, summary in c.fetchall():
        print(f"\n  Title: {title}")
        print(f"  URL: {url}")
        print(f"  Category: {category}")
        print(f"  Confidence: {confidence}%")
        print(f"  Summary: {summary[:200]}...")
    
    conn.close()

if __name__ == "__main__":
    print_table('search_results')
    print_table('queries')
    print_table('articles')
    print_table('scraped_articles')
    print_table('ai_analysis')
    print_ai_summary()
