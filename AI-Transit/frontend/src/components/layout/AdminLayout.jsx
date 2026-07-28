import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import { AppProvider } from '../../context/AppContext';

export default function AdminLayout() {
  const location = useLocation();
  
  // Determine title based on path
  const getTitle = () => {
    if (location.pathname.includes('route-map')) return 'Route Map';
    if (location.pathname.includes('optimize')) return 'Optimization';
    return 'Dashboard';
  };

  return (
    <AppProvider>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        
        {/* Main Content Wrapper - Offset by Sidebar width */}
        <div className="flex-1 ml-64 flex flex-col min-h-screen">
          <Navbar title={getTitle()} />
          
          <main className="flex-1 p-8 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </AppProvider>
  );
}
