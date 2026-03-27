import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMisReservas, getTasaCambio } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function MisReservasPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [reservas, setReservas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tasa, setTasa] = useState(null);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    Promise.all([
      getMisReservas(),
      getTasaCambio().catch(() => ({ data: { tasa_bcv: null } })),
    ])
      .then(([reservasRes, tasaRes]) => {
        setReservas(reservasRes.data);
        setTasa(tasaRes.data.tasa_bcv);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="page">
        <div className="container">
          <div className="loading"><div className="spinner" /></div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="container">
        <h2>Mis Reservas</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', marginBottom: '1.5rem' }}>
          {reservas.length} reserva{reservas.length !== 1 ? 's' : ''}
        </p>

        {reservas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3>No tienes reservas aún</h3>
            <p style={{ marginTop: '0.5rem', marginBottom: '1.5rem' }}>
              Busca un viaje y reserva tu asiento
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/viajes')}>
              Buscar Viajes
            </button>
          </div>
        ) : (
          <div className="reservas-list">
            {reservas.map((reserva) => (
              <div key={reserva.id} className="card reserva-card">
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                    <h4 style={{ margin: 0 }}>
                      {reserva.viaje_info.origen} → {reserva.viaje_info.destino}
                    </h4>
                    <span className={`reserva-estado estado-${reserva.estado}`}>
                      {reserva.estado_display}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    <span>
                      📅 {new Date(reserva.viaje_info.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                    <span>🕐 {reserva.viaje_info.hora_salida?.slice(0, 5)}</span>
                    <span>💺 Asiento #{reserva.numero_asiento}</span>
                    <span>🚌 {reserva.viaje_info.autobus}</span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div className="price-usd" style={{ fontSize: '1.1rem' }}>
                    ${Number(reserva.viaje_info.precio_usd).toFixed(2)}
                  </div>
                  {tasa && (
                    <div className="price-bs">
                      Bs. {(reserva.viaje_info.precio_usd * tasa).toLocaleString('es-VE', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </div>
                  )}
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    Reserva #{reserva.id}
                  </div>
                  {reserva.estado === 'confirmado' && reserva.grupo_pago && (
                    <button
                      className="btn btn-primary"
                      style={{ marginTop: '0.5rem', fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                      onClick={() => navigate(`/ticket/${reserva.grupo_pago}`)}
                    >
                      🎫 Ver Ticket
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
