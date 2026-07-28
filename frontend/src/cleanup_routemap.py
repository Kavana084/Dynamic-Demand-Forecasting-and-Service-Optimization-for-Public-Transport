import re
import os

file_path = 'f:/transit-ai-system/frontend/src/components/RouteMap.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the empty busPosition && () block
content = re.sub(r'\{/\*\s*── Live Bus Marker.*?\n\s*\*/\}\n\s*\{busPosition && \(\s*\)\}', '', content, flags=re.DOTALL)
content = re.sub(r'\{busPosition && \(\s*\)\}', '', content, flags=re.DOTALL)
content = re.sub(r'\{liveBus && \(\s*\)\}', '', content, flags=re.DOTALL)

# 2. Remove all unused variable declarations
content = re.sub(r'const busPosition =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const \[liveBus, setLiveBus\].*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const busStopIndex =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const \[simIndex, setSimIndex\].*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const timerRef =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const isWsDriven =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const busIcon =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const occupancyTier =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'let currentStopName =.*?;', '', content, flags=re.DOTALL)
content = re.sub(r'const currentStopName =.*?;', '', content, flags=re.DOTALL)

# 3. Remove useEffect hooks that are empty or only for bus simulation
content = re.sub(r'useEffect\(\(\) => \{\n\s*if \(isWsDriven.*?\}\s*\}, \[.*?\]\);', '', content, flags=re.DOTALL)
content = re.sub(r'useEffect\(\(\) => \{\n\s*setLiveBus.*?\}\s*\}, \[.*?\]\);', '', content, flags=re.DOTALL)

# 4. Remove unused imports
content = re.sub(r'import \{ useEffect, useRef, useState, useMemo \} from \'react\';', 'import { useEffect, useState, useMemo } from \'react\';', content)
content = re.sub(r'import \{.*?\} from \'react\';', lambda m: m.group(0).replace('useRef, ', '').replace(', useRef', ''), content)

# Remove unused variables from the component params if any (like `busData` was already removed)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done RouteMap.jsx cleanup")
