import os
import csv
from bs4 import BeautifulSoup
import requests
from googletrans import Translator
import google.generativeai as genai
import time
import asyncio  # Import asyncio for asynchronous functions

# 1. FILE PATHS
# Specify the input and output CSV file paths
input_csv_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/urls.csv"
output_csv_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/scraped_data.csv"

# 2. INITIALIZATIONS
# Set the environment variable for Google Generative AI
os.environ["GENAI_API_KEY"] = "AIzaSyAGIwk0u3_KuBxdP_g77lfuYV4-uDd-YHE"  # Replace with your actual API key

# Configure the Google Generative AI API using the environment variable
genai.configure(api_key=os.environ["GENAI_API_KEY"])

# Initialize the Google Translator API
translator = Translator()

# 3. FUNCTION: PROCESS AFFILIATIONS USING AI
def process_affiliations(affiliations):
    """
    Function to process and translate affiliations using Google Generative AI.
    """
    translated_affiliations = []
    model = genai.GenerativeModel('gemini-1.5-flash')  # Initialize the AI model

    for affiliation_text in affiliations:
        # Create a prompt for the AI model to translate and extract entity names
        prompt = (
            f"'{affiliation_text}' is a sentence in Persian or English, describing the affiliation of an author with a real university or research institute in Iran with some extra information like the city where the organization is located or the department, section, or branch in which the author has been working at. Please give me the name of the university or research organization in English. Please consider:1- IMPORTANT: In your response, do not write anything other than the English spelling of the name of the university or research institute. No city, country, department, or breach.2- Use these outputs as examples: 'Amirkabir University of Technology', 'Nuclear Science and Technology Research Institute', 'University of Tehran', 'University of Damghan', 'Arak University', 'University of Isfahan', 'Bu-Ali Sina University', 'Payame Noor University', 'Imam Hossein University', 'Noshirvani University of Technology', 'University of Guilan'"
        )

        try:
            # Generate the response using the AI model
            response = model.generate_content(prompt)
            translated_text = response.candidates[0].content.parts[0].text.strip()  # Extract the translated text
            translated_affiliations.append(translated_text)
            time.sleep(3)  # Introduce a time delay to avoid hitting API limits

        except Exception as error:
            print(f"Error processing affiliation '{affiliation_text}': {error}")
            translated_affiliations.append("Error")  # Record "Error" if the translation fails

    return "/".join(translated_affiliations)

def process_name(authors):
    """
    Function to process names using Google Generative AI.
    """
    processesed_names = []
    model = genai.GenerativeModel('gemini-1.5-flash')  # Initialize the AI model

    for author in authors:
        # Create a prompt for the AI model to translate and extract entity names
        prompt = (
            f"'{author}' is a Persian name of a person in Iran. Based on what is available in open-source, what is the most commonly used variation of this name, spelled in English. It is important that you comply with a rule and are consistent in the way you spell a name because there are multiple ways that one Persian name can be spelled in English. Please also consider the following:1- IMPORTANT: In your response, do not write anything other than the English spelling of the name.2- In case there is a first name that is made out of combining two different names (that is common for Iranian names) spell the name as a single name without spacing. Example: محمد رضا --> Mohammadreza 3- Apply the same rule 2 to the last names.3- If the input name is in English return it without a change 4- Leave one space between the First name and the Last name"
        )

        try:
            # Generate the response using the AI model
            response = model.generate_content(prompt)
            processesed_text = response.candidates[0].content.parts[0].text.strip()  # Extract the translated text
            processesed_names.append(processesed_text)
            time.sleep(3)  # Introduce a time delay to avoid hitting API limits

        except Exception as error:
            print(f"Error processing affiliation '{author}': {error}")
            processesed_names.append("Error")  # Record "Error" if the translation fails

    return "/".join(processesed_names)

# 4. FUNCTION: SCRAPE DATA FROM A SINGLE URL
async def scrape_url(url):  # Make this function asynchronous
    """
    Function to scrape data from a given URL on Civilica.com.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Check if the title is in English or Persian
    title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2 ltr")
    if title_element:  # Case 1: Title is in English
        title = title_element.text.strip()

        # Extract authors and affiliations
        authors = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]
        affiliations = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        authors_combined = process_name(authors)
        processed_affiliations = process_affiliations(affiliations)

        # Extract journal name and publication year
        journal_name = soup.find('span', class_='font-bold').find_next('a').get_text(strip=True).split("،")[0]
        year_persian = int(soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2").text.strip().split(":")[1].strip())
        year_english = year_persian + 621  # Convert Persian year to English year

        # Extract the abstract
        abstract = soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify ltr").text.strip()

        # Return the scraped data
        return [title, "N/A", authors_combined, "N/A", processed_affiliations, year_english, journal_name, abstract, "N/A"]

    else:  # Case 2: Title is in Persian
        title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2")
        title_persian = title_element.text.strip()

        # Extract authors and affiliations
        authors_persian = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]
        affiliations_persian = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        processed_authors = process_name(authors_persian)
        processed_affiliations = process_affiliations(affiliations_persian)

        # Extract journal name and publication year
        journal_name = soup.find('span', class_='font-bold').find_next('a').get_text(strip=True).split("،")[0]
        year_persian = int(soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2").text.strip().split(":")[1].strip())
        year_english = year_persian + 621  # Convert Persian year to English year

        # Extract the abstract and translate
        abstract_persian = soup.find('div', class_="prose max-w-none my-6 text-color-black text-justify").text.strip()
        title_translation = translator.translate(title_persian, src='fa', dest='en').text.strip()  # Remove await
        authors_persian = [author.strip() for author in authors_persian]
        abstract_translation = translator.translate(abstract_persian, src='fa', dest='en').text.strip()  # Remove await

        # Return the scraped and translated data
        return [title_translation, title_persian, processed_authors, ",".join(authors_persian), processed_affiliations, year_english, journal_name, abstract_translation, abstract_persian]

# 5. MAIN SCRIPT

async def main():  # Make the main function asynchronous
    # Read the list of URLs from the input CSV file
    with open(input_csv_path, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        urls = [row[0] for row in reader if row]  # Extract URLs from the CSV file

    # Open the output CSV file for writing the scraped data
    with open(output_csv_path, mode='w', newline='', encoding='UTF-8') as outfile:
        writer = csv.writer(outfile)

        # Write the CSV header
        writer.writerow(["English Title", "Persian Title", "English Author", "Persian Author", "Affiliation", "Year", "Publication Place", "English Abstract", "Persian Abstract"])

        # Process each URL and write the scraped data to the output CSV file
        for url in urls:
            try:
                scraped_data = await scrape_url(url)  # Use await
                if scraped_data:
                    writer.writerow(scraped_data)
            except Exception as error:
                print(f"Error processing URL {url}: {error}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())  # Use asyncio.run to run the main function

# 6. COMPLETION MESSAGE
print(f"Scraping completed. Data saved to {output_csv_path}")