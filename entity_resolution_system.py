import json
import difflib

# Step 1: Load JSON output from "extract_core_name.py"
with open("/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/translated_data.json", "r", encoding="utf-8-sig") as file:
    data = json.load(file)

# Step 2 & 3: Extract unique values from JSON file
authors_list = list(set(author for entry in data if "authors" in entry for author in entry["authors"]))
affiliations_list = list(set(affiliation for entry in data if "affiliations" in entry for affiliation in entry["affiliations"]))
journals_list = list(set(entry["journal"] for entry in data if "journal" in entry))

# Step 4: Command-line Interface for editing lists
def edit_list(category, values):
    new_values = values.copy()
    print(f"Editing {category} list. Current values:")
    for i, v in enumerate(new_values, 1):
        print(f"{i}. {v}")
    
    while True:
        user_input = input(f"Enter number to edit/delete, or 'done' to finish: ")
        if user_input.lower() == "done":
            break
        
        try:
            index = int(user_input) - 1
            if 0 <= index < len(new_values):
                action = input("Enter new value or type 'delete' to remove: ")
                if action.lower() == "delete":
                    new_values.pop(index)
                else:
                    new_values[index] = action
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Enter a valid number or 'done'.")
    
    return new_values

# Let user edit each list
standard_authors = edit_list("Authors", authors_list)
standard_affiliations = edit_list("Affiliations", affiliations_list)
standard_journals = edit_list("Journals", journals_list)

# Step 6: Function to match values to the standard list
def match_to_standard(value, standard_list):
    match = difflib.get_close_matches(value, standard_list, n=1, cutoff=0.7)
    return match[0] if match else value

# Step 7: Standardize JSON file
standardized_data = []
for entry in data:
    standardized_entry = entry.copy()
    if "authors" in entry:
        standardized_entry["authors"] = match_to_standard(entry["authors"], standard_authors)
    if "affiliations" in entry:
        standardized_entry["affiliations"] = match_to_standard(entry["affiliations"], standard_affiliations)
    if "journal" in entry:
        standardized_entry["journal"] = match_to_standard(entry["journal"], standard_journals)
    standardized_data.append(standardized_entry)

# Save the standardized JSON
with open("standardized_output.json", "w", encoding="utf-8") as outfile:
    json.dump(standardized_data, outfile, indent=4, ensure_ascii=False)

print("Standardized JSON saved as standardized_output.json")
