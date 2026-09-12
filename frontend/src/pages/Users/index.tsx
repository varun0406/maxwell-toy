import { useState, useEffect } from 'react';
import { useAuthStore } from '../../store/auth';
import { usersApi, authApi } from '../../api/endpoints';
import { UserPlus, UserX, UserCheck, Shield } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const registerSchema = z.object({
  username: z.string().min(3, 'Username required'),
  email: z.string().email().optional().or(z.literal('')),
  password: z.string().min(8, 'Password must be 8+ chars'),
});
type RegisterForm = z.infer<typeof registerSchema>;

export default function Users() {
  const { user } = useAuthStore();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const registerForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await usersApi.list();
      setUsers(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (data: RegisterForm) => {
    try {
      await authApi.register({ username: data.username, email: data.email || undefined, password: data.password });
      registerForm.reset();
      setShowCreate(false);
      fetchUsers();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleToggleStatus = async (id: number, currentStatus: boolean) => {
    if (id === user?.id) {
      alert("You cannot deactivate yourself.");
      return;
    }
    if (!confirm(`Are you sure you want to ${currentStatus ? 'deactivate' : 'activate'} this user?`)) return;
    try {
      await usersApi.updateStatus(id, !currentStatus);
      fetchUsers();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to update user status');
    }
  };

  if (!user?.is_superuser) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
        <Shield size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
        <h2>Access Denied</h2>
        <p>Only super administrators can manage users.</p>
      </div>
    );
  }

  return (
    <div className="page-container pop-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">User Management</h1>
          <p className="page-subtitle">Manage access to the application</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <UserPlus size={16} /> New User
        </button>
      </div>

      {error && <div className="card" style={{ background: 'var(--danger-bg)', color: 'var(--danger)', marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ minWidth: 600 }}>
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>Loading...</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>No users found</td>
                </tr>
              ) : (
                users.map(u => (
                  <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.5 }}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.username} {u.id === user?.id && '(You)'}</td>
                    <td>{u.email || '-'}</td>
                    <td>
                      <span className="badge" style={{ background: u.is_superuser ? 'var(--accent)' : 'var(--bg-elevated)', color: u.is_superuser ? '#fff' : 'var(--text-primary)' }}>
                        {u.is_superuser ? 'Super Admin' : 'User'}
                      </span>
                    </td>
                    <td>
                      <span className="badge" style={{ background: u.is_active ? 'var(--success-bg)' : 'var(--danger-bg)', color: u.is_active ? 'var(--success)' : 'var(--danger)' }}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      {u.id !== user?.id && !u.is_superuser && (
                        <button
                          className="btn"
                          style={{
                            padding: '6px 12px', fontSize: 12,
                            background: u.is_active ? 'var(--danger-bg)' : 'var(--success-bg)',
                            color: u.is_active ? 'var(--danger)' : 'var(--success)',
                            border: 'none',
                          }}
                          onClick={() => handleToggleStatus(u.id, u.is_active)}
                        >
                          {u.is_active ? <span style={{display: 'flex', gap: 4, alignItems: 'center'}}><UserX size={14}/> Deactivate</span> : <span style={{display: 'flex', gap: 4, alignItems: 'center'}}><UserCheck size={14}/> Activate</span>}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16
        }}>
          <div className="card pop-in" style={{ width: '100%', maxWidth: 400 }}>
            <h2 style={{ marginBottom: 16, fontSize: 20 }}>Create New User</h2>
            <form onSubmit={registerForm.handleSubmit(handleCreateUser)}>
              <div className="form-group">
                <label className="form-label">Username</label>
                <input className="form-input" {...registerForm.register('username')} />
                {registerForm.formState.errors.username && <span className="form-error">{registerForm.formState.errors.username.message}</span>}
              </div>
              <div className="form-group">
                <label className="form-label">Email (optional)</label>
                <input className="form-input" type="email" {...registerForm.register('email')} />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" type="password" {...registerForm.register('password')} />
                {registerForm.formState.errors.password && <span className="form-error">{registerForm.formState.errors.password.message}</span>}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                <button type="button" className="btn" style={{ flex: 1 }} onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
