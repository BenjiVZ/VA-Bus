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
              <div key={reserva.id} className={`reserva-card estado-borde-${reserva.estado}`}>
                {/* Encabezado: ruta + estado */}
                <div className="reserva-card-head">
                  <h4 className="reserva-ruta">
                    {reserva.viaje_info.origen}
                    <span className="reserva-flecha">→</span>
                    {reserva.viaje_info.destino}
                  </h4>
                  <span className={`reserva-estado estado-${reserva.estado}`}>
                    {reserva.estado_display}
                  </span>
                </div>

                {/* Datos del viaje en chips */}
                <div className="reserva-meta">
                  <span className="reserva-chip">
                    📅 {new Date(reserva.viaje_info.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </span>
                  <span className="reserva-chip">🕐 {reserva.viaje_info.hora_salida?.slice(0, 5)}</span>
                  <span className="reserva-chip">💺 Asiento #{reserva.numero_asiento}</span>
                  <span className="reserva-chip">🚌 {reserva.viaje_info.autobus}</span>
                </div>

                {/* Pie: identificadores + precio + acción */}
                <div className="reserva-card-foot">
                  <div className="reserva-ids">
                    <span className="reserva-id-item">Reserva <strong>#{reserva.id}</strong></span>
                    {reserva.codigo_ticket && (
                      <span className="reserva-id-item">Ticket <code>{reserva.codigo_ticket}</code></span>
                    )}
                    {(reserva.referencia_pago?.referencia || reserva.referencia_pago?.operacion_id) && (
                      <span className="reserva-id-item">
                        Operación <code>{reserva.referencia_pago.referencia || reserva.referencia_pago.operacion_id}</code>
                      </span>
                    )}
                  </div>

                  <div className="reserva-precio-accion">
                    <div className="reserva-precio">
                      <span className="price-usd">${Number(reserva.viaje_info.precio_usd).toFixed(2)}</span>
                      {tasa && (
                        <span className="price-bs">
                          Bs. {(reserva.viaje_info.precio_usd * tasa).toLocaleString('es-VE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2,
                          })}
                        </span>
                      )}
                    </div>
                    {reserva.estado === 'confirmado' && reserva.grupo_pago && (
                      <button
                        className="btn btn-primary reserva-btn"
                        onClick={() => navigate(`/ticket/${reserva.grupo_pago}`)}
                      >
                        🎫 Ver Ticket
                      </button>
                    )}
                    {reserva.estado === 'pendiente' && reserva.grupo_pago && (
                      <button
                        className="btn reserva-btn reserva-btn-pagar"
                        onClick={() => navigate(`/pago?grupo=${reserva.grupo_pago}`)}
                      >
                        💳 Ir a pagar
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
