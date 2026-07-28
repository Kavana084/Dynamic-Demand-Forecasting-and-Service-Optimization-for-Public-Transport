import { useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes';
import { initTheme } from './theme/theme';
import { initPreferences } from './theme/preferences';

function App() {
  useEffect(() => {
    initTheme();
    initPreferences();
  }, []);

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-background text-ink font-sans">
        <AppRoutes />
      </div>
    </Router>
  );
}

export default App;
