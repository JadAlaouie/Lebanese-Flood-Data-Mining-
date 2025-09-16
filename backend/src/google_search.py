import os
import requests
from dotenv import load_dotenv
import json
from .database import save_search_result

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def google_search(query, api_key=None, cx=None, num=10):
    """
    Search Google and return results. 
    Maximum num=10 per API call due to Google's limits.
    For more results, multiple API calls would be needed.
    """
    print(f"google_search called with query: {query}")
    api_key = api_key or GOOGLE_API_KEY
    cx = cx or GOOGLE_CSE_ID
    url = "https://www.googleapis.com/customsearch/v1"
    
    # Set to maximum allowed by Google API
    num = min(num, 10)  # Google Custom Search API max is 10 per request
    
    params = {
        'q': query,
        'key': api_key,
        'cx': cx,
        'num': num
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    items = response.json().get('items', [])
    print(f"Raw API results: {len(items)} items")
    for item in items:
        print(f"Saving to DB: {item.get('title')} | {item.get('link')}")
        save_search_result(item.get('title'), item.get('link'), item.get('snippet'))
    return items

def google_search_mock(query):
    print(f"google_search called with query: {query}")
    
    results = [
        {
            'title': 'FEMA Flood Maps',
            'link': 'https://www.fema.gov/flood-maps',
            'snippet': 'Official FEMA flood mapping information and resources.'
        },
        {
            'title': 'Floods | Ready.gov',
            'link': 'https://www.ready.gov/floods',
            'snippet': 'Learn how to prepare for floods and what to do during and after a flood.'
        },
    ]
    
    print(f"Raw API results: {len(results)} items")
    
    for item in results:
        save_search_result(item.get('title'), item.get('link'), item.get('snippet'))
    
    return results
