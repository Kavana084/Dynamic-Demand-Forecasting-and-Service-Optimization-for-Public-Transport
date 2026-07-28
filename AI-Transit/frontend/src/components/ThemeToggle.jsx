import { useEffect, useMemo, useState } from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';
import clsx from 'clsx';
import { getThemePreference, setThemePreference } from '../theme/theme';

const options = [
  { key: 'light', label: 'Light', icon: Sun },
  { key: 'dark', label: 'Dark', icon: Moon },
  { key: 'auto', label: 'Auto', icon: Monitor },
];

export default function ThemeToggle({ compact = false }) {
  const [pref, setPref] = useState(() => getThemePreference());

  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'st.theme') setPref(getThemePreference());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const sizeClass = useMemo(() => (compact ? 'h-9 px-2 text-xs' : 'h-10 px-2.5 text-sm'), [compact]);

  return (
    <div
      className={clsx(
        'inline-flex items-center rounded-xl border border-border bg-surface shadow-st-sm p-1',
        compact ? 'gap-0.5' : 'gap-1'
      )}
      role="group"
      aria-label="Theme selection"
    >
      {options.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          onClick={() => {
            setPref(key);
            setThemePreference(key);
          }}
          className={clsx(
            'st-focusable inline-flex items-center gap-2 rounded-lg transition-colors',
            sizeClass,
            pref === key
              ? 'bg-primary text-white'
              : 'text-muted hover:bg-background'
          )}
          aria-pressed={pref === key}
        >
          <Icon className={clsx(compact ? 'h-4 w-4' : 'h-4 w-4')} />
          {!compact && <span className="font-semibold">{label}</span>}
        </button>
      ))}
    </div>
  );
}

