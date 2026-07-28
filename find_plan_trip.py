import os

search_dir = "frontend"
search_str = "plan_trip"

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    content = f.read()
                    if search_str in content:
                        print(f"Found {search_str} in {path}")
                except UnicodeDecodeError:
                    pass
