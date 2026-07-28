with open('backend/app/services/ai_assistant_service.py', encoding='utf-8') as f:
    lines = f.readlines()

with open('search_out.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if 'predict' in line or 'demand' in line or '_plan_trip' in line or 'journey' in line:
            out.write(f"{i+1}: {line.rstrip()}\n")
