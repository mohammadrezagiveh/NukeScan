import json
import requests
from bs4 import BeautifulSoup

# File paths
input_csv_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/urls.csv"
output_json_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/scraped_data.json"

# Function to scrape data from a single Civilica URL
def scrape_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title (Persian or English)
        title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2") or \
                        soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2 ltr")
        title = title_element.text.strip() if title_element else "Title Not Found"

        # Extract authors
        authors = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]

        # Extract affiliations
        affiliations = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        # Extract journal name
        journal_element = soup.find('span', class_='font-bold')
        journal_name = journal_element.find_next('a').text.strip() if journal_element else "Unknown"

        # Extract publication year
        year_element = soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2")
        year = int(year_element.text.strip().split(":")[1].strip()) + 621 if year_element else "Unknown"

        # Extract abstract
        abstract_element = soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify") or \
                           soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify ltr")
        abstract = abstract_element.text.strip() if abstract_element else "No Abstract Available"

        return {
            "title": title,
            "authors": authors,
            "affiliations": affiliations,
            "year": year,
            "journal": journal_name,
            "abstract": abstract,
            "url": url
        }

    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        return None

# Read URLs from the CSV file
with open(input_csv_path, mode='r', newline='', encoding='utf-8-sig') as infile:
    urls = [line.strip() for line in infile.readlines() if line.strip().startswith("http")]

# Scrape each URL and store the results
scraped_data = []
for url in urls:
    data = scrape_url(url)
    if data:
        scraped_data.append(data)

# Save the scraped data to a JSON file
with open(output_json_path, mode='w', encoding='utf-8-sig') as jsonfile:
    json.dump(scraped_data, jsonfile, ensure_ascii=False, indent=4)

print(f"Scraping completed. Data saved to {output_json_path}")