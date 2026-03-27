import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { getTicket, getTasaCambio } from '../services/api';
import { Bus, MapPin, Calendar, Clock, Armchair, User, CreditCard, Printer } from 'lucide-react';
import './TicketPage.css';

export default function TicketPage() {
  const { grupoPago } = useParams();
  const [data, setData] = useState(null);
  const [tasa, setTasa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      getTicket(grupoPago),
      getTasaCambio(),
    ]).then(([ticketRes, tasaRes]) => {
      setData(ticketRes.data);
      setTasa(tasaRes.data.tasa_bcv);
    }).catch(err => {
      setError(err.response?.data?.error || 'Error al cargar el ticket.');
    }).finally(() => setLoading(false));
  }, [grupoPago]);

  const handlePrint = () => window.print();

  if (loading) {
    return (
      <div className="page">
        <div className="container" style={{ textAlign: 'center', padding: '4rem 0' }}>
          <div className="loading-spinner" />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Cargando ticket...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="container">
          <div className="empty-state">
            <div className="empty-state-icon">❌</div>
            <h3>{error}</h3>
            <Link to="/mis-reservas" className="btn btn-primary" style={{ marginTop: '1rem' }}>
              Ir a Mis Reservas
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const { viaje, tickets, empresa, rif } = data;
  const baseUrl = window.location.origin;

  const formatFecha = (fecha) =>
    new Date(fecha + 'T00:00:00').toLocaleDateString('es-VE', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });

  return (
    <div className="page ticket-page">
      <div className="container">
        <div className="ticket-header-actions no-print">
          <h2>🎫 Tus Boletos</h2>
          <button className="btn btn-secondary" onClick={handlePrint}>
            <Printer size={16} /> Imprimir
          </button>
        </div>

        {tickets.map((ticket, index) => (
          <div key={ticket.id} className="ticket-boleto">
            {/* Top decorative border */}
            <div className="ticket-top-border" />

            {/* Header */}
            <div className="ticket-empresa">
              <div className="ticket-empresa-logo">🚌</div>
              <div>
                <h3 className="ticket-empresa-name">{empresa}</h3>
                {rif && <span className="ticket-empresa-rif">RIF: {rif}</span>}
              </div>
              <div className="ticket-numero">
                Boleto #{ticket.id}
              </div>
            </div>

            {/* Route */}
            <div className="ticket-ruta">
              <div className="ticket-ciudad">
                <MapPin size={16} />
                <span>{viaje.origen}</span>
              </div>
              <div className="ticket-ruta-arrow">
                {viaje.tipo_viaje === 'ida_vuelta' ? '⇄' : '→'}
              </div>
              <div className="ticket-ciudad">
                <MapPin size={16} />
                <span>{viaje.destino}</span>
              </div>
            </div>

            {viaje.tipo_viaje === 'ida_vuelta' && (
              <div className="ticket-badge-roundtrip">Ida y Vuelta</div>
            )}

            {/* Details grid */}
            <div className="ticket-detalles">
              <div className="ticket-detalle">
                <Calendar size={14} />
                <div>
                  <span className="ticket-detalle-label">Fecha de Ida</span>
                  <span className="ticket-detalle-value">{formatFecha(viaje.fecha_salida)}</span>
                </div>
              </div>
              <div className="ticket-detalle">
                <Clock size={14} />
                <div>
                  <span className="ticket-detalle-label">Hora</span>
                  <span className="ticket-detalle-value">{viaje.hora_salida?.slice(0, 5)}</span>
                </div>
              </div>
              {viaje.tipo_viaje === 'ida_vuelta' && viaje.fecha_vuelta && (
                <div className="ticket-detalle">
                  <Calendar size={14} />
                  <div>
                    <span className="ticket-detalle-label">Fecha de Vuelta</span>
                    <span className="ticket-detalle-value">{formatFecha(viaje.fecha_vuelta)}</span>
                  </div>
                </div>
              )}
              <div className="ticket-detalle">
                <Bus size={14} />
                <div>
                  <span className="ticket-detalle-label">Autobús</span>
                  <span className="ticket-detalle-value">{viaje.autobus}</span>
                </div>
              </div>
              <div className="ticket-detalle">
                <Armchair size={14} />
                <div>
                  <span className="ticket-detalle-label">Asiento</span>
                  <span className="ticket-detalle-value">
                    #{ticket.numero_asiento} — Piso {ticket.piso_asiento}
                  </span>
                </div>
              </div>
              <div className="ticket-detalle">
                <CreditCard size={14} />
                <div>
                  <span className="ticket-detalle-label">Precio</span>
                  <span className="ticket-detalle-value">
                    ${Number(viaje.precio_usd).toFixed(2)}
                    {tasa && (
                      <small style={{ display: 'block', opacity: 0.7 }}>
                        Bs. {(viaje.precio_usd * tasa).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                      </small>
                    )}
                  </span>
                </div>
              </div>
            </div>

            {/* Passenger - Buyer info */}
            <div className="ticket-pasajero">
              <User size={16} />
              <div>
                <span className="ticket-pasajero-label">Comprador</span>
                <span className="ticket-pasajero-nombre">
                  {ticket.nombre_pasajero || 'Sin nombre'}
                </span>
                {ticket.cedula_pasajero && (
                  <span className="ticket-pasajero-cedula">C.I. {ticket.cedula_pasajero}</span>
                )}
              </div>
            </div>

            {/* Assigned person info */}
            {ticket.para_otra_persona && ticket.nombre_asignado && (
              <div className="ticket-pasajero ticket-asignado">
                <User size={16} />
                <div>
                  <span className="ticket-pasajero-label">Asignado a</span>
                  <span className="ticket-pasajero-nombre">{ticket.nombre_asignado}</span>
                  {ticket.cedula_asignado && (
                    <span className="ticket-pasajero-cedula">C.I. {ticket.cedula_asignado}</span>
                  )}
                </div>
              </div>
            )}

            {/* Minor badge */}
            {ticket.es_menor_edad && (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                background: '#fef3c7', color: '#92400e', fontSize: '0.75rem',
                fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '999px',
                margin: '0.5rem auto', textTransform: 'uppercase'
              }}>
                👶 Menor de edad
              </div>
            )}

            {/* Tear line + QR */}
            <div className="ticket-tear-line" />

            <div className="ticket-qr-section">
              <QRCodeSVG
                value={`${baseUrl}/verificar/${ticket.codigo_ticket}`}
                size={140}
                level="M"
                includeMargin={false}
              />
              <div className="ticket-qr-code">{ticket.codigo_ticket}</div>
              <div className="ticket-qr-hint">Escanea para verificar</div>
            </div>
          </div>
        ))}

        <div className="no-print" style={{ textAlign: 'center', marginTop: '2rem' }}>
          <Link to="/mis-reservas" className="btn btn-secondary">
            ← Volver a Mis Reservas
          </Link>
        </div>
      </div>
    </div>
  );
}
