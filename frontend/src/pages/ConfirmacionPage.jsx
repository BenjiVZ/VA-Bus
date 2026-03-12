import { useLocation, useNavigate, Link } from 'react-router-dom';

export default function ConfirmacionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state;

  if (!state) {
    return (
      <div className="page">
        <div className="container">
          <div className="empty-state">
            <div className="empty-state-icon">❌</div>
            <h3>No hay datos de reserva</h3>
            <p style={{ marginTop: '0.5rem' }}>
              <Link to="/" className="btn btn-primary" style={{ marginTop: '1rem', display: 'inline-flex' }}>
                Volver al Inicio
              </Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  const { reservas, whatsapp_url, viaje, total_usd, total_bs } = state;

  return (
    <div className="page">
      <div className="container">
        <div className="confirmation-card card">
          <div className="confirmation-icon">✅</div>
          <h2>¡Reserva Creada!</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Tu reserva está <strong style={{ color: 'var(--warning-400)' }}>pendiente de confirmación</strong>.
            Coordina el pago con nuestro vendedor por WhatsApp.
          </p>

          <div className="confirmation-details">
            <div className="confirmation-row">
              <span className="confirmation-label">Ruta</span>
              <span className="confirmation-value">{viaje.ruta.origen} → {viaje.ruta.destino}</span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Fecha</span>
              <span className="confirmation-value">
                {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })}
              </span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Hora</span>
              <span className="confirmation-value">{viaje.hora_salida?.slice(0, 5)}</span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Autobús</span>
              <span className="confirmation-value">{viaje.autobus.nombre}</span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Asientos</span>
              <span className="confirmation-value">
                {reservas.map((r) => `#${r.numero_asiento}`).join(', ')}
              </span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Reserva(s)</span>
              <span className="confirmation-value">
                {reservas.map((r) => `#${r.id}`).join(', ')}
              </span>
            </div>
            <div className="confirmation-row">
              <span className="confirmation-label">Total USD</span>
              <span className="confirmation-value" style={{ color: 'var(--primary-400)', fontWeight: '800' }}>
                ${Number(total_usd).toFixed(2)}
              </span>
            </div>
            {total_bs && (
              <div className="confirmation-row" style={{ borderBottom: 'none' }}>
                <span className="confirmation-label">Total Bs</span>
                <span className="confirmation-value">
                  Bs. {Number(total_bs).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}
          </div>

          <div className="alert alert-info">
            📱 Envía un mensaje por WhatsApp al vendedor para confirmar tu pago. Una vez confirmado, tu puesto quedará reservado.
          </div>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginTop: '1rem' }}>
            <a
              href={whatsapp_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-whatsapp"
            >
              📱 Contactar por WhatsApp
            </a>
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/mis-reservas')}
            >
              Ver Mis Reservas
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
