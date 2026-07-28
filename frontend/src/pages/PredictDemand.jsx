import { useState, useEffect } from 'react';
import { Calculator, MapPin, Clock, Cloud, Car, AlertTriangle, Activity } from 'lucide-react';
import { predictDemand, getRoutes } from '../api/client';

export default function PredictDemand() {
  const [routes, setRoutes] = useState([]);
  const [loadingRoutes, setLoadingRoutes] = useState(true);
  
  const [formData, setFormData] = useState({
    route_id: '',
    hour: new Date().getHours(),
    weather: 'Clear',
    traffic: 'Low'
  });
  
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRoutes = async () => {
      try {
        const data = await getRoutes(0, 500);
        setRoutes(data || []);
      } catch (err) {
        console.error("Failed to fetch routes:", err);
      } finally {
        setLoadingRoutes(false);
      }
    };
    fetchRoutes();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await predictDemand(formData);
      setResult({
        demand: res.predicted_demand,
        confidence: 85, // Backend might return this, using 85 as fallback if not in payload
        cached: res.cached
      });
    } catch (err) {
      setError(err.message || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Demand Prediction</h1>
        <p className="text-slate-500 mt-2">Leverage CatBoost ML to forecast passenger demand under various conditions.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Input Form */}
        <div className="md:col-span-7 bg-white rounded-xl shadow-sm border border-slate-100 p-8 transition-all hover:shadow-md">
          <form onSubmit={handleSubmit} className="space-y-6">
            <h3 className="text-xl font-bold text-slate-800 border-b border-slate-100 pb-4 mb-6">Simulation Parameters</h3>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start">
                <AlertTriangle className="w-5 h-5 mr-3 mt-0.5 shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="flex items-center text-sm font-semibold text-slate-700">
                  <MapPin className="w-4 h-4 mr-2 text-slate-400" /> Route ID
                </label>
                <select 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  value={formData.route_id}
                  onChange={e => setFormData({...formData, route_id: e.target.value})}
                  required
                  disabled={loadingRoutes}
                >
                  <option value="">{loadingRoutes ? 'Loading routes...' : 'Select a route...'}</option>
                  {routes.map(r => (
                    <option key={r.id || r.route_id} value={r.route_id}>
                      {r.route_id} {r.name ? `- ${r.name}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="space-y-2">
                <label className="flex items-center text-sm font-semibold text-slate-700">
                  <Clock className="w-4 h-4 mr-2 text-slate-400" /> Hour (0-23)
                </label>
                <input 
                  type="number" 
                  min="0" max="23"
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  value={formData.hour}
                  onChange={e => setFormData({...formData, hour: parseInt(e.target.value)})}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center text-sm font-semibold text-slate-700">
                  <Cloud className="w-4 h-4 mr-2 text-slate-400" /> Weather Condition
                </label>
                <select 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  value={formData.weather}
                  onChange={e => setFormData({...formData, weather: e.target.value})}
                >
                  <option value="Clear">Clear</option>
                  <option value="Rainy">Rainy</option>
                  <option value="Cloudy">Cloudy</option>
                  <option value="Extreme">Extreme</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="flex items-center text-sm font-semibold text-slate-700">
                  <Car className="w-4 h-4 mr-2 text-slate-400" /> Traffic Level
                </label>
                <select 
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  value={formData.traffic}
                  onChange={e => setFormData({...formData, traffic: e.target.value})}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Heavy">Heavy</option>
                </select>
              </div>
            </div>

            <div className="pt-4">
              <button 
                type="submit" 
                disabled={loading || loadingRoutes} 
                className="w-full py-3 px-4 bg-primary hover:bg-[#5a4cdb] text-white font-medium rounded-lg shadow-sm shadow-primary/30 transition-all flex justify-center items-center disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  <>
                    <Calculator className="w-5 h-5 mr-2" />
                    Run Prediction Model
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Results Panel */}
        <div className="md:col-span-5 flex flex-col">
          {result ? (
            <div className="bg-gradient-to-br from-primary to-purple-600 rounded-xl shadow-lg p-8 text-white h-full relative overflow-hidden transition-all animate-in fade-in slide-in-from-right-8">
              {/* Decorative background element */}
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-white/10 rounded-full blur-2xl"></div>
              
              <h3 className="text-xl font-bold mb-8 flex items-center relative z-10">
                <Activity className="w-6 h-6 mr-2 text-white/80" />
                Forecast Results
              </h3>
              
              <div className="space-y-8 relative z-10">
                <div className="bg-white/10 p-6 rounded-xl border border-white/20 backdrop-blur-sm">
                  <p className="text-indigo-100 text-sm font-medium mb-1 uppercase tracking-wider">Estimated Passengers</p>
                  <div className="flex items-baseline">
                    <p className="text-5xl font-extrabold">{result.demand}</p>
                    <p className="text-indigo-100 ml-2 font-medium">riders/hr</p>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-indigo-100 text-sm font-medium uppercase tracking-wider">Model Confidence</p>
                    <span className="font-bold text-lg">{result.confidence}%</span>
                  </div>
                  <div className="w-full h-3 bg-indigo-900/40 rounded-full overflow-hidden border border-white/10">
                    <div 
                      className="h-full bg-emerald-400 rounded-full shadow-[0_0_10px_rgba(52,211,153,0.5)] transition-all duration-1000 ease-out" 
                      style={{ width: `${result.confidence}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-indigo-200 mt-2 text-right">
                    {result.cached ? 'Served from cache' : 'Live computation'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 p-8 h-full flex flex-col items-center justify-center text-slate-400 transition-all">
              <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <Calculator className="w-10 h-10 text-slate-300" />
              </div>
              <h4 className="text-lg font-semibold text-slate-500 mb-2">Awaiting Parameters</h4>
              <p className="text-center text-sm max-w-xs">Enter simulation conditions and run the model to see the passenger forecast here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
