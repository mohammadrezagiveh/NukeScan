from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Credentials from .env
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAI_KEY]):
    raise ValueError("Missing credentials in .env file")

os.environ["OPENAI_API_KEY"] = OPENAI_KEY  # Required for OpenAILLM

# Debuggable retriever class
class DebuggableText2CypherRetriever(Text2CypherRetriever):
    def generate_cypher(self, user_question: str) -> str:
        prompt = f"""
You are a Cypher expert. Given the schema:

Nodes:
- Author(name: string)
- Paper(title: string, abstract: string, year: int, url: string)
- Affiliation(name: string)
- Journal(name: string)

Relationships:
- (Author)-[:WROTE]->(Paper)
- (Author)-[:AFFILIATED_WITH]->(Affiliation)
- (Paper)-[:PUBLISHED_AT]->(Journal)

Write a Cypher query to answer:
"{user_question}"

Only return the Cypher query.
"""
        response = self.llm.invoke(prompt)
        cypher = response.content.strip()  # ✅ confirmed correct attribute

        print("🔬 Generated Cypher Query:\n")
        print(cypher)
        return cypher

# Initialize LLM
llm = OpenAILLM(
    model_name="gpt-4",
    model_params={"temperature": 0.2}
)

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Create retriever
retriever = DebuggableText2CypherRetriever(
    driver=driver,
    llm=llm,
    neo4j_schema=""  # prompt is inlined
)

# Ask your question
question = "Who are the most prolific authors in nuclear safety research?"
cypher_query = retriever.generate_cypher(question)

# Run the Cypher query
print("\n📡 Running query in Neo4j...")
with driver.session() as session:
    result = session.run(cypher_query)
    rows = result.data()
    for row in rows:
        print(row)

driver.close()