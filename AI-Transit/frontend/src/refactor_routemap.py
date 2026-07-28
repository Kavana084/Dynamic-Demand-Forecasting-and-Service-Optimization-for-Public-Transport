import re

file_path = 'f:/transit-ai-system/frontend/src/components/RouteMap.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove busData from props and component parameters
content = re.sub(r'busData\s*=\s*\{\},?', '', content)

# 2. Remove busData extraction block
content = re.sub(r'const \{\s*busId.*?=\s*busData;', '', content, flags=re.DOTALL)

# 3. Remove liveBus state and effect
content = re.sub(r'// ── Live values:.*?\}\);', '', content, flags=re.DOTALL)

# 4. Remove Simulation and WebSocket driven logic
content = re.sub(r'// ── Bus stop index:.*?const busStopIndex = useMemo\(\(\) => \{.*?\n  \}, \[.*?\]\);', '', content, flags=re.DOTALL)

# 5. Remove bus position logic
content = re.sub(r'// Bus position.*?\}, \[.*?\]\);', '', content, flags=re.DOTALL)

# 6. Remove bus icon logic
content = re.sub(r'// Bus icon — only recreated.*?\}, \[.*?\]\s*\);', '', content, flags=re.DOTALL)
content = re.sub(r'// Bus icon — recreated only when occupancy tier changes.*?function makeBusIcon.*?\}', '', content, flags=re.DOTALL)

# 7. Remove currentStopName
content = re.sub(r'// Current stop name for the bus popup "At stop" row\s*const currentStopName = .*?;', '', content)

# 8. Remove Live status strip (Legend bar is right above it)
content = re.sub(r'\{/\* ── Live status strip.*?\{/\* ── Map ── \*/\}', '{/* ── Map ── */}', content, flags=re.DOTALL)

# 9. Remove Live Bus Marker block
content = re.sub(r'\{/\* ── Live Bus Marker ──────────────────────────────────────────────────.*?\{/\* ── Live Bus Marker.*?\}\)', '', content, flags=re.DOTALL)

# 10. Remove busPulse keyframes
content = re.sub(r'\{/\* Keyframe for bus pulse animation \(injected once into the document\) \*/\}.*?</style>', '', content, flags=re.DOTALL)

# 11. Remove Live Bus from legend
content = re.sub(r'<span className="flex items-center gap-1\.5">\s*<span className="w-4 h-3 rounded bg-indigo-900 inline-block" /> Live Bus\s*</span>', '', content)

# 12. Fix "busStopIndex is not defined" error from currentStopName if missed
content = re.sub(r'const currentStopName.*?;', '', content)

# 13. Remove any `<Marker key="live-bus"` if regex failed
content = re.sub(r'<Marker\s*key="live-bus".*?</Marker>', '', content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done refactoring RouteMap.jsx")
