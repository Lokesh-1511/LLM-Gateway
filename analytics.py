import os
from sqlalchemy import func
from database import SessionLocal, RequestLog

def generate_analytics():
    db = SessionLocal()
    try:
        # 1. Total requests handled
        total_requests = db.query(RequestLog).count()

        # 2. Total PII threats blocked
        pii_blocked = db.query(RequestLog).filter(RequestLog.was_pii_detected == True).count()

        # 3. Total 'Money Saved' (Sum of token_count where cache_hit is True * 0.000002)
        # Using func.sum to let the database do the calculation
        tokens_saved = db.query(func.sum(RequestLog.token_count)).filter(RequestLog.was_cache_hit == True).scalar()
        if tokens_saved is None:
            tokens_saved = 0
            
        money_saved = tokens_saved * 0.000002

        print("="*40)
        print("PromptOps Analytics Summary")
        print("="*40)
        print(f"Total Requests Handled  : {total_requests}")
        print(f"Total PII Threats Blocked: {pii_blocked}")
        print(f"Tokens Saved via Cache  : {tokens_saved:,}")
        print(f"Estimated Money Saved   : ${money_saved:.6f}")
        print("="*40)
        
    except Exception as e:
        print(f"Failed to fetch analytics: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_analytics()
