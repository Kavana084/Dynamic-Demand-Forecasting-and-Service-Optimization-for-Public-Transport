import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  Sliders,
  Users,
  Shield,
  LogOut,
} from 'lucide-react';
import clsx from 'clsx';
import { clearAuthSession, getAuthSession } from '../../utils/auth';

const navItems = [
  { label: 'Overview', to: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Demand Analytics', to: '/admin/analytics', icon: Activity },
  { label: 'Fleet Optimization', to: '/admin/fleet', icon: Sliders },
  { label: 'User Administration', to: '/admin/access', icon: Users },
];

export default function AdminSidebar() {
  const navigate = useNavigate();
  const { role, username } = getAuthSession();

  const handleLogout = () => {
    clearAuthSession();
    navigate('/login', { replace: true });
  };

  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-[260px] flex-col border-r border-border bg-sidebar text-ink shadow-st-sm select-none">
      {/* Top Logo Section */}
      <div className="border-b border-border px-6 py-5 bg-sidebar">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: 'color-mix(in srgb, var(--st-primary) 12%, transparent)', color: 'var(--st-primary)' }}>
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 leading-none">ADMIN PORTAL</p>
            <h1 className="text-base font-bold mt-1">Smart Transit</h1>
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 space-y-1.5 px-4 py-6 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-st-sm font-semibold'
                    : 'text-muted hover:bg-background hover:text-ink'
                )
              }
            >
              <Icon className="h-4.5 w-4.5 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom User Card & Logout */}
      <div className="border-t border-border p-4 bg-background">
        <div className="flex items-center gap-3 mb-4 p-2 rounded-xl bg-surface border border-border shadow-st-sm">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold uppercase" style={{ background: 'color-mix(in srgb, var(--st-primary) 14%, transparent)', color: 'var(--st-primary)', border: '1px solid color-mix(in srgb, var(--st-primary) 18%, var(--st-border))' }}>
            {(username || 'A').charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate">
              {username || 'admin'}
            </p>
            <p className="text-xs text-muted font-medium truncate">
              {role === 'Admin' ? 'Administrator' : (role || 'Administrator')}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs font-semibold text-muted transition-colors hover:bg-background hover:text-ink"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
