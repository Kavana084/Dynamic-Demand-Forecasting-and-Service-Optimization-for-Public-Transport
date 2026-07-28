import re

file_path = 'f:/transit-ai-system/frontend/src/pages/TripPlanner.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the existing lucide-react import with one that includes all needed icons
new_import = """import {
  MapPin, Search, ArrowLeftRight, Loader2,
  AlertTriangle, ChevronDown, ChevronUp,
  Navigation, CheckCircle2,
  ArrowRight, GitBranch,
  Bus, Clock, Zap, CreditCard, Shield, Smile
} from 'lucide-react';"""

content = re.sub(r'import\s+\{.*?\s+.*?\}\s+from\s+\'lucide-react\';', new_import, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done fixing TripPlanner.jsx imports")
