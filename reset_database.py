from rag.vector_store import client, collection


client.delete_collection(collection.name)
client.get_or_create_collection(name=collection.name)
print(f"Reset ChromaDB collection: {collection.name}")