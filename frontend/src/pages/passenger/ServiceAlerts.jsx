import { useState, useEffect } from 'react';
import { getAlerts } from '../../api/client';
import { Bell, CloudRain, Car, AlertTriangle, ShieldCheck, RefreshCw, Loader2, AlertCircle, X, Filter, Clock } from 'lucide-react';
import clsx from 'clsx';

function AlertCardSkeleton() {
  return (
    <div className="modern-card p-6 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-muted rounded-2xl" />
        <div className="flex-1 space-y-2">
          <div className="h-5 bg-muted rounded w-1/3" />
          <div className="h-4 bg-muted rounded w-1/4" />
          <div className="h-16 bg-muted rounded w-full" />
        </div>
      </div>
    </div>
  );
}

export default function ServiceAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');

  const fetchAlerts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getAlerts();
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
      setError(err.message || 'Failed to load service alerts');
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const getIcon = (type) => {
    switch (type) {
      case 'Weather': return <CloudRain className="w-6 h-6 text-accent-cyan" />;
      case 'Traffic': return <Car className="w-6 h-6 text-warning" />;
      case 'Demand': return <AlertTriangle className="w-6 h-6 text-danger" />;
      default: return <ShieldCheck className="w-6 h-6 text-success" />;
    }
  };

  const getSeverityConfig = (severity) => {
    switch (severity) {
      case 'Critical': return {
        bg: 'bg-danger/10',
        border: 'border-danger/30',
        badge: 'bg-danger text-white',
        icon: 'text-danger'
      };
      case 'High': return {
        bg: 'bg-warning/10',
        border: 'border-warning/30',
        badge: 'bg-warning text-white',
        icon: 'text-warning'
      };
      case 'Medium': return {
        bg: 'bg-accent-cyan/10',
        border: 'border-accent-cyan/30',
        badge: 'bg-accent-cyan text-white',
        icon: 'text-accent-cyan'
      };
      default: return {
        bg: 'bg-success/10',
        border: 'border-success/30',
        badge: 'bg-success text-white',
        icon: 'text-success'
      };
    }
  };

  const filteredAlerts = filter === 'all' 
    ? alerts 
    : alerts.filter(alert => alert.severity === filter);

  const severityCounts = {
    all: alerts.length,
    Critical: alerts.filter(a => a.severity === 'Critical').length,
    High: alerts.filter(a => a.severity === 'High').length,
    Medium: alerts.filter(a => a.severity === 'Medium').length,
    Normal: alerts.filter(a => a.severity === 'Normal').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center">
            <Bell className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-ink">Service Alerts</h2>
            <p className="text-sm text-muted">Live updates on disruptions and service status</p>
          </div>
        </div>
        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="theme-button-secondary st-focusable py-2 px-4 gap-2 smooth-transition"
        >
          <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {['all', 'Critical', 'High', 'Medium', 'Normal'].map((severity) => (
          <button
            key={severity}
            onClick={() => setFilter(severity)}
            className={clsx(
              'st-focusable rounded-full px-4 py-2 text-sm font-medium border smooth-transition',
              filter === severity
                ? 'bg-primary text-white border-primary'
                : 'bg-surface text-muted border-border hover:text-ink hover:bg-background'
            )}
          >
            {severity === 'all' ? 'All' : severity}
            {severity !== 'all' && severityCounts[severity] > 0 && (
              <span className="ml-1 bg-white/20 px-2 py-0.5 rounded-full text-xs">
                {severityCounts[severity]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <AlertCardSkeleton key={i} />)}
        </div>
      ) : error ? (
        <div className="bg-danger/10 border border-danger/30 rounded-2xl p-8 text-center">
          <AlertCircle className="w-16 h-16 text-danger mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-ink mb-2">Unable to load service alerts</h3>
          <p className="text-muted text-sm mb-4">{error}</p>
          <button
            onClick={fetchAlerts}
            className="theme-button-primary st-focusable py-2 px-4 gap-2 smooth-transition"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="bg-success/10 border border-success/30 rounded-2xl p-12 text-center">
          <ShieldCheck className="w-20 h-20 text-success mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-ink mb-2">
            {filter === 'all' ? 'All systems operational' : `No ${filter.toLowerCase()} alerts`}
          </h3>
          <p className="text-muted text-sm mb-4">
            {filter === 'all' 
              ? 'There are currently no active service alerts.' 
              : `There are no ${filter.toLowerCase()} severity alerts at this time.`}
          </p>
          {filter !== 'all' && (
            <button
              onClick={() => setFilter('all')}
              className="theme-button-secondary st-focusable py-2 px-4 smooth-transition"
            >
              View all alerts
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAlerts.map((alert, idx) => {
            const config = getSeverityConfig(alert.severity);
            return (
              <div 
                key={idx} 
                className={clsx("modern-card p-6 flex items-start gap-4", config.bg, config.border)}
              >
                <div className={clsx("w-12 h-12 rounded-2xl bg-surface flex items-center justify-center flex-shrink-0 shadow-sm", config.icon)}>
                  {getIcon(alert.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <h3 className="text-lg font-bold text-ink">{alert.title}</h3>
                    <span className={clsx("text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider", config.badge)}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-muted mt-2">{alert.message}</p>
                  {alert.affected_routes && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {alert.affected_routes.map((route, i) => (
                        <span 
                          key={i}
                          className="inline-flex items-center gap-1 bg-surface/50 px-3 py-1 rounded-full text-xs font-medium text-ink border border-border"
                        >
                          Route {route}
                        </span>
                      ))}
                    </div>
                  )}
                  {alert.expected_resolution && (
                    <p className="text-xs text-muted mt-3 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Expected resolution: {alert.expected_resolution}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
