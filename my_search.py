import os

def search():
    keywords = ['occupancy', 'comfort', 'predicted_passengers', 'additional_buses', 'demand_level']
    dirs = ['backend', 'frontend']
    with open('search_out_utf8.txt', 'w', encoding='utf-8') as out_f:
        for d in dirs:
            if not os.path.exists(d): continue
            for root, _, files in os.walk(d):
                for file in files:
                    if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.html')):
                        path = os.path.join(root, file)
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                for i, line in enumerate(lines):
                                    if any(kw in line.lower() for kw in keywords):
                                        out_f.write(f"{path}:{i+1}: {line.strip()}\n")
                        except Exception as e:
                            pass

if __name__ == "__main__":
    search()
