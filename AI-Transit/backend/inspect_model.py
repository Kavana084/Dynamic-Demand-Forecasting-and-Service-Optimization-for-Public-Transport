"""
Inspect the CatBoost model to see what features it uses
"""
import joblib
import os

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'outputs', 'model.pkl')

print(f"Loading model from: {model_path}")

try:
    data = joblib.load(model_path)
    
    if isinstance(data, dict):
        print("\n=== Model is a dictionary ===")
        print(f"Keys: {list(data.keys())}")
        
        if 'model' in data:
            model = data['model']
            print(f"\nModel type: {type(model)}")
            print(f"Model class: {model.__class__.__name__}")
            
            if hasattr(model, 'feature_names_'):
                print(f"\nFeature names: {model.feature_names_}")
            else:
                print("\nModel does not have feature_names_ attribute")
                
            if hasattr(model, 'tree_count_'):
                print(f"Tree count: {model.tree_count_}")
        
        if 'encoders' in data:
            print(f"\nEncoders: {list(data['encoders'].keys())}")
            for key, encoder in data['encoders'].items():
                print(f"  {key}: {type(encoder).__name__}")
                if hasattr(encoder, 'classes_'):
                    print(f"    Classes: {encoder.classes_[:20]}...")  # First 20
        
        if 'features' in data:
            print(f"\nFeatures from data: {data['features']}")
    else:
        print("\n=== Model is not a dictionary ===")
        print(f"Type: {type(data)}")
        print(f"Class: {data.__class__.__name__}")
        
        if hasattr(data, 'feature_names_'):
            print(f"\nFeature names: {data.feature_names_}")
            
except Exception as e:
    print(f"Error loading model: {e}")
    import traceback
    traceback.print_exc()
