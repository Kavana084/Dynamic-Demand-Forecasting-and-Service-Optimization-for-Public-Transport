import { Search, User } from 'lucide-react';

export default function Header() {
  return (
    <header className="h-16 bg-slate-900/50 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="relative w-64">
        <span className="absolute inset-y-0 left-0 flex items-center pl-3">
          <Search className="w-4 h-4 text-slate-500" />
        </span>
        <input 
          type="text" 
          placeholder="Search routes..." 
          className="w-full bg-slate-800 border border-slate-700 rounded-full pl-10 pr-4 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
        />
      </div>

      <div className="flex items-center space-x-4">
        <div className="h-8 w-8 rounded-full bg-sky-500/20 border border-sky-500/50 flex items-center justify-center text-sky-400 cursor-pointer">
          <User className="w-4 h-4" />
        </div>
      </div>
    </header>
  );
}
