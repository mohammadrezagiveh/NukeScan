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

# Global variable to store user preference for confirming matches
CONFIRM_MATCHES = False

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
- For research organizations: Keep only the university, institute, or main organization name. Remove departments, labs, addresses, and personal titles.
- For journals/conferences: Keep only the journal or conference name. Remove volume, issue numbers, and extra formatting.

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

def load_entities(file_path):
    """Load all entities from a single JSON file"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entities = json.load(f)
                if not isinstance(entities, list):
                    return []
                return entities
        except json.JSONDecodeError:
            print(f"Error loading {file_path}, creating empty list")
    return []  # start with an empty list if file doesn't exist or is invalid

def save_entities(file_path, entities):
    """Save all entities to a single JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=4)

def resolve_name(name, all_entities, entity_type, url):
    """Resolve a name against entities of a specific type with variants"""
    # Filter entities by type
    entity_list = [e for e in all_entities if e.get("type") == entity_type]
    
    name_embedding = model.encode(name, convert_to_tensor=True)
    
    # Check all standard names and variants
    best_match = None
    best_score = 0
    best_entry = None
    best_match_source = None  # Track if match came from standard name or variant
    
    for entry in entity_list:
        # Check the standard name
        standard_embedding = model.encode(entry["standard_name"], convert_to_tensor=True)
        score = util.cos_sim(name_embedding, standard_embedding)[0][0].item()
        
        if score > best_score:
            best_score = score
            best_match = entry["standard_name"]
            best_entry = entry
            best_match_source = "standard"
        
        # Check all variants
        for variant in entry["variants"]:
            variant_embedding = model.encode(variant, convert_to_tensor=True)
            score = util.cos_sim(name_embedding, variant_embedding)[0][0].item()
            
            if score > best_score:
                best_score = score
                best_match = entry["standard_name"]
                best_entry = entry
                best_match_source = "variant"

    # If we found a good match
    if best_score > 0.85 and best_entry:
        # If user wants to confirm matches, ask for confirmation
        if CONFIRM_MATCHES:
            match_info = f"variant '{variant}'" if best_match_source == "variant" else f"standard name '{best_match}'"
            print(f"\nFound potential match for '{name}':")
            print(f"Match: {best_match} (similarity: {best_score:.2f})")
            print(f"Matched with {match_info}")
            confirm = input("Accept this match? (y/n): ").strip().lower()
            
            if confirm in ['y', 'yes']:
                if name not in best_entry["variants"]:
                    best_entry["variants"].append(name)
                return best_match, all_entities
            else:
                # User rejected the match, prompt for manual input
                return prompt_user(name, entity_type, url, all_entities)
        else:
            # Auto-accept the match without confirmation
            if name not in best_entry["variants"]:
                best_entry["variants"].append(name)
            return best_match, all_entities
    
    # No good match found, prompt user
    return prompt_user(name, entity_type, url, all_entities)

