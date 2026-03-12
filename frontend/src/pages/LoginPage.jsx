import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login, getPerfil } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
      setError(
        err.response?.data?.detail || 'Credenciales inválidas. Intenta de nuevo.'
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

          {error && <div className="alert alert-error">{error}</div>}

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
              <input
                type="password"
                className="form-control"
                placeholder="Tu contraseña"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
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

          <div className="auth-footer">
            ¿No tienes cuenta? <Link to="/registro">Regístrate aquí</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
