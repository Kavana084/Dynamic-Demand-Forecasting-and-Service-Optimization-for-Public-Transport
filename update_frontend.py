import re

with open('frontend/src/components/admin/AnalyticsDashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add isoLast7Days()
iso_today_func = """function isoToday() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}"""
iso_last7_func = """
function isoLast7Days() {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}
"""
if 'isoLast7Days()' not in content:
    content = content.replace(iso_today_func, iso_today_func + iso_last7_func)

# Change default filter for dateFrom to isoLast7Days() if not provided or to empty
# Wait, user wants "Last 7 Days is only used when dates are not supplied". So if we send '', backend will do Last 7 Days.
# Let's change the useState to use '' for both dateFrom and dateTo by default, unless location.state provides them.
# The previous code:
#   const [filters, setFilters] = useState(() => ({
#     dateFrom: location.state?.filters?.dateFrom || isoToday(),
#     dateTo: location.state?.filters?.dateTo || isoToday(),
old_filters = """  const [filters, setFilters] = useState(() => ({
    dateFrom: location.state?.filters?.dateFrom || isoToday(),
    dateTo: location.state?.filters?.dateTo || isoToday(),"""
new_filters = """  const [filters, setFilters] = useState(() => ({
    dateFrom: location.state?.filters?.dateFrom || '',
    dateTo: location.state?.filters?.dateTo || '',"""
content = content.replace(old_filters, new_filters)

# Add Data Window indicator
old_header = """        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-bold text-ink">Demand Analytics Dashboard</h3>
        </div>"""
new_header = """        <div className="flex items-center gap-2 flex-wrap">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-bold text-ink">Demand Analytics Dashboard</h3>
          <span className="ml-2 text-sm font-medium text-muted bg-surface px-2 py-1 rounded-md border border-border">
            Data Window: {filters.dateFrom || 'Last 7 Days'} &rarr; {filters.dateTo || 'Today'}
          </span>
        </div>"""
content = content.replace(old_header, new_header)

# Remove the two cards
# 1. Peak Demand Route
#         <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
#           <p className="text-xs font-semibold text-muted uppercase tracking-wider">Peak Demand Route</p>
#           <p className="mt-2 text-2xl font-extrabold text-ink">{summaryData?.peak_demand_route || 'N/A'}</p>
#         </div>
# 2. Average Occupancy
#         <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
#           <p className="text-xs font-semibold text-muted uppercase tracking-wider">Average Occupancy</p>
#           <p className="mt-2 text-2xl font-extrabold text-ink">{summaryData?.average_occupancy || 0}%</p>
#         </div>

peak_demand_card = r'        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">\s*<p className="text-xs font-semibold text-muted uppercase tracking-wider">Peak Demand Route</p>\s*<p className="mt-2 text-2xl font-extrabold text-ink">\{summaryData\?\.peak_demand_route \|\| \'N/A\'\}</p>\s*</div>\n'
avg_occ_card = r'        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">\s*<p className="text-xs font-semibold text-muted uppercase tracking-wider">Average Occupancy</p>\s*<p className="mt-2 text-2xl font-extrabold text-ink">\{summaryData\?\.average_occupancy \|\| 0\}%</p>\s*</div>\n'

content = re.sub(peak_demand_card, '', content)
content = re.sub(avg_occ_card, '', content)

# Change grid from lg:grid-cols-3 to lg:grid-cols-4 for the summary cards
content = content.replace('<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">', '<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">')

with open('frontend/src/components/admin/AnalyticsDashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated AnalyticsDashboard.jsx')
