import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registro, login, getPerfil } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    cedula_tipo: 'V',
    cedula: '',
    telefono: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.password2) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      const submitData = {
        ...form,
        cedula: form.cedula ? `${form.cedula_tipo}-${form.cedula}` : '',
      };
      delete submitData.cedula_tipo;
      delete submitData.password2;
      await registro(submitData);
      // Auto login after registration
      const loginRes = await login(form.username, form.password);
      localStorage.setItem('access_token', loginRes.data.access);
      localStorage.setItem('refresh_token', loginRes.data.refresh);
      const perfilRes = await getPerfil();
      loginUser(loginRes.data, perfilRes.data);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const messages = Object.values(data).flat().join(' ');
        setError(messages);
      } else {
        setError('Error al registrar. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="auth-container" style={{ maxWidth: '500px' }}>
        <div className="card auth-card">
          <div className="auth-title">
            <h2>Crear Cuenta ✨</h2>
            <p>Regístrate para reservar tus viajes</p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="passenger-form">
              <div className="form-group">
                <label>Nombre</label>
                <input
                  type="text"
                  name="first_name"
                  className="form-control"
                  placeholder="Tu nombre"
                  value={form.first_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Apellido</label>
                <input
                  type="text"
                  name="last_name"
                  className="form-control"
                  placeholder="Tu apellido"
                  value={form.last_name}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Usuario</label>
              <input
                type="text"
                name="username"
                className="form-control"
                placeholder="Elige un nombre de usuario"
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Correo Electrónico</label>
              <input
                type="email"
                name="email"
                className="form-control"
                placeholder="tucorreo@ejemplo.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className="passenger-form">
              <div className="form-group">
                <label>Cédula</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <select
                    name="cedula_tipo"
                    className="form-control"
                    value={form.cedula_tipo}
                    onChange={handleChange}
                    style={{ width: '70px', flexShrink: 0 }}
                  >
                    <option value="V">V</option>
                    <option value="J">J</option>
                    <option value="E">E</option>
                  </select>
                  <input
                    type="text"
                    name="cedula"
                    className="form-control"
                    placeholder="12345678"
                    value={form.cedula}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '');
                      setForm({ ...form, cedula: val });
                    }}
                    inputMode="numeric"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Teléfono</label>
                <input
                  type="text"
                  name="telefono"
                  className="form-control"
                  placeholder="0412-1234567"
                  value={form.telefono}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="passenger-form">
              <div className="form-group">
                <label>Contraseña</label>
                <input
                  type="password"
                  name="password"
                  className="form-control"
                  placeholder="Mínimo 6 caracteres"
                  value={form.password}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Confirmar Contraseña</label>
                <input
                  type="password"
                  name="password2"
                  className="form-control"
                  placeholder="Repite tu contraseña"
                  value={form.password2}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={loading}
            >
              {loading ? 'Registrando...' : 'Crear Cuenta'}
            </button>
          </form>

          <div className="auth-footer">
            ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
