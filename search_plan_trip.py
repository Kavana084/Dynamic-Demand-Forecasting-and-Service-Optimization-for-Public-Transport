content = open('backend/app/database/models.py', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ['OptimizationResult', 'optimization_result', 'allocated_buses']):
        print(f'{i}: {line}')
