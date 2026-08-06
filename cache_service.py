import os
import json
import uuid
import logging
import chromadb
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from database import SessionLocal
from models import PromptCache

logger = logging.getLogger("SemanticCache")
logger.setLevel(logging.INFO)

class SemanticCache:
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        # Initialize SentenceTransformers model for embedding generation
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info(f"Initialized Semantic Cache (pgvector) with distance threshold {threshold}")

    def query_cache(self, prompt: str) -> dict | None:
        """
        Searches the Postgres cache for a semantically similar prompt.
        Returns the cached response if distance is below the threshold.
        """
        if not prompt.strip():
            return None
            
        embedding = self.model.encode(prompt).tolist()
        
        db = SessionLocal()
        try:
            # Query for the closest match using <=> (cosine distance)
            distance_query = db.query(PromptCache.embedding.cosine_distance(embedding).label('distance'), PromptCache.response_json).order_by('distance').limit(1).first()
            if distance_query and distance_query.distance < self.threshold:
                logger.info(f"✅ Cache Hit! Distance: {distance_query.distance:.4f}")
                return json.loads(distance_query.response_json)
        
            logger.info("❌ Cache Miss.")
            return None
        except Exception as e:
            logger.error(f"Error querying cache: {e}")
            return None
        finally:
            db.close()

    def add_to_cache(self, prompt: str, response: dict):
        """
        Adds a new prompt and its corresponding LLM response to the Postgres cache.
        """
        if not prompt.strip() or not response:
            return
            
        embedding = self.model.encode(prompt).tolist()
        
        db = SessionLocal()
        try:
            new_cache = PromptCache(
                prompt_text=prompt,
                embedding=embedding,
                response_json=json.dumps(response)
            )
            db.add(new_cache)
            db.commit()
            logger.info("💾 Added new interaction to Postgres Semantic Cache")
        except Exception as e:
            logger.error(f"Failed to add to cache: {e}")
            db.rollback()
        finally:
            db.close()

class PolicyGuardrail:
    def __init__(self, threshold: float = 0.35):
        self.threshold = threshold
        # Initialize chromadb persistent client
        self.chroma_client = chromadb.PersistentClient(path="./.chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(name="corporate_policies")
        logger.info(f"Initialized PolicyGuardrail with threshold {self.threshold}")
        
    def check_policy_violation(self, prompt: str) -> tuple[bool, str]:
        """
        Checks if the prompt violates any corporate policy.
        Returns (violation: bool, policy_description: str)
        """
        if not prompt.strip():
            return False, ""
            
        results = self.collection.query(
            query_texts=[prompt],
            n_results=1
        )
        
        if results and results["distances"] and results["distances"][0]:
            distance = results["distances"][0][0]
            if distance < self.threshold:
                policy_desc = results["documents"][0][0]
                logger.warning(f"🚨 Policy Violation Detected! Distance: {distance:.4f} Policy: {policy_desc}")
                return True, policy_desc
                
        return False, ""
