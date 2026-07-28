import pandas as pd
import numpy as np
import sys
from build_dataset import build_dataset

def validate_dataset():
    print("--- Mandatory Dataset Integrity Check ---")
    df = build_dataset()
    
    if df is None or len(df) < 50:
        print("Not enough data to run integrity checks.")
        sys.exit(1)
        
    target = 'passenger_count'
    
    # 1. Variance Check (No flat distributions)
    print("\n[1] Variance Check:")
    flat_cols = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].std() == 0:
            flat_cols.append(col)
            
    if flat_cols:
        print(f"❌ ERROR: Flat distributions found in columns: {flat_cols}")
        sys.exit(1)
    else:
        print("✔ No flat distributions detected.")
        
    # 2. NaN Leakage Check
    print("\n[2] NaN Leakage Check:")
    nan_counts = df.isna().sum()
    if nan_counts.sum() > 0:
        print(f"❌ ERROR: NaNs detected in the final dataset:\n{nan_counts[nan_counts > 0]}")
        sys.exit(1)
    else:
        print("✔ No missing values in final dataset.")
        
    # 3. Correlation Check
    print("\n[3] Correlation with Target (passenger_count):")
    correlations = df[numeric_cols].corr()[target].sort_values(ascending=False)
    print(correlations)
    
    # We expect some correlation. If everything is ~0, the logic is broken.
    strong_corrs = correlations[abs(correlations) > 0.1]
    if len(strong_corrs) <= 1: # Only self-correlated
        print("❌ WARNING: Very weak or random correlations detected with target!")
    else:
        print("✔ Meaningful correlations established.")
        
    # 4. Temporal Sequence Verification
    print("\n[4] Temporal Leakage Check:")
    if not df['timestamp'].is_monotonic_increasing:
        print("❌ ERROR: Dataset is NOT strictly ordered by time.")
        sys.exit(1)
    else:
        print("✔ Dataset is strictly time-ordered.")
        
    print("\n✅ INTEGRITY PASSED. Dataset is ready for ML training.")

if __name__ == "__main__":
    validate_dataset()
