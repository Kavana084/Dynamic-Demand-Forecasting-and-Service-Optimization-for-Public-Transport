import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { useMemo } from 'react';

export default function RouteLoadPie({ data, total }) {
  const chartData = useMemo(() => data || [], [data]);

  const renderCustomLegend = (props) => {
    const { payload } = props;
    if (!payload || !Array.isArray(payload)) return null;

    return (
      <ul className="flex flex-col space-y-3 ml-4">
        {payload.map((entry, index) => {
          const rawValue = entry.payload?.value || 0;
          const percentage = total > 0 ? Math.round((rawValue / total) * 100) : 0;
          
          return (
            <li key={`item-${index}`} className="flex items-center text-sm">
              <span 
                className="w-3 h-3 rounded-full mr-3 shrink-0" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-slate-600 font-medium flex-1">{entry.value}</span>
              <span className="text-slate-800 font-bold ml-4">
                {rawValue} <span className="text-slate-400 font-normal">({percentage}%)</span>
              </span>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <div className="h-72 w-full flex items-center">
      <div className="w-1/2 h-full relative">
        <ResponsiveContainer width="99%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              innerRadius={70}
              outerRadius={90}
              paddingAngle={5}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center Label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-sm text-slate-500 font-medium">Total</span>
          <span className="text-2xl font-bold text-slate-800">{total}</span>
          <span className="text-xs text-slate-400">Routes</span>
        </div>
      </div>
      
      <div className="w-1/2 flex items-center">
        <Legend content={renderCustomLegend} layout="vertical" verticalAlign="middle" />
      </div>
    </div>
  );
}
