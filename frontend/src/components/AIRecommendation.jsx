import { Lightbulb, TrendingUp, TrendingDown, Bus, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function AIRecommendation({ 
  recommendation, 
  reason, 
  confidence 
}) {
  const getRecommendationIcon = () => {
    if (!recommendation) return Lightbulb;
    
    const lowerRec = recommendation.toLowerCase();
    if (lowerRec.includes('increase') || lowerRec.includes('deploy')) return TrendingUp;
    if (lowerRec.includes('reduce') || lowerRec.includes('decrease')) return TrendingDown;
    if (lowerRec.includes('peak')) return AlertTriangle;
    if (lowerRec.includes('low demand')) return TrendingDown;
    if (lowerRec.includes('demand increasing')) return TrendingUp;
    if (lowerRec.includes('demand decreasing')) return TrendingDown;
    if (lowerRec.includes('fleet')) return Bus;
    
    return Lightbulb;
  };

  const getRecommendationColor = () => {
    if (!recommendation) return 'blue';
    
    const lowerRec = recommendation.toLowerCase();
    if (lowerRec.includes('increase') || lowerRec.includes('deploy') || lowerRec.includes('peak')) return 'amber';
    if (lowerRec.includes('reduce') || lowerRec.includes('decrease')) return 'emerald';
    if (lowerRec.includes('demand increasing')) return 'amber';
    if (lowerRec.includes('demand decreasing')) return 'emerald';
    
    return 'indigo';
  };

  const RecommendationIcon = getRecommendationIcon();
  const color = getRecommendationColor();

  const colorClasses = {
    indigo: { bg: 'bg-indigo-50', border: 'border-indigo-100', text: 'text-indigo-700', icon: 'text-indigo-500' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-100', text: 'text-amber-700', icon: 'text-amber-500' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-100', text: 'text-emerald-700', icon: 'text-emerald-500' },
    blue: { bg: 'bg-blue-50', border: 'border-blue-100', text: 'text-blue-700', icon: 'text-blue-500' },
  };

  const c = colorClasses[color];

  if (!recommendation) return null;

  return (
    <div className={`${c.bg} ${c.border} border rounded-2xl p-5 shadow-sm`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center`}>
            <RecommendationIcon className={`w-5 h-5 ${c.icon}`} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-700">AI Recommendation</h3>
            {confidence && (
              <p className="text-xs text-slate-400">Confidence: {confidence}</p>
            )}
          </div>
        </div>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text} border ${c.border}`}>
          <CheckCircle2 className="w-3 h-3" />
          AI Generated
        </span>
      </div>

      <div className="space-y-3">
        <div className={`${c.bg} rounded-xl p-4 border ${c.border}`}>
          <p className={`text-lg font-extrabold ${c.text} capitalize`}>
            {recommendation}
          </p>
        </div>

        {reason && (
          <div className="bg-white rounded-xl p-4 border border-slate-100">
            <p className="text-xs text-slate-500 font-semibold uppercase mb-1">Reason</p>
            <p className="text-sm text-slate-700">{reason}</p>
          </div>
        )}
      </div>
    </div>
  );
}
