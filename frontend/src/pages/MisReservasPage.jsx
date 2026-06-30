import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMisReservas, getTasaCambio } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Calendar, Clock, Armchair, Bus, Ticket, CreditCard } from 'lucide-react';

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
              <div key={reserva.id} className={`reserva-ticket estado-borde-${reserva.estado}`}>
                {/* ── Cuerpo principal del boleto ── */}
                <div className="reserva-ticket-main">
                  <div className="reserva-ticket-head">
                    <h4 className="reserva-ruta">
                      {reserva.viaje_info.origen}
                      <span className="reserva-flecha">→</span>
                      {reserva.viaje_info.destino}
                    </h4>
                    <span className={`reserva-estado estado-${reserva.estado}`}>
                      {reserva.estado_display}
                    </span>
                  </div>

                  <div className="reserva-ticket-grid">
                    <div className="reserva-dato">
                      <Calendar size={15} />
                      <div>
                        <span className="reserva-dato-label">Fecha</span>
                        <span className="reserva-dato-value">
                          {new Date(reserva.viaje_info.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                            day: 'numeric', month: 'short', year: 'numeric',
                          })}
                        </span>
                      </div>
                    </div>
                    <div className="reserva-dato">
                      <Clock size={15} />
                      <div>
                        <span className="reserva-dato-label">Hora</span>
                        <span className="reserva-dato-value">{reserva.viaje_info.hora_salida?.slice(0, 5)}</span>
                      </div>
                    </div>
                    <div className="reserva-dato">
                      <Armchair size={15} />
                      <div>
                        <span className="reserva-dato-label">Asiento</span>
                        <span className="reserva-dato-value">#{reserva.numero_asiento}</span>
                      </div>
                    </div>
                    <div className="reserva-dato">
                      <Bus size={15} />
                      <div>
                        <span className="reserva-dato-label">Autobús</span>
                        <span className="reserva-dato-value">{reserva.viaje_info.autobus}</span>
                      </div>
                    </div>
                  </div>

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
                </div>

                {/* ── Talón (perforación a la izquierda) ── */}
                <div className="reserva-ticket-stub">
                  <div className="reserva-precio">
                    <span className="reserva-precio-label">Total</span>
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
                      <Ticket size={15} /> Ver Ticket
                    </button>
                  )}
                  {reserva.estado === 'pendiente' && reserva.grupo_pago && (
                    <button
                      className="btn reserva-btn reserva-btn-pagar"
                      onClick={() => navigate(`/pago?grupo=${reserva.grupo_pago}`)}
                    >
                      <CreditCard size={15} /> Ir a pagar
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
