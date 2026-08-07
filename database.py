import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from models import Base, RequestLog

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger("Database")
logger.setLevel(logging.INFO)

# Create engine and session
# Check if DATABASE_URL is set, otherwise use a local sqlite fallback for safety or raise an error
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found in .env. Falling back to local sqlite database (llm_logs.db).")
    DATABASE_URL = "sqlite:///./llm_logs.db"

# We use check_same_thread=False for SQLite if it's the fallback
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Try to connect and create tables, if it fails, fallback to sqlite
try:
    if engine.dialect.name == 'postgresql':
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized and tables verified.")
except OperationalError as e:
    logger.error(f"Failed to connect to primary database: {e}")
    logger.warning("Falling back to local sqlite database (llm_logs.db).")
    DATABASE_URL = "sqlite:///./llm_logs.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Local SQLite database initialized and tables verified.")

def log_request(original_prompt: str, was_pii_detected: bool, was_cache_hit: bool, token_count: int, latency_ms: float, estimated_cost: float, user_id: str = None, department_id: str = None, was_failover_used: bool = False, provider: str = ""):
    """
    Saves the request details to the database. This function is synchronous and should be called via BackgroundTasks.
    """
    db = SessionLocal()
    try:
        new_log = RequestLog(
            original_prompt=original_prompt,
            was_pii_detected=was_pii_detected,
            was_cache_hit=was_cache_hit,
            token_count=token_count,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            was_failover_used=was_failover_used,
            provider=provider,
            user_id=user_id,
            department_id=department_id
        )
        db.add(new_log)
        db.commit()
        logger.info(f"💾 Logged request to DB (Cache Hit: {was_cache_hit}, Tokens: {token_count}, Latency: {latency_ms:.2f}ms)")
    except Exception as e:
        logger.error(f"Failed to log request to DB: {e}")
        db.rollback()
    finally:
        db.close()
