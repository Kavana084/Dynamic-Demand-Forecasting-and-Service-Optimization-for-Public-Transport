import { createContext, useState, useContext, useEffect } from 'react';
import { getDashboardData } from '../api/client';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Global filters
  const [globalFilters, setGlobalFilters] = useState({
    timeRange: 'today',
  });

  useEffect(() => {
    let intervalId;

    const loadData = async () => {
      // Only set loading to true on first load to prevent flickering
      if (!dashboardData) setLoading(true);
      try {
        const data = await getDashboardData();
        setDashboardData(data);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
    intervalId = setInterval(loadData, 10000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [globalFilters.timeRange]);

  return (
    <AppContext.Provider value={{
      dashboardData,
      loading,
      error,
      globalFilters,
      setGlobalFilters
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
