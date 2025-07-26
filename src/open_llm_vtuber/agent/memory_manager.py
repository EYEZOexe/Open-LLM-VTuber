import chromadb
from chromadb.config import Settings
import uuid
import json
import os
from loguru import logger

class ChromaMemoryManager:
    def __init__(self, db_path="./memories/chroma.db", collection_name="vtuber_memories"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
        logger.info(f"Loaded {self.collection.count()} memories from ChromaDB.")
        if self.collection.count() == 0:
            self.import_json(path="./memories/memoryinit.json")

    def add_memory(self, document, metadata=None, memory_id=None, role=None):
        if memory_id is None:
            memory_id = str(uuid.uuid4())
        # Always provide a non-empty metadata dict as required by ChromaDB
        if not metadata or not isinstance(metadata, dict) or len(metadata) == 0:
            metadata = {"source": "memory"}
        self.collection.upsert([memory_id], documents=[document], metadatas=[metadata])
        return memory_id

    def query_memories(self, query, n_results=5):
        results = self.collection.query(query_texts=[query], n_results=n_results)
        return results

    def import_json(self, path="./memories/memoryinit.json"):
        if not os.path.exists(path):
            logger.warning(f"No memoryinit.json found at {path}")
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for memory in data.get("memories", []):
            self.add_memory(memory["document"], memory["metadata"], memory["id"])
        logger.info(f"Imported {len(data.get('memories', []))} memories from {path}")

    def export_json(self, path="./memories/memories.json"):
        memories = self.collection.get()
        data = {"memories": []}
        for i in range(len(memories["ids"])):
            data["memories"].append({
                "id": memories["ids"][i],
                "document": memories["documents"][i],
                "metadata": memories["metadatas"][i],
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(data['memories'])} memories to {path}")

    def clear_short_term(self):
        short_term = self.collection.get(where={"type": "short-term"})
        for id in short_term["ids"]:
            self.collection.delete(id)

    def wipe(self):
        self.chroma_client.reset()
        self.collection = self.chroma_client.get_or_create_collection(name="vtuber_memories")

    def get_memories(self, query=None, n_results=30):
        if not query:
            memories = self.collection.get()
            return [{
                "id": memories["ids"][i],
                "document": memories["documents"][i],
            } for i in range(len(memories["ids"]))]
        else:
            memories = self.collection.query(query_texts=[query], n_results=n_results)
            return [{
                "id": memories["ids"][0][i],
                "document": memories["documents"][0][i],
                "distance": memories["distances"][0][i],
            } for i in range(len(memories["ids"][0]))]

    def memory_exists(self, document, role=None):
        # Check for an exact match in ChromaDB for the given document (ignore role)
        results = self.collection.get()
        docs = results.get("documents", [])
        for doc in docs:
            if doc.strip() == document.strip():
                return True
        return False
