import os
import re

backend_dir = r"f:\transit-ai-system\backend"
models_file = os.path.join(backend_dir, "app", "database", "models.py")

with open(models_file, "r", encoding="utf-8") as f:
    models_content = f.read()

models = re.findall(r"class (\w+)\(Base\):", models_content)

def search_in_files(search_terms):
    results = {term: [] for term in search_terms}
    for root, _, files in os.walk(backend_dir):
        if "__pycache__" in root or ".venv" in root:
            continue
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    lines = f.readlines()
                except UnicodeDecodeError:
                    continue
                for i, line in enumerate(lines):
                    for term in search_terms:
                        if re.search(r'\b' + term + r'\b', line):
                            results[term].append((filepath, i+1, line.strip()))
    return results

res = search_in_files(models + ["forecast_service", "service", "test_catboost_integration", "Predictor", "DemandPredictionService"])

with open(r"f:\transit-ai-system\audit_results.txt", "w", encoding="utf-8") as out:
    out.write("--- AUDIT RESULTS ---\n")
    for term, occurrences in res.items():
        out.write(f"\n[{term}] - {len(occurrences)} occurrences\n")
        for filepath, line_num, line_content in occurrences:
            out.write(f"  {os.path.relpath(filepath, backend_dir)}:{line_num} - {line_content}\n")
