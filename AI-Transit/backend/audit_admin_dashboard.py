"""
Admin Dashboard Data Audit Script
Creates traceability table for all UI components, API endpoints, and data sources.
"""
import json
import os
import re
from datetime import datetime

def scan_frontend_files():
    """Scan frontend files to identify UI components and their data sources."""
    frontend_dir = "f:/transit-ai-system/frontend/src"
    components = []
    
    # Key files to scan
    files_to_scan = [
        "pages/admin/AdminDashboard.jsx",
        "components/admin/AnalyticsDashboard.jsx",
        "components/admin/OptimizationInsights.jsx",
        "components/admin/UserManagement.jsx",
        "pages/admin/DemandForecastingFleetOptimization.jsx"
    ]
    
    for file_path in files_to_scan:
        full_path = os.path.join(frontend_dir, file_path)
        if not os.path.exists(full_path):
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract API calls
        api_pattern = r'fetch\(["\']([^"\']+)["\']'
        api_calls = re.findall(api_pattern, content)
        
        # Extract component names
        component_pattern = r'(?:export default function|const)\s+(\w+)'
        component_names = re.findall(component_pattern, content)
        
        # Extract state variables
        state_pattern = r'const\s+\[(\w+)\s*,\s*set\w+'
        state_vars = re.findall(state_pattern, content)
        
        if component_names:
            components.append({
                "file": file_path,
                "component": component_names[0] if component_names else "Unknown",
                "api_endpoints": list(set(api_calls)),
                "state_variables": list(set(state_vars))
            })
    
    return components

def scan_backend_endpoints():
    """Scan backend API files to identify endpoints."""
    backend_dir = "f:/transit-ai-system/backend/app/api"
    endpoints = []
    
    files_to_scan = [
        "admin.py",
        "api_routes.py",
        "navigation.py"
    ]
    
    for file_path in files_to_scan:
        full_path = os.path.join(backend_dir, file_path)
        if not os.path.exists(full_path):
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract endpoint definitions
        endpoint_pattern = r'@router\.(get|post|put|delete)\(["\']([^"\']+)["\']'
        endpoint_matches = re.findall(endpoint_pattern, content)
        
        for method, path in endpoint_matches:
            # Extract function name
            func_pattern = rf'def\s+(\w+)\([^)]*\):[^{{]*?@router\.(?:get|post|put|delete)\(["\']{re.escape(path)}["\']'
            func_match = re.search(func_pattern, content, re.MULTILINE | re.DOTALL)
            
            # Alternative: find function after decorator
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if f'@router.{method}("{path}")' in line or f"@router.{method}('{path}')" in line:
                    if i + 1 < len(lines):
                        func_line = lines[i + 1]
                        func_match = re.search(r'def\s+(\w+)', func_line)
                        if func_match:
                            endpoints.append({
                                "file": file_path,
                                "method": method,
                                "path": path,
                                "function": func_match.group(1)
                            })
                            break
    
    return endpoints

def scan_database_models():
    """Scan database models to identify data sources."""
    models_file = "f:/transit-ai-system/backend/app/database/models.py"
    
    if not os.path.exists(models_file):
        return []
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract model class definitions
    model_pattern = r'class\s+(\w+)\([^)]*\):'
    models = re.findall(model_pattern, content)
    
    return models

