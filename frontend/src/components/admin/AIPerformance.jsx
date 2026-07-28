import React, { useState, useEffect } from 'react';

export default function AIPerformance() {
  const [performance, setPerformance] = useState(null);
  const [history, setHistory] = useState(null);
  const [pipelineValid, setPipelineValid] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      
      const valRes = await fetch('/api/admin/pipeline/validation', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (valRes.ok) {
        const valData = await valRes.json();
        setPipelineValid(valData);
        if (valData.demand_history?.count === 0 || valData.prediction_records?.count === 0) {
          setLoading(false);
          return;
        }
      }

      const [perfRes, histRes] = await Promise.all([
        fetch('/api/admin/ai/performance', { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch('/api/admin/historical/monitoring', { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      if (perfRes.ok) setPerformance(await perfRes.json());
      if (histRes.ok) setHistory(await histRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse">Loading AI Metrics...</div>;
  if (pipelineValid && pipelineValid.demand_history?.count === 0) {
    return (
      <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
        <h3 className="text-xl font-medium text-gray-600 mb-2">No demand aggregation data available yet.</h3>
        <p className="text-gray-400">Generate some searches or wait for the hourly aggregator to run.</p>
      </div>
    );
  }

  if (pipelineValid && pipelineValid.prediction_records?.count === 0) {
    return (
      <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
        <h3 className="text-xl font-medium text-gray-600 mb-2">No forecasting data available yet.</h3>
        <p className="text-gray-400">Wait for the forecasting pipeline to run.</p>
      </div>
    );
  }
  if (!performance && !history) return (
    <div className="p-12 text-center border-2 border-dashed border-gray-300 rounded-xl">
      <h3 className="text-xl font-medium text-gray-600 mb-2">AI Performance Data Unavailable</h3>
      <p className="text-gray-400">No model metadata or forecast alignment data found.</p>
    </div>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
      <h2 className="text-xl font-semibold text-gray-800 border-b border-gray-100 pb-4">AI Model Performance</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 p-4 rounded-xl border border-indigo-100">
          <div className="text-sm font-medium text-indigo-600 mb-1">RMSE</div>
          <div className="text-2xl font-bold text-gray-900">{performance?.rmse?.toFixed(2) || 'N/A'}</div>
        </div>
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 p-4 rounded-xl border border-emerald-100">
          <div className="text-sm font-medium text-emerald-600 mb-1">MAE</div>
          <div className="text-2xl font-bold text-gray-900">{performance?.mae?.toFixed(2) || 'N/A'}</div>
        </div>
        <div className="bg-gradient-to-br from-amber-50 to-orange-50 p-4 rounded-xl border border-amber-100">
          <div className="text-sm font-medium text-amber-600 mb-1">Accuracy (MAPE)</div>
          <div className="text-2xl font-bold text-gray-900">{performance?.mape ? `${performance.mape.toFixed(2)}%` : 'N/A'}</div>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-4 rounded-xl border border-purple-100">
          <div className="text-sm font-medium text-purple-600 mb-1">Model Version</div>
          <div className="text-xl font-bold text-gray-900 mt-1">{performance?.version || 'N/A'}</div>
        </div>
      </div>

      <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">Feature Importance</h3>
        {performance?.feature_importance === "Feature Importance Data Unavailable" ? (
          <div className="text-gray-500 italic text-sm">{performance.feature_importance}</div>
        ) : (
          <div className="text-gray-800 text-sm">{JSON.stringify(performance?.feature_importance)}</div>
        )}
      </div>

      {history?.rmseTrend && history.rmseTrend.length > 0 && (
        <div>
          <h3 className="text-md font-medium text-gray-800 mb-3">RMSE Historical Trend</h3>
          <div className="h-48 flex items-end space-x-2 border-b border-l border-gray-200 p-2">
            {history.rmseTrend.map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center group">
                <div 
                  className="w-full bg-indigo-400 rounded-t-md group-hover:bg-indigo-500 transition-colors"
                  style={{ height: `${Math.max(10, (h.rmse / Math.max(...history.rmseTrend.map(x=>x.rmse))) * 100)}%` }}
                ></div>
                <div className="text-[10px] text-gray-400 mt-2 rotate-45 origin-left">
                  {new Date(h.timestamp).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
