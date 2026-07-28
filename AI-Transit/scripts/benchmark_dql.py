import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from backend.app.services.dql_bus_allocator import DQLAgent, train_model

def run_benchmark():
    print("=== Training DQL Agent for Benchmarking ===")
    agent = DQLAgent()
    model_path = os.path.join(base_dir, "backend", "models", "benchmark_dql_model.npz")
    
    metrics = train_model(agent, episodes=3000, model_path=model_path)
    print("\n--- Training Metrics ---")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
        
    print("\n=== Running Evaluation Scenarios ===")
    
    agent.load_model(model_path)
    
    scenarios = [
        {"name": "Scenario A: Low Demand", "demand": 20},
        {"name": "Scenario B: Medium Demand", "demand": 80},
        {"name": "Scenario C: High Demand", "demand": 150}
    ]
    
    for s in scenarios:
        state_dict = {
            "predicted_demand": s["demand"],
            "hour": 18,
            "weather": "clear",
            "traffic": "medium",
            "occupancy_rate": 0.5,
            "available_buses": 10
        }
        
        result = agent.predict_optimal_bus_count(state_dict)
        print(f"\n{s['name']}")
        print(f"Demand: {s['demand']}")
        print(f"Recommended buses: {result['recommended_buses']}")
        print(f"Occupancy prediction: {result['occupancy_prediction']}")
        print(f"Confidence: {result['confidence']}")

if __name__ == "__main__":
    run_benchmark()
