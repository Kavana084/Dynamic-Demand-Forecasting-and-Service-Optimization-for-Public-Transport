import sys
import os

try:
    sys.path.insert(0, os.path.abspath("f:/transit-ai-system/backend"))
    import main
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
