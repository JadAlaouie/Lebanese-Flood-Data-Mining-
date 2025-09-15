# import re

# def filter_results_by_year(results, min_year=2024):
#     """
#     Filters a list of search result dicts, keeping only those mentioning min_year or later in title or snippet.
#     """
#     filtered = []
#     for item in results:
#         text = (item.get('title', '') + ' ' + item.get('snippet', '')).lower()
#         years = re.findall(r'\b(20[2-9][0-9])\b', text)
#         if any(int(year) >= min_year for year in years):
#             filtered.append(item)
#     return filtered

