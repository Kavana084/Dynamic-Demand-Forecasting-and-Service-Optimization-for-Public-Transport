import { Bell as BellIcon, ChevronDown as ChevronDownIcon, Search as SearchIcon } from 'lucide-react';

export default function Navbar({ title }) {
  return (
    <header className="h-20 bg-background/80 backdrop-blur-md flex items-center justify-between px-8 sticky top-0 z-10">
      <div className="flex items-center space-x-4">
        <h2 className="text-2xl font-bold text-slate-800">{title || 'Dashboard'}</h2>
      </div>

      <div className="flex items-center space-x-6">
        {/* Search */}
        <div className="relative hidden md:block">
          <SearchIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-full text-sm focus:outline-none focus:ring-1 focus:ring-primary w-64"
          />
        </div>

        {/* Date Filter */}
        <div className="flex items-center space-x-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 cursor-pointer">
          <span className="text-sm font-medium text-slate-600">Today</span>
          <ChevronDownIcon className="w-4 h-4 text-slate-400" />
        </div>

        {/* Notifications */}
        <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors bg-white border border-slate-200 rounded-full">
          <BellIcon className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white"></span>
        </button>

        {/* User Profile */}
        <div className="flex items-center space-x-3 border-l border-slate-200 pl-6">
          <img 
            src="https://ui-avatars.com/api/?name=Admin+Transit&background=6c5ce7&color=fff" 
            alt="User" 
            className="w-9 h-9 rounded-full"
          />
          <div className="hidden md:block">
            <p className="text-sm font-semibold text-slate-800 leading-tight">Admin</p>
            <p className="text-xs text-slate-500">Transit Authority</p>
          </div>
        </div>
      </div>
    </header>
  );
}
