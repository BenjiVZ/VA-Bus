import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { solicitarResetPassword, resetPassword } from '../services/api';

export default function RecuperarPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: pedir email, 2: código + nueva contraseña
  const [email, setEmail] = useState('');
  const [codigo, setCodigo] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPassword2, setNewPassword2] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSolicitarCodigo = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const res = await solicitarResetPassword(email);
      setSuccess(res.data.mensaje);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.error || 'Error al enviar código.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== newPassword2) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      const res = await resetPassword(email, codigo, newPassword, newPassword2);
      setSuccess(res.data.mensaje);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.response?.data?.error || 'Error al restablecer contraseña.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="auth-container">
        <div className="card auth-card">
          <div className="auth-title">
            <h2>Recuperar Contraseña 🔑</h2>
            <p>
              {step === 1
                ? 'Ingresa tu email y te enviaremos un código'
                : `Ingresa el código enviado a ${email}`}
            </p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {success && (
            <div className="alert" style={{ background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '12px' }}>
              {success}
            </div>
          )}

          {step === 1 ? (
            <form onSubmit={handleSolicitarCodigo}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  className="form-control"
                  placeholder="tucorreo@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={loading}
              >
                {loading ? 'Enviando...' : 'Enviar Código de Recuperación'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleResetPassword}>
              <div className="form-group">
                <label>Código de Verificación</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="123456"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '8px', fontWeight: 700 }}
                  maxLength={6}
                  inputMode="numeric"
                  required
                />
              </div>

              <div className="form-group">
                <label>Nueva Contraseña</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Mínimo 6 caracteres"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Confirmar Contraseña</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Repite tu nueva contraseña"
                  value={newPassword2}
                  onChange={(e) => setNewPassword2(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={loading || codigo.length !== 6}
              >
                {loading ? 'Restableciendo...' : 'Restablecer Contraseña'}
              </button>

              <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => { setStep(1); setCodigo(''); setSuccess(''); setError(''); }}
                  style={{
                    background: 'none', border: 'none', color: '#0052cc',
                    cursor: 'pointer', fontSize: '0.85rem', textDecoration: 'underline'
                  }}
                >
                  ¿No recibiste el código? Reenviar
                </button>
              </div>
            </form>
          )}

          <div className="auth-footer">
            <Link to="/login">← Volver al inicio de sesión</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
