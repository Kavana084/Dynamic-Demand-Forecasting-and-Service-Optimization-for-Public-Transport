import os
import sys

# Add backend to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from catboost import CatBoostRegressor

def test_model_loading():
    model_path = settings.model_path
    
    print("========================================")
    print("PHASE 1: TEST CATBOOST MODEL LOADING")
    print("========================================")
    print(f"Model path configured as: {model_path}")
    print(f"File exists: {os.path.exists(model_path)}")
    
    try:
        model = CatBoostRegressor()
        print("Attempting to load model...")
        model.load_model(model_path)
        print("SUCCESS: Model loaded successfully!")
        
        # Test a quick prediction
        # Let's provide a dummy feature array (we don't know exact size here, 
        # but if we just check model info that's good enough to prove it loaded)
        print(f"Tree count: {model.tree_count_}")
        print(f"Learning rate: {model.learning_rate_}")
        if hasattr(model, 'feature_names_'):
            print(f"Feature count: {len(model.feature_names_)}")
            
    except Exception as e:
        import traceback
        print("\nFAILURE: Failed to load CatBoost model.")
        print("Exception trace:")
        traceback.print_exc()

if __name__ == "__main__":
    test_model_loading()
