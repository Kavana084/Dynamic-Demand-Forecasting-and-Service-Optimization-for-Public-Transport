import re

with open('backend/app/api/admin.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the return None, None in _resolve_window
content = content.replace('    return None, None\n', '    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)\n    return today - timedelta(days=7), today + timedelta(days=1)\n')

# Remove the fallback blocks
fallback_pattern = r'    if not start or not end:\n        today = datetime\.utcnow\(\)\.replace\(hour=0, minute=0, second=0, microsecond=0\)\n        start, end = today, today \+ timedelta\(days=1\)\n'
content = re.sub(fallback_pattern, '', content)

with open('backend/app/api/admin.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated admin.py')
