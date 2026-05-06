import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { verificarEmail, reenviarCodigo } from '../services/api';

export default function VerificarEmailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const emailParam = searchParams.get('email') || '';

  const [email] = useState(emailParam);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [reenviando, setReenviando] = useState(false);

  const handleVerificar = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const res = await verificarEmail(email, codigo);
      setSuccess('¡Email verificado exitosamente! ✅ Redirigiendo al login...');
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.response?.data?.error || 'Error al verificar.');
    } finally {
      setLoading(false);
    }
  };

  const handleReenviar = async () => {
    setError('');
    setSuccess('');
    setReenviando(true);

    try {
      await reenviarCodigo(email);
      setSuccess('Se envió un nuevo código a tu email.');
    } catch (err) {
      setError(err.response?.data?.error || 'Error al reenviar código.');
    } finally {
      setReenviando(false);
    }
  };

  return (
    <div className="page">
      <div className="auth-container">
        <div className="card auth-card">
          <div className="auth-title">
            <h2>Verifica tu Email 📧</h2>
            <p>
              Enviamos un código de 6 dígitos a<br />
              <strong style={{ color: '#0052cc' }}>{email}</strong>
            </p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {success && (
            <div className="alert" style={{ background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '12px' }}>
              {success}
            </div>
          )}

          <form onSubmit={handleVerificar}>
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

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={loading || codigo.length !== 6}
            >
              {loading ? 'Verificando...' : 'Verificar Email'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <button
              onClick={handleReenviar}
              disabled={reenviando}
              style={{
                background: 'none', border: 'none', color: '#0052cc',
                cursor: 'pointer', fontSize: '0.9rem', textDecoration: 'underline'
              }}
            >
              {reenviando ? 'Enviando...' : '¿No recibiste el código? Reenviar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
