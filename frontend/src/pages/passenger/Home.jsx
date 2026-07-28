import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Navigation,
  Bell,
  MapPin,
  Clock,
  ArrowRight,
  Sparkles,
  Thermometer,
  Cloud,
  Sun,
  CloudRain,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Bot,
  History,
  Activity,
  Wifi,
} from 'lucide-react';
import { isAuthenticated } from '../../utils/auth';
import { getAlerts } from '../../api/client';

function getGreeting() {
  const hour = new Date().getHours();
  if (hour >= 0 && hour < 12) return 'Morning';
  if (hour >= 12 && hour < 17) return 'Afternoon';
  return 'Evening';
}

function getWeatherCondition() {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 18) return { temp: 28, condition: 'Clear Sky', icon: Sun, advice: 'Good conditions for travelling.' };
  return { temp: 24, condition: 'Clear Night', icon: Cloud, advice: 'Cool evening, comfortable for travel.' };
}

export default function Home() {
  const navigate = useNavigate();
  const authed = isAuthenticated();
  const session = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('authSession') || '{}');
    } catch {
      return {};
    }
  }, []);

  const [alerts, setAlerts] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    getAlerts()
      .then((d) => setAlerts(d?.alerts || d || []))
      .catch(() => setAlerts(null));

    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const serviceState = useMemo(() => {
    if (alerts === null) return { tone: 'warning', label: 'Status unavailable', icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' };
    if (alerts.length === 0) return { tone: 'success', label: 'All Services Running Normally', icon: CheckCircle2, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' };
    const hasMajor = alerts.some(a => a.severity === 'high' || a.severity === 'critical');
    if (hasMajor) return { tone: 'danger', label: 'Major Disruptions', icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', border: 'border-danger/20' };
    return { tone: 'warning', label: 'Minor Delays', icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' };
  }, [alerts]);

  const weather = getWeatherCondition();
  const greeting = getGreeting();

  const quickActions = [
    { icon: Navigation, label: 'Plan Journey', description: 'Find the best route', path: '/plan-journey', color: 'bg-primary/10 text-primary' },
    { icon: Bot, label: 'AI Assistant', description: 'Get smart help', path: '/ai-assistant', color: 'bg-accent-indigo/10 text-accent-indigo' },
    { icon: History, label: 'Journey History', description: 'View past trips', path: '/route-history', color: 'bg-accent-cyan/10 text-accent-cyan' },
    { icon: Bell, label: 'Service Alerts', description: 'Check disruptions', path: '/alerts', color: 'bg-warning/10 text-warning' },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="modern-card bg-gradient-to-r from-primary/10 to-accent-indigo/10 border-primary/20 overflow-hidden relative">
        <div className="p-4 md:p-6">
          <div className="grid grid-cols-3 gap-4 relative z-10">
            {/* Left - Greeting */}
            <div className="flex flex-col justify-center">
              <h1 className="text-xl md:text-2xl font-bold text-ink mb-1">
                Good {greeting}{session.username ? `, ${session.username}` : ''}
              </h1>
              <p className="text-muted text-sm">Ready for your next journey?</p>
            </div>
            {/* Middle - Date/Time */}
            <div className="flex flex-col items-center justify-center gap-2 text-center">
              <p className="text-lg md:text-xl font-semibold text-ink">{currentTime.toLocaleDateString()}</p>
              <p className="text-3xl md:text-4xl font-extrabold text-primary">{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
              <div className="flex items-center gap-2 text-xs text-muted">
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                Live System
              </div>
            </div>
            {/* Right - Bus Image */}
            <div className="flex items-center justify-center">
              <img src="/Bus.png" alt="Bus" className="w-32 h-32 md:w-40 md:h-40 object-contain opacity-80" />
            </div>
          </div>
        </div>
      </div>

      {/* Primary Action */}
      <button
        onClick={() => navigate('/plan-journey')}
        className="w-full theme-button-primary py-4 gap-2 text-base font-semibold shadow-st-md hover:shadow-st-lg hover:-translate-y-1"
      >
        <Navigation className="w-5 h-5" />
        Plan Journey
        <ArrowRight className="w-5 h-5" />
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Transit Network Status */}
        <div className="modern-card p-5 flex flex-col">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl ${serviceState.bg} ${serviceState.border} border flex items-center justify-center`}>
              <serviceState.icon className={`w-5 h-5 ${serviceState.color}`} />
            </div>
            <div>
              <h3 className={`text-sm font-bold ${serviceState.color}`}>Transit Status</h3>
              <p className="text-xs text-muted">Live overview</p>
            </div>
          </div>
          <div className={`flex items-center gap-2 p-3 rounded-lg ${serviceState.bg} ${serviceState.border} border flex-1`}>
            <serviceState.icon className={`w-6 h-6 ${serviceState.color}`} />
            <p className={`text-base font-extrabold ${serviceState.color}`}>{serviceState.label}</p>
          </div>
        </div>

        {/* Active Service Alerts */}
        <div className="modern-card p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-danger/10 flex items-center justify-center">
                <Bell className="w-5 h-5 text-danger" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-ink">Service Alerts</h3>
                <p className="text-xs text-muted">Latest disruptions</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/alerts')}
              className="text-xs font-semibold text-primary hover:text-primary-hover smooth-transition"
            >
              View All
            </button>
          </div>
          
          {alerts === null ? (
            <div className="text-center py-3 flex-1 flex items-center justify-center">
              <p className="text-sm text-muted">Unable to load</p>
            </div>
          ) : alerts.length === 0 ? (
            <div className="text-center py-3 flex-1 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-success mx-auto mb-1" />
              <p className="text-xs font-semibold text-ink">No disruptions</p>
            </div>
          ) : (
            <div className="space-y-2 flex-1">
              {alerts.slice(0, 2).map((alert, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-background border border-border hover:bg-background/80 smooth-transition">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className={clsx(
                      'text-xs font-semibold',
                      alert.severity?.toLowerCase() === 'high' || alert.severity?.toLowerCase() === 'critical'
                        ? 'text-danger'
                        : 'text-warning'
                    )}>
                      {alert.severity || 'Info'}
                    </span>
                    <span className="text-xs text-muted">
                      {alert.updated_at ? new Date(alert.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-ink mb-0.5 line-clamp-1">{alert.title || alert.message || 'Service Alert'}</p>
                  <p className="text-xs text-muted line-clamp-1">{alert.description || alert.message || 'No description available.'}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Weather Card */}
        <div className="modern-card p-5 flex flex-col">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-accent-cyan/10 flex items-center justify-center">
              <weather.icon className="w-5 h-5 text-accent-cyan" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-ink">Weather</h3>
              <p className="text-xs text-muted">Current conditions</p>
            </div>
          </div>
          <div className="bg-gradient-to-br from-accent-cyan/20 to-accent-indigo/20 rounded-xl p-4 flex-1 flex flex-col justify-center">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-2xl font-extrabold text-ink">{weather.temp}°C</p>
                <p className="text-xs text-muted">{weather.condition}</p>
              </div>
              <weather.icon className="w-10 h-10 text-accent-cyan" />
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-success/20 text-success px-2 py-1 rounded-full text-xs font-semibold">
                {weather.advice}
              </span>
            </div>
          </div>
        </div>

        {/* AI Assistant Card */}
        <div className="modern-card p-5 flex flex-col bg-gradient-to-br from-primary/5 to-accent-indigo/5 border-primary/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-ink">AI Assistant</h3>
              <p className="text-xs text-muted">Your travel companion</p>
            </div>
          </div>
          <p className="text-xs text-ink mb-4">
            Need help planning your journey? Ask about routes, delays, or transit information.
          </p>
          <div className="mt-auto flex justify-center">
            <button
              onClick={() => navigate('/ai-assistant')}
              className="w-12 h-12 rounded-[14px] bg-primary flex items-center justify-center shadow-md shadow-primary/30 hover:scale-110 transition-transform duration-200 cursor-pointer"
              title="Chat with AI Assistant"
            >
              <Bot className="w-6 h-6 text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
