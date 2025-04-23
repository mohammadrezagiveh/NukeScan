import requests

# Your personal Elsevier API key
API_KEY = "1bbb43a5c73e332a4526e6d0c9689cf8"

# DOI of the paper you want metadata for
doi = "10.1016/j.pnucene.2020.103590"

# API endpoint
url = f"https://api.elsevier.com/content/abstract/doi/{doi}"

# Headers including your API key and desired response format
headers = {
    "X-ELS-APIKey": API_KEY,
    "Accept": "application/xml"
}


# Make the API request
response = requests.get(url, headers=headers)

# Check response
print("Status code:", response.status_code)
print("Response body:\n", response.text)




import xml.etree.ElementTree as ET

# Only run this if the response was successful
if response.status_code == 200:
    # Parse the XML response
    root = ET.fromstring(response.text)

    # Define XML namespaces
    ns = {
        "dc": "http://purl.org/dc/elements/1.1/",
        "prism": "http://prismstandard.org/namespaces/basic/2.0/"
    }

    # Extract desired fields
    title = root.find(".//dc:title", ns)
    authors = root.findall(".//dc:creator/author", ns)
    author_names = []
    for author in authors:
        indexed_name = author.find("ce:indexed-name", {
            "ce": "http://www.elsevier.com/xml/ani/common"
        })
        if indexed_name is not None:
            author_names.append(indexed_name.text)
    journal = root.find(".//prism:publicationName", ns)
    pub_date = root.find(".//prism:coverDate", ns)
    doi_elem = root.find(".//prism:doi", ns)

    # Print clean metadata
    print("\n--- Article Metadata ---")
    print("Title:", title.text if title is not None else "N/A")
    print("Authors:", ", ".join(author_names) if author_names else "N/A")
    print("DOI:", doi_elem.text if doi_elem is not None else "N/A")
    print("Journal:", journal.text if journal is not None else "N/A")
    print("Publication Date:", pub_date.text if pub_date is not None else "N/A")
else:
    print("Could not parse metadata due to unsuccessful request.")