import os

def search_dir(d, q):
    for root, _, files in os.walk(d):
        if 'venv' in root or '.venv' in root: continue
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        for i, line in enumerate(file):
                            if q in line:
                                print(f"{path}:{i+1}: {line.strip()}")
                except Exception:
                    pass

print("Searching backend...")
search_dir('f:/transit-ai-system/backend', 'optimize_fleet')
print("Searching ml...")
search_dir('f:/transit-ai-system/ml', 'optimize_fleet')
print("Searching root...")
search_dir('f:/transit-ai-system', 'optimize_fleet')
