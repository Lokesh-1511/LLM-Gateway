import os
import json
import uuid
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("SemanticCache")
logger.setLevel(logging.INFO)

class SemanticCache:
    def __init__(self, db_path: str = "./.chroma_db", threshold: float = 0.1):
        self.threshold = threshold
        
        # Initialize Persistent Client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Use SentenceTransformers embedding function
        # This will automatically download all-MiniLM-L6-v2 on first run
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="prompt_cache",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"} # Use cosine distance
        )
        logger.info(f"Initialized Semantic Cache at {db_path} with distance threshold {threshold}")

    def query_cache(self, prompt: str) -> dict | None:
        """
        Searches the cache for a semantically similar prompt.
        Returns the cached response if distance is below the threshold.
        """
        if not prompt.strip():
            return None
            
        results = self.collection.query(
            query_texts=[prompt],
            n_results=1
        )
        
        # Check if we got any results
        if results['distances'] and len(results['distances'][0]) > 0:
            distance = results['distances'][0][0]
            if distance < self.threshold:
                logger.info(f"✅ Cache Hit! Distance: {distance:.4f}")
                # The response is stored in the metadata as a JSON string
                metadata = results['metadatas'][0][0]
                if metadata and 'response' in metadata:
                    return json.loads(metadata['response'])
        
        logger.info("❌ Cache Miss.")
        return None

    def add_to_cache(self, prompt: str, response: dict):
        """
        Adds a new prompt and its corresponding LLM response to the cache.
        """
        if not prompt.strip() or not response:
            return
            
        doc_id = str(uuid.uuid4())
        
        # We store the response as stringified JSON in the metadata
        self.collection.add(
            documents=[prompt],
            metadatas=[{"response": json.dumps(response)}],
            ids=[doc_id]
        )
        logger.info(f"💾 Added new interaction to Semantic Cache (ID: {doc_id})")
