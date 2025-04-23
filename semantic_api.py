import requests

# Example DOI (you can replace with any)
doi = "10.1080/00295639.2021.1989932"

# Semantic Scholar API URL
url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"

# Fields to request
params = {
    "fields": "title,abstract,authors"
}

# Send request
response = requests.get(url, params=params)

# Parse response
if response.status_code == 200:
    data = response.json()
    print("Title:", data.get("title", "N/A"))
    print("Abstract:", data.get("abstract", "N/A"))
    print("Authors:", ", ".join(author["name"] for author in data.get("authors", [])))
else:
    print("Error:", response.status_code)