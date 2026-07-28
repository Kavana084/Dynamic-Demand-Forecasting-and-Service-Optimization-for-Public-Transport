import os
for root, dirs, files in os.walk("f:/transit-ai-system/backend"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if "Route not found" in line:
                        print(f"FOUND IN {file} LINE {i+1}: {line.strip()}")
