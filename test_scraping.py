import requests

# Test scraping endpoint
try:
    response = requests.post('http://localhost:5000/scrape')
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")