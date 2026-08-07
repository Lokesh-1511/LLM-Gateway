from routing_service import RoutingEngine

def test_routing_engine():
    engine = RoutingEngine()
    
    print("=== TEST 1: Initial State (Healthy) ===")
    health = engine.get_health_score(engine.PRIMARY_MODEL)
    print(f"Primary Health: {health}")
    print(f"Model for Engineering: {engine.select_model('Engineering')}")
    print(f"Model for Marketing: {engine.select_model('Marketing')}")
    assert engine.select_model('Engineering') == engine.PRIMARY_MODEL
    
    print("\n=== TEST 2: High Latency Simulation (>2000ms) ===")
    # Simulate 5 requests with 3000ms latency
    for _ in range(5):
        engine.record_metric(engine.PRIMARY_MODEL, 3000.0, 200)
    
    health = engine.get_health_score(engine.PRIMARY_MODEL)
    print(f"Primary Health: {health}")
    selected = engine.select_model('Engineering')
    print(f"Model for Engineering (Expected Fallback): {selected}")
    assert selected == engine.FALLBACK_MODEL
    
    print("\n=== TEST 3: High Error Rate Simulation (>20%) ===")
    # Reset engine
    engine = RoutingEngine()
    # Simulate 2 successful requests, and 1 failed request (33% error rate)
    engine.record_metric(engine.PRIMARY_MODEL, 500.0, 200)
    engine.record_metric(engine.PRIMARY_MODEL, 500.0, 200)
    engine.record_metric(engine.PRIMARY_MODEL, 500.0, 503)
    
    health = engine.get_health_score(engine.PRIMARY_MODEL)
    print(f"Primary Health: {health}")
    selected = engine.select_model('Engineering')
    print(f"Model for Engineering (Expected Fallback): {selected}")
    assert selected == engine.FALLBACK_MODEL
    
    print("\n✅ All routing engine unit tests passed!")

if __name__ == "__main__":
    test_routing_engine()
