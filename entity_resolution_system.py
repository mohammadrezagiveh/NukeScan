import json
import pandas as pd
from difflib import get_close_matches
from fuzzywuzzy import fuzz, process
import os

class EntityResolver:
    def __init__(self, input_json_path, output_dir="./standardized"):
        """Initialize the entity resolver with input and output paths."""
        self.input_json_path = input_json_path
        self.output_dir = output_dir
        self.data = self.load_json()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Paths for standardized entity lists
        self.authors_path = os.path.join(self.output_dir, "standardized_authors.json")
        self.affiliations_path = os.path.join(self.output_dir, "standardized_affiliations.json")
        self.journals_path = os.path.join(self.output_dir, "standardized_journals.json")
        
        # Load or create standardized lists
        self.std_authors = self.load_or_create_list(self.authors_path)
        self.std_affiliations = self.load_or_create_list(self.affiliations_path)
        self.std_journals = self.load_or_create_list(self.journals_path)

    def load_json(self):
        """Load JSON file into a Python dictionary."""
        try:
            with open(self.input_json_path, "r", encoding="utf-8-sig") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
    
    def load_or_create_list(self, path):
        """Load a standardized list if it exists, or create an empty one."""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as file:
                    return json.load(file)
            except Exception as e:
                print(f"Error loading {path}: {e}")
                return {}
        return {}
    
    def extract_unique_entities(self):
        """Extract unique entities from the data."""
        authors = set()
        affiliations = set()
        journals = set()
        
        for item in self.data:
            # Extract authors
            if 'authors' in item and isinstance(item['authors'], list):
                for author in item['authors']:
                    if author:
                        authors.add(author)
            
            # Extract affiliations
            if 'affiliations' in item and isinstance(item['affiliations'], list):
                for aff in item['affiliations']:
                    if aff:
                        affiliations.add(aff)
            
            # Extract journals
            if 'journal' in item and item['journal']:
                journals.add(item['journal'])
        
        return list(authors), list(affiliations), list(journals)
    
    def generate_standardized_lists(self, threshold=80):
        """Generate standardized entity lists with initial grouping."""
        authors, affiliations, journals = self.extract_unique_entities()
        
        # Process authors
        self._process_entity_list(authors, self.std_authors, threshold)
        self._save_standardized_list(self.std_authors, self.authors_path)
        
        # Process affiliations
        self._process_entity_list(affiliations, self.std_affiliations, threshold)
        self._save_standardized_list(self.std_affiliations, self.affiliations_path)
        
        # Process journals
        self._process_entity_list(journals, self.std_journals, threshold)
        self._save_standardized_list(self.std_journals, self.journals_path)
        
        print(f"Generated standardized lists in {self.output_dir}")
    
    def _process_entity_list(self, entity_list, std_dict, threshold):
        """Process a list of entities to find potential duplicates."""
        # First pass: group similar entities
        processed = set()
        for entity in entity_list:
            if entity in processed:
                continue
                
            processed.add(entity)
            
            # Find similar entities
            similar_entities = []
            for other in entity_list:
                if other != entity and other not in processed:
                    similarity = fuzz.ratio(entity.lower(), other.lower())
                    if similarity >= threshold:
                        similar_entities.append((other, similarity))
                        processed.add(other)
            
            # Add to standardized dictionary
            if entity not in std_dict:
                std_dict[entity] = {
                    "standard_form": entity,
                    "variants": [e for e, _ in similar_entities],
                    "confirmed": False
                }
    
    def _save_standardized_list(self, std_dict, path):
        """Save a standardized list to a JSON file."""
        with open(path, "w", encoding="utf-8-sig") as file:
            json.dump(std_dict, file, ensure_ascii=False, indent=4)
    
    def apply_standardization(self, output_path=None):
        """Apply standardization to the data using the confirmed standard forms."""
        if output_path is None:
            output_path = self.input_json_path.replace(".json", "_standardized.json")
        
        standardized_data = []
        
        for item in self.data:
            new_item = item.copy()
            
            # Standardize authors
            if 'authors' in item and isinstance(item['authors'], list):
                new_item['authors'] = [self._get_standard_form(author, self.std_authors) for author in item['authors']]
            
            # Standardize affiliations
            if 'affiliations' in item and isinstance(item['affiliations'], list):
                new_item['affiliations'] = [self._get_standard_form(aff, self.std_affiliations) for aff in item['affiliations']]
            
            # Standardize journal
            if 'journal' in item and item['journal']:
                new_item['journal'] = self._get_standard_form(item['journal'], self.std_journals)
            
            standardized_data.append(new_item)
        
        # Save standardized data
        with open(output_path, "w", encoding="utf-8-sig") as file:
            json.dump(standardized_data, file, ensure_ascii=False, indent=4)
        
        print(f"Standardized data saved to {output_path}")
        return output_path
    
    def _get_standard_form(self, entity, std_dict):
        """Get the standard form of an entity."""
        # Direct match
        if entity in std_dict and std_dict[entity]["confirmed"]:
            return std_dict[entity]["standard_form"]
        
        # Check if it's a variant
        for std_entity, info in std_dict.items():
            if info["confirmed"] and entity in info["variants"]:
                return info["standard_form"]
        
        # Fuzzy match if no direct match found
        best_match = None
        best_score = 0
        
        for std_entity, info in std_dict.items():
            if info["confirmed"]:
                score = fuzz.ratio(entity.lower(), std_entity.lower())
                if score > best_score and score >= 85:  # Higher threshold for automatic matching
                    best_score = score
                    best_match = info["standard_form"]
        
        return best_match if best_match else entity
    
    def create_interactive_editor(self):
        """Create an interactive editor to manually review and confirm standardizations."""
        return EntityEditorUI(self)

