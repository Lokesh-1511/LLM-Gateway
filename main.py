import time
import tiktoken
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

import copy
from security_service import StatefulPIIFirewall
from cache_service import SemanticCache, PolicyGuardrail
from database import log_request, SessionLocal
from routing_service import RoutingEngine
from compression_service import compress_prompt
from models import RequestLog, User, Chat, Message, Department, SystemConfig
from auth_service import get_current_user, get_admin_user, get_db, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from shadow_service import evaluate_migration_potential
from pydantic import BaseModel
from sqlalchemy import func

app = FastAPI(
    title="PromptOps Gateway",
    description="Enterprise LLM Gateway Pass-Through Proxy",
    version="1.0.0"
)

# Enable CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the PII Firewall once when the app starts
firewall = StatefulPIIFirewall()
# Initialize the Semantic Cache
cache = SemanticCache()
# Initialize the Policy Guardrail
guardrail = PolicyGuardrail()
# Initialize the Routing Engine
routing_engine = RoutingEngine()

@app.post("/api/auth/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "department_id": user.department_id, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

class SignupRequest(BaseModel):
    email: str
    password: str
    department_id: str

class DepartmentRequest(BaseModel):
    name: str

class ConfigRequest(BaseModel):
    key: str
    value: str

class AIModelRequest(BaseModel):
    display_name: str
    provider_name: str
    model_id_string: str
    api_key: str
    base_url: str
    is_active: bool = True

class DeptModelsRequest(BaseModel):
    model_ids: list[str]

@app.post("/api/departments")
async def create_department(req: DepartmentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    if db.query(Department).filter(Department.name == req.name).first():
        raise HTTPException(status_code=400, detail="Department already exists")
    new_dept = Department(name=req.name)
    db.add(new_dept)
    db.commit()
    return {"message": "Department created"}

@app.get("/api/departments")
async def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@app.post("/api/auth/signup")
async def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        department_id=req.department_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/api/users/invite")
async def invite_user(req: SignupRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        department_id=req.department_id,
        role="user"
    )
    db.add(new_user)
    db.commit()
    return {"message": "User invited successfully"}

@app.get("/api/config")
async def get_configs(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    configs = db.query(SystemConfig).all()
    # Mask values to prevent sending plaintext API keys on initial load
    return [{"key": c.key, "value": "********"} for c in configs]

@app.post("/api/config")
async def set_config(req: ConfigRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    config = db.query(SystemConfig).filter(SystemConfig.key == req.key).first()
    if config:
        config.value = req.value
    else:
        new_config = SystemConfig(key=req.key, value=req.value)
        db.add(new_config)
    db.commit()
    return {"message": "Config updated"}

@app.get("/api/models")
async def get_all_models(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import AIModel
    models = db.query(AIModel).all()
    # Mask API keys
    result = []
    for m in models:
        result.append({
            "id": m.id,
            "display_name": m.display_name,
            "provider_name": m.provider_name,
            "model_id_string": m.model_id_string,
            "api_key": "********",
            "base_url": m.base_url,
            "is_active": m.is_active
        })
    return result

@app.post("/api/models")
async def create_model(req: AIModelRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import AIModel
    new_model = AIModel(
        display_name=req.display_name,
        provider_name=req.provider_name,
        model_id_string=req.model_id_string,
        api_key=req.api_key,
        base_url=req.base_url,
        is_active=req.is_active
    )
    db.add(new_model)
    db.commit()
    return {"message": "Model registered successfully"}

@app.get("/api/departments/{dept_id}/models")
async def get_department_models(dept_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import DepartmentModelAccess
    mappings = db.query(DepartmentModelAccess).filter(DepartmentModelAccess.department_id == dept_id).all()
    return [m.aimodel_id for m in mappings]

@app.post("/api/departments/{dept_id}/models")
async def set_department_models(dept_id: str, req: DeptModelsRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    from models import DepartmentModelAccess
    # Delete existing
    db.query(DepartmentModelAccess).filter(DepartmentModelAccess.department_id == dept_id).delete()
    # Add new
    for model_id in req.model_ids:
        db.add(DepartmentModelAccess(department_id=dept_id, aimodel_id=model_id))
    db.commit()
    return {"message": "Department models updated"}

@app.get("/api/models/available")
async def get_available_models(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import AIModel, DepartmentModelAccess
    if not current_user.department_id:
        return []
    
    mappings = db.query(DepartmentModelAccess).filter(DepartmentModelAccess.department_id == current_user.department_id).all()
    allowed_model_ids = [m.aimodel_id for m in mappings]
    
    models = db.query(AIModel).filter(AIModel.id.in_(allowed_model_ids), AIModel.is_active == True).all()
    return [{"id": m.id, "display_name": m.display_name, "provider_name": m.provider_name, "model_id_string": m.model_id_string} for m in models]

@app.get("/api/chats")
async def get_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at.desc()).all()

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()

async def log_and_evaluate_background(
    full_prompt: str,
    any_pii_detected: bool,
    token_count: int,
    latency_ms: float,
    estimated_cost: float,
    current_user_id: str,
    current_user_dept: str,
    was_failover_used: bool,
    provider_used: str,
    masked_response_content: str,
    original_token_count: int = 0,
    compressed_token_count: int = 0,
    tokens_saved_by_compression: int = 0,
    model_id: str = None
):
    log_id = await run_in_threadpool(
        log_request,
        original_prompt=full_prompt,
        was_pii_detected=any_pii_detected,
        was_cache_hit=False,
        token_count=token_count,
        latency_ms=latency_ms,
        estimated_cost=estimated_cost,
        user_id=current_user_id,
        department_id=current_user_dept,
        was_failover_used=was_failover_used,
        provider=provider_used,
        original_token_count=original_token_count,
        compressed_token_count=compressed_token_count,
        tokens_saved_by_compression=tokens_saved_by_compression,
        model_id=model_id
    )
    
    if log_id:
        await evaluate_migration_potential(
            prompt=full_prompt,
            primary_response=masked_response_content,
            log_id=log_id,
            primary_cost=estimated_cost
        )


async def generate_chat_title(chat_id: str, first_message: str):
    """
    Background task to generate a short title for a new chat based on the first message.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    
    prompt = f"Generate a highly concise, 3-word title summarizing this message. Do NOT wrap it in quotes. Only return the 3 words: {first_message}"
    
    try:
        response = await forward_to_groq({
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        })
        
        title = response["choices"][0]["message"]["content"].strip(' "')
        
        def update_chat_title_in_db():
            db = SessionLocal()
            try:
                chat = db.query(Chat).filter(Chat.id == chat_id).first()
                if chat:
                    chat.title = title
                    db.commit()
                    logger.info(f"✨ Generated new chat title: '{title}' for chat {chat_id}")
            finally:
                db.close()
                
        await run_in_threadpool(update_chat_title_in_db)
            
    except Exception as e:
        logger.error(f"Failed to generate chat title: {e}")



@app.post("/v1/chat/completions")
async def proxy_chat_completions(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Intercepts POST requests to /v1/chat/completions and proxies them to the target LLM API.
    """
    try:
        # Parse the incoming JSON body
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    chat_id = request.headers.get("X-Chat-Id")
    target_model_id = request.headers.get("X-Model-Target")
    
    if not target_model_id:
        raise HTTPException(status_code=400, detail="X-Model-Target header is required")
        
    from models import AIModel, DepartmentModelAccess
    
    # Check access control
    access = db.query(DepartmentModelAccess).filter(
        DepartmentModelAccess.department_id == current_user.department_id,
        DepartmentModelAccess.aimodel_id == target_model_id
    ).first()
    
    if not access:
        raise HTTPException(status_code=403, detail="Forbidden: Your department does not have access to this model.")
        
    target_model = db.query(AIModel).filter(AIModel.id == target_model_id).first()
    if not target_model or not target_model.is_active:
        raise HTTPException(status_code=400, detail="Requested model is inactive or does not exist.")
    
    is_new_chat = False
    if not chat_id or chat_id == "null":
        new_chat = Chat(user_id=current_user.id, title="New Chat")
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        chat_id = new_chat.id
        is_new_chat = True
        
    user_message = body.get("messages", [])[-1].get("content", "") if body.get("messages") else ""
    if user_message:
        db.add(Message(chat_id=chat_id, role="user", content=user_message))
        db.commit()
        
        if is_new_chat:
            background_tasks.add_task(generate_chat_title, chat_id, user_message)

        
    start_time = time.time()
    
    # --- PHASE 0.5: PROMPT COMPRESSION ---
    original_token_count = 0
    compressed_token_count = 0
    
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    orig_tokens = len(encoding.encode(message["content"]))
                    original_token_count += orig_tokens
                except Exception:
                    pass
                
                compressed_content, _ = await run_in_threadpool(compress_prompt, message["content"])
                message["content"] = compressed_content
                
                try:
                    comp_tokens = len(encoding.encode(compressed_content))
                    compressed_token_count += comp_tokens
                except Exception:
                    pass
                
                import logging
                logger = logging.getLogger("uvicorn")
                logger.info("--- PROMPT COMPRESSION ---")
                logger.info(f"Compressed To: '{compressed_content}'")
                logger.info(f"Tokens Saved: {orig_tokens - comp_tokens if 'orig_tokens' in locals() and 'comp_tokens' in locals() else 'Unknown'}")
                    
    tokens_saved_by_compression = max(0, original_token_count - compressed_token_count)
    
    # Re-extract the user message if it was modified
    user_message = body.get("messages", [])[-1].get("content", "") if body.get("messages") else ""
    # -------------------------------------

    # --- PHASE 1: POLICY GUARDRAIL ---
    if user_message:
        violation, policy_desc = await run_in_threadpool(guardrail.check_policy_violation, user_message)
        if violation:
            await run_in_threadpool(
                log_request,
                original_prompt=user_message,
                was_pii_detected=False,
                was_cache_hit=False,
                token_count=0,
                latency_ms=(time.time() - start_time) * 1000,
                estimated_cost=0.0,
                user_id=current_user.id,
                department_id=current_user.department_id,
                was_blocked_by_policy=True,
                policy_violation_reason=policy_desc
            )
            raise HTTPException(status_code=403, detail=f"Policy Violation: {policy_desc}")
    # ---------------------------------
    
    # --- PHASE 2: SECURITY MODULE ---
    # Intercept the messages and scrub PII before forwarding
    full_prompt = ""
    any_pii_detected = False
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                original_content = message["content"]
                # Pass the user's prompt through the firewall
                scrubbed_content, pii_detected = await run_in_threadpool(firewall.mask_pii, original_content, str(chat_id), db)
                message["content"] = scrubbed_content
                any_pii_detected = any_pii_detected or pii_detected
                # Concatenate all messages into a single prompt string for caching
                full_prompt += scrubbed_content + "\n"
    
    full_prompt = full_prompt.strip()
    # ---------------------------------
    
    # --- PHASE 3: SEMANTIC CACHE ---
    # Check if we have a semantically similar prompt already cached
    cached_response = await run_in_threadpool(cache.query_cache, full_prompt)
    if cached_response:
        latency_ms = (time.time() - start_time) * 1000
        
        # Estimate tokens since we bypassed Groq
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            cached_content = cached_response["choices"][0]["message"]["content"]
            token_count = len(encoding.encode(full_prompt)) + len(encoding.encode(cached_content))
        except Exception:
            token_count = 0
            
        # Log to Database
        background_tasks.add_task(
            log_request,
            original_prompt=full_prompt,
            was_pii_detected=any_pii_detected,
            was_cache_hit=True,
            token_count=token_count,
            latency_ms=latency_ms,
            estimated_cost=0.0, # Cache hits cost us nothing
            user_id=current_user.id,
            department_id=current_user.department_id,
            was_failover_used=False,
            provider="cache",
            original_token_count=original_token_count,
            compressed_token_count=compressed_token_count,
            tokens_saved_by_compression=tokens_saved_by_compression
        )
        
        # Unmask the cached response before returning
        if "choices" in cached_response:
            for choice in cached_response["choices"]:
                if "message" in choice and "content" in choice["message"] and isinstance(choice["message"]["content"], str):
                    choice["message"]["content"] = firewall.unmask_response(choice["message"]["content"], str(chat_id), db)
                    
        return cached_response
    # ---------------------------------
    
    # --- PHASE 4: DYNAMIC FORWARDING ---
    from proxy_service import forward_to_provider
    provider_used = target_model.provider_name
    
    try:
        response = await forward_to_provider(
            request_body=body, 
            api_key=target_model.api_key, 
            base_url=target_model.base_url, 
            target_model=target_model.model_id_string
        )
        latency_ms = (time.time() - start_time) * 1000
    except HTTPException as e:
        raise e
    # ---------------------------------
    
    # Extract total tokens from Groq response
    token_count = 0
    if "usage" in response and "total_tokens" in response["usage"]:
        token_count = response["usage"]["total_tokens"]
        
    estimated_cost = token_count * 0.000002
    
    masked_response_content = ""
    if "choices" in response:
        for choice in response["choices"]:
            if "message" in choice and "content" in choice["message"] and isinstance(choice["message"]["content"], str):
                masked_response_content += choice["message"]["content"]

    # --- PHASE 4 & 5: ADD TO DB & RUN SHADOW EVAL ---
    background_tasks.add_task(
        log_and_evaluate_background,
        full_prompt=full_prompt,
        any_pii_detected=any_pii_detected,
        token_count=token_count,
        latency_ms=latency_ms,
        estimated_cost=estimated_cost,
        current_user_id=current_user.id,
        current_user_dept=current_user.department_id,
        was_failover_used=False,
        provider_used=provider_used,
        masked_response_content=masked_response_content,
        original_token_count=original_token_count,
        compressed_token_count=compressed_token_count,
        tokens_saved_by_compression=tokens_saved_by_compression,
        model_id=target_model.id
    )
    
    # --- PHASE 3: ADD TO CACHE ---
    # Save the sanitized prompt and the response to the cache in the background
    # Deepcopy to ensure the cache stores the masked version
    background_tasks.add_task(cache.add_to_cache, full_prompt, copy.deepcopy(response))
    # ---------------------------------
    
    # --- PHASE 3: UNMASK PII ---
    # Unmask the LLM response before sending it back to the client
    unmasked_response_content = ""
    if "choices" in response:
        for choice in response["choices"]:
            if "message" in choice and "content" in choice["message"] and isinstance(choice["message"]["content"], str):
                choice["message"]["content"] = firewall.unmask_response(choice["message"]["content"], str(chat_id), db)
                unmasked_response_content += choice["message"]["content"]
    # ---------------------------------
    
    # Save the assistant's response to the database
    if unmasked_response_content:
        db.add(Message(chat_id=chat_id, role="assistant", content=unmasked_response_content))
        db.commit()
    
    # Add chat_id to the response headers so the frontend can update its URL/state
    headers = {"X-Chat-Id": str(chat_id)}
    from fastapi.responses import JSONResponse
    return JSONResponse(content=response, headers=headers)
    


@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """
    Returns aggregated analytics from the database.
    """
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        from models import AIModel
        
        # Base metrics
        total_requests = db.query(RequestLog).count()
        total_pii_blocked = db.query(RequestLog).filter(RequestLog.was_pii_detected == True).count()
        total_policy_violations = db.query(RequestLog).filter(RequestLog.was_blocked_by_policy == True).count()
        total_cache_hits = db.query(RequestLog).filter(RequestLog.was_cache_hit == True).count()
        
        cache_savings = db.query(func.sum(RequestLog.token_count)).filter(RequestLog.was_cache_hit == True).scalar() or 0
        compression_tokens_saved = db.query(func.sum(RequestLog.tokens_saved_by_compression)).scalar() or 0
        money_saved = (cache_savings + compression_tokens_saved) * 0.000002
        cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        total_original_tokens = db.query(func.sum(RequestLog.original_token_count)).scalar() or 0
        savings_percentage = (compression_tokens_saved / total_original_tokens * 100) if total_original_tokens > 0 else 0.0

        # Model Distribution & Performance Metrics
        models = db.query(AIModel).all()
        model_distribution = []
        performance_metrics = []
        
        for m in models:
            req_count = db.query(RequestLog).filter(RequestLog.model_id == m.id).count()
            tokens = db.query(func.sum(RequestLog.token_count)).filter(RequestLog.model_id == m.id).scalar() or 0
            avg_latency = db.query(func.avg(RequestLog.latency_ms)).filter(RequestLog.model_id == m.id).scalar() or 0.0
            
            if req_count > 0:
                model_distribution.append({
                    "name": m.display_name,
                    "requests": req_count,
                    "tokens": tokens
                })
                performance_metrics.append({
                    "name": m.display_name,
                    "avg_latency": avg_latency,
                    "error_rate": 0.0 # Placeholder since we don't log HTTP errors explicitly yet
                })

        # Department Spend
        departments = db.query(Department).all()
        department_spend = []
        for dept in departments:
            cost = db.query(func.sum(RequestLog.estimated_cost)).filter(RequestLog.department_id == dept.id).scalar() or 0.0
            tokens = db.query(func.sum(RequestLog.token_count)).filter(RequestLog.department_id == dept.id).scalar() or 0
            department_spend.append({
                "department": dept.name,
                "cost": cost,
                "tokens": tokens
            })

        # Time-Series Data (Last 24h)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_logs = db.query(RequestLog).filter(RequestLog.timestamp >= twenty_four_hours_ago).all()
        
        # Bucket by hour in python to be DB agnostic
        ts_buckets = {}
        for h in range(24):
            dt = twenty_four_hours_ago + timedelta(hours=h)
            bucket_key = dt.strftime("%Y-%m-%d %H:00")
            ts_buckets[bucket_key] = {"time": bucket_key, "requests": 0, "avg_latency": 0.0}
            
        latency_sums = {k: 0.0 for k in ts_buckets.keys()}
        
        for log in recent_logs:
            if not log.timestamp: continue
            bucket_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            if bucket_key in ts_buckets:
                ts_buckets[bucket_key]["requests"] += 1
                latency_sums[bucket_key] += (log.latency_ms or 0)
                
        time_series_data = []
        for k, v in ts_buckets.items():
            if v["requests"] > 0:
                v["avg_latency"] = latency_sums[k] / v["requests"]
            time_series_data.append(v)
            
        time_series_data.sort(key=lambda x: x["time"])

        return {
            "total_requests": total_requests,
            "total_pii_blocked": total_pii_blocked,
            "total_policy_violations": total_policy_violations,
            "cache_hit_rate": cache_hit_rate,
            "money_saved": money_saved,
            "savings_percentage": savings_percentage,
            "model_distribution": model_distribution,
            "performance_metrics": performance_metrics,
            "department_spend": department_spend,
            "time_series_data": time_series_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# Trigger reload
