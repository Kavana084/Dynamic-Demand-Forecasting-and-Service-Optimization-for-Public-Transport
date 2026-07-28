import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, Lock, ShieldCheck, User, UserPlus } from 'lucide-react';
import { register } from '../../api/client';
import { getAuthSession, getPostLoginRoute } from '../../utils/auth';

export default function SignupPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    const { accessToken, role } = getAuthSession();
    if (accessToken && role) {
      navigate(getPostLoginRoute(role), { replace: true });
    }
  }, [navigate]);

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await register({
        username: username.trim(),
        password,
      });

      if (response?.success) {
        const message = 'Account created successfully. Please login.';
        setSuccessMessage(message);
        setUsername('');
        setPassword('');

        setTimeout(() => {
          navigate('/login', {
            replace: true,
            state: { message },
          });
        }, 1200);
      } else {
        setError('We could not create your account. Please try again.');
      }
    } catch (err) {
      setError(err.message || 'We could not create your account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="theme-auth-shell">
      <div className="theme-auth-card">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/10 mb-4">
            <UserPlus className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold theme-title">Create account</h1>
          <p className="theme-subtitle text-sm mt-2 text-center max-w-sm">
            Register a passenger account to start planning trips immediately.
          </p>
        </div>

        <form onSubmit={handleSignup} className="space-y-5">
          {successMessage && (
            <div className="rounded-2xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
              {successMessage}
            </div>
          )}

          {error && (
            <div className="rounded-2xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {error}
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
                placeholder="Choose a username"
                className="theme-input pl-10"
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
                placeholder="Create a password"
                className="theme-input pl-10"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="rounded-2xl border border-primary/10 bg-primary/5 px-4 py-3 text-sm text-slate-600">
            Your account will be saved persistently and can be used immediately on the login page.
          </div>

          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            className="theme-button-primary w-full gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Sign Up</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <p className="text-sm theme-subtitle text-center">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary hover:text-[var(--theme-primary-dark)]">
              Login
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
