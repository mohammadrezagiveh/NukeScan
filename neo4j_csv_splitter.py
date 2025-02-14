import pandas as pd

# Load the dataset
file_path = "/Users/mohammadrezagiveh/Documents/Neo4j/SECTIONTDATA.csv"  # Update this path if needed
df = pd.read_csv(file_path)

# Generate unique Paper IDs
df['paper_id'] = ['P' + str(i+1).zfill(4) for i in range(len(df))]

# Select relevant columns
papers_df = df[['paper_id', 'EnglishTitle', 'PublicationPlace', 'Year', 'EnglishAbstract', 'Link']]
papers_df.columns = ['paper_id', 'title', 'journal', 'year', 'abstract', 'link']

# Save to CSV
papers_df.to_csv("papers.csv", index=False)