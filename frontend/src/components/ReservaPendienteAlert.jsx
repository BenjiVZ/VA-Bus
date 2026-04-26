import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getMisReservas } from '../services/api';
import { Clock, X, CreditCard } from 'lucide-react';

export default function ReservaPendienteAlert() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pendientes, setPendientes] = useState([]);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user) return;

    getMisReservas()
      .then((res) => {
        const pends = res.data.filter((r) => r.estado === 'pendiente' && r.grupo_pago);
        setPendientes(pends);
      })
      .catch(() => {});
  }, [user, location.pathname]);

  if (!user || dismissed || pendientes.length === 0) return null;

  // Don't show if already on the payment page
  if (location.pathname.startsWith('/pago')) return null;

  // Group by grupo_pago
  const grupos = {};
  pendientes.forEach((r) => {
    if (!grupos[r.grupo_pago]) {
      grupos[r.grupo_pago] = {
        grupo_pago: r.grupo_pago,
        reservas: [],
        ruta: `${r.viaje_info.origen} → ${r.viaje_info.destino}`,
        fecha: r.viaje_info.fecha_salida,
      };
    }
    grupos[r.grupo_pago].reservas.push(r);
  });

  const gruposList = Object.values(grupos);
  const totalAsientos = pendientes.length;

  return (
    <div style={{
      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      color: '#fff',
      padding: '0.75rem 1.25rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.75rem',
      fontSize: '0.9rem',
      fontWeight: '500',
      flexWrap: 'wrap',
      position: 'relative',
      animation: 'slideDown 0.3s ease-out',
    }}>
      <Clock size={18} style={{ flexShrink: 0 }} />
      <span style={{ textAlign: 'center' }}>
        <strong>¡Tienes {totalAsientos} asiento{totalAsientos > 1 ? 's' : ''} pendiente{totalAsientos > 1 ? 's' : ''} de pago!</strong>
        {' '}{gruposList[0].ruta}
        {gruposList.length > 1 && ` y ${gruposList.length - 1} más`}
      </span>
      <button
        onClick={() => navigate(`/pago?grupo=${gruposList[0].grupo_pago}`)}
        style={{
          background: '#fff',
          color: '#d97706',
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
        <CreditCard size={14} />
        Ir a pagar
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
    </div>
  );
}
