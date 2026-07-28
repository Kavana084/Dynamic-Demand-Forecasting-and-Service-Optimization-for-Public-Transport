import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { theme } from '../theme/theme';

const demandData = [
  { time: '06:00', demand: 45 },
  { time: '08:00', demand: 120 },
  { time: '10:00', demand: 85 },
  { time: '12:00', demand: 60 },
  { time: '14:00', demand: 55 },
  { time: '16:00', demand: 90 },
  { time: '18:00', demand: 140 },
  { time: '20:00', demand: 70 },
];

const utilizationData = [
  { route: 'R-01', utilization: 85 },
  { route: 'R-05', utilization: 92 },
  { route: 'R-12', utilization: 78 },
  { route: 'R-22', utilization: 65 },
  { route: 'R-45', utilization: 88 },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 p-3 rounded-xl shadow-lg">
        <p className="text-slate-900 font-medium mb-1">{label}</p>
        <p className="text-sm" style={{ color: theme.primary }}>
          {payload[0].name}: {payload[0].value}
        </p>
      </div>
    );
  }
  return null;
};

export default function Analytics() {
  const [pipelineValid, setPipelineValid] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchValidation = async () => {
      try {
        const token = localStorage.getItem('token') || localStorage.getItem('access_token');
        const res = await fetch('/api/admin/pipeline/validation', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          setPipelineValid(await res.json());
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchValidation();
  }, []);

  if (loading) return <div className="p-8 text-center text-slate-500 animate-pulse">Loading Analytics...</div>;

  if (pipelineValid && pipelineValid.demand_history?.count === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-slate-500 mt-1">Deep dive into historical data and fleet performance.</p>
        </div>
        <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
          <h3 className="text-xl font-medium text-gray-600 mb-2">No demand aggregation data available yet.</h3>
        </div>
      </div>
    );
  }

  if (pipelineValid && pipelineValid.prediction_records?.count === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard</h1>
          <p className="text-slate-500 mt-1">Deep dive into historical data and fleet performance.</p>
        </div>
        <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
          <h3 className="text-xl font-medium text-gray-600 mb-2">No forecasting data available yet.</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Analytics Dashboard</h1>
        <p className="text-slate-500 mt-1">Deep dive into historical data and fleet performance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="theme-section-card">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Passenger Demand Over Time</h2>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={demandData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.border} vertical={false} />
                <XAxis dataKey="time" stroke={theme.textSecondary} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke={theme.textSecondary} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  name="Demand"
                  dataKey="demand" 
                  stroke={theme.primary}
                  strokeWidth={3}
                  dot={{ r: 4, fill: theme.surface, stroke: theme.primary, strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: theme.primary }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="theme-section-card">
          <h2 className="text-lg font-semibold text-slate-900 mb-6">Fleet Utilization by Route</h2>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={utilizationData} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.border} horizontal={false} />
                <XAxis type="number" domain={[0, 100]} stroke={theme.textSecondary} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis dataKey="route" type="category" stroke={theme.textSecondary} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: theme.primarySoft }} />
                <Bar 
                  name="Utilization %"
                  dataKey="utilization" 
                  fill={theme.primary}
                  radius={[0, 4, 4, 0]} 
                  barSize={24}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
