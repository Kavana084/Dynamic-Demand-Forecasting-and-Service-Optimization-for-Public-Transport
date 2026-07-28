import json
import pandas as pd
import numpy as np

def generate_quality_report():
    df = pd.read_csv('outputs/processed_dataset.csv')
    
    missing_values = df.isnull().sum().to_dict()
    missing_values = {k: int(v) for k, v in missing_values.items() if v > 0}
    
    duplicate_rows = int(df.duplicated().sum())
    
    # Passenger count stats
    target = 'passenger_count'
    if target in df.columns:
        pc = df[target]
        min_demand = int(pc.min())
        max_demand = int(pc.max())
        mean_demand = float(pc.mean())
        percentiles = {
            "25th": float(pc.quantile(0.25)),
            "50th": float(pc.quantile(0.50)),
            "75th": float(pc.quantile(0.75)),
            "90th": float(pc.quantile(0.90)),
            "99th": float(pc.quantile(0.99))
        }
        
        # Outliers (using IQR)
        Q1 = pc.quantile(0.25)
        Q3 = pc.quantile(0.75)
        IQR = Q3 - Q1
        outliers = int(((pc < (Q1 - 1.5 * IQR)) | (pc > (Q3 + 1.5 * IQR))).sum())
        
        # Correlations with target
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        correlations = df[numeric_cols].corr()[target].drop(target).to_dict()
        correlations = {k: float(v) if not np.isnan(v) else 0.0 for k, v in correlations.items()}
    else:
        min_demand = max_demand = mean_demand = outliers = 0
        percentiles = {}
        correlations = {}
        
    # Highlight data leakage risks
    leakage_risks = []
    for k, v in correlations.items():
        if abs(v) > 0.8:
            leakage_risks.append(f"High correlation ({v:.2f}) with {k}")
            
    report = {
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "outliers": outliers,
        "passenger_count_distribution": {
            "min_demand": min_demand,
            "max_demand": max_demand,
            "mean_demand": mean_demand,
            "percentiles": percentiles
        },
        "feature_correlations": correlations,
        "data_leakage_risks": leakage_risks
    }
    
    with open('outputs/dataset_quality_report.json', 'w') as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    generate_quality_report()
