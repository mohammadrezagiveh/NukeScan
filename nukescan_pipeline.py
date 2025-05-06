import json
import os
import re
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import openai
from sentence_transformers import SentenceTransformer, util
import torch
import uuid

_prompt_handler = None

def set_prompt_handler(handler):
    global _prompt_handler
    _prompt_handler = handler

# === Setup ===
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/mohammadrezagiveh/Downloads/elite-conquest-413518-a5f253d67208.json"
translator = translate.Client()
gpt_client = openai.OpenAI()
model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

# === Utilities ===
def translate_text(text):
    if not text.strip(): return text
    try:
        result = translator.translate(text, target_language="en")
        return result.get("translatedText", text)
    except Exception as e:
        print(f"[Translation Error] {e}")
        return text

def clean_text(text):
    text = text.lower()
    return re.sub(r"[^\w\s]", "", text).strip()

def extract_core_name(text):
    if not text: return text
    prompt = f"""Extract the core name of research organizations and journals/conferences from the following text.

Rules:
• For research organizations: Keep only the university, institute, or main organization name. Remove departments, labs, addresses, and personal titles.
• For journals/conferences: Keep only the journal or conference name. Remove volume, issue numbers, and extra formatting.

Only return the cleaned-up name without any explanations. If you can't extract a core name, do not modify the input.

Text: "{text}"
Core Name:"""
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        return text

def load_standard_list(file_path):
    """Load standard list from JSON file with rich structure"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error loading {file_path}, creating empty list")
    return []

def save_standard_list(file_path, data_list):
    """Save standard list to JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

def resolve_name(name, standard_list, category, url):
    """Resolve a name against a standard list with variants"""
    name_embedding = model.encode(name, convert_to_tensor=True)
    
    # Check all standard names and variants
    best_match = None
    best_score = 0
    best_entry = None
    
    for entry in standard_list:
        # Check the standard name
        standard_embedding = model.encode(entry["standard_name"], convert_to_tensor=True)
        score = util.cos_sim(name_embedding, standard_embedding)[0][0].item()
        
        if score > best_score:
            best_score = score
            best_match = entry["standard_name"]
            best_entry = entry
        
        # Check all variants
        for variant in entry["variants"]:
            variant_embedding = model.encode(variant, convert_to_tensor=True)
            score = util.cos_sim(name_embedding, variant_embedding)[0][0].item()
            
            if score > best_score:
                best_score = score
                best_match = entry["standard_name"]
                best_entry = entry

    # If we found a good match, add this as a new variant if not already present
    if best_score > 0.85 and best_entry:
        if name not in best_entry["variants"]:
            best_entry["variants"].append(name)
        return best_match, standard_list
    
    # No good match found, prompt user
    return prompt_user(name, category, url, standard_list)

def prompt_user(name, category, url, standard_list):
    """Prompt user for a new standard name or to select an existing one"""
    if _prompt_handler:
        user_input, additional_info = _prompt_handler(category, name)
    else:
        print(f"\nUnrecognized {category} in {url}:\n{name}")
        user_input = input("Enter standardized version or press Enter to keep as-is: ").strip()
        additional_info = {}
        
        if user_input and category == "Affiliation":
            additional_info["city"] = input("Enter city (optional): ").strip()
            additional_info["province_state"] = input("Enter province/state (optional): ").strip()
        elif user_input and category == "Journal":
            additional_info["publisher"] = input("Enter publisher ID (optional): ").strip()

    if user_input:
        # Check if this standard name already exists
        existing_entry = next((entry for entry in standard_list if entry["standard_name"] == user_input), None)
        
        if existing_entry:
            # Add this name as a variant to the existing entry
            if name not in existing_entry["variants"]:
                existing_entry["variants"].append(name)
            return user_input, standard_list
        else:
            # Create a new entry
            new_entry = {
                "id": str(uuid.uuid4()),
                "standard_name": user_input,
                "variants": [name] if name != user_input else []
            }
            
            # Add category-specific fields
            if category == "Affiliation":
                new_entry["city"] = additional_info.get("city", "")
                new_entry["province_state"] = additional_info.get("province_state", "")
            elif category == "Journal":
                new_entry["publisher"] = additional_info.get("publisher", "")
                
            standard_list.append(new_entry)
            return user_input, standard_list
    
    # User wants to keep the original name
    new_entry = {
        "id": str(uuid.uuid4()),
        "standard_name": name,
        "variants": []
    }
    
    # Add category-specific fields
    if category == "Affiliation":
        new_entry["city"] = ""
        new_entry["province_state"] = ""
    elif category == "Journal":
        new_entry["publisher"] = ""
        
    standard_list.append(new_entry)
    return name, standard_list

def scrape_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2") or \
                        soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2 ltr")
        title = title_element.text.strip() if title_element else "Title Not Found"

        authors = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]
        affiliations = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        journal_element = soup.find('span', class_='font-bold')
        journal_name = journal_element.find_next('a').text.strip() if journal_element else "Unknown"

        year_element = soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2")
        year = int(year_element.text.strip().split(":")[1].strip()) + 621 if year_element else "Unknown"

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
        print(f"[Scrape Error] {url} - {e}")
        return None

# === Main Pipeline ===
def run_pipeline(input_csv, output_json):
    with open(input_csv, mode='r', encoding='utf-8-sig') as infile:
        urls = [line.strip() for line in infile if line.strip().startswith("http")]

    # Use JSON files instead of CSV for richer data structure
    authors_json = "standard_authors.json"
    affiliations_json = "standard_affiliations.json"
    journals_json = "standard_journals.json"

    standard_authors = load_standard_list(authors_json)
    standard_affiliations = load_standard_list(affiliations_json)
    standard_journals = load_standard_list(journals_json)

    processed_data = []
    for url in urls:
        print(f"🔍 Processing {url}")
        raw = scrape_url(url)
        if not raw: continue

        entry = {}
        entry["url"] = url
        entry["year"] = raw.get("year", "")

        entry["title"] = clean_text(translate_text(raw.get("title", "")))
        entry["abstract"] = clean_text(translate_text(raw.get("abstract", "")))

        entry["authors"] = []
        for a in raw.get("authors", []):
            trans = clean_text(translate_text(a))
            resolved, standard_authors = resolve_name(trans, standard_authors, "Author", url)
            entry["authors"].append(resolved)

        entry["affiliations"] = []
        for a in raw.get("affiliations", []):
            trans = clean_text(extract_core_name(translate_text(a)))
            resolved, standard_affiliations = resolve_name(trans, standard_affiliations, "Affiliation", url)
            entry["affiliations"].append(resolved)

        journal = raw.get("journal", "")
        journal_clean = clean_text(extract_core_name(translate_text(journal)))
        resolved, standard_journals = resolve_name(journal_clean, standard_journals, "Journal", url)
        entry["journal"] = resolved

        processed_data.append(entry)

    with open(output_json, mode='w', encoding='utf-8-sig') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)

    save_standard_list(authors_json, standard_authors)
    save_standard_list(affiliations_json, standard_affiliations)
    save_standard_list(journals_json, standard_journals)

    print(f"\n✅ All done! Output saved to {output_json}")

# === CLI Interface ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NukeScan Academic Preprocessing Pipeline")
    parser.add_argument("--input", type=str, required=True, help="Path to URL CSV file")
    parser.add_argument("--output", type=str, required=True, help="Path to save final processed JSON")
    args = parser.parse_args()

    run_pipeline(args.input, args.output)