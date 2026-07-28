from backend.app.main import app

print("--- FastAPI Routes ---")
for route in app.routes:
    path = getattr(route, "path", "No path")
    methods = getattr(route, "methods", "No methods")
    name = getattr(route, "name", "No name")
    print(f"{methods} {path} ({name})")
print("----------------------")
