import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Create ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")

# Create collection
collection = client.get_or_create_collection(
    name="medical_reports"
)

# Sample chunks
chunks = [
    "Fasting blood sugar: 103 mg/dL",
    "Post prandial blood sugar: 136 mg/dL",
    "Total cholesterol: 220 mg/dL",
    "Hemoglobin: 12.4 g/dL"
]

# Generate embeddings
embeddings = model.encode(chunks).tolist()

# Store in ChromaDB
collection.add(
    documents=chunks,
    embeddings=embeddings,
    ids=[f"chunk_{i}" for i in range(len(chunks))]
)

print("Chunks successfully stored in ChromaDB!")

# Check number of stored documents
print("Number of documents:", collection.count())

query = "What is the fasting blood sugar?"

# Convert query into embedding
query_embedding = model.encode([query]).tolist()[0]

# Search ChromaDB
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=2
)

print("\nQuery:")
print(query)

print("\nRetrieved chunks:")

for document in results["documents"][0]:
    print(document)