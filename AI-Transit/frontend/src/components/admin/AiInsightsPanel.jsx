import { Brain, Sparkles, HelpCircle, ArrowRight } from 'lucide-react';
import clsx from 'clsx';

function ConfidenceBar({ value }) {
  const pct = Math.max(0, Math.min(100, Math.round((value ?? 0) * 100)));
  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-[11px] text-muted">
        <span>Confidence</span>
        <span className="font-semibold text-ink">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-background overflow-hidden border border-border mt-1">
        <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AiInsightsPanel({ insights = [], onDrillDown }) {
  return (
    <div className="rounded-2xl border border-border bg-surface shadow-st-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center gap-2">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: 'color-mix(in srgb, var(--st-primary) 12%, transparent)' }}
        >
          <Brain className="w-4.5 h-4.5 text-primary" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-ink">AI Insights</h3>
          <p className="text-xs text-muted">Explainable recommendations for today’s operations.</p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {insights.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-background/60 p-4 text-center text-sm text-muted">
            No insights available yet. Run forecasting and optimization to populate recommendations.
          </div>
        ) : (
          insights.map((it, idx) => (
            <div key={idx} className="rounded-xl border border-border bg-background/50 p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface border border-border">
                  <Sparkles className="w-4 h-4 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-ink">{it.recommendation}</p>
                  {it.explainability && (
                    <p className="text-xs text-muted mt-1 flex items-start gap-2">
                      <HelpCircle className="w-3.5 h-3.5 mt-0.5 text-muted-2 shrink-0" />
                      <span>{it.explainability}</span>
                    </p>
                  )}
                  {typeof it.confidence === 'number' ? <ConfidenceBar value={it.confidence} /> : null}

                  {Array.isArray(it.actions) && it.actions.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {it.actions.map((a, i) => (
                        <button
                          key={i}
                          type="button"
                          className={clsx(
                            'st-focusable inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-ink hover:bg-background'
                          )}
                          onClick={() => onDrillDown?.(a)}
                        >
                          <span>{a.label}</span>
                          <ArrowRight className="w-3.5 h-3.5 text-muted" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
