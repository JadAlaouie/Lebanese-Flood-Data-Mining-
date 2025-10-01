"""Search functionality for flood data mining (Google + DuckDuckGo fallback)"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote
import time
import re

def google_search(query, num=10, lang='en'):
    """
    Perform a web search and return results (tries Google, then DuckDuckGo)
    
    Args:
        query: Search query string
        num: Number of results to return (default 10)
        lang: Language for results (default 'en')
    
    Returns:
        List of dictionaries with 'title', 'link', and 'snippet' keys
    """
    
    # Try Google first
    results = _google_search(query, num, lang)
    
    # If Google fails or returns no results, try DuckDuckGo
    if not results:
        print(f"→ Google blocked or no results, trying DuckDuckGo...")
        results = _duckduckgo_search(query, num)
    
    return results

def _google_search(query, num=10, lang='en'):
    """Try to get results from Google"""
    results = []
    
    # Encode the query for URL
    encoded_query = quote_plus(query)
    
    # Google search URL
    url = f"https://www.google.com/search?q={encoded_query}&num={num * 2}&hl={lang}"
    
    # Headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple selectors for search results
        search_results = soup.find_all('div', class_='g') or \
                        soup.find_all('div', {'data-sokoban-container': True}) or \
                        soup.select('div[data-hveid]')
        
        for result in search_results:
            if len(results) >= num:
                break
                
            # Extract title
            title_elem = result.find('h3')
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            
            # Extract link
            link_elem = result.find('a', href=True)
            if not link_elem:
                continue
            
            link = link_elem.get('href', '')
            
            # Clean up the link
            if link.startswith('/url?q='):
                link = link.split('/url?q=')[1].split('&')[0]
            elif link.startswith('/url?'):
                match = re.search(r'[?&]q=([^&]+)', link)
                if match:
                    link = unquote(match.group(1))
            
            # Skip non-http links
            if not link.startswith('http'):
                continue
            
            # Extract snippet
            snippet = ''
            snippet_elem = result.find('div', class_='VwiC3b') or \
                          result.find('span', class_='aCOpRe') or \
                          result.find('div', {'data-sncf': '1'}) or \
                          result.find('div', {'style': lambda x: x and 'line-height' in x})
            
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
            
            results.append({
                'title': title,
                'link': link,
                'snippet': snippet
            })
        
        if results:
            print(f"✓ Google search returned {len(results)} results for: {query}")
        else:
            print(f"⚠ Google returned 0 results for: {query}")
        
    except Exception as e:
        print(f"✗ Google search failed for query '{query}': {str(e)}")
    
    return results

def _duckduckgo_search(query, num=10):
    """Fallback: Search using DuckDuckGo HTML"""
    results = []
    
    # Encode the query
    encoded_query = quote_plus(query)
    
    # DuckDuckGo HTML search URL
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all result divs
        search_results = soup.find_all('div', class_='result')
        
        for result in search_results[:num]:
            # Extract title and link
            title_elem = result.find('a', class_='result__a')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            link = title_elem.get('href', '')
            
            # DuckDuckGo uses redirects, extract actual URL
            if link.startswith('//duckduckgo.com/l/?'):
                match = re.search(r'uddg=([^&]+)', link)
                if match:
                    link = unquote(match.group(1))
            
            # Extract snippet
            snippet_elem = result.find('a', class_='result__snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
            
            if link and link.startswith('http'):
                results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet
                })
        
        print(f"✓ DuckDuckGo returned {len(results)} results for: {query}")
        
    except Exception as e:
        print(f"✗ DuckDuckGo search failed for query '{query}': {str(e)}")
    
    # Add a small delay to be polite
    time.sleep(1)
    
    return results
