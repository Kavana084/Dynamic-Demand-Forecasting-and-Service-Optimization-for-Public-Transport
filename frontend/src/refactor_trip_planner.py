import re

file_path = 'f:/transit-ai-system/frontend/src/pages/TripPlanner.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace emojis with Lucide React icons
content = content.replace("🗺️ Journey Planner", "Journey Planner")
content = content.replace("🟢 From", "From")
content = content.replace("🔴 To", "To")
content = content.replace("🕐 Travel Time (Optional)", "Travel Time")
content = content.replace("🚌", "<Bus size={16} />")
content = content.replace("🪑", "<CheckCircle2 size={16} />")
content = content.replace("✅", "<CheckCircle2 size={16} />")
content = content.replace("🚍", "<Bus size={16} />")
content = content.replace("🚦", "<AlertTriangle size={16} />")
content = content.replace("⏱️", "<Clock size={16} />")
content = content.replace("🔄", "<ArrowLeftRight size={16} />")
content = content.replace("🎯", "<MapPin size={16} />")
content = content.replace("⚡", "<Zap size={16} />")
content = content.replace("💰", "<CreditCard size={16} />")
content = content.replace("🛡️", "<Shield size={16} />")
content = content.replace("😊", "<Smile size={16} />")


# 2. Fix getCrowdInfo
crowd_info_new = """function getCrowdInfo(occupancyPercent) {
  const pct = Number(occupancyPercent) || 0;
  if (pct > 85) {
    return {
      label: 'Quite Crowded',
      desc: 'High demand expected.',
      color: '#F59E0B',
      bg: 'rgba(245,158,11,0.12)',
      border: 'rgba(245,158,11,0.35)',
      textClass: 'text-amber-500',
      gaugeColor: '#F59E0B',
    };
  }
  if (pct >= 60) {
    return {
      label: 'Moderate Crowd',
      desc: 'Moderate demand expected.',
      color: '#EAB308',
      bg: 'rgba(234,179,8,0.12)',
      border: 'rgba(234,179,8,0.35)',
      textClass: 'text-yellow-500',
      gaugeColor: '#EAB308',
    };
  }
  return {
    label: 'Low Crowd',
    desc: 'Plenty of available seats expected.',
    color: '#16A34A',
    bg: 'rgba(22,163,74,0.12)',
    border: 'rgba(22,163,74,0.35)',
    textClass: 'text-green-600',
    gaugeColor: '#16A34A',
  };
}"""

content = re.sub(r'function getCrowdInfo\(occupancyPercent\).*?\}\n\n// Convert', crowd_info_new + '\n\n// Convert', content, flags=re.DOTALL)


# 3. Fix getServiceInfo
service_info_new = """function getServiceInfo(recommendedFleet, requiredBuses) {
  const extra = (recommendedFleet || 0) - (requiredBuses || 0);
  if (extra > 0) {
    return {
      title: 'More Buses Recommended',
      desc: 'Fleet API suggests deploying additional buses.',
      isExtra: true,
    };
  }
  return {
    title: 'Current Service Looks Good',
    desc: 'The current fleet is sufficient.',
    isExtra: false,
  };
}"""

content = re.sub(r'// Service recommendation from fleet data\nfunction getServiceInfo.*?\}\n\n// AI insights', '// Service recommendation from fleet data\n' + service_info_new + '\n\n// AI insights', content, flags=re.DOTALL)


# 4. Fix buildAIInsights
ai_insights_new = """function buildAIInsights(result) {
  const insights = [];
  if (result?.occupancy_percent || result?.predicted_demand) {
      insights.push({ icon: <CheckCircle2 size={16} />, text: `Crowd occupancy predicted at ${result.occupancy_percent || demandToOccupancy(result.predicted_demand)}%.` });
  }
  if (result?.recommendation_reason) {
      insights.push({ icon: <Bus size={16} />, text: result.recommendation_reason });
  }
  return insights;
}"""

content = re.sub(r'function buildAIInsights.*?return insights;\n\}', ai_insights_new, content, flags=re.DOTALL)


# 5. Remove generateAlternatives and WHY_CARDS entirely.
content = re.sub(r'// Why recommended cards.*?\}\n\n// ─── Occupancy Gauge', '// ─── Occupancy Gauge', content, flags=re.DOTALL)
content = re.sub(r'// ─── Alternative Route Card ────────────────────────────────────────────────────.*?\}\n\n// ─── Section Header', '// ─── Section Header', content, flags=re.DOTALL)

# 6. Remove travel time input field in JSX
content = re.sub(r'\{\/\* Travel Time \(Optional\) \*\/\}.*?<\/div>', '', content, flags=re.DOTALL)
content = re.sub(r'const \[travelTime, setTravelTime\] = useState\(\'\'\);', '', content)


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done refactoring TripPlanner.jsx")
