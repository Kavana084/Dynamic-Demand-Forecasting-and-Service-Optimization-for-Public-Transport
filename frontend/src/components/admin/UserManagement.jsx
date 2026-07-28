import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import {
  Users,
  Search,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import EmptyStatePanel from './EmptyStatePanel';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [toast, setToast] = useState(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createUsername, setCreateUsername] = useState('');

  const token = useMemo(
    () => localStorage.getItem('access_token') || localStorage.getItem('token'),
    []
  );

  const api = async (path, init) => {
    const res = await fetch(path, {
      ...init,
      headers: {
        ...(init?.headers || {}),
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => '');
      throw new Error(txt || 'Request failed');
    }
    return res.json().catch(() => ({}));
  };

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api('/api/admin/users');
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message || 'User directory temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) => {
      return u.username.toLowerCase().includes(q);
    });
  }, [users, query]);

  const setToastAuto = (payload) => {
    setToast(payload);
    window.setTimeout(() => setToast(null), 2800);
  };

  const createUser = async () => {
    const username = createUsername.trim();
    if (!username) {
      setToastAuto({ tone: 'danger', msg: 'Username is required.' });
      return;
    }
    await api('/api/admin/users', { method: 'POST', body: JSON.stringify({ username, role: 'User' }) });
  };

  const deleteUser = async (userId) => {
    await api(`/api/admin/users/${userId}`, { method: 'DELETE' });
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-muted">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
        <span className="text-sm font-semibold">Loading user directory…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/10 p-6 shadow-st-sm">
        <p className="font-semibold text-ink">User directory temporarily unavailable.</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button className="mt-4 theme-button-secondary st-focusable py-2 px-3 text-xs" onClick={fetchUsers}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + controls */}
      <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center border border-border bg-background">
              <Users className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-ink">User Administration</h3>
              <p className="text-xs text-muted">Manage system users.</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-muted-2 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="theme-input st-focusable h-10 pl-9"
                placeholder="Search users by username…"
              />
            </div>
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              className="theme-button-primary st-focusable py-2 px-3 text-xs gap-2"
            >
              <Plus className="w-4 h-4" />
              Add user
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <EmptyStatePanel
          variant="data"
          title={users.length === 0 ? 'No users yet' : 'No matching users'}
          description={users.length === 0
            ? 'Add the first user to the system.'
            : 'Try clearing the search or broadening your filters.'}
          actionLabel={users.length === 0 ? 'Add user' : undefined}
          onAction={users.length === 0 ? () => setCreateOpen(true) : undefined}
        />
      ) : (
        <div className="rounded-2xl border border-border bg-surface shadow-st-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[500px] text-left">
              <thead className="bg-background text-muted text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 font-semibold">Username</th>
                  <th className="px-6 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((u) => (
                  <tr key={u.id} className="hover:bg-background/60">
                    <td className="px-6 py-4 font-semibold text-ink">{u.username}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        type="button"
                        className="st-focusable inline-flex items-center gap-2 rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs font-semibold text-danger hover:bg-danger/15"
                        onClick={async () => {
                          try {
                            await deleteUser(u.id);
                            setToastAuto({ tone: 'success', msg: 'User deleted.' });
                            fetchUsers();
                          } catch (e2) {
                            setToastAuto({ tone: 'danger', msg: e2.message || 'Failed to delete user.' });
                          }
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create user modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-3xl border border-border bg-surface shadow-st-md overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-ink">Add user</h3>
                <p className="text-xs text-muted mt-0.5">Enter username to create a new user.</p>
              </div>
              <button
                type="button"
                className="st-focusable rounded-lg border border-border bg-background p-2 text-muted hover:text-ink"
                onClick={() => setCreateOpen(false)}
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted">Username</label>
              <input
                className="theme-input st-focusable h-10 mt-1 w-full"
                value={createUsername}
                onChange={(e) => setCreateUsername(e.target.value)}
                placeholder="e.g. user@example.com"
              />
            </div>

            <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-2">
              <button
                type="button"
                className="theme-button-secondary st-focusable py-2 px-3 text-xs"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="theme-button-primary st-focusable py-2 px-3 text-xs"
                onClick={async () => {
                  try {
                    await createUser();
                    setCreateOpen(false);
                    setCreateUsername('');
                    setToastAuto({ tone: 'success', msg: 'User added.' });
                    fetchUsers();
                  } catch (e) {
                    setToastAuto({ tone: 'danger', msg: e.message || 'Failed to add user.' });
                  }
                }}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50">
          <div
            className={clsx(
              'rounded-2xl border px-4 py-3 shadow-st-md text-sm font-semibold',
              toast.tone === 'success'
                ? 'border-success/25 bg-success/10 text-success'
                : toast.tone === 'danger'
                  ? 'border-danger/25 bg-danger/10 text-danger'
                  : 'border-border bg-surface text-ink'
            )}
          >
            {toast.msg}
          </div>
        </div>
      )}
    </div>
  );
}
