import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { actualizarPerfil, cambiarPassword } from '../services/api';
import {
  User, Mail, Phone, CreditCard, Save, Lock,
  CheckCircle, AlertTriangle, Eye, EyeOff,
} from 'lucide-react';

export default function PerfilPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  // Profile form
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    telefono: '',
  });
  // Cédula separada: tipo (V/E/J/P) por selección + número.
  const [cedulaTipo, setCedulaTipo] = useState('V');
  const [cedulaNum, setCedulaNum] = useState('');
  const [saving, setSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState('');
  const [profileErr, setProfileErr] = useState('');

  // Password form
  const [passForm, setPassForm] = useState({
    current_password: '',
    new_password: '',
    new_password2: '',
  });
  const [showPass, setShowPass] = useState({});
  const [savingPass, setSavingPass] = useState(false);
  const [passMsg, setPassMsg] = useState('');
  const [passErr, setPassErr] = useState('');

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    setForm({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      email: user.email || '',
      telefono: user.telefono || '',
    });
    // Separar la cédula guardada (ej. "V-12345678") en tipo + número.
    const m = (user.cedula || '').match(/^([VEJP])-?(.*)$/i);
    if (m) {
      setCedulaTipo(m[1].toUpperCase());
      setCedulaNum(m[2].replace(/\D/g, ''));
    } else {
      setCedulaNum((user.cedula || '').replace(/\D/g, ''));
    }
  }, [user, navigate]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handlePassChange = (e) => {
    setPassForm({ ...passForm, [e.target.name]: e.target.value });
  };

  const toggleShowPass = (field) => {
    setShowPass(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    setProfileMsg('');
    setProfileErr('');

    try {
      const payload = {
        ...form,
        cedula: cedulaNum ? `${cedulaTipo}-${cedulaNum}` : '',
      };
      await actualizarPerfil(payload);
      if (refreshUser) await refreshUser();
      setProfileMsg('Perfil actualizado correctamente.');
      setTimeout(() => setProfileMsg(''), 4000);
    } catch (err) {
      const data = err.response?.data;
      if (data && typeof data === 'object') {
        const msgs = Object.entries(data)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('; ');
        setProfileErr(msgs);
      } else {
        setProfileErr('Error al actualizar el perfil.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setSavingPass(true);
    setPassMsg('');
    setPassErr('');

    try {
      const res = await cambiarPassword(passForm);
      setPassMsg(res.data.mensaje || 'Contraseña actualizada.');
      setPassForm({ current_password: '', new_password: '', new_password2: '' });
      setTimeout(() => setPassMsg(''), 4000);
    } catch (err) {
      setPassErr(err.response?.data?.error || 'Error al cambiar la contraseña.');
    } finally {
      setSavingPass(false);
    }
  };

  if (!user) return null;

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '600px' }}>
        <h2 style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <User size={24} /> Mi Perfil
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          Administra tu información personal
        </p>

        {/* ═══ Profile Info ═══ */}
        <form className="perfil-section" onSubmit={handleSaveProfile}>
          <h3 className="perfil-section-title">Información personal</h3>

          {profileMsg && (
            <div className="alert alert-success">
              <CheckCircle size={16} /> {profileMsg}
            </div>
          )}
          {profileErr && (
            <div className="alert alert-error">
              <AlertTriangle size={16} /> {profileErr}
            </div>
          )}

          <div className="perfil-grid">
            <div className="form-group">
              <label><User size={14} /> Nombre</label>
              <input
                type="text"
                className="form-control"
                name="first_name"
                value={form.first_name}
                onChange={handleChange}
                placeholder="Tu nombre"
              />
            </div>

            <div className="form-group">
              <label><User size={14} /> Apellido</label>
              <input
                type="text"
                className="form-control"
                name="last_name"
                value={form.last_name}
                onChange={handleChange}
                placeholder="Tu apellido"
              />
            </div>
          </div>

          <div className="form-group">
            <label><Mail size={14} /> Correo electrónico</label>
            <input
              type="email"
              className="form-control"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="tu@correo.com"
            />
          </div>

          <div className="perfil-grid">
            <div className="form-group">
              <label><CreditCard size={14} /> Cédula</label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <select
                  className="form-control"
                  value={cedulaTipo}
                  onChange={(e) => setCedulaTipo(e.target.value)}
                  style={{ maxWidth: '80px' }}
                  aria-label="Tipo de cédula"
                >
                  <option value="V">V</option>
                  <option value="E">E</option>
                  <option value="J">J</option>
                  <option value="P">P</option>
                </select>
                <input
                  type="text"
                  className="form-control"
                  value={cedulaNum}
                  onChange={(e) => setCedulaNum(e.target.value.replace(/\D/g, ''))}
                  placeholder="12345678"
                  inputMode="numeric"
                />
              </div>
            </div>

            <div className="form-group">
              <label><Phone size={14} /> Teléfono</label>
              <input
                type="tel"
                className="form-control"
                name="telefono"
                value={form.telefono}
                onChange={handleChange}
                placeholder="0412-1234567"
              />
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '0.5rem' }}>
            <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Usuario: <strong>{user.username}</strong>
            </label>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            {saving ? 'Guardando...' : <><Save size={16} /> Guardar cambios</>}
          </button>
        </form>

        {/* ═══ Change Password ═══ */}
        <form className="perfil-section" onSubmit={handleChangePassword} style={{ marginTop: '2rem' }}>
          <h3 className="perfil-section-title"><Lock size={18} /> Cambiar contraseña</h3>

          {passMsg && (
            <div className="alert alert-success">
              <CheckCircle size={16} /> {passMsg}
            </div>
          )}
          {passErr && (
            <div className="alert alert-error">
              <AlertTriangle size={16} /> {passErr}
            </div>
          )}

          <div className="form-group">
            <label>Contraseña actual</label>
            <div className="perfil-pass-input">
              <input
                type={showPass.current ? 'text' : 'password'}
                className="form-control"
                name="current_password"
                value={passForm.current_password}
                onChange={handlePassChange}
                placeholder="••••••"
              />
              <button type="button" className="perfil-pass-toggle" onClick={() => toggleShowPass('current')}>
                {showPass.current ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="perfil-grid">
            <div className="form-group">
              <label>Nueva contraseña</label>
              <div className="perfil-pass-input">
                <input
                  type={showPass.new1 ? 'text' : 'password'}
                  className="form-control"
                  name="new_password"
                  value={passForm.new_password}
                  onChange={handlePassChange}
                  placeholder="Mín. 6 caracteres"
                />
                <button type="button" className="perfil-pass-toggle" onClick={() => toggleShowPass('new1')}>
                  {showPass.new1 ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Confirmar nueva</label>
              <div className="perfil-pass-input">
                <input
                  type={showPass.new2 ? 'text' : 'password'}
                  className="form-control"
                  name="new_password2"
                  value={passForm.new_password2}
                  onChange={handlePassChange}
                  placeholder="Repetir contraseña"
                />
                <button type="button" className="perfil-pass-toggle" onClick={() => toggleShowPass('new2')}>
                  {showPass.new2 ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-accent"
            disabled={savingPass || !passForm.current_password || !passForm.new_password}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            {savingPass ? 'Cambiando...' : <><Lock size={16} /> Cambiar contraseña</>}
          </button>
        </form>
      </div>
    </div>
  );
}
