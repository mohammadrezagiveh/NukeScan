import json
import openai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Path to your JSON file
json_file_path = "/Users/mohammadrezagiveh/Desktop/ScrapeCivilica/translated_data.json"

# Get OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Verify API key is available
if not openai.api_key:
    raise ValueError("No OpenAI API key found. Please check your .env file.")

# Function to extract core names
def extract_core_name(text):
    if not text:
        return text  # Return as-is if empty

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
        client = openai.OpenAI()  # API key is automatically used from environment
        
        response = client.chat.completions.create(
            model="gpt-4",  # Fixed typo in model name from "gpt-4o" to "gpt-4"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing text: {e}")
        return text  # Return original text if there's an error

# Load the JSON file
try:
    with open(json_file_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # Process each paper entry
    for paper in data: 
        if "affiliations" in paper and isinstance(paper["affiliations"], list):
            paper["affiliations"] = [extract_core_name(aff) for aff in paper["affiliations"]]
        if "journal" in paper:
            paper["journal"] = extract_core_name(paper["journal"])

    # Save the modified JSON file
    with open(json_file_path, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("JSON file updated successfully.")
except Exception as e:
    print(f"Error processing JSON file: {e}")
