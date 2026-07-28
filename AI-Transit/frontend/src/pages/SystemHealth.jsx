import { useState, useEffect } from 'react';
import { ShieldCheck, Database, Cpu, Settings2, HardDrive, Zap, AlertTriangle } from 'lucide-react';
import { fetchSystemHealth } from '../api/health';
import { getSystemMetrics } from '../api/client';

export default function SystemHealth() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const [res, metricsRes] = await Promise.all([
          fetchSystemHealth(),
          getSystemMetrics()
        ]);
        setHealth({ ...res, metrics: metricsRes });
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      } catch (err) {
        console.error(err);
        setError("Unable to reach health endpoint. System may be down.");
      } finally {
        setLoading(false);
      }
    };
    
    loadHealth();
    const interval = setInterval(loadHealth, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  const StatusCard = ({ icon: Icon, title, isReady }) => (
    <div className="flex items-center justify-between p-4 bg-white border border-slate-100 shadow-sm rounded-xl transition-all">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg ${isReady ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
          <Icon className="w-5 h-5" />
        </div>
        <span className="font-semibold text-slate-700">{title}</span>
      </div>
      <div className={`px-3 py-1 rounded-full text-xs font-bold ${isReady ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
        {isReady ? 'Active' : 'Offline'}
      </div>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">System Monitoring</h1>
          <p className="text-slate-500 mt-2">Live diagnostic overview of platform microservices.</p>
        </div>
        {lastUpdated && !loading && (
          <span className="text-sm font-medium text-slate-500 flex items-center bg-white px-3 py-1.5 border border-slate-200 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span>
            Updated: {lastUpdated}
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl flex items-start">
          <AlertTriangle className="w-6 h-6 mr-4 mt-0.5 shrink-0" />
          <div>
            <h3 className="font-bold">Connection Error</h3>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
        <div className="flex items-center space-x-3 mb-8 pb-4 border-b border-slate-100">
          <ShieldCheck className={`w-8 h-8 ${health?.status === 'healthy' ? 'text-emerald-500' : 'text-slate-400'}`} />
          <div>
            <h2 className="text-xl font-bold text-slate-800">API Gateway Status</h2>
            <p className="text-sm text-slate-500">
              {health?.status === 'healthy' ? 'All systems operational and responding securely.' : 'Checking gateway...'}
            </p>
          </div>
        </div>

        {health ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <StatusCard 
              icon={Database} 
              title="Database Connection" 
              isReady={health.database_connected} 
            />
            <StatusCard 
              icon={Cpu} 
              title="CatBoost ML Engine" 
              isReady={health.model_loaded} 
            />
            <StatusCard 
              icon={Settings2} 
              title="MILP Optimizer" 
              isReady={health.optimizer_ready} 
            />
            <StatusCard 
              icon={Zap} 
              title="Redis Cache" 
              isReady={health.cache_available} 
            />
            <StatusCard 
              icon={HardDrive} 
              title="Disk Persistence" 
              isReady={health.disk_persistence_available} 
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-slate-100 rounded-xl w-full"></div>
            ))}
          </div>
        )}

        {health?.metrics && (
          <div className="mt-8 pt-8 border-t border-slate-100">
            <h2 className="text-xl font-bold text-slate-800 mb-6">Hardware Utilization</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-500">CPU Usage</span>
                  <Cpu className="w-4 h-4 text-sky-500" />
                </div>
                <div className="text-2xl font-bold text-slate-800">{health.metrics.cpu_usage.toFixed(1)}%</div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mt-3">
                  <div className={`h-1.5 rounded-full ${health.metrics.cpu_usage > 80 ? 'bg-red-500' : 'bg-sky-500'}`} style={{ width: `${health.metrics.cpu_usage}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-500">Memory Usage</span>
                  <Database className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="text-2xl font-bold text-slate-800">{health.metrics.memory_usage.toFixed(1)}%</div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mt-3">
                  <div className={`h-1.5 rounded-full ${health.metrics.memory_usage > 80 ? 'bg-red-500' : 'bg-indigo-500'}`} style={{ width: `${health.metrics.memory_usage}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-500">Disk Usage</span>
                  <HardDrive className="w-4 h-4 text-amber-500" />
                </div>
                <div className="text-2xl font-bold text-slate-800">{health.metrics.disk_usage.toFixed(1)}%</div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 mt-3">
                  <div className={`h-1.5 rounded-full ${health.metrics.disk_usage > 85 ? 'bg-red-500' : 'bg-amber-500'}`} style={{ width: `${health.metrics.disk_usage}%` }}></div>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-500">Active Threads</span>
                  <Settings2 className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-bold text-slate-800">{health.metrics.active_threads}</div>
                <div className="text-xs text-slate-400 mt-2">Running across system</div>
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}
