#!/usr/bin/env python3
"""
Enhanced Nuclear Research GraphRAG System
- Local embedding management with persistence
- Hybrid retrieval (vector + graph traversal)
- User-controlled embedding updates
"""

import os
import json
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Neo4j GraphRAG imports
from neo4j_graphrag.retrievers import VectorRetriever, Text2CypherRetriever, HybridRetriever
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.indexes import create_vector_index, upsert_vectors

# Alternative embeddings for local processing
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

class NuclearResearchGraphRAG:
    def __init__(self, use_local_embeddings=True):
        """
        Initialize Nuclear Research GraphRAG System
        
        Args:
            use_local_embeddings: If True, uses HuggingFace embeddings stored locally
                                If False, uses OpenAI embeddings (requires API calls)
        """
        print("🚀 Initializing Nuclear Research GraphRAG System...")
        
        # Configuration
        self.use_local_embeddings = use_local_embeddings
        self.embeddings_dir = Path("nuclear_embeddings")
        self.embeddings_file = self.embeddings_dir / "paper_embeddings.pkl"
        self.metadata_file = self.embeddings_dir / "embedding_metadata.json"
        
        # Create embeddings directory
        self.embeddings_dir.mkdir(exist_ok=True)
        
        # Neo4j connection (using your existing setup)
        # Neo4j connection from .env file
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_username = os.getenv("NEO4J_USERNAME")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")

        # Validate required environment variables
        if not all([self.neo4j_uri, self.neo4j_username, self.neo4j_password]):
            missing = [var for var, val in [("NEO4J_URI", self.neo4j_uri), 
                                           ("NEO4J_USERNAME", self.neo4j_username), 
                                           ("NEO4J_PASSWORD", self.neo4j_password)] if not val]
            raise ValueError(f"Missing required Neo4j credentials in .env file: {', '.join(missing)}")
        
        # Connect to Neo4j
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_username, self.neo4j_password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Connected to Neo4j at {self.neo4j_uri}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
        
        # Initialize embeddings model
        self._setup_embeddings()

        # Validate OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Missing OPENAI_API_KEY in .env file")
        
        # Initialize LLM
        self.llm = OpenAILLM(
            model_name="gpt-4",
            model_params={
                "max_tokens": 2000,
                "temperature": 0.2,
            }
        )
        
        # Vector index configuration
        self.vector_index_name = "nuclear_papers_vector_index"
        
        # Load or create embeddings
        self.paper_embeddings = self._load_or_create_embeddings()
        
        # Setup retrievers
        self._setup_retrievers()
        
        # Initialize GraphRAG with hybrid retriever
        self.graph_rag = GraphRAG(
            retriever=self.hybrid_retriever,
            llm=self.llm
        )
        
        print("✅ Nuclear Research GraphRAG System initialized!")
    
    def _setup_embeddings(self):
        """Setup embedding model (local or OpenAI)"""
        if self.use_local_embeddings:
            print("📥 Loading local HuggingFace embeddings model...")
            self.embedder = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu', 'trust_remote_code': False},
                encode_kwargs={'normalize_embeddings': True, 'batch_size': 32}
            )
            print("✅ Local embeddings model loaded")
        else:
            print("🌐 Using OpenAI embeddings...")
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("Missing OPENAI_API_KEY in .env file for OpenAI embeddings")
            self.embedder = OpenAIEmbeddings(model="text-embedding-3-large")
            print("✅ OpenAI embeddings configured")
    
    def _load_or_create_embeddings(self):
        """Load existing embeddings or create new ones"""
        
        # Check if embeddings exist
        if self.embeddings_file.exists() and self.metadata_file.exists():
            print("📁 Found existing embeddings...")
            
            # Load metadata to check last update
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            
            print(f"📊 Existing embeddings info:")
            print(f"   - Last updated: {metadata.get('last_updated', 'Unknown')}")
            print(f"   - Number of papers: {metadata.get('paper_count', 'Unknown')}")
            print(f"   - Embedding model: {metadata.get('model_name', 'Unknown')}")
            print(f"   - Dimensions: {metadata.get('dimensions', 'Unknown')}")
            
            # Ask user if they want to update
            choice = input("\n🔄 Do you want to update embeddings? (y/n/auto): ").strip().lower()
            
            if choice in ['y', 'yes']:
                return self._create_new_embeddings()
            elif choice in ['auto']:
                # Auto-update if database has more papers than embeddings
                current_paper_count = self._get_paper_count_from_db()
                if current_paper_count > metadata.get('paper_count', 0):
                    print(f"🔄 Auto-updating: Found {current_paper_count} papers vs {metadata.get('paper_count', 0)} embedded")
                    return self._create_new_embeddings()
                else:
                    print("✅ Using existing embeddings (no new papers detected)")
                    return self._load_embeddings()
            else:
                print("✅ Using existing embeddings")
                return self._load_embeddings()
        else:
            print("🆕 No existing embeddings found. Creating new embeddings...")
            return self._create_new_embeddings()
    
    def _get_paper_count_from_db(self):
        """Get current paper count from Neo4j"""
        with self.driver.session() as session:
            result = session.run("MATCH (p:Paper) RETURN count(p) as count")
            return result.single()["count"]
    
    def _load_embeddings(self):
        """Load embeddings from local file"""
        try:
            with open(self.embeddings_file, 'rb') as f:
                embeddings_data = pickle.load(f)
            print(f"✅ Loaded {len(embeddings_data)} paper embeddings from cache")
            return embeddings_data
        except Exception as e:
            print(f"❌ Error loading embeddings: {e}")
            print("🔄 Creating new embeddings...")
            return self._create_new_embeddings()
    
    def _create_new_embeddings(self):
        """Create new embeddings from Neo4j data"""
        print("🔄 Creating embeddings for all papers in Neo4j...")
        
        # Get all papers from Neo4j
        papers_data = self._fetch_papers_from_neo4j()
        
        if not papers_data:
            print("❌ No papers found in Neo4j database")
            return {}
        
        print(f"📚 Processing {len(papers_data)} papers...")
        
        embeddings_data = {}
        
        for i, paper in enumerate(papers_data, 1):
            try:
                paper_id = paper['paper_id']
                
                # Create comprehensive text for embedding
                # Similar to your rag_app.py approach
                text_content = self._create_paper_text_content(paper)
                
                # Generate embedding
                if self.use_local_embeddings:
                    # HuggingFace embeddings return list directly
                    embedding = self.embedder.embed_query(text_content)
                else:
                    # OpenAI embeddings
                    embedding = self.embedder.embed_query(text_content)
                
                embeddings_data[paper_id] = {
                    'embedding': embedding,
                    'title': paper.get('title', ''),
                    'abstract': paper.get('abstract', ''),
                    'authors': paper.get('authors', []),
                    'year': paper.get('year', ''),
                    'url': paper.get('url', ''),
                    'text_content': text_content[:500] + "..." if len(text_content) > 500 else text_content
                }
                
                if i % 10 == 0:
                    print(f"   ✅ Processed {i}/{len(papers_data)} papers")
                    
            except Exception as e:
                print(f"   ❌ Error processing paper {i}: {e}")
                continue
        
        # Save embeddings to file
        self._save_embeddings(embeddings_data, papers_data)
        
        print(f"✅ Created and saved {len(embeddings_data)} paper embeddings")
        return embeddings_data
    
    def _fetch_papers_from_neo4j(self):
        """Fetch all papers with their relationships from Neo4j"""
        query = """
        MATCH (p:Paper)
        OPTIONAL MATCH (a:Author)-[:WROTE]->(p)
        OPTIONAL MATCH (p)-[:PUBLISHED_AT]->(j:Journal)
        OPTIONAL MATCH (a)-[:AFFILIATED_WITH]->(af:Affiliation)
        
        WITH p, 
             collect(DISTINCT a.name) as authors,
             j.name as journal,
             collect(DISTINCT af.name) as affiliations
        
        RETURN elementId(p) as paper_id,
               p.title as title,
               p.abstract as abstract,
               p.year as year,
               p.url as url,
               authors,
               journal,
               affiliations
        """
        
        papers = []
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                papers.append({
                    'paper_id': record['paper_id'],
                    'title': record['title'] or '',
                    'abstract': record['abstract'] or '',
                    'year': record['year'] or '',
                    'url': record['url'] or '',
                    'authors': [a for a in record['authors'] if a],
                    'journal': record['journal'] or '',
                    'affiliations': [a for a in record['affiliations'] if a]
                })
        
        return papers
    
    def _create_paper_text_content(self, paper):
        """Create rich text content for embedding (similar to rag_app.py)"""
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        authors = ', '.join(paper.get('authors', []))
        journal = paper.get('journal', '')
        affiliations = ', '.join(paper.get('affiliations', []))
        year = paper.get('year', '')
        
        content = f"""
Nuclear Research Paper

Title: {title}

Authors: {authors}

Abstract: {abstract}

Publication Details:
- Journal/Conference: {journal}
- Year: {year}
- Affiliations: {affiliations}

Research Context: This nuclear science research by {authors} published in {journal} ({year}) focuses on {title.lower()}. The study involves work from {affiliations} and addresses key aspects of nuclear engineering, safety, and technology development.

Keywords: nuclear science, nuclear engineering, nuclear safety, nuclear technology, research collaboration, {title.lower()}, {journal.lower()}
        """.strip()
        
        return content
    
    def _save_embeddings(self, embeddings_data, papers_data):
        """Save embeddings and metadata to local files"""
        
        # Save embeddings
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump(embeddings_data, f)
        
        # Save metadata
        sample_embedding = next(iter(embeddings_data.values()))['embedding']
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'paper_count': len(embeddings_data),
            'model_name': 'sentence-transformers/all-MiniLM-L6-v2' if self.use_local_embeddings else 'text-embedding-3-large',
            'dimensions': len(sample_embedding),
            'use_local_embeddings': self.use_local_embeddings
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _setup_retrievers(self):
        """Setup different types of retrievers"""
        
        # Setup vector index in Neo4j
        self._setup_neo4j_vector_index()
        
        # 1. Vector Retriever - for semantic similarity
        self.vector_retriever = VectorRetriever(
            driver=self.driver,
            index_name=self.vector_index_name,
            embedder=self.embedder if not self.use_local_embeddings else self._wrap_huggingface_embedder()
        )
        
        # 2. Text2Cypher Retriever - for relationship queries
        nuclear_schema = self._get_nuclear_schema()
        
        self.text2cypher_retriever = Text2CypherRetriever(
            driver=self.driver,
            llm=self.llm,
            neo4j_schema=nuclear_schema
        )
        
        # 3. Hybrid Retriever - combines vector and fulltext search
        # First, we need to create a fulltext index for hybrid search
        self._create_fulltext_index()

        self.hybrid_retriever = HybridRetriever(
            driver=self.driver,
            vector_index_name=self.vector_index_name,
            fulltext_index_name="nuclear_papers_fulltext_index",
            embedder=self.embedder if not self.use_local_embeddings else self._wrap_huggingface_embedder(),
            return_properties=["title", "abstract", "url"]
        )

    def _create_fulltext_index(self):
        """Create fulltext index for hybrid search"""
        try:
            with self.driver.session() as session:
                # Check if fulltext index exists
                result = session.run("SHOW INDEXES")
                existing_indexes = [record["name"] for record in result]

                if "nuclear_papers_fulltext_index" not in existing_indexes:
                    # Create fulltext index on Paper nodes
                    session.run("""
                        CREATE FULLTEXT INDEX nuclear_papers_fulltext_index
                        FOR (p:Paper) ON EACH [p.title, p.abstract]
                    """)
                    print("✅ Fulltext index 'nuclear_papers_fulltext_index' created")
                else:
                    print("✅ Fulltext index 'nuclear_papers_fulltext_index' already exists")
                
        except Exception as e:
            print(f"❌ Error creating fulltext index: {e}")
    
    def _wrap_huggingface_embedder(self):
        """Wrap HuggingFace embedder to be compatible with Neo4j GraphRAG"""
        class HuggingFaceWrapper:
            def __init__(self, hf_embedder):
                self.hf_embedder = hf_embedder
            
            def embed_query(self, text):
                return self.hf_embedder.embed_query(text)
            
            def embed_documents(self, texts):
                return self.hf_embedder.embed_documents(texts)
        
        return HuggingFaceWrapper(self.embedder)
    
    def _setup_neo4j_vector_index(self):
        """Create vector index in Neo4j and upload embeddings"""
        
        # Determine dimensions
        if self.paper_embeddings:
            sample_embedding = next(iter(self.paper_embeddings.values()))['embedding']
            dimensions = len(sample_embedding)
        else:
            dimensions = 384 if self.use_local_embeddings else 3072
        
        try:
            # Create vector index
            create_vector_index(
                driver=self.driver,
                name=self.vector_index_name,
                label="Paper",
                embedding_property="abstract_embedding",
                dimensions=dimensions,
                similarity_fn="cosine",
            )
            print(f"✅ Vector index '{self.vector_index_name}' created/verified")
            
            # Upload embeddings to Neo4j
            self._upload_embeddings_to_neo4j()
            
        except Exception as e:
            print(f"❌ Vector index setup error: {e}")
    
    def _upload_embeddings_to_neo4j(self):
        """Upload local embeddings to Neo4j vector index"""
        if not self.paper_embeddings:
            return
        
        print("🔄 Uploading embeddings to Neo4j...")
        
        # Check which papers need embeddings
        with self.driver.session() as session:
            # Get papers without embeddings
            result = session.run("""
                MATCH (p:Paper) 
                WHERE p.abstract_embedding IS NULL
                RETURN elementId(p) as paper_id
            """)
            
            papers_needing_embeddings = [record['paper_id'] for record in result]
        
        if not papers_needing_embeddings:
            print("✅ All papers already have embeddings in Neo4j")
            return
        
        print(f"📤 Uploading embeddings for {len(papers_needing_embeddings)} papers...")
        
        # Upload embeddings
        for paper_id in papers_needing_embeddings:
            if paper_id in self.paper_embeddings:
                try:
                    embedding = self.paper_embeddings[paper_id]['embedding']
                    
                    # Update paper with embedding
                    with self.driver.session() as session:
                        session.run("""
                            MATCH (p:Paper) 
                            WHERE elementId(p) = $paper_id
                            SET p.abstract_embedding = $embedding
                        """, paper_id=paper_id, embedding=embedding)
                        
                except Exception as e:
                    print(f"❌ Error uploading embedding for paper {paper_id}: {e}")
        
        print("✅ Embeddings uploaded to Neo4j")
    
    def _get_nuclear_schema(self):
        """Get Neo4j schema optimized for nuclear research queries"""
        return """
        Nuclear Research Database Schema:
        
        Nodes:
        - Author: Represents research authors {name: string}
        - Paper: Represents research papers {title: string, abstract: string, year: integer, url: string}
        - Affiliation: Represents institutions {name: string}
        - Journal: Represents journals/conferences {name: string}
        
        Relationships:
        - (Author)-[:WROTE]->(Paper): Author wrote a paper
        - (Author)-[:AFFILIATED_WITH]->(Affiliation): Author affiliated with institution
        - (Paper)-[:PUBLISHED_AT]->(Journal): Paper published in journal
        - (Author)-[:COAUTHORED]->(Author): Authors collaborated on papers
        
        Example Queries for Nuclear Research:
        - "Who are the most prolific nuclear safety researchers?" 
          -> MATCH (a:Author)-[:WROTE]->(p:Paper) WHERE p.abstract CONTAINS 'nuclear safety' OR p.title CONTAINS 'nuclear safety' RETURN a.name, count(p) ORDER BY count(p) DESC LIMIT 10
        
        - "Which institutions collaborate most in nuclear research?"
          -> MATCH (a1:Author)-[:AFFILIATED_WITH]->(af1:Affiliation), (a2:Author)-[:AFFILIATED_WITH]->(af2:Affiliation), (a1)-[:COAUTHORED]->(a2) WHERE af1 <> af2 RETURN af1.name, af2.name, count(*) ORDER BY count(*) DESC LIMIT 10
        
        - "What are the recent nuclear energy research trends?"
          -> MATCH (p:Paper) WHERE p.year >= 2020 AND (p.abstract CONTAINS 'nuclear energy' OR p.title CONTAINS 'nuclear energy') RETURN p.title, p.year, p.abstract ORDER BY p.year DESC LIMIT 20
        
        - "Find collaboration networks in nuclear waste management"
          -> MATCH (a1:Author)-[:WROTE]->(p:Paper)<-[:WROTE]-(a2:Author) WHERE p.abstract CONTAINS 'nuclear waste' OR p.title CONTAINS 'nuclear waste' RETURN a1.name, a2.name, p.title
        """
    
    def query(self, user_question: str, retriever_type: str = "hybrid"):
        """
        Query the nuclear research knowledge graph
        
        Args:
            user_question: Natural language question
            retriever_type: "hybrid" (default), "vector", or "text2cypher"
        """
        print(f"\n🔍 Processing question: {user_question}")
        print(f"🔧 Using {retriever_type} retriever")
        
        # Select retriever
        retrievers = {
            "vector": self.vector_retriever,
            "text2cypher": self.text2cypher_retriever,
            "hybrid": self.hybrid_retriever  # BEST: automatically combines both
        }
        
        if retriever_type not in retrievers:
            return f"❌ Invalid retriever type. Choose: {', '.join(retrievers.keys())}"
        
        # Create GraphRAG with selected retriever
        selected_retriever = retrievers[retriever_type]
        if retriever_type in ["text2cypher", "hybrid"] and hasattr(selected_retriever, "generate_cypher_query"):
            print("🔬 Generated Cypher Query:")
            print(selected_retriever.generate_cypher_query(user_question))
        temp_rag = GraphRAG(retriever=selected_retriever, llm=self.llm)
        
        try:
            # Execute query
            response = temp_rag.search(
                query_text=user_question,)
            
            # Limit to top_k results if applicable
            top_k = 5
            if isinstance(response, list):
                response = response[:top_k]
            elif hasattr(response, 'documents'):
                response.documents = response.documents[:top_k]
            
            return {
                "question": user_question,
                "answer": response.answer,
                "retriever_used": retriever_type,
                "embedding_type": "Local HuggingFace" if self.use_local_embeddings else "OpenAI"
            }
            
        except Exception as e:
            return {
                "question": user_question,
                "answer": f"❌ Error: {e}",
                "retriever_used": retriever_type,
                "embedding_type": "Local HuggingFace" if self.use_local_embeddings else "OpenAI"
            }
    
    def demonstrate_hybrid_capabilities(self):
        """Demonstrate how hybrid retrieval handles different query types"""
        
        demo_queries = [
            {
                "query": "Who are the most prolific authors in nuclear safety research?",
                "expected_method": "Primarily Text2Cypher (relationship analysis)",
                "retriever": "hybrid"
            },
            {
                "query": "Find papers similar to reactor containment failure studies",
                "expected_method": "Primarily Vector Search (semantic similarity)",
                "retriever": "hybrid"
            },
            {
                "query": "What are emerging trends in nuclear waste management and which institutions lead this research?",
                "expected_method": "BOTH: Vector search for content + Graph traversal for institutional analysis",
                "retriever": "hybrid"
            }
        ]
        
        print("\n🎯 DEMONSTRATING HYBRID RETRIEVAL CAPABILITIES")
        print("=" * 60)
        
        for i, demo in enumerate(demo_queries, 1):
            print(f"\n{i}. Query: {demo['query']}")
            print(f"   Expected method: {demo['expected_method']}")
            print("-" * 40)
            
            result = self.query(demo['query'], demo['retriever'])
            print(f"   Answer: {result['answer']}")
            print(f"   Retriever: {result['retriever_used']}")
            print("=" * 60)
    
    def get_embedding_stats(self):
        """Get statistics about current embeddings"""
        if not self.paper_embeddings:
            return "No embeddings loaded"
        
        return {
            "total_papers": len(self.paper_embeddings),
            "embedding_dimensions": len(next(iter(self.paper_embeddings.values()))['embedding']),
            "model_type": "Local HuggingFace" if self.use_local_embeddings else "OpenAI",
            "storage_location": str(self.embeddings_file)
        }
    
    def close(self):
        """Close connections and cleanup"""
        if self.driver:
            self.driver.close()
        print("✅ GraphRAG system closed")


