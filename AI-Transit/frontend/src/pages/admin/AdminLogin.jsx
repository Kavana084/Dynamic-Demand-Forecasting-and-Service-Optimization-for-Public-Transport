import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Lock, Loader2, ShieldCheck, User } from 'lucide-react';
import { login } from '../../api/client';
import { getAuthSession, getRoleBasedRedirect, setAuthSession } from '../../utils/auth';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const { accessToken, role } = getAuthSession();
    if (location.state?.message) {
      setInfoMessage(location.state.message);
    }

    if (accessToken && role) {
      const redirectTarget = getRoleBasedRedirect(role);
      console.log('[Auth] Stored role:', role);
      console.log('[Auth] Redirect target:', redirectTarget);
      navigate(redirectTarget, { replace: true });
    }
  }, [location.state, navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setInfoMessage('');
    setLoading(true);

    try {
      const response = await login({
        username: username.trim(),
        password,
      });
      console.log('[Auth] Login response:', response);

      if (response?.success && response?.access_token && response?.refresh_token && response?.role) {
        setAuthSession({
          ...response,
          username: username.trim(),
        });
        const session = getAuthSession();
        const redirectTarget = getRoleBasedRedirect(session.role || response.role);
        console.log('[Auth] Login response:', response);
        console.log('[Auth] Stored role:', session.role);
        console.log('[Auth] Redirect target:', redirectTarget);
        navigate(redirectTarget, { replace: true });
      } else {
        console.log('[Auth] Login failed:', response);
        setError('Login failed. Please try again.');
      }
    } catch (err) {
      console.error('[Auth] Login error:', err);
      setError(err.message || 'We could not sign you in. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="theme-auth-shell">
      <div className="theme-auth-card">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/10 mb-4">
            <ShieldCheck className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold theme-title">Welcome back</h1>
          <p className="theme-subtitle text-sm mt-2 text-center max-w-sm">
            Sign in to continue to the Smart Transit system with your passenger or admin account.
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {infoMessage && (
            <div className="rounded-2xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
              {infoMessage}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-2">Username</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="text"
                required
                className="theme-input pl-10"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-2">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="password"
                required
                className="theme-input pl-10"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="rounded-2xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            className="theme-button-primary w-full gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><span>Sign In</span><ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <p className="mt-6 text-center text-sm theme-subtitle">
          New passenger account?{' '}
          <Link to="/signup" className="font-semibold text-primary hover:text-[var(--theme-primary-dark)]">
            Create one here
          </Link>
        </p>
      </div>
    </div>
  );
}
