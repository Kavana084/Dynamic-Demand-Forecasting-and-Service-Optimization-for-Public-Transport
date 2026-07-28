import { Outlet, useNavigate } from 'react-router-dom';
import { LogOut, User, Menu } from 'lucide-react';
import clsx from 'clsx';
import { clearAuthSession, getAuthSession, isAuthenticated } from '../../utils/auth';
import ThemeToggle from '../ThemeToggle';
import { useState, useRef } from 'react';
import ModernSidebar from './ModernSidebar';

export default function PassengerLayout() {
  const navigate = useNavigate();
  const session = getAuthSession();
  const authenticated = isAuthenticated();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    clearAuthSession();
    navigate('/', { replace: true });
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(prev => !prev);
  };

  return (
    <div className="min-h-screen bg-background flex font-sans text-ink">
      {/* Modern Sidebar */}
      <ModernSidebar mobileOpen={mobileMenuOpen} setMobileOpen={setMobileMenuOpen} />

      {/* Main Content Area */}
      <div className="flex-1 md:ml-20 flex flex-col">
        {/* Header */}
        <header className="bg-sidebar border-b border-border shadow-st-sm sticky top-0 z-40 h-16">
          <div className="h-full px-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Mobile menu button */}
              <button
                onClick={toggleMobileMenu}
                className="md:hidden p-2 rounded-lg hover:bg-background text-muted hover:text-ink smooth-transition"
                aria-label="Toggle menu"
              >
                <Menu className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-lg font-bold text-ink">
                  {authenticated ? `Good ${getGreeting()}, ${session.username || 'Traveller'} 👋` : 'Welcome to Smart Transit'}
                </h1>
                <p className="text-xs text-muted">Where are you travelling today?</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <ThemeToggle compact />
              {authenticated ? (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface border border-border">
                    <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold text-sm shadow-st-sm">
                      {(session.username || 'U').charAt(0).toUpperCase()}
                    </div>
                    <p className="text-sm font-semibold hidden sm:block">{session.username || 'User'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="theme-button-primary gap-2 py-2 px-4 smooth-transition"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="hidden sm:inline">Logout</span>
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => navigate('/login')}
                    className="theme-button-secondary py-2 px-4 smooth-transition"
                  >
                    <span>Login</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/signup')}
                    className="theme-button-primary py-2 px-4 smooth-transition"
                  >
                    <span>Sign Up</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content — scrollable */}
        <main className="flex-1 p-6 overflow-y-auto" style={{ scrollBehavior: 'smooth' }}>
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="bg-sidebar border-t border-border py-3">
          <div className="px-6 flex flex-col items-center justify-center text-center text-muted text-xs gap-1">
            <p>&copy; {new Date().getFullYear()} AI Smart Transit Assistant</p>
            <p className="text-muted-2">Version 1.0 | Powered by AI Route Optimization</p>
          </div>
        </footer>
      </div>
    </div>
  );
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Morning';
  if (hour < 18) return 'Afternoon';
  return 'Evening';
}
