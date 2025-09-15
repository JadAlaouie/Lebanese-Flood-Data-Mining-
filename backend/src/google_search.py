import os
import requests
from dotenv import load_dotenv

 # from backend.src.filter import filter_results_by_year
from backend.src.database import save_search_result

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def google_search(query, api_key=None, cx=None, num=10):
    print(f"google_search called with query: {query}")
    api_key = api_key or GOOGLE_API_KEY
    cx = cx or GOOGLE_CSE_ID
    url = "https://www.googleapis.com/customsearch/v1"
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
