import re

with open('frontend/src/components/admin/AnalyticsDashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove 'Allocated Buses' column
content = re.sub(r'\s*<th className="p-4 font-semibold text-right">Allocated Buses</th>', '', content)
content = re.sub(r'\s*<td className="p-4 text-right text-muted">\{row\.allocated_buses\}</td>', '', content)

# Remove 'Allocation Status' column
content = re.sub(r'\s*<th className="p-4 font-semibold">Allocation Status</th>', '', content)
content = re.sub(r'\s*<td className="p-4 whitespace-nowrap">\s*<span className=\{clsx\("inline-flex items-center px-2 py-0\.5 rounded text-\[11px\] font-semibold border", getAllocationBadgeColor\(row\.allocation_status\)\)\}>\s*\{row\.allocation_status\}\s*</span>\s*</td>', '', content)

with open('frontend/src/components/admin/AnalyticsDashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated AnalyticsDashboard.jsx columns')
