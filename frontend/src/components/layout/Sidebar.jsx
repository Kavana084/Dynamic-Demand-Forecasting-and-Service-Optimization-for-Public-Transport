import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Map, 
  TrendingUp, 
  Settings, 
  Bell, 
  BarChart, 
  Bus,
  Activity
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { name: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { name: 'Demand Prediction', path: '/admin/predict', icon: TrendingUp },
  { name: 'Fleet Optimization', path: '/admin/optimize', icon: Settings },
  { name: 'Fleet Management', path: '/admin/fleet', icon: Bus },
  { name: 'Demand & Fleet Opt.', path: '/admin/demand-fleet', icon: TrendingUp },
  { name: 'System Monitoring', path: '/admin/monitoring', icon: Activity },
  { name: 'Prediction History', path: '/admin/history', icon: BarChart },
  { name: 'Route Analytics', path: '/admin/routes', icon: Map },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-sidebar h-screen flex flex-col text-slate-300 fixed left-0 top-0 overflow-y-auto">
      {/* Logo Area */}
      <div className="p-6 flex items-center space-x-3">
        <div className="bg-primary p-2 rounded-lg">
          <Bus className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-white leading-tight">Smart Transit</h1>
          <p className="text-xs text-slate-400">Optimization</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1 mt-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => clsx(
                "flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium",
                isActive 
                  ? "bg-primary text-white" 
                  : "hover:bg-slate-800/50 hover:text-white"
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="p-4 mt-auto">
        <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">System Status</span>
            <span className="flex items-center text-xs text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
              Operational
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Model Status</span>
            <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">Active</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
