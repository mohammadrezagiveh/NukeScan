import json
import pandas as pd

class JSONExplorer:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = self.load_json()
        self.df = pd.DataFrame(self.data)

    def load_json(self):
        """Load JSON file into a Python dictionary."""
        try:
            with open(self.json_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []

    def display_data(self, num_rows=10):
        """Display a preview of the JSON data as a table."""
        print(self.df.head(num_rows))

    def search_data(self, column, value):
        """Search for specific values in the dataset."""
        if column not in self.df.columns:
            print("Column not found.")
            return
        result = self.df[self.df[column].str.contains(value, na=False, case=False)]
        print(result)

    def edit_entry(self, index, column, new_value):
        """Edit a specific entry in the dataset."""
        if index not in self.df.index or column not in self.df.columns:
            print("Invalid index or column name.")
            return
        self.df.at[index, column] = new_value
        print(f"Updated row {index}: {column} -> {new_value}")

    def delete_entry(self, index):
        """Delete an entry from the dataset."""
        if index not in self.df.index:
            print("Invalid index.")
            return
        self.df.drop(index, inplace=True)
        print(f"Deleted row {index}")

    def save_json(self, output_file):
        """Save the modified data back to a JSON file."""
        self.df.to_json(output_file, orient="records", indent=4)
        print(f"Data saved to {output_file}")

if __name__ == "__main__":
    explorer = JSONExplorer(json_file="scraped_data.json")

    while True:
        print("\nOptions:")
        print("1. View Data")
        print("2. Search Data")
        print("3. Edit Entry")
        print("4. Delete Entry")
        print("5. Save JSON")
        print("6. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            explorer.display_data()
        elif choice == "2":
            col = input("Enter column name to search: ")
            val = input("Enter search value: ")
            explorer.search_data(col, val)
        elif choice == "3":
            idx = int(input("Enter index to edit: "))
            col = input("Enter column to edit: ")
            new_val = input("Enter new value: ")
            explorer.edit_entry(idx, col, new_val)
        elif choice == "4":
            idx = int(input("Enter index to delete: "))
            explorer.delete_entry(idx)
        elif choice == "5":
            output_file = input("Enter output file name (e.g., cleaned_data.json): ")
            explorer.save_json(output_file)
        elif choice == "6":
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")