def scan_backend_services():
    """Scan backend services to identify business logic."""
    services_dir = "f:/transit-ai-system/backend/app/services"
    services = []
    
    if not os.path.exists(services_dir):
        return services
    
    for file_name in os.listdir(services_dir):
        if file_name.endswith('.py') and file_name != '__init__.py':
            file_path = os.path.join(services_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract class definitions
            class_pattern = r'class\s+(\w+)\([^)]*\):'
            classes = re.findall(class_pattern, content)
            
            # Extract function definitions
            func_pattern = r'def\s+(\w+)\([^)]*\):'
            functions = re.findall(func_pattern, content)
            
            services.append({
                "file": file_name,
                "classes": classes,
                "functions": functions
            })
    
    return services

def create_traceability_table(frontend_components, backend_endpoints, database_models, backend_services):
    """Create a comprehensive traceability table."""
    traceability = []
    
    # Map frontend components to backend endpoints
    for component in frontend_components:
        for api_endpoint in component["api_endpoints"]:
            # Find matching backend endpoint
            matching_endpoint = None
            for endpoint in backend_endpoints:
                if endpoint["path"] in api_endpoint or api_endpoint in endpoint["path"]:
                    matching_endpoint = endpoint
                    break
            
            # Find potential database models (heuristic)
            potential_models = []
            endpoint_lower = api_endpoint.lower()
            for model in database_models:
                model_lower = model.lower()
                if model_lower in endpoint_lower or endpoint_lower in model_lower:
                    potential_models.append(model)
            
            traceability.append({
                "ui_component": component["component"],
                "file": component["file"],
                "api_endpoint": api_endpoint,
                "backend_function": matching_endpoint["function"] if matching_endpoint else "Unknown",
                "backend_file": matching_endpoint["file"] if matching_endpoint else "Unknown",
                "potential_database_models": potential_models,
                "state_variables": component["state_variables"]
            })
    
    return traceability

def identify_hardcoded_values(frontend_components, backend_endpoints):
    """Identify potential hardcoded values."""
    hardcoded = []
    
    # Check for common hardcoded patterns
    hardcoded_patterns = [
        (r'\b\d+\b', 'Numeric literal'),
        (r'["\'][A-Z][A-Z_]+["\']', 'Uppercase constant'),
        (r'["\'][\d.]+["\']', 'String number'),
    ]
    
    for component in frontend_components:
        file_path = os.path.join("f:/transit-ai-system/frontend/src", component["file"])
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for pattern, description in hardcoded_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Filter out common non-hardcoded values
                filtered = [m for m in matches if not re.match(r'^\d{1,2}$', m) or int(m) > 100]
                if filtered:
                    hardcoded.append({
                        "component": component["component"],
                        "file": component["file"],
                        "pattern": description,
                        "matches": filtered[:5]  # Limit to first 5 matches
                    })
    
    return hardcoded

def identify_duplicated_calculations():
    """Identify potentially duplicated calculations."""
    # This is a heuristic check - look for similar calculation patterns
    duplications = []
    
    frontend_dir = "f:/transit-ai-system/frontend/src"
    
    # Look for common calculation patterns
    calculation_patterns = [
        r'\*\s*\d+\s*\+\s*\d+',  # Multiplication and addition
        r'\/\s*\d+',  # Division
        r'Math\.(round|floor|ceil)',  # Math operations
    ]
    
    for root, dirs, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith('.jsx'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in calculation_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        duplications.append({
                            "file": os.path.relpath(file_path, frontend_dir),
                            "pattern": pattern,
                            "count": len(matches)
                        })
    
    return duplications

def generate_audit_report(traceability, hardcoded, duplications, database_models, backend_services):
    """Generate the audit report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_ui_components": len(set(t["ui_component"] for t in traceability)),
            "total_api_endpoints": len(set(t["api_endpoint"] for t in traceability)),
            "total_database_models": len(database_models),
            "total_backend_services": len(backend_services),
            "hardcoded_values_found": len(hardcoded),
            "duplicated_calculations_found": len(duplications)
        },
        "traceability_table": traceability,
        "hardcoded_values": hardcoded,
        "duplicated_calculations": duplications,
        "database_models": database_models,
        "backend_services": backend_services
    }
    
    return report

def main():
    print("=" * 80)
    print("ADMIN DASHBOARD DATA AUDIT")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Scan frontend components
    print("Scanning frontend components...")
    frontend_components = scan_frontend_files()
    print(f"Found {len(frontend_components)} components")
    for comp in frontend_components:
        print(f"  - {comp['component']} ({comp['file']})")
    print()
    
    # Scan backend endpoints
    print("Scanning backend endpoints...")
    backend_endpoints = scan_backend_endpoints()
    print(f"Found {len(backend_endpoints)} endpoints")
    for endpoint in backend_endpoints[:10]:
        print(f"  - {endpoint['method'].upper()} {endpoint['path']} -> {endpoint['function']}")
    if len(backend_endpoints) > 10:
        print(f"  ... and {len(backend_endpoints) - 10} more")
    print()
    
    # Scan database models
    print("Scanning database models...")
    database_models = scan_database_models()
    print(f"Found {len(database_models)} models")
    for model in database_models:
        print(f"  - {model}")
    print()
    
    # Scan backend services
    print("Scanning backend services...")
    backend_services = scan_backend_services()
    print(f"Found {len(backend_services)} services")
    for service in backend_services[:5]:
        print(f"  - {service['file']}: {len(service['classes'])} classes, {len(service['functions'])} functions")
    print()
    
    # Create traceability table
    print("Creating traceability table...")
    traceability = create_traceability_table(frontend_components, backend_endpoints, database_models, backend_services)
    print(f"Generated {len(traceability)} traceability entries")
    print()
    
    # Identify hardcoded values
    print("Identifying hardcoded values...")
    hardcoded = identify_hardcoded_values(frontend_components, backend_endpoints)
    print(f"Found {len(hardcoded)} potential hardcoded values")
    print()
    
    # Identify duplicated calculations
    print("Identifying duplicated calculations...")
    duplications = identify_duplicated_calculations()
    print(f"Found {len(duplications)} potential duplicated calculations")
    print()
    
    # Generate report
    print("Generating audit report...")
    report = generate_audit_report(traceability, hardcoded, duplications, database_models, backend_services)
    
    # Save report
    output_file = "outputs/admin_dashboard_audit.json"
    os.makedirs("outputs", exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to: {output_file}")
    print()
    
    # Print summary
    print("=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"UI Components: {report['summary']['total_ui_components']}")
    print(f"API Endpoints: {report['summary']['total_api_endpoints']}")
    print(f"Database Models: {report['summary']['total_database_models']}")
    print(f"Backend Services: {report['summary']['total_backend_services']}")
    print(f"Hardcoded Values: {report['summary']['hardcoded_values_found']}")
    print(f"Duplicated Calculations: {report['summary']['duplicated_calculations_found']}")
    print()
    print(f"Completed at: {datetime.now()}")

if __name__ == "__main__":
    main()
