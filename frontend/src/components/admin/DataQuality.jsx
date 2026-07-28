import React, { useState, useEffect } from 'react';

/**
 * DataQuality — reads /api/admin/data-quality
 *
 * Backend response contract (DataQualityService):
 * {
 *   overall_score:      number (0–100),
 *   completeness_score: number (0–100),
 *   freshness_score:    number (0–100),
 *   consistency_score:  number (0–100),
 *   integrity_score:    number (0–100),
 *   details: {
 *     missing_weather_records: number,
 *     optimization_failures:   number,
 *     gtfs_stops:              number
 *   }
 * }
 */
export default function DataQuality() {
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuality();
  }, []);

  const fetchQuality = async () => {
    try {
      const token =
        localStorage.getItem('access_token') || localStorage.getItem('token');
      const res = await fetch('/api/admin/data-quality', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setQuality(await res.json());
    } catch (err) {
      console.error('[DataQuality]', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading)
    return (
      <div className="p-8 text-center text-gray-500 animate-pulse">
        Loading Data Quality...
      </div>
    );

  if (!quality)
    return (
      <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
        <h3 className="text-xl font-medium text-gray-600 mb-2">
          Data Quality Unavailable
        </h3>
        <p className="text-gray-400">
          Unable to compute data quality metrics at this time.
        </p>
      </div>
    );

  /**
   * Sub-score definitions.
   * Keys match DataQualityService response exactly (with _score suffix).
   */
  const subScores = [
    {
      label: 'Completeness (40%)',
      value: quality.completeness_score ?? 0,
      color: 'bg-blue-500',
    },
    {
      label: 'Freshness (30%)',
      value: quality.freshness_score ?? 0,
      color: 'bg-emerald-500',
    },
    {
      label: 'Consistency (20%)',
      value: quality.consistency_score ?? 0,
      color: 'bg-amber-500',
    },
    {
      label: 'Integrity (10%)',
      value: quality.integrity_score ?? 0,
      color: 'bg-purple-500',
    },
  ];

  /**
   * Detail tiles — only fields that the backend actually returns.
   * Removed: missing_demand, missing_predictions, gtfs_anomalies
   *   (these fields do not exist in the API response).
   * Present: missing_weather_records, optimization_failures, gtfs_stops
   */
  const detailTiles = [
    {
      label: 'Missing Weather Records',
      value: quality.details?.missing_weather_records ?? 0,
      cls: 'border-red-100 bg-red-50 text-red-800 font-bold-value text-red-600',
      labelCls: 'text-red-800',
      valueCls: 'text-red-600',
    },
    {
      label: 'Optimization Failures',
      value: quality.details?.optimization_failures ?? 0,
      labelCls: 'text-orange-800',
      valueCls: 'text-orange-600',
      cls: 'border-orange-100 bg-orange-50',
    },
    {
      label: 'GTFS Stops (Integrity)',
      value: quality.details?.gtfs_stops ?? 0,
      labelCls: 'text-teal-800',
      valueCls: 'text-teal-600',
      cls: 'border-teal-100 bg-teal-50',
    },
  ];

  const overallScore = quality.overall_score ?? 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
      <h2 className="text-xl font-semibold text-gray-800 border-b border-gray-100 pb-4">
        Data Quality Dashboard
      </h2>

      {/* Overall score ring + sub-scores */}
      <div className="flex flex-col md:flex-row items-center gap-8">
        {/* Score ring */}
        <div className="w-48 h-48 rounded-full border-8 border-gray-50 flex items-center justify-center relative shadow-inner shrink-0">
          <div
            className="absolute inset-0 rounded-full border-8 border-indigo-500"
            style={{
              clipPath: `polygon(0 0, 100% 0, 100% ${overallScore}%, 0 ${overallScore}%)`,
            }}
          />
          <div className="text-center z-10">
            <span className="block text-4xl font-bold text-gray-800">
              {overallScore}%
            </span>
            <span className="text-xs font-medium text-gray-400 uppercase tracking-widest mt-1">
              Overall Score
            </span>
          </div>
        </div>

        {/* Sub-score bars */}
        <div className="flex-1 w-full grid grid-cols-2 gap-4">
          {subScores.map(({ label, value, color }) => (
            <div
              key={label}
              className="p-4 rounded-lg bg-gray-50 border border-gray-100"
            >
              <div className="text-xs font-semibold text-gray-500 uppercase mb-1">
                {label}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-gray-800">
                  {value}%
                </span>
                <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${color}`}
                    style={{ width: `${Math.min(100, value)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail tiles — backed by real API fields only */}
      <div className="mt-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Pipeline Detail Monitor
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {detailTiles.map(({ label, value, cls, labelCls, valueCls }) => (
            <div
              key={label}
              className={`border p-3 rounded-lg flex justify-between items-center ${cls}`}
            >
              <span className={`text-xs font-medium ${labelCls}`}>{label}</span>
              <span className={`text-lg font-bold ${valueCls}`}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
