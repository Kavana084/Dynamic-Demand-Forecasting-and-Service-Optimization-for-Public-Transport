import { Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout from '../components/admin/AdminLayout';
import AdminDashboard from '../pages/admin/AdminDashboard';
import AdminLogin from '../pages/admin/AdminLogin';
import AnalyticsDashboard from '../components/admin/AnalyticsDashboard';
import OptimizationInsights from '../components/admin/OptimizationInsights';
import UserManagement from '../components/admin/UserManagement';
import PassengerLayout from '../components/layout/PassengerLayout';
import PassengerHome from '../pages/passenger/Home';
import JourneyPlanner from '../pages/TripPlanner';
import RouteHistoryPage from '../pages/passenger/RouteHistoryPage';
import ServiceAlerts from '../pages/passenger/ServiceAlerts';
import TransitAIAssistant from '../pages/passenger/TransitAIAssistant';
import SignupPage from '../pages/passenger/SignupPage';
import ErrorBoundary from '../components/ErrorBoundary';
import { getAuthSession, getPostLoginRoute, hasAccessToken, isAdminRole } from '../utils/auth';

function RequireAuth({ children }) {
  if (!hasAccessToken()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function RequireAdmin({ children }) {
  const { accessToken, role } = getAuthSession();

  if (!accessToken) {
    console.log('[Auth] RequireAdmin: No accessToken, redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  if (!isAdminRole(role)) {
    const redirectTarget = getPostLoginRoute(role);
    console.log('[Auth] RequireAdmin: Access denied for role:', role);
    console.log('[Auth] RequireAdmin: Redirecting to:', redirectTarget);
    return <Navigate to={redirectTarget} replace />;
  }

  console.log('[Auth] RequireAdmin: Access granted for admin role');
  return children;
}

function LoginRoute() {
  const { accessToken, role } = getAuthSession();

  if (accessToken) {
    const redirectTarget = getPostLoginRoute(role);
    console.log('[Auth] Stored role:', role);
    console.log('[Auth] Redirect target:', redirectTarget);
    return <Navigate to={redirectTarget} replace />;
  }

  return <AdminLogin />;
}

function PlanJourneyRoute() {
  return (
    <RequireAuth>
      <ErrorBoundary>
        <JourneyPlanner />
      </ErrorBoundary>
    </RequireAuth>
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/admin/login" element={<LoginRoute />} />
      <Route path="/signup" element={<SignupPage />} />

      {/* Passenger Portal Routes */}
      <Route path="/" element={<PassengerLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<PassengerHome />} />
        <Route path="plan-journey" element={<PlanJourneyRoute />} />
        <Route path="ai-assistant" element={<TransitAIAssistant />} />
        <Route path="journey" element={<Navigate to="/plan-journey" replace />} />
        <Route path="plan-trip" element={<Navigate to="/plan-journey" replace />} />
        <Route path="trip-planner" element={<Navigate to="/plan-journey" replace />} />
        <Route path="route-history" element={<RouteHistoryPage />} />
        {/* Backward-compat redirect */}
        <Route path="route-status" element={<Navigate to="/route-history" replace />} />
        {/* Routes removed - now part of journey planning and AI assistant */}
        <Route path="routes" element={<Navigate to="/plan-journey" replace />} />
        <Route path="alerts" element={<ServiceAlerts />} />
      </Route>

      {/* Admin Dashboard Routes */}
      <Route
        path="/admin"
        element={(
          <RequireAdmin>
            <AdminLayout />
          </RequireAdmin>
        )}
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<ErrorBoundary><AdminDashboard /></ErrorBoundary>} />
        <Route path="analytics" element={<ErrorBoundary><AnalyticsDashboard /></ErrorBoundary>} />
        <Route path="fleet" element={<ErrorBoundary><OptimizationInsights /></ErrorBoundary>} />
        <Route path="access" element={<ErrorBoundary><UserManagement /></ErrorBoundary>} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
