import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useMemo } from 'react';

export default function BeforeAfterBar({ data }) {
  const chartData = useMemo(() => {
    if (!data) return [];
    return data.slice(0, 10).map(item => ({
      route: item.route_id,
      optimized: item.buses_assigned,
    }));
  }, [data]);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="99%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: -20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis 
            dataKey="route" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#64748b', fontSize: 12 }} 
            dx={-10}
          />
          <Tooltip 
            cursor={{ fill: '#f8fafc' }}
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Legend 
            iconType="circle" 
            wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }}
            verticalAlign="top"
            align="right"
          />

          <Bar 
            dataKey="optimized" 
            name="Optimized" 
            fill="#6c5ce7" 
            radius={[4, 4, 0, 0]}
            barSize={20}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
