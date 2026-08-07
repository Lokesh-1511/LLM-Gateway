import os
import httpx
import logging
import re
from database import SessionLocal
from models import RequestLog

logger = logging.getLogger("ShadowService")
logger.setLevel(logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
SHADOW_MODEL = "llama-3.1-8b-instant"
JUDGE_MODEL = "llama-3.1-8b-instant"

async def call_llm(prompt: str, model: str, system_prompt: str = None) -> str:
    if not GROQ_API_KEY:
        return None
        
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{GROQ_BASE_URL}/chat/completions"
    if url.endswith("/chat/completions/chat/completions"):
        url = url.replace("/chat/completions/chat/completions", "/chat/completions")
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Shadow service LLM call failed: {e}")
            return None

async def evaluate_migration_potential(prompt: str, primary_response: str, log_id: str, primary_cost: float):
    """
    Runs in the background to evaluate if a cheaper model could have answered this prompt just as well.
    """
    logger.info(f"Running shadow evaluation for log {log_id}...")
    
    # 1. Get Response B (Shadow)
    shadow_response = await call_llm(prompt, SHADOW_MODEL)
    if not shadow_response:
        logger.warning("Shadow evaluation aborted: shadow response failed.")
        return
        
    # 2. Judge Response A vs Response B
    judge_prompt = f"""
Compare Response A (Primary) and Response B (Shadow). 
On a scale of 0.0 to 1.0, is Response B an acceptable substitute for A? 
Return only the number.

Response A:
{primary_response}

Response B:
{shadow_response}
"""
    judge_score_str = await call_llm(
        judge_prompt, 
        JUDGE_MODEL, 
        "You are an impartial judge. Only output a float number between 0.0 and 1.0."
    )
    
    if not judge_score_str:
        logger.warning("Shadow evaluation aborted: judge response failed.")
        return
        
    try:
        # Extract the float from the judge response
        match = re.search(r"0\.\d+|1\.0|0|1", judge_score_str)
        if match:
            score = float(match.group(0))
        else:
            score = 0.0
    except ValueError:
        score = 0.0
        
    # Calculate potential savings if score is acceptable (e.g., >= 0.8)
    # Assume shadow model is approximately 1/5th the cost of the premium primary models.
    # If primary model was already the 8b, savings is 0.
    shadow_cost = primary_cost / 5.0
    potential_savings = (primary_cost - shadow_cost) if score >= 0.8 else 0.0
    
    # Ensure savings isn't negative if costs are weird
    if potential_savings < 0:
        potential_savings = 0.0
    
    # 3. Update Database
    db = SessionLocal()
    try:
        log_entry = db.query(RequestLog).filter(RequestLog.id == log_id).first()
        if log_entry:
            log_entry.shadow_score = score
            log_entry.potential_savings = potential_savings
            db.commit()
            logger.info(f"Shadow eval complete for {log_id}: Score {score}, Savings ${potential_savings:.6f}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update shadow score for {log_id}: {e}")
    finally:
        db.close()
