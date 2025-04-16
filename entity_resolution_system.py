import json
import os
import csv
from sentence_transformers import SentenceTransformer, util
import torch

# Step 1: Load JSON output
with open("/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/translated_data.json", "r", encoding="utf-8-sig") as file:
    data = json.load(file)

# Step 2: Utility functions for loading and saving CSV lists
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

# Load embedding model
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

def resolve_name(name, standard_list, category, url):
    if not standard_list:
        print(f"\nUnrecognized {category} in {url}:\n{name}")
        user_input = input(f"Enter standardized version or press Enter to keep as is: ").strip()
        if user_input:
            standard_list.append(user_input)
            return user_input, standard_list
        return name, standard_list

    name_embedding = model.encode(name, convert_to_tensor=True)
    standard_embeddings = model.encode(standard_list, convert_to_tensor=True)
    cosine_scores = util.cos_sim(name_embedding, standard_embeddings)[0]

    best_score_idx = torch.argmax(cosine_scores).item()
    best_score = cosine_scores[best_score_idx].item()

    if best_score > 0.85:
        return standard_list[best_score_idx], standard_list
    else:
        print(f"\nUnrecognized {category} in {url}:\n{name}")
        user_input = input(f"Enter standardized version or press Enter to keep as is: ").strip()
        if user_input:
            standard_list.append(user_input)
            return user_input, standard_list
        return name, standard_list

# Step 4: File paths for standard lists
authors_csv = "/Users/mohammadrezagiveh/Desktop/standard_authors.csv"
affiliations_csv = "/Users/mohammadrezagiveh/Desktop/standard_affiliations.csv"
journals_csv = "/Users/mohammadrezagiveh/Desktop/standard_journals.csv"

standard_authors = load_standard_list(authors_csv)
standard_affiliations = load_standard_list(affiliations_csv)
standard_journals = load_standard_list(journals_csv)

# Step 5: Standardize the data
standardized_data = []
for entry in data:
    standardized_entry = entry.copy()

    if "authors" in entry:
        new_authors = []
        for author in entry["authors"]:
            resolved, standard_authors = resolve_name(author, standard_authors, "Author", entry["url"])
            new_authors.append(resolved)
        standardized_entry["authors"] = new_authors

    if "affiliations" in entry:
        new_affils = []
        for affil in entry["affiliations"]:
            resolved, standard_affiliations = resolve_name(affil, standard_affiliations, "Affiliation", entry["url"])
            new_affils.append(resolved)
        standardized_entry["affiliations"] = new_affils

    if "journal" in entry:
        resolved, standard_journals = resolve_name(entry["journal"], standard_journals, "Journal", entry["url"])
        standardized_entry["journal"] = resolved

    standardized_data.append(standardized_entry)

# Step 6: Save output
with open("standardized_output.json", "w", encoding="utf-8") as outfile:
    json.dump(standardized_data, outfile, indent=4, ensure_ascii=False)

save_standard_list(authors_csv, standard_authors)
save_standard_list(affiliations_csv, standard_affiliations)
save_standard_list(journals_csv, standard_journals)

print("Standardized JSON saved as standardized_output.json")
