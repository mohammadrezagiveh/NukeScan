import json
import os
from google.cloud import translate_v2 as translate

# Set Google Cloud Credentials (Modify the path to your service account JSON)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/mohammadrezagiveh/Downloads/elite-conquest-413518-a5f253d67208.json"

# Initialize the Google Cloud translation client
client = translate.Client()

# File paths
input_json_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/scraped_data.json"
output_json_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/translated_data.json"

# Function to translate Persian text to English
def translate_text(text, target_lang="en"):
    if not text.strip():  # Skip empty text
        return text
    result = client.translate(text, target_language=target_lang)
    return result.get("translatedText", text)  # Return original text if translation fails

# Function to translate content fields in the JSON data
def translate_content(data):
    translated_data = []
    
    for item in data:
        translated_item = item.copy()

        # Translate Title
        if 'title' in item:
            translated_item['title'] = translate_text(item['title'])

        # Translate Authors (List)
        if 'authors' in item:
            translated_item['authors'] = [translate_text(author) for author in item['authors']]

        # Translate Affiliations (List)
        if 'affiliations' in item:
            translated_item['affiliations'] = [translate_text(affiliation) for affiliation in item['affiliations']]

        # Translate Abstract
        if 'abstract' in item:
            translated_item['abstract'] = translate_text(item['abstract'])

        translated_data.append(translated_item)

    return translated_data

# Read the scraped data from the JSON file
with open(input_json_path, mode='r', encoding='utf-8-sig') as infile:
    scraped_data = json.load(infile)

# Translate the content
translated_data = translate_content(scraped_data)

# Save the translated data to a new JSON file
with open(output_json_path, mode='w', encoding='utf-8-sig') as jsonfile:
    json.dump(translated_data, jsonfile, ensure_ascii=False, indent=4)

print(f"✅ Translation completed. Data saved to {output_json_path}")