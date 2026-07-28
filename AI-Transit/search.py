import os

for root, dirs, files in os.walk('F:/transit-ai-system'):
    if 'node_modules' in dirs:
        dirs.remove('node_modules')
    if '.git' in dirs:
        dirs.remove('.git')
    if 'venv' in dirs:
        dirs.remove('venv')
        
    for file in files:
        if file.endswith('.py'):
            try:
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'def check_db_connectivity' in content:
                        print(f"Found check_db_connectivity in {os.path.join(root, file)}")
                    if '@router.get("/stops"' in content or '@app.get("/api/stops"' in content or '/api/stops' in content:
                        print(f"Found stops endpoint in {os.path.join(root, file)}")
                    if 'outputs/models/catboost_demand_model.cbm' in content:
                        print(f"Found model path in {os.path.join(root, file)}")
                    if 'check_db_connectivity()' in content:
                         print(f"Found check_db_connectivity() call in {os.path.join(root, file)}")
                    if 'engine.url' in content:
                         print(f"Found engine.url in {os.path.join(root, file)}")
            except Exception as e:
                pass