def prompt_user(name, entity_type, url, all_entities):
    """Prompt user for a new standard name or to select an existing one"""
    if _prompt_handler:
        user_input, additional_info = _prompt_handler(entity_type, name)
    else:
        print(f"\nUnrecognized {entity_type} in {url}:\n{name}")
        print("Options: Enter standardized version, type 'empty' for no value, or press Enter to keep as-is")
        raw_input = input(f"Your choice: ").strip()
        
        # Handle empty values without cleaning
        if raw_input.lower() in ["empty", "none"]:
            return "", all_entities
            
        # Clean the input for all other cases
        user_input = clean_text(raw_input) if raw_input else ""
        additional_info = {}
        
        # Collect additional fields based on entity type
        if user_input:
            if entity_type == "affiliation":
                additional_info["city"] = clean_text(input("Enter city (optional): ").strip())
                additional_info["province_state"] = clean_text(input("Enter province/state (optional): ").strip())
                additional_info["country"] = clean_text(input("Enter country (optional): ").strip())
            elif entity_type == "journal":
                additional_info["publisher"] = clean_text(input("Enter publisher ID (optional): ").strip())

    if user_input:
        # Check if this standard name already exists
        existing_entry = next((entry for entry in all_entities 
                              if entry.get("type") == entity_type and 
                              entry["standard_name"] == user_input), None)
        
        if existing_entry:
            # Add this name as a variant to the existing entry
            if name not in existing_entry["variants"]:
                existing_entry["variants"].append(name)
            return user_input, all_entities
        else:
            # Create a new entry with common fields
            new_entry = {
                "id": str(uuid.uuid4()),
                "type": entity_type,
                "standard_name": user_input,
                "variants": [name] if name != user_input else []
            }
            
            # Add entity-specific fields
            if entity_type == "affiliation":
                new_entry["city"] = additional_info.get("city", "")
                new_entry["province_state"] = additional_info.get("province_state", "")
                new_entry["country"] = additional_info.get("country", "")
            elif entity_type == "journal":
                new_entry["publisher"] = additional_info.get("publisher", "")
                
            all_entities.append(new_entry)
            return user_input, all_entities
    
    # User wants to keep the original name
    if not user_input:
        print(f"Keeping original name: {name}")
        user_input = name
        
        # Still ask for additional information
        if entity_type == "affiliation":
            print("Would you like to add location information?")
            additional_info["city"] = clean_text(input("Enter city (optional): ").strip())
            additional_info["province_state"] = clean_text(input("Enter province/state (optional): ").strip())
            additional_info["country"] = clean_text(input("Enter country (optional): ").strip())
        elif entity_type == "journal":
            additional_info["publisher"] = clean_text(input("Enter publisher ID (optional): ").strip())
    
        # Create a new entry with common fields
        new_entry = {
            "id": str(uuid.uuid4()),
            "type": entity_type,
            "standard_name": user_input,
            "variants": []
        }
        
        # Add entity-specific fields
        if entity_type == "affiliation":
            new_entry["city"] = additional_info.get("city", "")
            new_entry["province_state"] = additional_info.get("province_state", "")
            new_entry["country"] = additional_info.get("country", "")
        elif entity_type == "journal":
            new_entry["publisher"] = additional_info.get("publisher", "")
            
        all_entities.append(new_entry)
        return user_input, all_entities

def scrape_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title_element = soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2") or \
                        soup.find('h1', class_="font-bold h_title mb-2 border-b pb-2 ltr")
        title = title_element.text.strip() if title_element else "No Title Available"

        authors = [div.find('a', {"title": True}).text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('a', {"title": True})]
        affiliations = [div.find('p').text.strip() for div in soup.find_all('div', class_="flex flex-col") if div.find('p')]

        journal_element = soup.find('span', class_='font-bold')
        journal_name = journal_element.find_next('a').text.strip() if journal_element else "No Journal Available"

        year_element = soup.find('div', class_="text-color-base dark:text-color-base-dark flex py-2")
        year = int(year_element.text.strip().split(":")[1].strip()) + 621 if year_element else "No Year Available"

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

def manual_entry():
    """Allow user to manually enter paper details"""
    print("\n=== Manual Paper Entry ===")
    
    entry = {}
    entry["url"] = ""  # No URL for manual entries
    
    # Get title
    title = input("Enter paper title (or 'empty' to skip): ").strip()
    if title.lower() == "empty":
        entry["title"] = ""
    else:
        entry["title"] = clean_text(title)
    
    # Get year
    year = input("Enter publication year (or 'empty' to skip): ").strip()
    if year.lower() == "empty":
        entry["year"] = ""
    else:
        try:
            entry["year"] = int(year)
        except ValueError:
            print("Invalid year format. Setting to empty.")
            entry["year"] = ""
    
    # Get abstract
    abstract = input("Enter abstract (or 'empty' to skip): ").strip()
    if abstract.lower() == "empty":
        entry["abstract"] = ""
    else:
        entry["abstract"] = clean_text(abstract)
    
    # Get authors
    entry["authors"] = []
    while True:
        author = input("Enter author name (or 'done' when finished, 'empty' to skip): ").strip()
        if author.lower() == "done":
            break
        if author.lower() == "empty":
            continue
        entry["authors"].append(clean_text(author))
    
    # Get affiliations
    entry["affiliations"] = []
    while True:
        affiliation = input("Enter affiliation (or 'done' when finished, 'empty' to skip): ").strip()
        if affiliation.lower() == "done":
            break
        if affiliation.lower() == "empty":
            continue
        clean_affiliation = clean_text(extract_core_name(affiliation))
        entry["affiliations"].append(clean_affiliation)
    
    # Get journal
    journal = input("Enter journal/conference (or 'empty' to skip): ").strip()
    if journal.lower() == "empty":
        entry["journal"] = ""
    else:
        entry["journal"] = clean_text(extract_core_name(journal))
    
    return entry

