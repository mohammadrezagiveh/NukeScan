import json
import os
import re
from google.cloud import translate_v2 as translate
import openai
from dotenv import load_dotenv


# === Setup ===
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/mohammadrezagiveh/Downloads/elite-conquest-413518-a5f253d67208.json"
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# === Paths ===
input_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/scraped_data.json"
output_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/processed_data.json"

# === Clients ===
translator = translate.Client()
gpt_client = openai.OpenAI()

# === Helpers ===
def translate_text(text, target_lang="en"):
    if not text.strip(): return text
    try:
        result = translator.translate(text, target_language=target_lang)
        return result.get("translatedText", text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # remove punctuation
    return text.strip()

def extract_core_name(text):
    if not text: return text
    prompt = f"""Extract the core name of research organizations and journals/conferences from the following text.

Rules:
	•	For research organizations: Keep only the university, institute, or main organization name. Remove departments, labs, addresses, and personal titles.
	•	For journals/conferences: Keep only the journal or conference name. Remove volume, issue numbers, and extra formatting.

Examples:
	1.	Input: "Laboratory of Agricultural Zoology and Entomology, Department of Crop Science, Agricultural University of Athens; ۷۵ Iera Odos str., ۱۱۸۵۵ Athens, Attica, Greece"
Output: "Agricultural University of Athens"
	2.	Input: "Radiation Physics and Engineering، Vol: 5، Issue: 1"
Output: "Radiation Physics and Engineering"

Only return the cleaned-up name without any explanations. If you can't extract a core name, do not modify the input text. This is an API so I need a clear and concise answer without any additional text.

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
        print(f"OpenAI error: {e}")
        return text

# === Processing ===
with open(input_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

processed = []
for item in data:
    entry = item.copy()

    entry['title'] = clean_text(translate_text(entry.get('title', '')))
    entry['abstract'] = clean_text(translate_text(entry.get('abstract', '')))

    entry['authors'] = [clean_text(translate_text(a)) for a in entry.get('authors', [])]
    entry['affiliations'] = [clean_text(extract_core_name(translate_text(a))) for a in entry.get('affiliations', [])]
    
    if 'journal' in entry:
        entry['journal'] = clean_text(extract_core_name(translate_text(entry['journal'])))

    processed.append(entry)

with open(output_path, 'w', encoding='utf-8-sig') as f:
    json.dump(processed, f, ensure_ascii=False, indent=4)

print(f"✅ Preprocessing complete. Output saved to {output_path}")