import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registro } from '../services/api';
import GoogleLoginButton from '../components/GoogleLoginButton';
import { Eye, EyeOff } from 'lucide-react';
import Flatpickr from "react-flatpickr";
import "flatpickr/dist/themes/material_blue.css";
import { Spanish } from "flatpickr/dist/l10n/es.js";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    cedula_tipo: 'V',
    cedula: '',
    telefono: '',
    fecha_nacimiento: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (form.password !== form.password2) {
      setFieldErrors({ password2: ['Las contraseñas no coinciden.'] });
      return;
    }

    setLoading(true);
    try {
      const submitData = {
        ...form,
        cedula: form.cedula ? `${form.cedula_tipo}-${form.cedula}` : '',
      };
      // El backend (RegistroSerializer) valida password2, así que NO se elimina.
      delete submitData.cedula_tipo;
      const res = await registro(submitData);
      // Si la verificación por email está activa, ir a ingresar el código.
      // Si no (correo deshabilitado), la cuenta ya queda lista → al login.
      if (res.data?.requiere_verificacion) {
        navigate(`/verificar-email?email=${encodeURIComponent(form.email)}`);
      } else {
        navigate('/login?registrado=1');
      }
    } catch (err) {
      const data = err.response?.data;
      // Etiquetas legibles para mostrar el detalle exacto en el cartel superior.
      const labels = {
        first_name: 'Nombre', last_name: 'Apellido', username: 'Usuario',
        email: 'Correo electrónico', cedula: 'Cédula', telefono: 'Teléfono',
        fecha_nacimiento: 'Fecha de nacimiento', password: 'Contraseña',
        password2: 'Confirmar contraseña',
      };
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        setFieldErrors(data);
        const detalle = Object.entries(data)
          .map(([campo, msgs]) => {
            const texto = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
            return `${labels[campo] || campo}: ${texto}`;
          })
          .join(' · ');
        setError(detalle || 'Por favor, corrige los errores en el formulario.');
      } else if (data) {
        const messages = Object.values(data).flat().join(' ');
        setError(messages || 'Error al registrar.');
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

          {/* ── Registro rápido con Google ── */}
          <GoogleLoginButton />

          <div style={{
            display: 'flex', alignItems: 'center', gap: '1rem',
            margin: '1.25rem 0', color: '#94a3b8', fontSize: '0.85rem'
          }}>
            <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
            o regístrate con tus datos
            <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
          </div>

          <form onSubmit={handleSubmit}>
            <div className="passenger-form">
              <div className="form-group">
                <label>Nombre</label>
                <input
                  type="text"
                  name="first_name"
                  className="form-control"
                  style={{ borderColor: fieldErrors.first_name ? '#ef4444' : undefined }}
                  placeholder="Tu nombre"
                  value={form.first_name}
                  onChange={handleChange}
                  required
                />
                {fieldErrors.first_name && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.first_name.join(' ')}</span>}
              </div>
              <div className="form-group">
                <label>Apellido</label>
                <input
                  type="text"
                  name="last_name"
                  className="form-control"
                  style={{ borderColor: fieldErrors.last_name ? '#ef4444' : undefined }}
                  placeholder="Tu apellido"
                  value={form.last_name}
                  onChange={handleChange}
                  required
                />
                {fieldErrors.last_name && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.last_name.join(' ')}</span>}
              </div>
            </div>

            <div className="form-group">
              <label>Usuario</label>
              <input
                type="text"
                name="username"
                className="form-control"
                style={{ borderColor: fieldErrors.username ? '#ef4444' : undefined }}
                placeholder="Elige un nombre de usuario"
                value={form.username}
                onChange={handleChange}
                required
              />
              {fieldErrors.username && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.username.join(' ')}</span>}
            </div>

            <div className="form-group">
              <label>Correo Electrónico</label>
              <input
                type="email"
                name="email"
                className="form-control"
                style={{ borderColor: fieldErrors.email ? '#ef4444' : undefined }}
                placeholder="tucorreo@ejemplo.com"
                value={form.email}
                onChange={handleChange}
                required
              />
              {fieldErrors.email && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.email.join(' ')}</span>}
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
                    style={{ width: '70px', flexShrink: 0, borderColor: fieldErrors.cedula ? '#ef4444' : undefined }}
                  >
                    <option value="V">V</option>
                    <option value="J">J</option>
                    <option value="E">E</option>
                  </select>
                  <input
                    type="text"
                    name="cedula"
                    className="form-control"
                    style={{ borderColor: fieldErrors.cedula ? '#ef4444' : undefined }}
                    placeholder="12345678"
                    value={form.cedula}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '');
                      setForm({ ...form, cedula: val });
                    }}
                    inputMode="numeric"
                  />
                </div>
                {fieldErrors.cedula && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.cedula.join(' ')}</span>}
              </div>
              <div className="form-group">
                <label>Teléfono</label>
                <input
                  type="text"
                  name="telefono"
                  className="form-control"
                  style={{ borderColor: fieldErrors.telefono ? '#ef4444' : undefined }}
                  placeholder="0412-1234567"
                  value={form.telefono}
                  onChange={handleChange}
                />
                {fieldErrors.telefono && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.telefono.join(' ')}</span>}
              </div>
            </div>

            <div className="form-group">
              <label>Fecha de Nacimiento</label>
              <Flatpickr
                name="fecha_nacimiento"
                className="form-control"
                style={{ borderColor: fieldErrors.fecha_nacimiento ? '#ef4444' : undefined }}
                value={form.fecha_nacimiento}
                onChange={(dates, dateStr) => setForm(prev => ({ ...prev, fecha_nacimiento: dateStr }))}
                options={{
                  locale: Spanish,
                  dateFormat: "Y-m-d",
                  altInput: true,
                  altFormat: "d/m/Y",
                  disableMobile: false,
                  onOpen: () => { document.body.style.overflow = 'hidden'; },
                  onClose: () => { document.body.style.overflow = ''; },
                }}
                required
                placeholder="Seleccionar fecha"
              />
              {fieldErrors.fecha_nacimiento && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.fecha_nacimiento.join(' ')}</span>}
            </div>

            <div className="passenger-form">
              <div className="form-group">
                <label>Contraseña</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    className="form-control"
                    style={{ borderColor: fieldErrors.password ? '#ef4444' : undefined, paddingRight: '2.8rem' }}
                    placeholder="Mínimo 6 caracteres"
                    value={form.password}
                    onChange={handleChange}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute', right: '0.6rem', top: '50%',
                      transform: 'translateY(-50%)', background: 'none',
                      border: 'none', cursor: 'pointer', color: '#94a3b8',
                      padding: '0.25rem', display: 'flex', alignItems: 'center',
                      transition: 'color 0.2s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = '#1e3a5f'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {fieldErrors.password && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.password.join(' ')}</span>}
              </div>
              <div className="form-group">
                <label>Confirmar Contraseña</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword2 ? 'text' : 'password'}
                    name="password2"
                    className="form-control"
                    style={{ borderColor: fieldErrors.password2 ? '#ef4444' : undefined, paddingRight: '2.8rem' }}
                    placeholder="Repite tu contraseña"
                    value={form.password2}
                    onChange={handleChange}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword2(!showPassword2)}
                    style={{
                      position: 'absolute', right: '0.6rem', top: '50%',
                      transform: 'translateY(-50%)', background: 'none',
                      border: 'none', cursor: 'pointer', color: '#94a3b8',
                      padding: '0.25rem', display: 'flex', alignItems: 'center',
                      transition: 'color 0.2s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = '#1e3a5f'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}
                    tabIndex={-1}
                  >
                    {showPassword2 ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {fieldErrors.password2 && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.25rem', display: 'block' }}>{fieldErrors.password2.join(' ')}</span>}
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
