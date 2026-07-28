import os

files = [r'f:\transit-ai-system\backend\check_tables.py', r'f:\transit-ai-system\backend\test_tables.py']
for f in files:
    if os.path.exists(f):
        c = open(f, 'r', encoding='utf-8').read()
        open(f, 'w', encoding='utf-8').write(c.replace('PredictionRecord', 'ForecastHistory'))
