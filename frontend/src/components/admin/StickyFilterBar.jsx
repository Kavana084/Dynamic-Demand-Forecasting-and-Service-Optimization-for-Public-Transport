import { Download, RefreshCw, CalendarRange, Clock } from 'lucide-react';
import clsx from 'clsx';

function isoDateString(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function Field({ label, icon: Icon, children }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
        <Icon className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>
      {children}
    </div>
  );
}

export default function StickyFilterBar({
  filters,
  onChange,
  onRefresh,
  onExport,
  lastRefreshedLabel,
}) {
  const handlePresetChange = (e) => {
    const val = e.target.value;
    const today = new Date();
    let from = '';
    let to = isoDateString(today);

    if (val === 'Today') {
      from = isoDateString(today);
    } else if (val === 'Yesterday') {
      const yesterday = new Date(today);
      yesterday.setDate(today.getDate() - 1);
      from = isoDateString(yesterday);
      to = isoDateString(yesterday);
    } else if (val === 'Last 7 Days') {
      const last7 = new Date(today);
      last7.setDate(today.getDate() - 6);
      from = isoDateString(last7);
    } else if (val === 'Last 30 Days') {
      const last30 = new Date(today);
      last30.setDate(today.getDate() - 29);
      from = isoDateString(last30);
    } else if (val === 'Custom Range') {
      from = filters.dateFrom || isoDateString(today);
      to = filters.dateTo || isoDateString(today);
    }

    onChange({ ...filters, dateRangePreset: val, dateFrom: from, dateTo: to });
  };

  const isCustom = filters.dateRangePreset === 'Custom Range';

  return (
    <div className="sticky top-0 z-10 -mx-8 px-8 py-3 border-b border-border bg-surface/85 backdrop-blur-md">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex flex-col sm:flex-row gap-3">
          <Field label="Date Range" icon={Clock}>
            <select
              className="theme-input st-focusable h-10 w-full sm:w-48"
              value={filters.dateRangePreset || 'Today'}
              onChange={handlePresetChange}
            >
              <option value="Today">Today</option>
              <option value="Yesterday">Yesterday</option>
              <option value="Last 7 Days">Last 7 Days</option>
              <option value="Last 30 Days">Last 30 Days</option>
              <option value="Custom Range">Custom Range</option>
            </select>
          </Field>
          {isCustom && (
            <>
              <Field label="From" icon={CalendarRange}>
                <input
                  type="date"
                  className="theme-input st-focusable h-10 w-full"
                  value={filters.dateFrom || ''}
                  onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
                  aria-label="From date"
                />
              </Field>
              <Field label="To" icon={CalendarRange}>
                <input
                  type="date"
                  className="theme-input st-focusable h-10 w-full"
                  value={filters.dateTo || ''}
                  onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
                  aria-label="To date"
                />
              </Field>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-between mt-2 xl:mt-0">
          <div className="text-xs text-muted mr-4">
            {lastRefreshedLabel ? (
              <span>Last Updated: <span className="font-semibold text-ink">{lastRefreshedLabel}</span></span>
            ) : (
              <span className="text-muted">Not refreshed yet</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onExport}
              className={clsx(
                'theme-button-secondary st-focusable py-2 px-3 gap-2 text-xs',
              )}
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <button
              type="button"
              onClick={onRefresh}
              className="theme-button-primary st-focusable py-2 px-3 gap-2 text-xs"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
