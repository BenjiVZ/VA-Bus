import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  adminGetReservas, adminCambiarEstado, adminCambiarAsiento,
  getAsientos,
} from '../services/api';
import SeatMap from '../components/SeatMap';
import { ArrowLeft, CheckCircle, XCircle, RefreshCw, ArrowRightLeft, Users, Clock, Hash, Crosshair, X } from 'lucide-react';

export default function AdminViajePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [reservas, setReservas] = useState([]);
  const [stats, setStats] = useState({});
  const [seatData, setSeatData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [changingSeat, setChangingSeat] = useState(null);
  const [movingReserva, setMovingReserva] = useState(null);

  useEffect(() => {
    if (!user?.is_staff) { navigate('/'); return; }
    loadData();
  }, [user, id]);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      adminGetReservas(id),
      getAsientos(id).catch(() => null),
    ])
      .then(([resReservas, resSeat]) => {
        setReservas(resReservas.data.reservas);
        setStats(resReservas.data);
        if (resSeat) setSeatData(resSeat.data);
      })
      .catch(() => setError('Error al cargar datos.'))
      .finally(() => setLoading(false));
  };

  const handleEstado = async (reservaId, estado) => {
    try {
      await adminCambiarEstado(reservaId, estado);
      loadData();
    } catch (err) {
      setError(err.response?.data?.error || 'Error');
    }
  };

  const handleMoverAsiento = async (reservaId, numero, piso) => {
    if (!numero) return;
    try {
      await adminCambiarAsiento(reservaId, numero, piso);
      setMovingReserva(null);
      loadData();
    } catch (err) {
      setError(err.response?.data?.error || 'Error al mover asiento');
    }
  };

  const handleSeatClickForMove = (seat) => {
    if (!movingReserva) return;
    handleMoverAsiento(movingReserva.id, seat.numero, seat.piso);
  };

  const startMoving = (reserva) => {
    setMovingReserva(movingReserva?.id === reserva.id ? null : reserva);
  };

  const cancelMoving = () => {
    setMovingReserva(null);
  };

  if (loading) {
    return (
      <div className="page"><div className="container">
        <div className="loading"><div className="spinner" /></div>
      </div></div>
    );
  }

  const viaje = seatData?.viaje;

  return (
    <div className="page">
      <div className="container">
        <button className="btn btn-secondary" onClick={() => navigate('/admin/panel')}
          style={{ marginBottom: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
          <ArrowLeft size={16} /> Volver al Panel
        </button>

        <h2 style={{ marginBottom: '0.25rem' }}>
          {viaje ? `${viaje.ruta.origen} → ${viaje.ruta.destino}` : `Viaje #${id}`}
        </h2>
        {viaje && (
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            {viaje.autobus.nombre} ·{' '}
            {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
              weekday: 'long', day: 'numeric', month: 'long',
            })} · {viaje.hora_salida?.slice(0, 5)}
          </p>
        )}

        {error && <div className="alert alert-error" style={{ marginBottom: '1rem' }}>{error}</div>}

        {/* Stats */}
        <div className="admin-stats-bar">
          <div className="admin-stat-box">
            <span className="stat-num">{stats.total || 0}</span>
            <span className="stat-label"><Users size={14} style={{ verticalAlign: 'middle', marginRight: '3px' }} />Total</span>
          </div>
          <div className="admin-stat-box stat-success">
            <span className="stat-num">{stats.confirmadas || 0}</span>
            <span className="stat-label"><CheckCircle size={14} style={{ verticalAlign: 'middle', marginRight: '3px' }} />Confirmadas</span>
          </div>
          <div className="admin-stat-box stat-warning">
            <span className="stat-num">{stats.pendientes || 0}</span>
            <span className="stat-label"><Clock size={14} style={{ verticalAlign: 'middle', marginRight: '3px' }} />Pendientes</span>
          </div>
        </div>

        <div className="admin-viaje-layout">
          {/* Seat map */}
          {seatData?.pisos_config && (
            <div className="admin-seatmap-panel">
              {movingReserva && (
                <div className="seat-move-banner">
                  <div className="seat-move-banner-content">
                    <Crosshair size={18} className="seat-move-banner-icon" />
                    <div>
                      <strong>Moviendo Asiento #{movingReserva.numero_asiento}</strong>
                      <span className="seat-move-banner-sub">
                        {movingReserva.nombre_pasajero || movingReserva.usuario_info?.nombre || 'Sin nombre'}
                        {' · '}Haz clic en un asiento disponible
                      </span>
                    </div>
                  </div>
                  <button className="btn btn-sm seat-move-cancel" onClick={cancelMoving}>
                    <X size={14} /> Cancelar
                  </button>
                </div>
              )}
              <h4 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <Hash size={16} /> Mapa de Asientos
              </h4>
              <SeatMap
                pisosConfig={seatData.pisos_config}
                selectedSeats={[]}
                onToggleSeat={movingReserva ? handleSeatClickForMove : () => {}}
                isMovingMode={!!movingReserva}
                movingSeatNumber={movingReserva ? { numero: movingReserva.numero_asiento, piso: movingReserva.piso_asiento } : null}
              />
            </div>
          )}

          {/* Reservations table */}
          <div className="admin-reservas-panel">
            <h4 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <Users size={16} /> Reservas ({reservas.length})
            </h4>
            {reservas.length === 0 ? (
              <p style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '2rem' }}>
                No hay reservas para este viaje.
              </p>
            ) : (
              <div className="admin-reservas-list">
                {reservas.map((r) => (
                  <div key={r.id} className={`admin-reserva-card estado-${r.estado}`}>
                    <div className="reserva-header">
                      <span className="reserva-seat">Asiento #{r.numero_asiento} <small>(P{r.piso_asiento})</small></span>
                      <span className={`badge badge-${r.estado === 'confirmado' ? 'success' : r.estado === 'pendiente' ? 'warning' : 'danger'}`}>
                        {r.estado_display}
                      </span>
                    </div>
                    <div className="reserva-client">
                      <strong>{r.nombre_pasajero || r.usuario_info?.nombre || 'Sin nombre'}</strong>
                      {r.cedula_pasajero && <span> · CI: {r.cedula_pasajero}</span>}
                      {r.usuario_info?.telefono && <span> · Tel: {r.usuario_info.telefono}</span>}
                    </div>
                    <div className="reserva-user-detail">
                      <small>
                        Usuario: {r.usuario_info?.username} · {r.usuario_info?.email || ''}
                      </small>
                    </div>
                    <div className="reserva-actions">
                      {r.estado === 'pendiente' && (
                        <>
                          <button className="btn btn-success btn-sm" onClick={() => handleEstado(r.id, 'confirmado')}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                            <CheckCircle size={14} /> Confirmar Pago
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleEstado(r.id, 'cancelado')}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                            <XCircle size={14} /> Cancelar
                          </button>
                        </>
                      )}
                      {r.estado === 'confirmado' && (
                        <button className="btn btn-secondary btn-sm" onClick={() => handleEstado(r.id, 'cancelado')}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <XCircle size={14} /> Cancelar Reserva
                        </button>
                      )}
                      {r.estado === 'cancelado' && (
                        <button className="btn btn-secondary btn-sm" onClick={() => handleEstado(r.id, 'pendiente')}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <RefreshCw size={14} /> Reactivar
                        </button>
                      )}
                      <button className={`btn btn-sm ${movingReserva?.id === r.id ? 'btn-warning' : 'btn-secondary'}`}
                        onClick={() => startMoving(r)}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                        <ArrowRightLeft size={14} /> {movingReserva?.id === r.id ? 'Seleccionando...' : 'Cambiar Asiento'}
                      </button>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
