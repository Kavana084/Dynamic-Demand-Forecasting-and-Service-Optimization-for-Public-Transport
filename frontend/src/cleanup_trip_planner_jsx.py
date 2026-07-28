import re

file_path = 'f:/transit-ai-system/frontend/src/pages/TripPlanner.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove alternatives assignment
content = re.sub(r'const alternatives = result \? generateAlternatives\(result\) : \[\];', '', content)

# 2. Remove WHY_CARDS mapping
# It probably looks like:
# {WHY_CARDS.map((card) => ( ... ))}
content = re.sub(r'\{WHY_CARDS\.map\(\(card\) => \(.*?\}\)\)\}', '', content, flags=re.DOTALL)

# 3. Remove alternatives mapping
# It probably looks like:
# {alternatives.map((alt, idx) => ( <AltRouteCard ... /> ))}
content = re.sub(r'\{alternatives\.map\(\(alt, idx\) => \(.*?\}\)\)\}', '', content, flags=re.DOTALL)

# 4. Remove section headers for WHY_CARDS and alternatives if they exist
content = re.sub(r'<div className="mb-6">\s*<h3 className="text-lg font-bold text-ink mb-1">\s*Why this route\?\s*</h3>.*?</div>', '', content, flags=re.DOTALL)
content = re.sub(r'<div className="mb-4">\s*<h3 className="text-lg font-bold text-ink mb-1">\s*Alternative Routes\s*</h3>.*?</div>', '', content, flags=re.DOTALL)

# 5. Remove busData from RouteMap
content = re.sub(r'busData=\{wsData \? \{.*?\} : null\}', '', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done cleaning up remaining JSX references in TripPlanner.jsx")
