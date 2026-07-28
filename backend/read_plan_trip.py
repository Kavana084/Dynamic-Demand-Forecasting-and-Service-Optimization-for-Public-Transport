import re

file_path = 'f:/transit-ai-system/backend/app/api_routes.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'def plan_trip.*?return (.*?)\n', content, flags=re.DOTALL)
if match:
    # Just print the whole function
    pass
    
# Actually just print the end of the function
lines = content.split('\n')
start = -1
for i, line in enumerate(lines):
    if 'def plan_trip' in line:
        start = i
        break

if start != -1:
    end = start + 200
    print('\n'.join(lines[start:end]))
