# NukeScan Academic Pipeline

A comprehensive academic paper processing pipeline that scrapes, standardizes, and imports research paper data into knowledge graphs for social network analysis (SNA) in nuclear science research.

## 🚀 Features

- **Web Scraping**: Automatically extracts paper metadata from Civilica academic database
- **Multi-language Support**: Translates Persian/Farsi content to English using Google Translate
- **Intelligent Name Standardization**: Uses AI-powered semantic matching to standardize author names, affiliations, and journal names
- **Manual Entry**: Interactive mode for adding papers without URLs
- **Knowledge Graph Integration**: Direct import to Neo4j for network analysis
- **Entity Management**: Tracks standardized names with variants for consistent data
- **GUI Interface**: User-friendly graphical interface option
- **Social Network Analysis**: Pre-built Cypher queries for research collaboration analysis

## 📋 Prerequisites

- Python 3.8+
- Neo4j Database (local or cloud)
- OpenAI API key
- Google Cloud Translation API credentials
- Virtual environment (recommended)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nukescan-pipeline
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # OpenAI API Key
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Neo4j Configuration
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_neo4j_password_here
   
   # Google Cloud Translation
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google/credentials.json
   ```

5. **Set up Neo4j**
   - Install [Neo4j Desktop](https://neo4j.com/download/) or use [Neo4j AuraDB](https://neo4j.com/cloud/aura/)
   - Create a new database and note the connection details
   - Update your `.env` file with the correct credentials

## 📊 Data Schema

The pipeline creates the following knowledge graph structure:

### Nodes
- **Author**: `{name: string}`
- **Paper**: `{title: string, abstract: string, url: string, year: integer}`
- **Affiliation**: `{name: string}`
- **Journal**: `{name: string}`

### Relationships
- **WROTE**: Author → Paper
- **AFFILIATED_WITH**: Author → Affiliation
- **PUBLISHED_AT**: Paper → Journal
- **COAUTHORED**: Author ↔ Author

## 🎯 Usage

### Command Line Interface

#### Basic Processing (JSON output only)
```bash
python nukescan_pipeline.py --output processed_papers.json
```

#### With Neo4j Integration
```bash
python nukescan_pipeline_neo4j.py --output processed_papers.json --neo4j --clear-neo4j
```

#### Standalone Neo4j Import
```bash
python neo4j_integration.py --json processed_papers.json --clear
```

### GUI Interface
```bash
python pipeline_gui.py
```

### Input Formats

#### CSV Input (Civilica URLs)
Create a CSV file with URLs:
```
https://en.civilica.com/doc/1504010/
https://en.civilica.com/doc/1234567/
```

#### Manual Entry
Choose option 2 when running the pipeline to manually enter paper details.

## 📁 File Structure

```
nukescan-pipeline/
├── nukescan_pipeline.py              # Original pipeline (JSON only)
├── nukescan_pipeline_neo4j.py        # Enhanced pipeline with Neo4j
├── neo4j_integration.py              # Neo4j import module
├── pipeline_gui.py                   # GUI interface
├── elsevier_api.py                   # Elsevier API integration
├── standard_entities.json            # Standardized entity database
├── SNA_queries_cypher                # Social network analysis queries
├── json_import_cypher                # Neo4j import queries
├── input_papers.csv                  # Sample input file
├── requirements.txt                  # Python dependencies
├── .env.template                     # Environment variables template
└── README.md                         # This file
```

## 🧠 AI-Powered Features

### Semantic Name Matching
- Uses SentenceTransformers for intelligent name similarity
- Automatically matches variations of the same entity
- 85% similarity threshold for automatic matching
- Manual confirmation option for uncertain matches

### Name Standardization
- GPT-4 powered extraction of core organization names
- Removes departments, addresses, and formatting artifacts
- Maintains consistency across the dataset

## 🔍 Social Network Analysis

Pre-built Cypher queries for research analysis:

### Community Detection
```cypher
CALL gds.louvain.stream('socialGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS Author, communityId
ORDER BY communityId;
```

### Centrality Analysis
```cypher
MATCH (p:Author)-[r]->() 
RETURN p.name, COUNT(r) AS connections 
ORDER BY connections DESC;
```

### Collaboration Networks
```cypher
CALL gds.betweenness.stream('socialGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS person, score 
ORDER BY score DESC;
```

## 📈 Example Output

The pipeline generates structured JSON data:

```json
[
  {
    "url": "https://en.civilica.com/doc/1504010/",
    "year": 2022,
    "title": "computational model for predicting shock wave attenuation",
    "abstract": "using the autodyn hydrodynamic code blasts resulting from...",
    "authors": ["nasser hassanzadeh", "mohammadhossein keshavarz"],
    "affiliations": ["malek ashtar university of technology"],
    "journal": "national conference on application of new technologies"
  }
]
```

## 🔧 Configuration Options

### Pipeline Modes
1. **URL Processing**: Scrape from Civilica URLs
2. **Manual Entry**: Interactive paper input

### Neo4j Options
- Automatic import after processing
- Database clearing before import
- Connection configuration via environment variables

### Matching Behavior
- Automatic vs. manual confirmation of entity matches
- Customizable similarity thresholds
- Variant tracking for entity names

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Import Error: ModuleNotFoundError**
```bash
pip install -r requirements.txt
```

**Neo4j Connection Failed**
- Check if Neo4j is running
- Verify credentials in `.env` file
- Test connection with Neo4j Browser

**Google Translation Error**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path
- Check service account permissions
- Ensure Translation API is enabled

**OpenAI API Error**
- Verify API key in `.env` file
- Check API quota and billing
- Ensure GPT-4 access if using GPT-4

### Getting Help

1. Check the [Issues](../../issues) page for known problems
2. Create a new issue with detailed error messages
3. Include your Python version and OS information

## 🙏 Acknowledgments

- Built for nuclear science research collaboration analysis
- Uses OpenAI GPT-4 for intelligent text processing
- Integrates with Neo4j for graph database capabilities
- Supports Persian/English academic content processing