/**
 * Generates smart insights based on trip request parameters and resulting bus data.
 */
export const generateInsights = (buses, formData) => {
  const insights = [];
  const maxDelay = buses.reduce((max, bus) => Math.max(max, bus.delay), 0);
  if (maxDelay > 5) {
    insights.push("Leaving 10 minutes earlier may reduce delay during this window.");
  }

  if (formData.traffic?.toLowerCase() === 'high') {
    insights.push("Consider alternate routes for faster travel to bypass heavy traffic zones.");
  }

  return insights;
};


/**
 * Returns Tailwind classes for context badges based on condition strings.
 */
export const getBadgeForCondition = (condition) => {
  const cond = condition.toLowerCase();
  if (cond.includes('rain')) return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
  if (cond.includes('peak')) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
  if (cond.includes('traffic') || cond.includes('heavy')) return 'bg-red-500/20 text-red-400 border-red-500/30';
  return 'bg-slate-700 text-slate-300 border-slate-600';
};
