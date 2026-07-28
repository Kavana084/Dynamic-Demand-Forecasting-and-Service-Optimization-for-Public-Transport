import os

for root, _, files in os.walk(r'f:\transit-ai-system\backend'):
    if '.venv' in root: continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'FleetService' in content or 'fleet_service' in content:
                    print(filepath)
