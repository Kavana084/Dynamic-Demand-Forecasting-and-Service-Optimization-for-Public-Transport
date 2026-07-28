import React, { Suspense } from 'react';
import { Search, Filter, Bus } from 'lucide-react';

// Lazy load map to prevent unnecessary re-renders and heavy initial load
const TransitMap = React.lazy(() => import('../components/map/TransitMap'));

export default function RouteMap() {
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Map Controls */}
      <div className="flex items-center justify-between mb-4 space-x-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search route or location..." 
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-primary shadow-sm"
          />
        </div>
        <div className="flex items-center space-x-3">
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex items-center space-x-2 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors">
            <span className="text-sm font-medium text-slate-700">All Routes</span>
            <Filter className="w-4 h-4 text-slate-400" />
          </div>
          <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 flex items-center space-x-2 shadow-sm cursor-pointer hover:bg-slate-50 transition-colors">
            <span className="text-sm font-medium text-slate-700">Live Traffic</span>
            <Filter className="w-4 h-4 text-slate-400" />
          </div>
        </div>
      </div>

      {/* Main Map Area with Sidebar overlay concept */}
      <div className="flex-1 relative rounded-2xl shadow-sm border border-slate-200 overflow-hidden bg-white">
        <Suspense fallback={
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        }>
          <TransitMap />
        </Suspense>

        {/* Overlay Card - Route Load Legend */}
        <div className="absolute right-6 top-6 z-[400] bg-white p-5 rounded-2xl shadow-lg border border-slate-100 w-64 pointer-events-auto">
          <h4 className="text-sm font-bold text-slate-800 mb-4">Route Load</h4>
          <ul className="space-y-3">
            <li className="flex items-center text-sm text-slate-600">
              <span className="w-3 h-3 rounded-full bg-emerald-500 mr-3 shrink-0"></span>
              Low (0 - 40%)
            </li>
            <li className="flex items-center text-sm text-slate-600">
              <span className="w-3 h-3 rounded-full bg-amber-500 mr-3 shrink-0"></span>
              Medium (40 - 70%)
            </li>
            <li className="flex items-center text-sm text-slate-600">
              <span className="w-3 h-3 rounded-full bg-red-500 mr-3 shrink-0"></span>
              High (70%+)
            </li>
            <li className="flex items-center text-sm text-slate-600">
              <span className="w-3 h-3 rounded-full bg-slate-300 mr-3 shrink-0"></span>
              No Data
            </li>
          </ul>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <h4 className="text-sm font-bold text-slate-800 mb-2">Live Buses</h4>
            <div className="flex items-center space-x-2 text-primary font-medium">
              <Bus className="w-5 h-5" />
              <span>342 Active</span>
            </div>
            <button className="text-xs text-primary font-medium hover:text-[#5a4cdb] mt-3 block w-full text-left">
              View All Buses &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
