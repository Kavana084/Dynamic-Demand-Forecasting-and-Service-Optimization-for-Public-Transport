import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Bus, Activity, BarChart3, Settings, MapPin } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Trip Planner', path: '/trip-planner', icon: MapPin },
  { name: 'Predict Demand', path: '/predict', icon: TrendingUp },
  { name: 'Optimize Fleet', path: '/optimize', icon: Bus },
  { name: 'System Health', path: '/health', icon: Activity },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 h-screen flex flex-col shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <Bus className="w-6 h-6 text-sky-400 mr-3" />
        <span className="text-lg font-bold text-slate-100 tracking-wide">Smart Transit</span>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => twMerge(
                clsx(
                  'flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group',
                  isActive 
                    ? 'bg-sky-500/10 text-sky-400 shadow-[inset_2px_0_0_0_#38bdf8]' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                )
              )}
            >
              <Icon className="w-5 h-5 mr-3 shrink-0" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <button className="flex items-center px-3 py-2.5 w-full rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <Settings className="w-5 h-5 mr-3" />
          Settings
        </button>
      </div>
    </aside>
  );
}
