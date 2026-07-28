import { NavLink, useNavigate } from 'react-router-dom';
import { Navigation, Bot, History, BookMarked, X, Map, LayoutDashboard, MapPin } from 'lucide-react';
import clsx from 'clsx';
import { useState, useEffect } from 'react';

const navItems = [
  {
    name: 'Dashboard Overview',
    path: '/dashboard',
    icon: LayoutDashboard,
    desc: 'System overview',
  },
  {
    name: 'Journey Planner',
    path: '/plan-journey',
    icon: MapPin,
    desc: 'Plan your route',
  },
  {
    name: 'Route History',
    path: '/route-history',
    icon: History,
    desc: 'Past journeys',
  },
  {
    name: 'AI Assistant',
    path: '/ai-assistant',
    icon: Bot,
    desc: 'Get travel help',
  },
];

export default function ModernSidebar({ mobileOpen, setMobileOpen }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [aiPulse, setAiPulse] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Pulse AI suggestion indicator every 8s
  useEffect(() => {
    const interval = setInterval(() => setAiPulse(p => !p), 4000);
    return () => clearInterval(interval);
  }, []);

  const handleMouseEnter = () => { if (!isMobile) setIsExpanded(true); };
  const handleMouseLeave = () => { if (!isMobile) setIsExpanded(false); };

  const internalMobileOpen = isMobile ? mobileOpen : false;
  const setInternalMobileOpen = setMobileOpen || (() => {});
  const showLabels = isExpanded || isMobile;

  return (
    <>
      {/* Mobile backdrop */}
      {isMobile && internalMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setInternalMobileOpen(false)}
        />
      )}

      <aside
        className={clsx(
          'fixed left-0 top-0 h-screen z-50 flex flex-col',
          'transition-all duration-300 ease-in-out',
          isMobile
            ? internalMobileOpen ? 'w-72 translate-x-0' : '-translate-x-full w-72'
            : isExpanded ? 'w-72' : 'w-20'
        )}
        style={{
          background: 'var(--st-sidebar)',
          borderRight: '1px solid var(--st-border)',
          boxShadow: '4px 0 24px rgba(0,0,0,0.06)',
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* ── Logo Area ──────────────────────────────────────────────────── */}
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: showLabels ? '0 20px' : '0 14px',
          borderBottom: '1px solid var(--st-border)',
          transition: 'padding 0.3s',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Logo Icon */}
            <div style={{
              width: 44,
              height: 44,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #2563EB 0%, #1d4ed8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(37,99,235,0.35)',
              flexShrink: 0,
            }}>
              <Navigation size={22} color="#fff" />
            </div>

            {/* Brand name — visible when expanded */}
            {showLabels && (
              <div style={{ animation: 'fadeSlide 0.2s ease' }}>
                <p style={{ fontSize: 16, fontWeight: 800, color: 'var(--st-ink)', margin: 0, lineHeight: 1.2 }}>
                  Smart Transit
                </p>
                <p style={{ fontSize: 11, color: '#2563EB', margin: 0, fontWeight: 600 }}>
                  Passenger Portal
                </p>
              </div>
            )}
          </div>

          {/* Mobile close */}
          {isMobile && (
            <button
              onClick={() => setInternalMobileOpen(false)}
              style={{
                width: 32, height: 32, borderRadius: 8,
                background: 'var(--st-background)',
                border: '1px solid var(--st-border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: 'var(--st-muted)',
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* ── Navigation Items ────────────────────────────────────────────── */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '16px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {showLabels && (
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--st-muted-2)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '4px 12px 8px', margin: 0 }}>
              Navigation
            </p>
          )}
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={() => isMobile && setInternalMobileOpen(false)}
                title={!showLabels ? item.name : undefined}
                className={({ isActive }) => clsx(
                  'nav-item-link',
                  isActive ? 'nav-item-active' : 'nav-item-default'
                )}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: showLabels ? '12px 14px' : '12px',
                  borderRadius: 14,
                  textDecoration: 'none',
                  justifyContent: showLabels ? 'flex-start' : 'center',
                  transition: 'all 0.2s ease',
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(37,99,235,0.15) 0%, rgba(37,99,235,0.08) 100%)'
                    : 'transparent',
                  border: isActive ? '1px solid rgba(37,99,235,0.25)' : '1px solid transparent',
                  position: 'relative',
                  overflow: 'hidden',
                })}
              >
                {({ isActive }) => (
                  <>
                    {/* Active indicator bar */}
                    {isActive && (
                      <div style={{
                        position: 'absolute',
                        left: 0,
                        top: '20%',
                        bottom: '20%',
                        width: 3,
                        borderRadius: '0 4px 4px 0',
                        background: '#2563EB',
                      }} />
                    )}

                    {/* Icon chip */}
                    <div style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      background: isActive
                        ? 'linear-gradient(135deg, #2563EB 0%, #1d4ed8 100%)'
                        : 'var(--st-background)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      boxShadow: isActive ? '0 4px 10px rgba(37,99,235,0.3)' : 'none',
                      border: isActive ? 'none' : '1px solid var(--st-border)',
                      fontSize: 16,
                      transition: 'all 0.2s',
                    }}>
                      {isActive ? <Icon size={18} color="#fff" /> : <Icon size={18} color="var(--st-muted)" />}
                    </div>

                    {/* Label + desc */}
                    {showLabels && (
                      <div style={{ animation: 'fadeSlide 0.2s ease' }}>
                        <p style={{
                          margin: 0,
                          fontSize: 13,
                          fontWeight: isActive ? 700 : 500,
                          color: isActive ? '#2563EB' : 'var(--st-ink)',
                          lineHeight: 1.2,
                        }}>
                          {item.name}
                        </p>
                        {item.desc && (
                          <p style={{ margin: 0, fontSize: 10, color: 'var(--st-muted)', marginTop: 1 }}>
                            {item.desc}
                          </p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>



        {/* ── Live status bar ─────────────────────────────────────────────── */}
        <div style={{
          borderTop: '1px solid var(--st-border)',
          padding: showLabels ? '12px 20px' : '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: showLabels ? 'flex-start' : 'center',
          gap: 8,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: '#22C55E',
            animation: 'pulse-dot 2s ease-in-out infinite',
          }} />
          {showLabels && (
            <span style={{ fontSize: 11, color: 'var(--st-muted)', fontWeight: 500 }}>
              Live updates active
            </span>
          )}
        </div>
      </aside>

      {/* Sidebar animations */}
      <style>{`
        @keyframes fadeSlide {
          from { opacity: 0; transform: translateX(-8px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes ai-pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.7; }
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        .ai-card-hover:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 32px rgba(37,99,235,0.5) !important;
        }
        .nav-item-link:hover:not(.nav-item-active) {
          background: var(--st-background) !important;
          border-color: var(--st-border) !important;
        }
      `}</style>
    </>
  );
}
