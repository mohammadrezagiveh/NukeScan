import json
import os
import re
import csv
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
import openai
from sentence_transformers import SentenceTransformer, util
import torch

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

def resolve_name(name, standard_list, category, url):
    if not standard_list:
        return prompt_user(name, category, url, standard_list)

    name_embedding = model.encode(name, convert_to_tensor=True)
    standard_embeddings = model.encode(standard_list, convert_to_tensor=True)
    cosine_scores = util.cos_sim(name_embedding, standard_embeddings)[0]

    best_score_idx = torch.argmax(cosine_scores).item()
    best_score = cosine_scores[best_score_idx].item()

    if best_score > 0.85:
        return standard_list[best_score_idx], standard_list
    return prompt_user(name, category, url, standard_list)

def prompt_user(name, category, url, standard_list):
    print(f"\nUnrecognized {category} in {url}:\n{name}")
    user_input = input("Enter standardized version or press Enter to keep as-is: ").strip()
    if user_input:
        standard_list.append(user_input)
        return user_input, standard_list
    return name, standard_list

def load_standard_list(file_path):
    if os.path.exists(file_path):
        with open(file_path, newline='', encoding='utf-8') as f:
            return [row[0] for row in csv.reader(f) if row]
    return []

def save_standard_list(file_path, data_list):
    existing = set()
    if os.path.exists(file_path):
        with open(file_path, newline='', encoding='utf-8') as f:
            existing = {row[0] for row in csv.reader(f) if row}

    combined = sorted(existing.union(data_list))
    with open(file_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for item in combined:
            writer.writerow([item])

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

    authors_csv = "standard_authors.csv"
    affiliations_csv = "standard_affiliations.csv"
    journals_csv = "standard_journals.csv"

    standard_authors = load_standard_list(authors_csv)
    standard_affiliations = load_standard_list(affiliations_csv)
    standard_journals = load_standard_list(journals_csv)

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

    save_standard_list(authors_csv, standard_authors)
    save_standard_list(affiliations_csv, standard_affiliations)
    save_standard_list(journals_csv, standard_journals)

    print(f"\n✅ All done! Output saved to {output_json}")

# === CLI Interface ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NukeScan Academic Preprocessing Pipeline")
    parser.add_argument("--input", type=str, required=True, help="Path to URL CSV file")
    parser.add_argument("--output", type=str, required=True, help="Path to save final processed JSON")
    args = parser.parse_args()

    run_pipeline(args.input, args.output)