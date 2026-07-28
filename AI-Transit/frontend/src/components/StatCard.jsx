export default function StatCard({ title, value, change, icon: Icon }) {
  return (
    <div className="glass-panel p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-slate-100">{value}</h3>
          
          {change && (
            <div className={`flex items-center mt-2 text-xs font-medium ${change.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
              <span>{change}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="p-2 bg-slate-800 rounded-lg">
            <Icon className="w-5 h-5 text-sky-400" />
          </div>
        )}
      </div>
    </div>
  );
}
