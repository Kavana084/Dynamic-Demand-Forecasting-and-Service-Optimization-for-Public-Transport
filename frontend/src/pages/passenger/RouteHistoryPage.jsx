import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History, MapPin, Clock, ArrowRight, Navigation, TrendingUp,
  Calendar, RotateCcw, ChevronLeft, ChevronRight, AlertCircle,
  Loader2, Route, ExternalLink, Star, Repeat, Users,
} from 'lucide-react';
import { getJourneyHistory } from '../../api/client';
import { isAuthenticated, clearAuthSession } from '../../utils/auth';
import clsx from 'clsx';

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;

  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatTime(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function formatFullDate(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function groupByRelativeDate(items) {
  const groups = {};
  items.forEach((item) => {
    const label = formatDate(item.created_at);
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  });
  return Object.entries(groups);
}

// ─── Skeleton Loader ────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="modern-card p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-muted rounded-2xl" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-muted rounded w-1/3" />
          <div className="h-2 bg-muted rounded w-1/4" />
        </div>
      </div>
      <div className="h-3 bg-muted rounded w-3/4" />
    </div>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-b border-border animate-pulse">
      {[1, 2, 3, 4, 5, 6, 7].map((i) => (
        <td key={i} className="px-4 py-4">
          <div className="h-3 bg-muted rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

// ─── Summary Card ────────────────────────────────────────────────────────────

function SummaryCard({ icon: Icon, label, value, sub, gradient }) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl p-5 text-white flex flex-col gap-2 shadow-lg smooth-transition hover:shadow-xl hover:-translate-y-1"
      style={{ background: gradient }}
    >
      {/* decorative circle */}
      <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-white/10" />
      <div className="absolute -bottom-6 -left-6 w-24 h-24 rounded-full bg-white/5" />

      <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center z-10">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <p className="text-xs font-semibold uppercase tracking-widest text-white/70 z-10">{label}</p>
      <p className="text-2xl font-extrabold leading-none z-10">{value}</p>
      {sub && <p className="text-xs text-white/60 z-10">{sub}</p>}
    </div>
  );
}

// ─── Timeline item ───────────────────────────────────────────────────────────

function TimelineItem({ item, onViewRoute, isLast }) {
  return (
    <div className="flex gap-4">
      {/* Spine */}
      <div className="flex flex-col items-center">
        <div className="w-10 h-10 rounded-2xl bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5 border-2 border-primary/20">
          <Route className="w-5 h-5 text-primary" />
        </div>
        {!isLast && <div className="flex-1 w-px bg-border mt-3 mb-0" />}
      </div>

      {/* Content */}
      <div className="pb-6 flex-1 min-w-0">
        <div className="modern-card p-4 hover:bg-background smooth-transition cursor-pointer" onClick={() => onViewRoute(item)}>
          <div className="flex items-start justify-between gap-2 flex-wrap mb-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="font-semibold text-ink text-sm truncate">
                  {item.source_stop_name || item.source_stop_id || 'Unknown'}
                </span>
                <ArrowRight className="w-4 h-4 text-muted flex-shrink-0" />
                <span className="font-semibold text-ink text-sm truncate">
                  {item.destination_stop_name || item.destination_stop_id || 'Unknown'}
                </span>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                {item.route_summary && (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 px-2.5 py-1 rounded-full">
                    <Route className="w-3 h-3" />
                    {item.route_summary}
                  </span>
                )}
                {item.estimated_duration != null && (
                  <span className="text-xs text-muted flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {item.estimated_duration} min
                  </span>
                )}
                {item.transfer_count != null && (
                  <span className="text-xs text-muted flex items-center gap-1">
                    <Repeat className="w-3 h-3" /> {item.transfer_count} transfer{item.transfer_count !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-xs text-muted">{formatTime(item.created_at)}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onViewRoute(item);
                }}
                className="theme-button-secondary text-xs py-1.5 px-3 gap-1 smooth-transition"
              >
                <Navigation className="w-3 h-3" />
                Replan
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Empty State ─────────────────────────────────────────────────────────────

function EmptyState({ navigate }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div
        className="w-20 h-20 rounded-3xl flex items-center justify-center mb-6 shadow-lg"
        style={{ background: 'linear-gradient(135deg, #7C3AED, #8B5CF6)' }}
      >
        <History className="w-9 h-9 text-white" />
      </div>
      <h3 className="text-xl font-bold text-ink mb-2">No journey history available.</h3>
      <p className="text-muted text-sm max-w-xs leading-relaxed mb-8">
        Once you plan a trip, it will appear here so you can easily revisit and replay your routes.
      </p>
      <button
        onClick={() => navigate('/plan-journey')}
        className="theme-button-primary gap-2 px-6 py-3 smooth-transition"
      >
        <Navigation className="w-4 h-4" />
        Plan Your First Journey
      </button>
    </div>
  );
}

// ─── Unauthenticated State ───────────────────────────────────────────────────

function UnauthState({ navigate }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-warning/10 flex items-center justify-center mb-5">
        <AlertCircle className="w-8 h-8 text-warning" />
      </div>
      <h3 className="text-xl font-bold text-ink mb-2">Sign in to view your history</h3>
      <p className="text-muted text-sm max-w-xs mb-8">
        Journey history is personal. Please log in to see your previously planned trips.
      </p>
      <div className="flex gap-3">
        <button onClick={() => navigate('/login')} className="theme-button-primary gap-2 px-5 py-2.5 smooth-transition">
          Login
        </button>
        <button onClick={() => navigate('/plan-journey')} className="theme-button-secondary gap-2 px-5 py-2.5 smooth-transition">
          Plan Journey
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function RouteHistoryPage() {
  const navigate = useNavigate();
  const authenticated = isAuthenticated();

  const [history, setHistory] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('timeline'); // 'table' | 'timeline'

  const LIMIT = 15;
  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  const fetchHistory = useCallback(async (pg = 1) => {
    if (!authenticated) return;
    setLoading(true);
    setError('');
    try {
      const data = await getJourneyHistory(pg, LIMIT);
      setHistory(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      if (err.status === 401 || err.response?.status === 401) {
        clearAuthSession();
        navigate('/login', { state: { message: 'Session expired. Please log in again.' } });
        return;
      }
      setError(err.message || 'Failed to load journey history.');
    } finally {
      setLoading(false);
    }
  }, [authenticated, navigate]);

  useEffect(() => {
    fetchHistory(page);
  }, [page, fetchHistory]);

  // ── Summary Stats ────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!history.length) return null;

    const avgDuration = history.reduce((s, h) => s + (h.estimated_duration || 0), 0) / history.length;
    const lastJourney = history[0];

    // Most used destination
    const destCount = {};
    history.forEach((h) => {
      const d = h.destination_stop_name || h.destination_stop_id || 'Unknown';
      destCount[d] = (destCount[d] || 0) + 1;
    });
    const mostUsedDest = Object.entries(destCount).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—';

    return {
      total,
      mostUsedDest,
      avgDuration: avgDuration ? `${Math.round(avgDuration)} min` : '—',
      lastJourneyDate: lastJourney ? formatDate(lastJourney.created_at) : '—',
      lastJourneyRoute: lastJourney
        ? `${lastJourney.source_stop_name || '?'} → ${lastJourney.destination_stop_name || '?'}`
        : '—',
    };
  }, [history, total]);

  const timelineGroups = useMemo(() => groupByRelativeDate(history), [history]);

  const handleViewRoute = useCallback((item) => {
    if (item.source_stop_id && item.destination_stop_id) {
      navigate('/plan-journey', {
        state: {
          prefill: {
            source_id: item.source_stop_id,
            destination_id: item.destination_stop_id,
          },
        },
      });
    } else {
      navigate('/plan-journey');
    }
  }, [navigate]);

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #7C3AED, #8B5CF6)' }}
          >
            <History className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-ink">Journey History</h2>
            <p className="text-muted text-sm mt-0.5">Review your previous journey plans.</p>
          </div>
        </div>

        {authenticated && history.length > 0 && (
          <button
            onClick={() => fetchHistory(page)}
            disabled={loading}
            className="theme-button-secondary gap-2 py-2 smooth-transition"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            Refresh
          </button>
        )}
      </div>

      {/* ── Unauthenticated ── */}
      {!authenticated && (
        <div className="modern-card">
          <UnauthState navigate={navigate} />
        </div>
      )}

      {authenticated && (
        <>
          {/* ── Error Banner ── */}
          {error && (
            <div className="flex items-center gap-3 bg-danger/10 border border-danger/30 text-danger rounded-2xl px-5 py-4">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm font-medium">{error}</p>
              <button
                className="ml-auto text-xs font-semibold underline smooth-transition"
                onClick={() => fetchHistory(page)}
              >
                Retry
              </button>
            </div>
          )}

          {/* ── Summary Cards ── */}
          {loading && !history.length ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 rounded-2xl bg-muted animate-pulse" />
              ))}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <SummaryCard
                icon={TrendingUp}
                label="Total Trips"
                value={stats.total}
                sub="planned journeys"
                gradient="linear-gradient(135deg, #7C3AED, #8B5CF6)"
              />
              <SummaryCard
                icon={Star}
                label="Most Used Destination"
                value={stats.mostUsedDest}
                sub="most frequent"
                gradient="linear-gradient(135deg, #06b6d4, #0284c7)"
              />
              <SummaryCard
                icon={Clock}
                label="Avg Travel Time"
                value={stats.avgDuration}
                sub="estimated"
                gradient="linear-gradient(135deg, #10b981, #059669)"
              />
              <SummaryCard
                icon={Calendar}
                label="Last Journey"
                value={stats.lastJourneyDate}
                sub={stats.lastJourneyRoute}
                gradient="linear-gradient(135deg, #f59e0b, #d97706)"
              />
            </div>
          ) : null}

          {/* ── Empty State ── */}
          {!loading && !error && history.length === 0 && (
            <div className="modern-card">
              <EmptyState navigate={navigate} />
            </div>
          )}

          {/* ── Tabs + Content ── */}
          {history.length > 0 && (
            <div className="modern-card overflow-hidden">
              {/* Tab bar */}
              <div className="flex items-center gap-1 border-b border-border px-6 pt-4">
                {[
                  { key: 'timeline', label: 'Timeline', icon: History },
                  { key: 'table', label: 'History Table', icon: MapPin },
                ].map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-xl border-b-2 smooth-transition ${
                      activeTab === key
                        ? 'border-primary text-primary bg-primary/5'
                        : 'border-transparent text-muted hover:text-ink hover:bg-background'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                ))}
                <div className="ml-auto pb-2">
                  <span className="text-xs text-muted font-medium bg-background px-3 py-1.5 rounded-full border border-border">
                    {total} trip{total !== 1 ? 's' : ''} total
                  </span>
                </div>
              </div>

              {/* ── TIMELINE TAB ── */}
              {activeTab === 'timeline' && (
                <div className="p-6 space-y-8">
                  {loading ? (
                    <div className="space-y-4">
                      {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
                    </div>
                  ) : (
                    timelineGroups.map(([dateLabel, items]) => (
                      <div key={dateLabel}>
                        {/* Date header */}
                        <div className="flex items-center gap-3 mb-4">
                          <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                            <Calendar className="w-4 h-4 text-primary" />
                          </div>
                          <h4 className="text-sm font-bold text-ink">{dateLabel}</h4>
                          <div className="flex-1 h-px bg-border" />
                          <span className="text-xs text-muted">{items.length} trip{items.length !== 1 ? 's' : ''}</span>
                        </div>

                        {/* Timeline items */}
                        <div className="ml-4 border-l-2 border-border pl-6 space-y-0">
                          {items.map((item, idx) => (
                            <TimelineItem
                              key={item.id}
                              item={item}
                              onViewRoute={handleViewRoute}
                              isLast={idx === items.length - 1}
                            />
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ── TABLE TAB ── */}
              {activeTab === 'table' && (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px]">
                    <thead>
                      <tr className="bg-background border-b border-border">
                        {['Date', 'Time', 'Source', 'Destination', 'Route', 'Transfers', 'Duration', 'Action'].map((h) => (
                          <th
                            key={h}
                            className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider whitespace-nowrap"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {loading
                        ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
                        : history.map((item) => (
                            <tr
                              key={item.id}
                              className="hover:bg-background/70 smooth-transition group"
                            >
                              <td className="px-4 py-3.5 whitespace-nowrap">
                                <span className="text-xs font-semibold text-ink bg-background px-2 py-1 rounded-xl border border-border">
                                  {formatFullDate(item.created_at)}
                                </span>
                              </td>
                              <td className="px-4 py-3.5 text-xs text-muted whitespace-nowrap">
                                {formatTime(item.created_at)}
                              </td>
                              <td className="px-4 py-3.5">
                                <div className="flex items-center gap-1.5">
                                  <MapPin className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                                  <span className="text-sm text-ink font-medium max-w-[130px] truncate" title={item.source_stop_name}>
                                    {item.source_stop_name || item.source_stop_id || '—'}
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-3.5">
                                <div className="flex items-center gap-1.5">
                                  <MapPin className="w-3.5 h-3.5 text-success flex-shrink-0" />
                                  <span className="text-sm text-ink font-medium max-w-[130px] truncate" title={item.destination_stop_name}>
                                    {item.destination_stop_name || item.destination_stop_id || '—'}
                                  </span>
                                </div>
                              </td>
                              <td className="px-4 py-3.5">
                                {item.route_summary ? (
                                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 px-2.5 py-1 rounded-full whitespace-nowrap">
                                    <Route className="w-3 h-3" />
                                    {item.route_summary}
                                  </span>
                                ) : (
                                  <span className="text-muted text-xs">—</span>
                                )}
                              </td>
                              <td className="px-4 py-3.5 text-center">
                                <span className={clsx('text-xs font-bold px-2.5 py-1 rounded-full',
                                  item.transfer_count === 0
                                    ? 'bg-success/10 text-success'
                                    : 'bg-warning/10 text-warning'
                                )}>
                                  {item.transfer_count ?? '—'}
                                </span>
                              </td>
                              <td className="px-4 py-3.5 text-sm text-muted whitespace-nowrap">
                                {item.estimated_duration != null
                                  ? `${item.estimated_duration} min`
                                  : '—'}
                              </td>
                              <td className="px-4 py-3.5">
                                <button
                                  onClick={() => handleViewRoute(item)}
                                  className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-accent-indigo hover:bg-primary/10 px-3 py-1.5 rounded-xl smooth-transition border border-primary/20 group-hover:border-primary/40"
                                >
                                  <Navigation className="w-3 h-3" />
                                  View Route
                                </button>
                              </td>
                            </tr>
                          ))}
                    </tbody>
                  </table>

                  {/* ── Pagination ── */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-border">
                      <p className="text-xs text-muted">
                        Page <span className="font-semibold">{page}</span> of{' '}
                        <span className="font-semibold">{totalPages}</span>
                        {' '}· {total} total trips
                      </p>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={page === 1 || loading}
                          className="theme-button-secondary p-2 disabled:opacity-40 smooth-transition"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-sm font-semibold text-ink min-w-[2rem] text-center">
                          {page}
                        </span>
                        <button
                          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                          disabled={page === totalPages || loading}
                          className="theme-button-secondary p-2 disabled:opacity-40 smooth-transition"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── CTA when there are few trips ── */}
          {!loading && history.length > 0 && history.length < 5 && (
            <div
              className="modern-card p-6 flex items-center justify-between flex-wrap gap-4"
              style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.07), rgba(139,92,246,0.05))' }}
            >
              <div>
                <p className="font-semibold text-ink text-sm">Ready for your next journey?</p>
                <p className="text-muted text-xs mt-1">Plan a new trip and it will automatically appear in your history.</p>
              </div>
              <button
                onClick={() => navigate('/plan-journey')}
                className="theme-button-primary gap-2 py-2.5 smooth-transition"
              >
                <Navigation className="w-4 h-4" />
                Plan Journey
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