class EntityEditorUI:
    def __init__(self, resolver):
        """Initialize the UI with a resolver instance."""
        self.resolver = resolver
    
    def run(self):
        """Run the interactive editor."""
        while True:
            print("\nEntity Resolution Menu:")
            print("1. Edit Author Standardizations")
            print("2. Edit Affiliation Standardizations")
            print("3. Edit Journal Standardizations")
            print("4. Apply Standardizations")
            print("5. Exit")
            
            choice = input("Select an option: ")
            
            if choice == "1":
                self._edit_entities(self.resolver.std_authors, self.resolver.authors_path, "Authors")
            elif choice == "2":
                self._edit_entities(self.resolver.std_affiliations, self.resolver.affiliations_path, "Affiliations")
            elif choice == "3":
                self._edit_entities(self.resolver.std_journals, self.resolver.journals_path, "Journals")
            elif choice == "4":
                output_path = input("Enter output path (or press Enter for default): ")
                if not output_path:
                    output_path = None
                self.resolver.apply_standardization(output_path)
            elif choice == "5":
                print("Exiting...")
                break
            else:
                print("Invalid option. Try again.")
    
    def _edit_entities(self, entity_dict, save_path, entity_type):
        """Edit entities of a specific type."""
        while True:
            # Display entities
            print(f"\n{entity_type} Standardization:")
            entities = list(entity_dict.keys())
            
            for i, entity in enumerate(entities):
                status = "✓" if entity_dict[entity]["confirmed"] else "×"
                print(f"{i+1}. {status} {entity} -> {entity_dict[entity]['standard_form']}")
                if entity_dict[entity]["variants"]:
                    print(f"   Variants: {', '.join(entity_dict[entity]['variants'])}")
            
            print("\nOptions:")
            print("a. Edit standardization")
            print("b. Merge entities")
            print("c. Confirm all")
            print("d. Back to main menu")
            
            subchoice = input("Select an option: ")
            
            if subchoice == "a":
                idx = int(input("Enter entity number to edit: ")) - 1
                if 0 <= idx < len(entities):
                    entity = entities[idx]
                    new_std = input(f"Enter new standard form for '{entity}': ")
                    entity_dict[entity]["standard_form"] = new_std
                    entity_dict[entity]["confirmed"] = True
                    print(f"Updated standard form for '{entity}'.")
                else:
                    print("Invalid entity number.")
            
            elif subchoice == "b":
                idx1 = int(input("Enter first entity number: ")) - 1
                idx2 = int(input("Enter second entity number: ")) - 1
                
                if 0 <= idx1 < len(entities) and 0 <= idx2 < len(entities) and idx1 != idx2:
                    entity1 = entities[idx1]
                    entity2 = entities[idx2]
                    
                    # Choose which one to keep
                    keep = input(f"Keep (1) '{entity1}' or (2) '{entity2}' as standard form? ")
                    
                    if keep == "1":
                        standard = entity1
                        merged = entity2
                    elif keep == "2":
                        standard = entity2
                        merged = entity1
                    else:
                        print("Invalid choice.")
                        continue
                    
                    # Merge the entities
                    entity_dict[standard]["variants"].extend([merged] + entity_dict[merged]["variants"])
                    entity_dict[standard]["variants"] = list(set(entity_dict[standard]["variants"]))
                    entity_dict[standard]["confirmed"] = True
                    
                    # Delete the merged entity
                    del entity_dict[merged]
                    
                    print(f"Merged '{merged}' into '{standard}'.")
                else:
                    print("Invalid entity numbers.")
            
            elif subchoice == "c":
                for entity in entity_dict:
                    entity_dict[entity]["confirmed"] = True
                print("All entities confirmed.")
            
            elif subchoice == "d":
                # Save changes before returning
                self.resolver._save_standardized_list(entity_dict, save_path)
                break
            
            else:
                print("Invalid option. Try again.")

# Example usage
if __name__ == "__main__":
    input_json = input("Enter path to translated JSON file: ")
    resolver = EntityResolver(input_json)
    resolver.generate_standardized_lists()
    editor = resolver.create_interactive_editor()
    editor.run()