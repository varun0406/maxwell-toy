import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { authApi } from '../../api/endpoints';
import { Lock, User, Eye, EyeOff, Shield } from 'lucide-react';

const loginSchema = z.object({
  username: z.string().min(3, 'Username required'),
  password: z.string().min(8, 'Password must be 8+ chars'),
});

const registerSchema = loginSchema.extend({
  email: z.string().email().optional().or(z.literal('')),
  confirmPassword: z.string(),
}).refine((d) => d.password === d.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  const loginForm = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });
  const registerForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const handleLogin = async (data: LoginForm) => {
    setError(''); setLoading(true);
    try {
      const { data: tokens } = await authApi.login({ username: data.username!, password: data.password! });
      setTokens(tokens.access_token, tokens.refresh_token);
      const { data: user } = await authApi.me();
      setUser(user);
      navigate('/home');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Login failed');
    } finally { setLoading(false); }
  };

  const handleRegister = async (data: RegisterForm) => {
    setError(''); setLoading(true);
    try {
      await authApi.register({ username: data.username, email: data.email || undefined, password: data.password });
      const { data: tokens } = await authApi.login({ username: data.username, password: data.password });
      setTokens(tokens.access_token, tokens.refresh_token);
      const { data: user } = await authApi.me();
      setUser(user);
      navigate('/home');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Registration failed');
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-base)',
      overflow: 'auto',
    }}>
      {/* Background orbs */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-20%', right: '-20%', width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(circle, rgba(124,111,255,0.12) 0%, transparent 70%)' }} />
        <div style={{ position: 'absolute', bottom: '-10%', left: '-20%', width: 250, height: 250, borderRadius: '50%', background: 'radial-gradient(circle, rgba(34,211,165,0.08) 0%, transparent 70%)' }} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '40px 28px 20px', position: 'relative' }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 44 }} className="pop-in">
          <div style={{
            width: 78, height: 78,
            borderRadius: 24,
            background: 'linear-gradient(145deg, var(--accent), var(--accent-dark))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: 'var(--shadow-accent), 0 0 0 8px var(--accent-glow)',
          }}>
            <img src="/logo.png" alt="Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 900, letterSpacing: -0.8, color: 'var(--text-primary)' }}>
            Welcome Back
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: 6, fontSize: 14, fontWeight: 500 }}>
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        {/* Mode toggle */}
        <div style={{
          display: 'flex',
          background: 'var(--bg-elevated)',
          borderRadius: 14,
          padding: 4,
          marginBottom: 28,
          border: '1px solid var(--border)',
        }}>
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); }}
              style={{
                flex: 1,
                padding: '11px 0',
                borderRadius: 11,
                border: 'none',
                background: mode === m ? 'linear-gradient(140deg, var(--accent), var(--accent-dark))' : 'none',
                color: mode === m ? '#fff' : 'var(--text-muted)',
                fontFamily: 'inherit',
                fontWeight: 700,
                fontSize: 14,
                cursor: 'pointer',
                transition: 'all 0.25s',
                boxShadow: mode === m ? 'var(--shadow-accent)' : 'none',
                letterSpacing: -0.1,
              }}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: 'var(--danger-bg)',
            border: '1px solid rgba(248,113,113,0.3)',
            borderRadius: 12,
            padding: '12px 16px',
            marginBottom: 18,
            fontSize: 14,
            color: 'var(--danger)',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Login Form */}
        {mode === 'login' ? (
          <form onSubmit={loginForm.handleSubmit(handleLogin)}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <div style={{ position: 'relative' }}>
                <div style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>
                  <User size={16} />
                </div>
                <input
                  className="form-input"
                  placeholder="your_username"
                  style={{ paddingLeft: 40 }}
                  {...loginForm.register('username')}
                />
              </div>
              {loginForm.formState.errors.username && <span className="form-error">{loginForm.formState.errors.username.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <div style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>
                  <Lock size={16} />
                </div>
                <input
                  className="form-input"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  style={{ paddingLeft: 40, paddingRight: 46 }}
                  {...loginForm.register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(s => !s)}
                  style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {loginForm.formState.errors.password && <span className="form-error">{loginForm.formState.errors.password.message}</span>}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading}
              style={{ marginTop: 8, height: 52, fontSize: 16, letterSpacing: -0.2 }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                  Signing in…
                </span>
              ) : 'Sign In'}
            </button>
          </form>
        ) : (
          <form onSubmit={registerForm.handleSubmit(handleRegister)}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="form-input" placeholder="your_username" {...registerForm.register('username')} />
              {registerForm.formState.errors.username && <span className="form-error">{registerForm.formState.errors.username.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Email (optional)</label>
              <input className="form-input" type="email" placeholder="you@email.com" {...registerForm.register('email')} />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" type="password" placeholder="Min. 8 characters" {...registerForm.register('password')} />
              {registerForm.formState.errors.password && <span className="form-error">{registerForm.formState.errors.password.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input className="form-input" type="password" placeholder="••••••••" {...registerForm.register('confirmPassword')} />
              {registerForm.formState.errors.confirmPassword && <span className="form-error">{registerForm.formState.errors.confirmPassword.message}</span>}
            </div>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: 8, height: 52, fontSize: 16 }}>
              {loading ? 'Creating…' : 'Create Account'}
            </button>
          </form>
        )}
      </div>

      <div style={{ padding: '16px 24px 32px', textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
        🔒 End-to-end encrypted · No data stored locally
      </div>
    </div>
  );
}
