import { useAppContext } from '../context/AppContext';
import { Route, Bus, Users, Activity, AlertTriangle } from 'lucide-react';
import KpiCard from '../components/cards/KpiCard';
import DemandLineChart from '../components/charts/DemandLineChart';
import RouteLoadPie from '../components/charts/RouteLoadPie';
import CongestedRoutesTable from '../components/table/CongestedRoutesTable';

export default function Dashboard() {
  const { dashboardData, loading, error } = useAppContext();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="text-slate-500 animate-pulse">Loading live dashboard data...</p>
      </div>
    );
  }

  if (error || !dashboardData) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-500" />
        <p className="text-red-500 text-lg font-medium">Error loading dashboard data</p>
        <p className="text-slate-500">{error}</p>
      </div>
    );
  }

  const { kpis, hourlyDemand, routeDemand, fleetSummary, drlRecommendation } = dashboardData;

  // Process data for charts
  const demandOverTime = hourlyDemand.map(d => ({
    time: d.hour,
    predicted: d.passengers,
  }));

  // Process route load for pie chart
  const topRoutes = routeDemand.slice(0, 3);
  const otherRoutesDemand = routeDemand.slice(3).reduce((acc, r) => acc + r.demand, 0);
  const colors = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'];
  
  const routeLoadDistribution = [
    ...topRoutes.map((r, i) => ({ name: r.route, value: r.demand, color: colors[i] })),
    ...(otherRoutesDemand > 0 ? [{ name: 'Others', value: otherRoutesDemand, color: colors[3] }] : [])
  ];

  // Process congested routes table
  const congestedRoutes = routeDemand.slice(0, 5).map(r => ({
    route: r.route,
    currentLoad: "Data unavailable", 
    predictedLoad: Math.min(100, Math.floor(r.demand / 100)),
    status: r.demand > 6000 ? 'High' : 'Medium'
  }));

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard 
          title="Total Routes" 
          value={kpis?.totalRoutes || 0} 
          change="Live" 
          isPositive={true} 
          icon={Route}
          colorClass="bg-purple-500"
        />
        <KpiCard 
          title="Fleet Utilization" 
          value={kpis?.fleetUtilization || `${fleetSummary?.utilization || 0}%`} 
          change="Optimum" 
          isPositive={true} 
          icon={Bus}
          colorClass="bg-blue-500"
        />
        <KpiCard 
          title="Predicted Demand" 
          value={kpis?.predictedDemand?.toLocaleString() || 0} 
          change="+12%" 
          isPositive={true} 
          icon={Users}
          colorClass="bg-emerald-500"
        />
        <KpiCard 
          title="Schedule Engine" 
          value={kpis?.drlStatus || 'Active'} 
          change="Demand-Based" 
          isPositive={true} 
          icon={Activity}
          colorClass="bg-amber-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Line Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 transition-all hover:shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-primary" />
            Demand Forecast (Next 12 Hours)
          </h3>
          <DemandLineChart data={demandOverTime} />
        </div>

        {/* Donut Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 transition-all hover:shadow-md">
          <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
            <Users className="w-5 h-5 mr-2 text-primary" />
            Route Demand Distribution
          </h3>
          <RouteLoadPie data={routeLoadDistribution} total={kpis?.totalRoutes || routeDemand.length} />
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 lg:col-span-2 transition-all hover:shadow-md overflow-hidden">
          <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
            <Route className="w-5 h-5 mr-2 text-primary" />
            Highest Demand Routes
          </h3>
          <CongestedRoutesTable data={congestedRoutes} />
        </div>

        {/* Schedule Insights */}
        <div className="bg-gradient-to-br from-indigo-50 to-white rounded-xl shadow-sm border border-indigo-100 p-6 transition-all hover:shadow-md">
          <h3 className="text-lg font-bold text-indigo-900 mb-6 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-indigo-600" />
            Schedule Insights
          </h3>
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-lg border border-indigo-50 shadow-sm">
              <h4 className="text-sm font-semibold text-indigo-800 mb-1">Recommended Adjustment</h4>
              <p className="text-sm text-slate-600">{drlRecommendation?.action || 'System running optimally'}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-indigo-50 shadow-sm">
              <h4 className="text-sm font-semibold text-indigo-800 mb-1">Expected Impact</h4>
              <p className="text-sm text-emerald-600 font-medium">{drlRecommendation?.expectedReward || 'N/A'}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-indigo-50 shadow-sm">
              <h4 className="text-sm font-semibold text-indigo-800 mb-1">Priority Routes</h4>
              <div className="flex flex-wrap gap-2 mt-2">
                {drlRecommendation?.priorityRoutes?.length > 0
                  ? drlRecommendation.priorityRoutes.map((route, idx) => (
                      <span key={idx} className="px-2.5 py-1 bg-indigo-100 text-indigo-700 rounded-md text-xs font-medium">
                        {route}
                      </span>
                    ))
                  : <span className="text-xs text-slate-400 italic">All routes operating normally</span>
                }
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
