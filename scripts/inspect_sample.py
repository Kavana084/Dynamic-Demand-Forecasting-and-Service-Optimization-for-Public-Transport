import pandas as pd
# Quick sample inspection of a few rows
df = pd.read_csv('outputs/processed_dataset.csv', nrows=5)
print("Columns:", list(df.columns))
print("\nSample row:")
print(df.iloc[0].to_dict())
