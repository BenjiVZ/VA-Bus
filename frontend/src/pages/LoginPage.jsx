import { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { login, getPerfil } from '../services/api';
import { useAuth } from '../context/AuthContext';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();
  const [searchParams] = useSearchParams();
  const recienRegistrado = searchParams.get('registrado') === '1';
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await login(form.username, form.password);
      const tokens = res.data;

      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);

      const perfilRes = await getPerfil();
      loginUser(tokens, perfilRes.data);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      setError(
        data?.detail || 'Credenciales inválidas. Intenta de nuevo.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="auth-container">
        <div className="card auth-card">
          <div className="auth-title">
            <h2>Bienvenido 👋</h2>
            <p>Ingresa a tu cuenta para reservar</p>
          </div>

          {recienRegistrado && !error && (
            <div className="alert alert-success">
              ¡Cuenta creada! Ya puedes iniciar sesión con tu usuario y contraseña.
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          {/* ── Botón Google ── */}
          <GoogleLoginButton />

          <div style={{
            display: 'flex', alignItems: 'center', gap: '1rem',
            margin: '1.25rem 0', color: '#94a3b8', fontSize: '0.85rem'
          }}>
            <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
            o ingresa con tu usuario
            <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Usuario</label>
              <input
                type="text"
                className="form-control"
                placeholder="Tu nombre de usuario"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label>Contraseña</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-control"
                  placeholder="Tu contraseña"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
                  style={{ paddingRight: '2.8rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.6rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#94a3b8',
                    padding: '0.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    transition: 'color 0.2s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = '#1e3a5f'}
                  onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={loading}
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
            <Link to="/recuperar-password" style={{ color: '#0052cc', fontSize: '0.9rem' }}>
              ¿Olvidaste tu contraseña?
            </Link>
          </div>

          <div className="auth-footer">
            ¿No tienes cuenta? <Link to="/registro">Regístrate aquí</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

