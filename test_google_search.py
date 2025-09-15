import os
from backend.src.google_search import google_search

def main():
    query = "tamnin flood"
    results = google_search(query)
    for i, item in enumerate(results, 1):
        print(f"{i}. {item.get('title')} - {item.get('link')}")

if __name__ == "__main__":
    main()