def main():
    """Main demonstration function"""
    print("🧬 Nuclear Research GraphRAG System")
    print("=" * 50)
    
    # Initialize with local embeddings (change to False for OpenAI)
    nuclear_rag = NuclearResearchGraphRAG(use_local_embeddings=True)
    
    try:
        # Show embedding stats
        stats = nuclear_rag.get_embedding_stats()
        print(f"\n📊 Embedding Statistics: {stats}")
        
        # Demonstrate hybrid capabilities
        nuclear_rag.demonstrate_hybrid_capabilities()
        
        # Interactive mode
        print(f"\n🗣️  INTERACTIVE MODE")
        print("Ask questions about your nuclear research data!")
        print("Type 'quit' to exit, 'demo' for more examples")
        print("-" * 50)
        
        while True:
            user_question = input(f"\n❓ Your question: ").strip()
            
            if user_question.lower() in ['quit', 'exit', 'q']:
                break
            elif user_question.lower() == 'demo':
                nuclear_rag.demonstrate_hybrid_capabilities()
                continue
            elif not user_question:
                continue
            
            # Use hybrid retriever by default (best option)
            result = nuclear_rag.query(user_question, "hybrid")
            
            print(f"\n💡 Answer: {result['answer']}")
            print(f"🔧 Method: {result['retriever_used']} retrieval")
            print(f"📊 Embeddings: {result['embedding_type']}")
            
    finally:
        nuclear_rag.close()


if __name__ == "__main__":
    main()