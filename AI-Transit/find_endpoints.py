import os

target_files = []
for root, dirs, files in os.walk('backend/app'):
    for file in files:
        if file.endswith('.py'):
            target_files.append(os.path.join(root, file))

queries = ['/analytics/summary', '/analytics/route-ranking', '/forecast-history', '/forecast-latest']

for fpath in target_files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                for q in queries:
                    if q in line:
                        print(f"{fpath}:{i+1}  {line.strip()}")
    except Exception as e:
        pass
