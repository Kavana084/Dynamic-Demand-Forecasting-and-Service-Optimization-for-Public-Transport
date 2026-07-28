"""
audit_admin_dashboard.py
========================
Phase 2 Validation: Admin Dashboard Data Audit

Maps every admin dashboard card, chart, metric, and KPI to:
  - UI Component
  - API Endpoint
  - Backend Function
  - Database Source
  - Calculation Logic
  - Hardcoded? (Yes/No)

Flags:
  - Hardcoded values
  - Duplicated calculations
  - Stale metrics
  - Disconnected widgets
  - Unused backend endpoints

Output: dashboard_data_audit.md
"""

import os
import sys
import datetime
import sqlite3

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "transit_admin_secret")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "dashboard_data_audit.md")

# ---------------------------------------------------------------------------
# Static traceability map (from code analysis)
# ---------------------------------------------------------------------------

TRACEABILITY = [
    # ─── Admin Dashboard Bootstrap ──────────────────────────────────────────
    {
        "ui_component":    "Overview KPIs — Total Passengers",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:747",
        "db_source":       "DemandHistory.passenger_count (SUM)",
        "calc_logic":      "SUM(passenger_count) for date window, scope-filtered",
        "hardcoded":       "No",
        "stale_risk":      "Medium — defaults to 'today' window; empty if no data today",
        "issues":          [],
    },
    {
        "ui_component":    "Overview KPIs — Forecasted Demand",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:843",
        "db_source":       "ForecastHistory.predicted_passengers (SUM, latest per route)",
        "calc_logic":      "SUM of most recent forecast per route within date window",
        "hardcoded":       "No",
        "stale_risk":      "Medium — depends on scheduled pipeline writing to ForecastHistory",
        "issues":          [],
    },
    {
        "ui_component":    "Overview KPIs — Active Routes",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:830",
        "db_source":       "OptimizationResult.route_id (COUNT DISTINCT)",
        "calc_logic":      "COUNT(DISTINCT route_id) from OptimizationResult within window; fallback = total ever",
        "hardcoded":       "No",
        "stale_risk":      "High — shows 0 if no optimization run in current date window; fallback hides staleness",
        "issues":          ["Fallback to all-time count masks zero-optimization-runs scenario"],
    },
    {
        "ui_component":    "Overview KPIs — Allocated Buses",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:848",
        "db_source":       "OptimizationResult.allocated_buses (SUM, latest per route)",
        "calc_logic":      "SUM of allocated_buses from most recent optimization per route",
        "hardcoded":       "No",
        "stale_risk":      "Medium",
        "issues":          [],
    },
    {
        "ui_component":    "Overview KPIs — Avg Fleet Utilization",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:852",
        "db_source":       "OptimizationResult.utilization (AVG)",
        "calc_logic":      "AVG(utilization) from latest OptimizationResult per route — uses MILP-stored value directly",
        "hardcoded":       "No",
        "stale_risk":      "Medium — depends on optimization runs",
        "issues":          [],
    },
    {
        "ui_component":    "Overview KPIs — Assumed Bus Capacity (returned in payload)",
        "api_endpoint":    "GET /api/admin/overview-kpis",
        "backend_fn":      "get_overview_kpis() in admin.py:876",
        "db_source":       "None",
        "calc_logic":      "Constant: DEFAULT_BUS_CAPACITY = 50 (admin.py:24)",
        "hardcoded":       "Yes — 50 pax/bus constant",
        "stale_risk":      "N/A",
        "issues":          ["Conflicts with fleet_optimization_service.py which uses 60 pax/bus"],
    },
    # ─── Optimization Insights ───────────────────────────────────────────────
    {
        "ui_component":    "Optimization Insights — Allocated vs Required Buses",
        "api_endpoint":    "GET /api/admin/optimization/insights",
        "backend_fn":      "get_optimization_insights() in admin.py:488",
        "db_source":       "OptimizationResult (latest 250 records by model_version)",
        "calc_logic":      "total_required = SUM(ceil(predicted_demand/50)); total_allocated = SUM(allocated_buses)",
        "hardcoded":       "Partial — DEFAULT_BUS_CAPACITY=50 hardcoded in _required_buses()",
        "stale_risk":      "Low",
        "issues":          ["Uses 50 pax/bus for required calc; MILP used different capacity for allocation"],
    },
    {
        "ui_component":    "Optimization Insights — Avg Utilization",
        "api_endpoint":    "GET /api/admin/optimization/insights",
        "backend_fn":      "get_optimization_insights() in admin.py:511",
        "db_source":       "OptimizationResult.predicted_demand + allocated_buses",
        "calc_logic":      "_utilization() = demand / (allocated * capacity), clamped 0-1; capacity=50",
        "hardcoded":       "Partial — capacity=50 constant",
        "stale_risk":      "Low",
        "issues":          ["Recalculates utilization from raw fields rather than using stored OptimizationResult.utilization"],
    },
    {
        "ui_component":    "Optimization Insights — Recommendations",
        "api_endpoint":    "GET /api/admin/optimization/insights",
        "backend_fn":      "get_optimization_insights() in admin.py:542",
        "db_source":       "OptimizationResult + ForecastHistory (confidence by route)",
        "calc_logic":      "Dynamic: flags top-3 shortage routes; confidence from ForecastHistory AVG",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    # ─── Analytics Demand ────────────────────────────────────────────────────
    {
        "ui_component":    "Analytics Dashboard — Demand Summary",
        "api_endpoint":    "GET /api/admin/analytics/demand",
        "backend_fn":      "get_analytics_demand() → AnalyticsService.get_dashboard_summary()",
        "db_source":       "ForecastHistory (count) + DemandHistory (avg) + DemandHistory (top routes)",
        "calc_logic":      "total_predictions=COUNT(ForecastHistory); avg=AVG(DemandHistory.passenger_count); highest_route=GROUP BY route_id",
        "hardcoded":       "No",
        "stale_risk":      "High — defaults to 'today'; shows zeros if pipeline has not run today",
        "issues":          [],
    },
    {
        "ui_component":    "Analytics Dashboard — Top 5 Routes",
        "api_endpoint":    "GET /api/admin/analytics/demand",
        "backend_fn":      "AnalyticsService.get_top_routes()",
        "db_source":       "DemandHistory (AVG passenger_count per route)",
        "calc_logic":      "GROUP BY route_id, ORDER BY AVG(passenger_count) DESC, LIMIT 5",
        "hardcoded":       "No",
        "stale_risk":      "Medium",
        "issues":          [],
    },
    {
        "ui_component":    "Analytics Dashboard — Demand Heatmap (hour x route)",
        "api_endpoint":    "GET /api/admin/analytics/demand-heatmap",
        "backend_fn":      "AnalyticsService.get_demand_heatmap()",
        "db_source":       "DemandHistory (SUM passenger_count grouped by route_id + hour)",
        "calc_logic":      "SQLite: strftime('%H',timestamp); PostgreSQL: EXTRACT(hour). Top 8 routes by total pax.",
        "hardcoded":       "No",
        "stale_risk":      "Medium",
        "issues":          [],
    },
    # ─── Charts ──────────────────────────────────────────────────────────────
    {
        "ui_component":    "Demand Trend Chart",
        "api_endpoint":    "GET /api/admin/charts/demand-trend",
        "backend_fn":      "get_demand_trend_chart() in admin.py:955",
        "db_source":       "ForecastHistory (ordered by target_timestamp ASC, limit 100)",
        "calc_logic":      "Direct DB read; no calculations",
        "hardcoded":       "No",
        "stale_risk":      "Medium",
        "issues":          [],
    },
    {
        "ui_component":    "Fleet Utilization Chart",
        "api_endpoint":    "GET /api/admin/charts/fleet-utilization",
        "backend_fn":      "get_fleet_utilization_chart() in admin.py:980",
        "db_source":       "OptimizationResult (ordered ASC, limit 100)",
        "calc_logic":      "_utilization(predicted_demand, allocated_buses) — recalculated, not from stored field",
        "hardcoded":       "Partial — capacity=50 in _utilization()",
        "stale_risk":      "Low",
        "issues":          ["Recalculates utilization rather than using stored OptimizationResult.utilization — may differ"],
    },
    # ─── Tables ──────────────────────────────────────────────────────────────
    {
        "ui_component":    "Recent Demand Table",
        "api_endpoint":    "GET /api/admin/tables/recent-demand",
        "backend_fn":      "get_recent_demand_table() in admin.py:881",
        "db_source":       "DemandHistory (limit 10, DESC)",
        "calc_logic":      "Direct DB read",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    {
        "ui_component":    "Latest Predictions Table",
        "api_endpoint":    "GET /api/admin/tables/latest-predictions",
        "backend_fn":      "get_latest_predictions_table() in admin.py:905",
        "db_source":       "ForecastHistory (limit 10, DESC)",
        "calc_logic":      "Direct DB read",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    {
        "ui_component":    "Recent Optimizations Table",
        "api_endpoint":    "GET /api/admin/tables/recent-optimizations",
        "backend_fn":      "get_recent_optimizations_table() in admin.py:930",
        "db_source":       "OptimizationResult (limit 10, DESC)",
        "calc_logic":      "_utilization() recalculated — same divergence issue as fleet chart",
        "hardcoded":       "Partial — capacity=50 in _utilization()",
        "stale_risk":      "Low",
        "issues":          ["Utilization recalculated vs stored — potential inconsistency"],
    },
    # ─── AI Performance ──────────────────────────────────────────────────────
    {
        "ui_component":    "AI Performance Panel",
        "api_endpoint":    "GET /api/admin/ai/performance",
        "backend_fn":      "ForecastAlignmentService.get_alignment_report()",
        "db_source":       "ForecastHistory + DemandHistory",
        "calc_logic":      "Compares predicted vs actual to compute RMSE/MAE; dynamic",
        "hardcoded":       "No",
        "stale_risk":      "Medium — requires both ForecastHistory and DemandHistory to have overlapping data",
        "issues":          [],
    },
    # ─── Pipeline Monitor ────────────────────────────────────────────────────
    {
        "ui_component":    "Pipeline Monitor Panel",
        "api_endpoint":    "GET /api/admin/pipeline/monitor",
        "backend_fn":      "PipelineMonitorService.get_pipeline_status()",
        "db_source":       "PipelineExecutionLog",
        "calc_logic":      "Aggregation of pipeline run records",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    {
        "ui_component":    "Pipeline Validation Panel",
        "api_endpoint":    "GET /api/admin/pipeline/validation",
        "backend_fn":      "get_pipeline_validation() in admin.py:377",
        "db_source":       "JourneyHistory + DemandHistory + ForecastHistory + OptimizationResult",
        "calc_logic":      "COUNT per table; filters by ACTIVE_MODEL_VERSION='catboost+demand_adjusted'",
        "hardcoded":       "Partial — ACTIVE_MODEL_VERSION='catboost+demand_adjusted' is a string constant",
        "stale_risk":      "Low",
        "issues":          ["ACTIVE_MODEL_VERSION constant could silently filter out all records if model version changes"],
    },
    # ─── Data Quality ────────────────────────────────────────────────────────
    {
        "ui_component":    "Data Quality Panel",
        "api_endpoint":    "GET /api/admin/data-quality",
        "backend_fn":      "DataQualityService.get_data_quality()",
        "db_source":       "Multiple tables",
        "calc_logic":      "Checks for nulls, stale records, etc.",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    # ─── System Health ───────────────────────────────────────────────────────
    {
        "ui_component":    "System Health Panel",
        "api_endpoint":    "GET /api/admin/system/health",
        "backend_fn":      "SystemMonitorService.get_system_health()",
        "db_source":       "SystemMetric table",
        "calc_logic":      "Reads real-time system metrics",
        "hardcoded":       "No",
        "stale_risk":      "Low",
        "issues":          [],
    },
    # ─── Historical Monitoring ───────────────────────────────────────────────
    {
        "ui_component":    "Historical Monitoring — RMSE Trend",
        "api_endpoint":    "GET /api/admin/historical/monitoring",
        "backend_fn":      "get_historical_monitoring() in admin.py:717",
        "db_source":       "ModelMetadata (RMSE) + ForecastHistory + OptimizationResult",
        "calc_logic":      "Direct DB reads; forecastAccuracyTrend is always returned EMPTY []",
        "hardcoded":       "Yes — forecastAccuracyTrend: [] hardcoded in response",
        "stale_risk":      "High — forecastAccuracyTrend is always empty",
        "issues":          ["admin.py:739: `'forecastAccuracyTrend': []` is hardcoded empty — disconnected widget"],
    },
    # ─── Demand Prediction Page (non-admin) ──────────────────────────────────
    {
        "ui_component":    "PredictDemand.jsx — Model Confidence display",
        "api_endpoint":    "POST /api/predict_demand",
        "backend_fn":      "predict_demand() in api_routes.py:153",
        "db_source":       "ML model (CatBoost via PredictionService)",
        "calc_logic":      "Returns only: { route_id, predicted_demand, cached }. Confidence NOT returned.",
        "hardcoded":       "Yes — frontend PredictDemand.jsx:42 sets `confidence: 85` as fallback",
        "stale_risk":      "N/A",
        "issues":          [
            "Hardcoded confidence=85 in frontend regardless of model output",
            "CatBoost returns confidence_score (0.97 typical) but it is stripped at API boundary",
        ],
    },
    # ─── Old Dashboard endpoint ──────────────────────────────────────────────
    {
        "ui_component":    "Dashboard.jsx — System Health field",
        "api_endpoint":    "GET /api/dashboard",
        "backend_fn":      "get_dashboard() in api_routes.py:292",
        "db_source":       "None",
        "calc_logic":      "Returns literal string 'Unavailable'",
        "hardcoded":       "Yes — `'systemHealth': 'Unavailable'` hardcoded",
        "stale_risk":      "N/A",
        "issues":          ["api_routes.py:352: systemHealth='Unavailable' hardcoded", "api_routes.py:353: modelMetrics='Unavailable' hardcoded"],
    },
    {
        "ui_component":    "Dashboard.jsx — Fleet Available Buses",
        "api_endpoint":    "GET /api/dashboard",
        "backend_fn":      "get_dashboard() in api_routes.py:305",
        "db_source":       "None",
        "calc_logic":      "Returns literal 1000",
        "hardcoded":       "Yes — `'available': 1000` hardcoded",
        "stale_risk":      "N/A",
        "issues":          ["api_routes.py:306: available=1000 hardcoded — not from DB or config"],
    },
    # ─── Disconnected frontend endpoints ────────────────────────────────────
    {
        "ui_component":    "Frontend client.js — getDashboardUtilization()",
        "api_endpoint":    "GET /api/dashboard/utilization",
        "backend_fn":      "MISSING",
        "db_source":       "N/A",
        "calc_logic":      "N/A",
        "hardcoded":       "N/A",
        "stale_risk":      "N/A",
        "issues":          ["Endpoint /api/dashboard/utilization does not exist in backend — returns 404"],
    },
    {
        "ui_component":    "Frontend client.js — getDashboardForecastTrend(routeId)",
        "api_endpoint":    "GET /api/dashboard/forecast_trend/:id",
        "backend_fn":      "MISSING",
        "db_source":       "N/A",
        "calc_logic":      "N/A",
        "hardcoded":       "N/A",
        "stale_risk":      "N/A",
        "issues":          ["Endpoint /api/dashboard/forecast_trend/:id does not exist in backend — returns 404"],
    },
]

# ---------------------------------------------------------------------------
# Endpoint probing (optional, if backend is running)
# ---------------------------------------------------------------------------

PROBE_ENDPOINTS = [
    ("GET", "/api/admin/overview-kpis"),
    ("GET", "/api/admin/analytics/demand"),
    ("GET", "/api/admin/analytics/demand-heatmap"),
    ("GET", "/api/admin/pipeline/monitor"),
    ("GET", "/api/admin/pipeline/validation"),
    ("GET", "/api/admin/optimization/insights"),
    ("GET", "/api/admin/data-quality"),
    ("GET", "/api/admin/system/health"),
    ("GET", "/api/admin/historical/monitoring"),
    ("GET", "/api/admin/charts/demand-trend"),
    ("GET", "/api/admin/charts/fleet-utilization"),
    ("GET", "/api/admin/tables/recent-demand"),
    ("GET", "/api/admin/tables/latest-predictions"),
    ("GET", "/api/admin/tables/recent-optimizations"),
    ("GET", "/api/admin/dashboard/bootstrap"),
    ("GET", "/api/admin/ai/performance"),
    # Should 404:
    ("GET", "/api/dashboard/utilization"),
    ("GET", "/api/dashboard/forecast_trend/TEST"),
]

def probe_endpoints(requests_lib):
    results = {}
    for method, path in PROBE_ENDPOINTS:
        try:
            if method == "GET":
                r = requests_lib.get(
                    f"{BACKEND_URL}{path}",
                    headers={"X-Admin-Token": ADMIN_TOKEN, "Authorization": f"Bearer dummy"},
                    timeout=8
                )
            results[path] = r.status_code
        except Exception as e:
            results[path] = f"ERROR: {e}"
    return results

# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------

def run_dashboard_audit():
    requests_lib = None
    api_available = False
    endpoint_probe = {}

    try:
        import requests as rq
        requests_lib = rq
        r = requests_lib.get(f"{BACKEND_URL}/api/routes?limit=1", timeout=5)
        api_available = r.status_code in (200, 401, 403)
    except Exception:
        pass

    if api_available and requests_lib:
        print("[Dashboard Audit] Backend reachable, probing endpoints...")
        endpoint_probe = probe_endpoints(requests_lib)
    else:
        print("[Dashboard Audit] Backend not reachable, using static analysis only.")

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []

    lines.append("# Admin Dashboard Data Audit")
    lines.append(f"\n**Generated**: {now_str}")
    lines.append(f"**Backend**: {BACKEND_URL} (reachable: {api_available})")
    lines.append(f"**Method**: Static code analysis + runtime endpoint probing\n")
    lines.append("---\n")

    # 1. Full traceability table
    lines.append("## 1. Full Data Traceability Table\n")
    lines.append("| UI Component | API Endpoint | Backend Function | DB Source | Calculation Logic | Hardcoded? |")
    lines.append("|---|---|---|---|---|---|")
    for row in TRACEABILITY:
        hc = "🔴 Yes" if row["hardcoded"] == "Yes" else ("⚠️ Partial" if "Partial" in row["hardcoded"] else "✅ No")
        calc_short = row["calc_logic"][:80] + ("…" if len(row["calc_logic"]) > 80 else "")
        lines.append(f"| {row['ui_component']} | `{row['api_endpoint']}` | `{row['backend_fn']}` | {row['db_source']} | {calc_short} | {hc} |")
    lines.append("")

    # 2. Hardcoded values
    lines.append("## 2. Hardcoded Values\n")
    hardcoded_items = [r for r in TRACEABILITY if "Yes" in r["hardcoded"] or "Partial" in r["hardcoded"]]
    for item in hardcoded_items:
        lines.append(f"### `{item['api_endpoint']}`")
        lines.append(f"- **Component**: {item['ui_component']}")
        lines.append(f"- **Issue**: {item['hardcoded']}")
        for iss in item["issues"]:
            lines.append(f"  - {iss}")
        lines.append("")

    # 3. Disconnected widgets
    lines.append("## 3. Disconnected / Missing Endpoints\n")
    disconnected = [r for r in TRACEABILITY if "MISSING" in r["backend_fn"]]
    if disconnected:
        lines.append("| UI Component | Endpoint Called | Status |")
        lines.append("|---|---|---|")
        for d in disconnected:
            probe_status = endpoint_probe.get(d["api_endpoint"], "not probed")
            lines.append(f"| {d['ui_component']} | `{d['api_endpoint']}` | {probe_status} |")
    else:
        lines.append("✅ No missing endpoints detected.\n")
    lines.append("")

    # 4. Duplicated calculations
    lines.append("## 4. Duplicated Calculations\n")
    lines.append("| Calculation | Implemented In |")
    lines.append("|---|---|")
    lines.append("| `required_buses = ceil(demand/capacity)` | `admin.py:287 _required_buses()` AND `fleet_optimization_service.py:185 optimize()` AND `fleet_service.py:31` |")
    lines.append("| `utilization = demand / (allocated * capacity)` | `admin.py:295 _utilization()` AND `fleet_optimization_service.py:199` AND `optimization.py:88` |")
    lines.append("| `_apply_route_scope_filter()` | `admin.py:80` AND `analytics_service.py:18` (duplicate function) |")
    lines.append("| `_normalize_scope()` | `admin.py:27` AND `analytics_service.py:9` (duplicate function) |")
    lines.append("")
    lines.append("> ⚠️ These duplicated calculations are not centralized. Changes to the formula in one location")
    lines.append("> will NOT propagate to the others, causing silent inconsistencies.\n")

    # 5. Stale metric risk
    lines.append("## 5. Stale Metric Risk\n")
    stale_items = [r for r in TRACEABILITY if r["stale_risk"] in ("High", "Medium")]
    lines.append("| UI Component | Stale Risk | Reason |")
    lines.append("|---|---|---|")
    for s in stale_items:
        lines.append(f"| {s['ui_component']} | **{s['stale_risk']}** | {s['db_source']} — {s['stale_risk']} |")
    lines.append("")

    # 6. Endpoint probe results
    if endpoint_probe:
        lines.append("## 6. Live Endpoint Probe Results\n")
        lines.append("| Endpoint | HTTP Status | Expected |")
        lines.append("|---|---|---|")
        for ep, status in endpoint_probe.items():
            expected = "4xx" if "utilization" in ep or "forecast_trend" in ep else "200/401"
            ok = "✅" if (
                (str(status) in ("200", "401", "403") and "4xx" not in expected) or
                (str(status) in ("404", "405") and "4xx" in expected)
            ) else "❌"
            lines.append(f"| `{ep}` | {status} | {expected} | {ok} |")
        lines.append("")

    # 7. Unused backend endpoints
    lines.append("## 7. Unused Backend Endpoints\n")
    lines.append("The following admin endpoints exist in `admin.py` but are not referenced in any frontend component:\n")
    lines.append("| Endpoint | File | Notes |")
    lines.append("|---|---|---|")
    lines.append("| `GET /api/admin/filter-options` | admin.py:100 | Provides region/depot dropdowns — may be used by future filter UI |")
    lines.append("| `GET /api/admin/dashboard/insights` | admin.py:131 | Dashboard insights — separate from bootstrap; check if UI calls this |")
    lines.append("| `GET /api/admin/forecast-history` | admin.py:1042 | Direct ForecastHistory dump — may only be used by debug tools |")
    lines.append("| `GET /api/admin/demand-history` | admin.py:1007 | Direct DemandHistory dump — audit trail only |")
    lines.append("| `GET /api/admin/optimization/results` | admin.py:1077 | Direct OptimizationResult dump |")
    lines.append("")

    # 8. Key findings
    lines.append("## 8. Key Findings\n")
    all_issues = []
    for row in TRACEABILITY:
        for iss in row["issues"]:
            all_issues.append((row["ui_component"], iss))

    for comp, iss in all_issues:
        lines.append(f"- **{comp}**: {iss}")
    lines.append("")

    report_text = "\n".join(lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[Dashboard Audit] Report written to: {REPORT_PATH}")
    critical = sum(1 for r in TRACEABILITY if "Yes" in r["hardcoded"] or "MISSING" in r["backend_fn"])
    print(f"  Hardcoded/missing issues: {critical}")
    return critical


if __name__ == "__main__":
    issues = run_dashboard_audit()
    sys.exit(0 if issues == 0 else 1)
