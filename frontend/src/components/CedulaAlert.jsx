import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';

export default function CedulaAlert() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  if (!user || dismissed) return null;

  // Detectar campos faltantes
  const missing = [];
  if (!user.cedula) missing.push('Cédula');
  if (!user.telefono) missing.push('Teléfono');
  if (!user.first_name) missing.push('Nombre');
  if (!user.last_name) missing.push('Apellido');

  if (missing.length === 0) return null;

  const missingText = missing.join(', ');

  return (
    <div style={{
      background: 'linear-gradient(135deg, #ff6b35 0%, #e63946 100%)',
      color: '#fff',
      padding: '0.75rem 1.25rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.75rem',
      fontSize: '0.9rem',
      fontWeight: '500',
      flexWrap: 'wrap',
    }}>
      <AlertTriangle size={18} style={{ flexShrink: 0 }} />
      <span style={{ textAlign: 'center' }}>
        <strong>¡Completa tu perfil!</strong> Te faltan: <strong>{missingText}</strong>
      </span>
      <button
        onClick={() => navigate('/perfil')}
        style={{
          background: '#fff',
          color: '#e63946',
          border: 'none',
          padding: '0.4rem 1rem',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: '700',
          fontSize: '0.8rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          whiteSpace: 'nowrap',
          transition: 'transform 0.2s',
        }}
        onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
        onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
      >
        Completar perfil
      </button>
      <button
        onClick={() => setDismissed(true)}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'rgba(255,255,255,0.7)',
          cursor: 'pointer',
          padding: '0.25rem',
          position: 'absolute',
          right: '0.5rem',
          top: '50%',
          transform: 'translateY(-50%)',
        }}
        title="Cerrar"
      >
        <X size={16} />
      </button>

      <style>{`
        @keyframes slideDown {
          from { transform: translateY(-100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
