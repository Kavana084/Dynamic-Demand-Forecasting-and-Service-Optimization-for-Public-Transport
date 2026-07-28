"""
Inspect the actual model's feature names from model_config.json
to know exactly what to feed it.
"""
import json
import sys
sys.path.insert(0, 'scripts')

with open('outputs/model_config.json') as f:
    cfg = json.load(f)

print("=== FEATURE NAMES ===")
for i, fn in enumerate(cfg['feature_names']):
    print(f"  {i:2d}: {fn}")

print(f"\nTotal features: {len(cfg['feature_names'])}")

print("\n=== CATEGORICAL FEATURES ===")
for cf in cfg['categorical_features']:
    print(f"  {cf}")
