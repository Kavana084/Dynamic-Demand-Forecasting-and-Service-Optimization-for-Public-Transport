import { useState, useEffect } from 'react';
import { History, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react';
import { getPredictions } from '../api/client';
import clsx from 'clsx';

export default function PredictionHistory() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const limit = 15;

  const fetchPredictions = async (skipCount) => {
    setLoading(true);
    try {
      const data = await getPredictions(skipCount, limit);
      setPredictions(data || []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch prediction history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPredictions(page * limit);
  }, [page]);

  const handleNext = () => setPage(p => p + 1);
  const handlePrev = () => setPage(p => Math.max(0, p - 1));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold text-slate-800 flex items-center">
          <History className="w-6 h-6 mr-2 text-primary" />
          Prediction History
        </h2>
        <p className="text-sm text-slate-500 mt-1">Audit log of all AI demand predictions</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start">
          <AlertTriangle className="w-5 h-5 mr-3 mt-0.5 shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Timestamp</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Route ID</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Predicted Demand</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Confidence</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Model Version</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center">
                    <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-300 border-t-primary rounded-full"></div>
                    <p className="text-slate-500 mt-2 text-sm">Loading history...</p>
                  </td>
                </tr>
              ) : predictions.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-slate-500">
                    <History className="w-12 h-12 mx-auto text-slate-200 mb-3" />
                    <p>No predictions found for this page.</p>
                  </td>
                </tr>
              ) : (
                predictions.map((row, idx) => {
                  const date = new Date(row.timestamp);
                  return (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="py-4 px-6 text-sm text-slate-600">
                        {date.toLocaleString()}
                      </td>
                      <td className="py-4 px-6 text-sm font-bold text-slate-800">{row.route_id}</td>
                      <td className="py-4 px-6 text-sm font-bold text-primary text-right">{row.predicted_passengers}</td>
                      <td className="py-4 px-6 text-sm text-center">
                        <span className={clsx(
                          "px-2.5 py-1 rounded-full text-xs font-bold",
                          row.confidence_score > 0.8 ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                        )}>
                          {(row.confidence_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-4 px-6 text-sm text-slate-400 text-right">{row.model_version}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Controls */}
        <div className="bg-slate-50 py-3 px-6 border-t border-slate-100 flex items-center justify-between text-sm">
          <span className="text-slate-500">Page {page + 1}</span>
          <div className="flex space-x-2">
            <button 
              onClick={handlePrev} 
              disabled={page === 0 || loading}
              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-all"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button 
              onClick={handleNext} 
              disabled={predictions.length < limit || loading}
              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-all"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
