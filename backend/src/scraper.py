# Web scraping utilities
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

def scrape_article(url, timeout=15):
    """
    Scrape the full article content from a URL
    Returns dict with title, content, and metadata
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try with a session for better connection handling
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement']):
            element.decompose()
        
        # Try to find the main content
        title = extract_title(soup)
        content = extract_content(soup)
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'word_count': len(content.split()) if content else 0,
            'success': True
        }
        
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'title': None,
            'content': None,
            'error': 'Request timed out',
            'success': False
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'title': None,
            'content': None,
            'error': f'Request failed: {str(e)}',
            'success': False
        }
    except Exception as e:
        return {
            'url': url,
            'title': None,
            'content': None,
            'error': str(e),
            'success': False
        }

def extract_title(soup):
    """Extract article title"""
    # Try different title selectors
    title_selectors = [
        'h1',
        'title',
        '.article-title',
        '.entry-title',
        '[property="og:title"]'
    ]
    
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            if element.name == 'title':
                return element.get_text().strip()
            elif element.get('content'):
                return element.get('content').strip()
            else:
                return element.get_text().strip()
    
    return "No title found"

def extract_content(soup):
    """Extract main article content"""
    # Try different content selectors
    content_selectors = [
        'article',
        '.article-content',
        '.entry-content',
        '.post-content',
        '.content',
        'main',
        '.main-content'
    ]
    
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            # Clean up the text
            text = element.get_text(separator=' ', strip=True)
            if len(text) > 100:  # Only return if substantial content
                return text
    
    # Fallback: get all paragraphs
    paragraphs = soup.find_all('p')
    content = ' '.join([p.get_text(strip=True) for p in paragraphs])
    
    return content if len(content) > 50 else "No content extracted"

def scrape_url(url):
    """Legacy function - kept for compatibility"""
    result = scrape_article(url)
    return result['content'] if result['success'] else None
