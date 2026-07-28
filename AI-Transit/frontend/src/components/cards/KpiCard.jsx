import { TrendingUp, TrendingDown } from 'lucide-react';
import clsx from 'clsx';

export default function KpiCard({ title, value, change, isPositive, icon: Icon, colorClass }) {
  return (
    <div className="card p-6 flex flex-col justify-between h-full">
      <div className="flex items-center space-x-4">
        <div className={clsx("w-12 h-12 rounded-xl flex items-center justify-center shrink-0", colorClass)}>
          {Icon && <Icon className="w-6 h-6 text-white" />}
        </div>
        <div>
          <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
          <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
        </div>
      </div>
      
      {change && (
        <div className="mt-4 flex items-center text-sm font-medium">
          {isPositive ? (
            <span className="flex items-center text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded">
              <TrendingUp className="w-4 h-4 mr-1" />
              {change}
            </span>
          ) : (
            <span className="flex items-center text-red-500 bg-red-50 px-2 py-0.5 rounded">
              <TrendingDown className="w-4 h-4 mr-1" />
              {change}
            </span>
          )}
          <span className="text-slate-400 ml-2">vs yesterday</span>
        </div>
      )}
    </div>
  );
}
