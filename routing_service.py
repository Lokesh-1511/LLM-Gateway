import threading
from collections import deque
from typing import Dict, Any

class RoutingEngine:
    def __init__(self):
        # We define a primary and fallback model for our gateway
        self.PRIMARY_MODEL = "llama-3.1-8b-instant"
        self.FALLBACK_MODEL = "llama-3.3-70b-versatile"
        
        # Sliding window for latency and status codes
        # Format: deque of tuples (latency_ms, status_code)
        self.history = {
            self.PRIMARY_MODEL: deque(maxlen=10),
            self.FALLBACK_MODEL: deque(maxlen=10)
        }
        self.lock = threading.Lock()

    def record_metric(self, model: str, latency_ms: float, status_code: int):
        """Record the latency and status code for a model invocation."""
        with self.lock:
            if model not in self.history:
                self.history[model] = deque(maxlen=10)
            self.history[model].append((latency_ms, status_code))

    def get_health_score(self, provider: str) -> Dict[str, Any]:
        """Calculates health score based on average latency and error percentage."""
        with self.lock:
            records = list(self.history.get(provider, []))
            
        if not records:
            return {"avg_latency": 0.0, "error_rate": 0.0, "healthy": True}
            
        total_latency = sum(r[0] for r in records)
        errors = sum(1 for r in records if r[1] >= 400)
        
        avg_latency = total_latency / len(records)
        error_rate = (errors / len(records)) * 100 # percentage
        
        healthy = True
        # If average latency > 2s (2000ms) or errors > 20%, consider unhealthy
        if avg_latency > 2000 or error_rate > 20.0:
            healthy = False
            
        return {
            "avg_latency": avg_latency,
            "error_rate": error_rate,
            "healthy": healthy
        }

    def select_model(self, department: str) -> str:
        """
        Routing logic based on department and health scores.
        """
        primary_health = self.get_health_score(self.PRIMARY_MODEL)
        
        # Priority departments
        if department in ["Engineering", "Finance"]:
            # Prioritize primary unless health is low
            if not primary_health["healthy"]:
                return self.FALLBACK_MODEL
            return self.PRIMARY_MODEL
        else:
            # Other departments can use primary if healthy, otherwise fallback
            # (Can also be configured to default to fallback if cost is an issue)
            if not primary_health["healthy"]:
                return self.FALLBACK_MODEL
            return self.PRIMARY_MODEL
