import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { useMemo } from 'react';

export default function DemandLineChart({ data }) {
  // Memoize the chart component to prevent unnecessary re-renders
  const chartData = useMemo(() => data || [], [data]);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="99%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis 
            dataKey="time" 
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
            tickFormatter={(value) => `${value / 1000}K`}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Legend 
            iconType="circle" 
            wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }}
          />
          <Line 
            type="monotone" 
            dataKey="predicted" 
            name="Predicted Demand" 
            stroke="#6c5ce7" 
            strokeWidth={3}
            dot={{ r: 4, fill: '#6c5ce7', strokeWidth: 0 }}
            activeDot={{ r: 6, fill: '#6c5ce7', strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
