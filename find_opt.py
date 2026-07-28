import os
for root, _, files in os.walk(r'f:\transit-ai-system\backend\app\services'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if 'OptimizationResult' in line:
                        print(f"{file}:{i+1}: {line.strip()}")
