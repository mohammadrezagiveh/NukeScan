import csv
import requests
from bs4 import BeautifulSoup

# File paths
input_csv_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/urls.csv"
output_csv_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/scraped_data.csv"

# Function to scrape data from a single Civilica URL
def scrape_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title (Persian or English)
        if soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2"):
            title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2")
        else:
            title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2 ltr")
        title = title_element.text.strip() if title_element else "Title Not Found"

        # Extract authors
        authors = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]

        # Extract affiliations
        affiliations = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        # Extract journal name and publication year
        journal_element = soup.find('span', class_='font-bold')
        journal_name = journal_element.find_next('a').text.strip() if journal_element else "Unknown"

        # Extract publication year (if available)
        year_element = soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2")
        year = int(year_element.text.strip().split(":")[1].strip()) + 621 if year_element else "Unknown"

        # Extract abstract
        if soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify"):
            abstract_element = soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify")
        else:
            abstract_element = soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify ltr")
        abstract = abstract_element.text.strip() if abstract_element else "No Abstract Available"

        return [title, "/".join(authors), "/".join(affiliations), year, journal_name, abstract, url]

    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        return None

# Read URLs from the CSV file
with open(input_csv_path, mode='r', newline='', encoding='utf-8-sig') as infile:
    reader = csv.reader(infile)
    urls = [row[0].strip() for row in reader if row and row[0].startswith("http")]

# Open CSV file to save results
with open(output_csv_path, mode='w', newline='', encoding='utf-8-sig', errors="replace") as outfile:
    writer = csv.writer(outfile)
    writer.writerow(["Title", "Authors", "Affiliations", "Year", "Publication", "Abstract", "URL"])  # CSV header

    # Scrape each URL and save the data
    for url in urls:
        scraped_data = scrape_url(url)
        if scraped_data:
            writer.writerow(scraped_data)

print(f"Scraping completed. Data saved to {output_csv_path}")