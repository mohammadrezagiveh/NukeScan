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

# Generate unique Paper IDs
df['paper_id'] = ['P' + str(i+1).zfill(4) for i in range(len(df))]

# Select relevant columns
papers_df = df[['paper_id', 'EnglishTitle', 'PublicationPlace', 'Year', 'EnglishAbstract', 'Link']]
papers_df.columns = ['paper_id', 'title', 'journal', 'year', 'abstract', 'link']

# Save to CSV
papers_df.to_csv("papers.csv", index=False)

# Exploding the authors column into separate rows
authors_expanded = df[['EnglishAuthors']].copy()
authors_expanded['EnglishAuthors'] = authors_expanded['EnglishAuthors'].str.split(',')
authors_expanded = authors_expanded.explode('EnglishAuthors').drop_duplicates()

# Reset index and assign unique author IDs
authors_expanded = authors_expanded.reset_index(drop=True)
authors_expanded['author_id'] = ['A' + str(i+1).zfill(4) for i in range(len(authors_expanded))]
authors_expanded.columns = ['name', 'author_id']

# Save to CSV
authors_expanded.to_csv("authors.csv", index=False)

# Explode the affiliations column
affiliations_expanded = df[['Affiliations']].copy()
affiliations_expanded['Affiliations'] = affiliations_expanded['Affiliations'].str.split('/')
affiliations_expanded = affiliations_expanded.explode('Affiliations').drop_duplicates()

# Reset index and assign unique affiliation IDs
affiliations_expanded = affiliations_expanded.reset_index(drop=True)
affiliations_expanded['affiliation_id'] = ['AFF' + str(i+1).zfill(4) for i in range(len(affiliations_expanded))]
affiliations_expanded.columns = ['name', 'affiliation_id']

# Save to CSV
affiliations_expanded.to_csv("affiliations.csv", index=False)

# Create mapping from author name to author_id
author_map = dict(zip(authors_expanded['name'], authors_expanded['author_id']))

# Explode authors
authorship_data = df[['paper_id', 'EnglishAuthors']].copy()
authorship_data['EnglishAuthors'] = authorship_data['EnglishAuthors'].str.split(',')
authorship_data = authorship_data.explode('EnglishAuthors')

# Map to author_id
authorship_data['author_id'] = authorship_data['EnglishAuthors'].map(author_map)
authorship_data = authorship_data[['paper_id', 'author_id']].dropna()

# Save to CSV
authorship_data.to_csv("authorship.csv", index=False)

# Create mapping from affiliation name to affiliation_id
affiliation_map = dict(zip(affiliations_expanded['name'], affiliations_expanded['affiliation_id']))

# Explode authors and affiliations
affiliation_mapping_data = df[['EnglishAuthors', 'Affiliations']].copy()
affiliation_mapping_data['EnglishAuthors'] = affiliation_mapping_data['EnglishAuthors'].str.split(',')
affiliation_mapping_data['Affiliations'] = affiliation_mapping_data['Affiliations'].str.split('/')
affiliation_mapping_data = affiliation_mapping_data.explode('EnglishAuthors').explode('Affiliations')

# Map author_id and affiliation_id
affiliation_mapping_data['author_id'] = affiliation_mapping_data['EnglishAuthors'].map(author_map)
affiliation_mapping_data['affiliation_id'] = affiliation_mapping_data['Affiliations'].map(affiliation_map)
affiliation_mapping_data = affiliation_mapping_data[['author_id', 'affiliation_id']].dropna()

# Save to CSV
affiliation_mapping_data.to_csv("affiliation_mapping.csv", index=False)

import os
print("Generated files:")
print(os.listdir())  # Should show all five CSV files