with open(r'f:\transit-ai-system\backend\app\api\admin.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'ACTIVE_MODEL_VERSION' in line or 'OptimizationResult' in line:
            print(f'{i+1}: {line.strip()}')
