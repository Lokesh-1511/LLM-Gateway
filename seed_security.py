import chromadb
from database import SessionLocal
from models import Policy

policies = [
    {
        "id": "policy-1",
        "category": "Data Security",
        "description": "No sharing internal source code or proprietary algorithms."
    },
    {
        "id": "policy-2",
        "category": "HR & Privacy",
        "description": "No salary privacy violations or discussing compensation."
    },
    {
        "id": "policy-3",
        "category": "Time Theft",
        "description": "No personal travel planning or non-work activities on corporate time."
    },
    {
        "id": "policy-4",
        "category": "IT Security",
        "description": "No usage or discussion of unapproved third-party software."
    },
    {
        "id": "policy-5",
        "category": "Confidentiality",
        "description": "No sharing of unannounced product roadmaps or upcoming features."
    }
]

def seed_policies():
    print("Seeding Policy Guardrails...")
    
    # 1. Seed ChromaDB for vector similarity search
    client = chromadb.PersistentClient(path="./.chroma_db")
    collection = client.get_or_create_collection(name="corporate_policies")
    
    ids = [p["id"] for p in policies]
    documents = [p["description"] for p in policies]
    metadatas = [{"category": p["category"]} for p in policies]
    
    # Upsert avoids duplicates if run multiple times
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("Seeded ChromaDB corporate_policies collection.")

    # 2. Seed SQLite database for relational tracking (optional but good for dashboard)
    db = SessionLocal()
    try:
        for p in policies:
            existing = db.query(Policy).filter(Policy.description == p["description"]).first()
            if not existing:
                new_policy = Policy(category=p["category"], description=p["description"])
                db.add(new_policy)
        db.commit()
        print("Seeded SQLite Policy table.")
    except Exception as e:
        print(f"Failed to seed SQLite: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_policies()
