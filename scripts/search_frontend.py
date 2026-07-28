import os

print("Searching for verify_admin in frontend...")
for root, dirs, files in os.walk("f:/transit-ai-system/frontend/src"):
    for file in files:
        if file.endswith((".js", ".jsx")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if "verify_admin" in content or "verify-admin" in content or "verifyAdmin" in content:
                    print(f"FOUND IN: {path}")