def standardize_entry(entry, all_entities):
    """Standardize names in a manually entered or scraped entry"""
    # Temporary URL for display purposes in prompts
    url = entry.get("url", "manual entry")
    
    # For authors
    standardized_authors = []
    for author in entry.get("authors", []):
        if not author: continue
        resolved, all_entities = resolve_name(author, all_entities, "author", url)
        if resolved:  # Only add non-empty values
            standardized_authors.append(resolved)
    entry["authors"] = standardized_authors
    
    # For affiliations
    standardized_affiliations = []
    for affiliation in entry.get("affiliations", []):
        if not affiliation: continue
        resolved, all_entities = resolve_name(affiliation, all_entities, "affiliation", url)
        if resolved:  # Only add non-empty values
            standardized_affiliations.append(resolved)
    entry["affiliations"] = standardized_affiliations
    
    # For journal
    journal = entry.get("journal", "")
    if journal:
        resolved, all_entities = resolve_name(journal, all_entities, "journal", url)
        entry["journal"] = resolved
    
    return entry, all_entities

def run_pipeline(input_csv, output_json):
    # Load existing standardized entities
    entities_json = "standard_entities.json"
    all_entities = load_entities(entities_json)
    
    # Ask user if they want to confirm matches
    global CONFIRM_MATCHES
    confirm = input("Would you like to confirm all automatic matches? (y/n): ").strip().lower()
    CONFIRM_MATCHES = confirm in ['y', 'yes']
    
    # Ask user if they want to use Civilica CSV or manual entry
    mode = input("Choose input mode: (1) Process Civilica URLs from CSV, (2) Manual entry: ").strip()
    
    processed_data = []
    
    if mode == "1":
        # If input_csv wasn't provided as an argument, ask for it now
        if not input_csv:
            input_csv = input("Enter the path to your Civilica URLs CSV file: ").strip()
        
        # Process URLs from CSV file
        try:
            with open(input_csv, mode='r', encoding='utf-8-sig') as infile:
                urls = [line.strip() for line in infile if line.strip().startswith("http")]
            
            if not urls:
                print(f"No URLs found in {input_csv}. Please check the file format.")
                return
                
            print(f"Found {len(urls)} URLs to process.")
        except FileNotFoundError:
            print(f"Error: File {input_csv} not found.")
            return
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return
        
        for url in urls:
            print(f"🔍 Processing {url}")
            raw = scrape_url(url)
            if not raw: continue
            
            entry = {}
            entry["url"] = url
            entry["year"] = raw.get("year", "")
            entry["title"] = clean_text(translate_text(raw.get("title", "")))
            entry["abstract"] = clean_text(translate_text(raw.get("abstract", "")))
            
            # Authors
            entry["authors"] = []
            for a in raw.get("authors", []):
                trans = clean_text(translate_text(a))
                entry["authors"].append(trans)
            
            # Affiliations
            entry["affiliations"] = []
            for a in raw.get("affiliations", []):
                trans = clean_text(extract_core_name(translate_text(a)))
                entry["affiliations"].append(trans)
            
            # Journal
            journal = raw.get("journal", "")
            entry["journal"] = clean_text(extract_core_name(translate_text(journal)))
            
            # Standardize the entry
            standardized_entry, all_entities = standardize_entry(entry, all_entities)
            processed_data.append(standardized_entry)
    
    elif mode == "2":
        # Manual entry mode
        while True:
            print("\nEntering paper manually...")
            entry = manual_entry()
            
            # Standardize the entry
            standardized_entry, all_entities = standardize_entry(entry, all_entities)
            processed_data.append(standardized_entry)
            
            another = input("\nAdd another paper? (y/n): ").strip().lower()
            if another not in ['y', 'yes']:
                break
    
    else:
        print("Invalid mode selection. Exiting.")
        return
    
    # Save processed data and updated entities
    with open(output_json, mode='w', encoding='utf-8-sig') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)
    
    save_entities(entities_json, all_entities)
    
    print(f"\n✅ All done! Output saved to {output_json}")

# === CLI Interface ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NukeScan Academic Preprocessing Pipeline")
    parser.add_argument("--output", type=str, help="Path to save final processed JSON")
    args = parser.parse_args()

    output_json = args.output if args.output else input("Enter output JSON file path: ").strip()
    run_pipeline(None, output_json)