import { Outlet, useLocation } from 'react-router-dom';
import { AppProvider } from '../../context/AppContext';
import AdminSidebar from './AdminSidebar';
import { ShieldCheck } from 'lucide-react';
import ThemeToggle from '../ThemeToggle';

const routeDetailsMap = {
  '/admin/dashboard': {
    title: 'Overview & AI',
    subtitle: 'Operational view for transit administration and system oversight.'
  },
  '/admin/analytics': {
    title: 'Demand Analytics',
    subtitle: 'Deep-dive analytical tools for historical and predictive transit demands.'
  },
  '/admin/fleet': {
    title: 'Fleet Optimization',
    subtitle: 'Route-level shortage/surplus, allocation recommendations, and explainability.'
  },
  '/admin/pipeline': {
    title: 'Data Quality & Pipeline',
    subtitle: 'Is today’s data usable? Health, freshness, and pipeline stage readiness.'
  },
  '/admin/access': {
    title: 'User Administration',
    subtitle: 'Manage users, roles, and operational scope assignments.'
  },
  '/admin/audit': {
    title: 'Audit Logs',
    subtitle: 'Security and administrative change logs recorded in the system.'
  }
};

export default function AdminLayout() {
  const location = useLocation();
  const activeRoute = routeDetailsMap[location.pathname] || {
    title: 'Admin Portal',
    subtitle: 'Operational view for transit administration and system oversight.'
  };

  return (
    <AppProvider>
      <div className="min-h-screen bg-background text-ink antialiased font-sans">
        <AdminSidebar />
        <div className="ml-[260px] min-h-screen flex flex-col">
          <header className="sticky top-0 z-20 border-b border-border bg-surface/80 backdrop-blur-md px-8 py-5 flex items-center justify-between">
            <div className="min-w-0">
              <h2 className="text-xl font-bold tracking-tight leading-tight truncate">
                {activeRoute.title}
              </h2>
              <p className="mt-1 text-xs text-muted font-medium truncate">
                {activeRoute.subtitle}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <ThemeToggle compact />
              <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold border border-border bg-background text-muted shadow-st-sm">
                <ShieldCheck className="h-3.5 w-3.5 text-success" />
                System online
              </span>
            </div>
          </header>
          <main className="flex-1 p-8 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </AppProvider>
  );
}
