from neo4j import GraphDatabase
import json
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jGraph:
    def __init__(self, uri=None, username=None, password=None):
        """Initialize Neo4j connection"""
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution!)"""
        if not self.driver:
            return False
            
        with self.driver.session() as session:
            try:
                session.run("MATCH (n) DETACH DELETE n")
                print("🗑️  Database cleared")
                return True
            except Exception as e:
                print(f"Error clearing database: {e}")
                return False
    
    def create_constraints(self):
        """Create uniqueness constraints for better performance"""
        if not self.driver:
            return False
            
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.url IS UNIQUE", 
            "CREATE CONSTRAINT IF NOT EXISTS FOR (af:Affiliation) REQUIRE af.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Journal) REQUIRE j.name IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    # Constraint might already exist, that's okay
                    pass
        print("📋 Constraints created/verified")
        return True
    
    def import_papers(self, papers_data):
        """Import papers data into Neo4j graph"""
        if not self.driver:
            print("❌ No database connection available")
            return False
        
        if not papers_data:
            print("❌ No papers data provided")
            return False
        
        print(f"🔄 Importing {len(papers_data)} papers into Neo4j...")
        
        with self.driver.session() as session:
            for i, paper in enumerate(papers_data, 1):
                try:
                    self._import_single_paper(session, paper)
                    print(f"✅ Imported paper {i}/{len(papers_data)}: {paper.get('title', 'Unknown')[:50]}...")
                except Exception as e:
                    print(f"❌ Error importing paper {i}: {e}")
                    continue
        
        print("🎉 Import completed!")
        return True
    
    def _import_single_paper(self, session, paper):
        """Import a single paper and its relationships"""
        
        # 1. Create Paper node
        paper_query = """
        MERGE (p:Paper {url: $url})
        SET p.title = $title,
            p.abstract = $abstract,
            p.year = $year
        RETURN p
        """
        
        session.run(paper_query, {
            "url": paper.get("url", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "year": paper.get("year", "")
        })
        
        # 2. Create Journal node and relationship
        if paper.get("journal"):
            journal_query = """
            MATCH (p:Paper {url: $url})
            MERGE (j:Journal {name: $journal_name})
            MERGE (p)-[:PUBLISHED_AT]->(j)
            """
            
            session.run(journal_query, {
                "url": paper.get("url", ""),
                "journal_name": paper.get("journal")
            })
        
        # 3. Create Authors and their relationships
        authors = paper.get("authors", [])
        affiliations = paper.get("affiliations", [])
        
        for idx, author_name in enumerate(authors):
            if not author_name:
                continue
                
            # Create Author and relationship to Paper
            author_query = """
            MATCH (p:Paper {url: $url})
            MERGE (a:Author {name: $author_name})
            MERGE (a)-[:WROTE]->(p)
            """
            
            session.run(author_query, {
                "url": paper.get("url", ""),
                "author_name": author_name
            })
            
            # Create Affiliation relationship if available
            if idx < len(affiliations) and affiliations[idx]:
                affiliation_query = """
                MATCH (a:Author {name: $author_name})
                MERGE (af:Affiliation {name: $affiliation_name})
                MERGE (a)-[:AFFILIATED_WITH]->(af)
                """
                
                session.run(affiliation_query, {
                    "author_name": author_name,
                    "affiliation_name": affiliations[idx]
                })
        
        # 4. Create co-authorship relationships
        if len(authors) > 1:
            coauthor_query = """
            MATCH (p:Paper {url: $url})<-[:WROTE]-(a:Author)
            WITH collect(a) as authors, p
            UNWIND authors as a1
            UNWIND authors as a2
            WITH a1, a2 WHERE a1 <> a2
            MERGE (a1)-[:COAUTHORED]->(a2)
            """
            
            session.run(coauthor_query, {"url": paper.get("url", "")})
    
    def get_stats(self):
        """Get database statistics"""
        if not self.driver:
            return None
            
        stats_query = """
        MATCH (a:Author) WITH count(a) as authors
        MATCH (p:Paper) WITH authors, count(p) as papers
        MATCH (af:Affiliation) WITH authors, papers, count(af) as affiliations
        MATCH (j:Journal) WITH authors, papers, affiliations, count(j) as journals
        MATCH ()-[r:WROTE]->() WITH authors, papers, affiliations, journals, count(r) as authorship_relations
        MATCH ()-[r:COAUTHORED]->() WITH authors, papers, affiliations, journals, authorship_relations, count(r) as coauthor_relations
        RETURN authors, papers, affiliations, journals, authorship_relations, coauthor_relations
        """
        
        with self.driver.session() as session:
            result = session.run(stats_query)
            record = result.single()
            if record:
                return {
                    "authors": record["authors"],
                    "papers": record["papers"], 
                    "affiliations": record["affiliations"],
                    "journals": record["journals"],
                    "authorship_relations": record["authorship_relations"],
                    "coauthor_relations": record["coauthor_relations"]
                }
        return None


def import_to_neo4j(json_file_path, clear_db=False, neo4j_uri=None, neo4j_username=None, neo4j_password=None):
    """
    Standalone function to import JSON data to Neo4j
    
    Args:
        json_file_path: Path to the processed papers JSON file
        clear_db: Whether to clear the database before import
        neo4j_uri: Neo4j database URI (optional, uses env var if not provided)
        neo4j_username: Neo4j username (optional, uses env var if not provided) 
        neo4j_password: Neo4j password (optional, uses env var if not provided)
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Load JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8-sig') as f:
            papers_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return False
    
    # Connect to Neo4j
    graph = Neo4jGraph(neo4j_uri, neo4j_username, neo4j_password)
    
    if not graph.driver:
        return False
    
    try:
        # Clear database if requested
        if clear_db:
            print("⚠️  Clearing existing database...")
            graph.clear_database()
        
        # Create constraints
        graph.create_constraints()
        
        # Import data
        success = graph.import_papers(papers_data)
        
        # Print statistics
        if success:
            stats = graph.get_stats()
            if stats:
                print("\n📊 Database Statistics:")
                print(f"   Authors: {stats['authors']}")
                print(f"   Papers: {stats['papers']}")
                print(f"   Affiliations: {stats['affiliations']}")
                print(f"   Journals: {stats['journals']}")
                print(f"   Authorship Relations: {stats['authorship_relations']}")
                print(f"   Co-authorship Relations: {stats['coauthor_relations']}")
        
        return success
        
    finally:
        graph.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import processed papers to Neo4j")
    parser.add_argument("--json", type=str, required=True, help="Path to processed papers JSON file")
    parser.add_argument("--clear", action="store_true", help="Clear database before import")
    parser.add_argument("--uri", type=str, help="Neo4j URI (default: bolt://localhost:7687)")
    parser.add_argument("--username", type=str, help="Neo4j username (default: neo4j)")
    parser.add_argument("--password", type=str, help="Neo4j password")
    
    args = parser.parse_args()
    
    success = import_to_neo4j(
        json_file_path=args.json,
        clear_db=args.clear,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password
    )
    
    if success:
        print("🎉 Import completed successfully!")
    else:
        print("❌ Import failed!")