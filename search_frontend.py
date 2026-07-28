import os
for root, dirs, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Route Analysis Summary' in content or 'Fleet Optimization' in content or 'Predicted Passenger Demand' in content:
                    print(path)
