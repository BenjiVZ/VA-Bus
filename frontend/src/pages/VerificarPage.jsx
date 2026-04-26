import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { verificarTicket } from '../services/api';
import { MapPin, Calendar, Clock, Bus, Armchair, User, CreditCard } from 'lucide-react';
import '../styles/TicketPage.css';

export default function VerificarPage() {
  const { codigoTicket } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    verificarTicket(codigoTicket)
      .then(res => setData(res.data))
      .catch(err => {
        if (err.response?.data) {
          setData(err.response.data);
        } else {
          setData({ valido: false, mensaje: 'Error de conexión.' });
        }
      })
      .finally(() => setLoading(false));
  }, [codigoTicket]);

  if (loading) {
    return (
      <div className="page">
        <div className="container" style={{ textAlign: 'center', padding: '4rem 0' }}>
          <div className="loading-spinner" />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Verificando ticket...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page verificar-page">
      <div className="container">
        <div className="verificar-card">
          <div className="verificar-header">
            <div className="verificar-icon">
              {data.valido ? '✅' : '❌'}
            </div>
            <h2>{data.valido ? 'Ticket Válido' : 'Ticket Inválido'}</h2>
            <div className={`verificar-estado ${data.valido ? 'valido' : 'invalido'}`}>
              {data.estado || 'No encontrado'}
            </div>
          </div>

          {data.datos && (
            <div className="verificar-datos">
              <div className="verificar-row">
                <span className="verificar-label"><User size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Pasajero</span>
                <span className="verificar-value">{data.datos.nombre_pasajero || '—'}</span>
              </div>
              {data.datos.cedula_pasajero && (
                <div className="verificar-row">
                  <span className="verificar-label"><CreditCard size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Cédula</span>
                  <span className="verificar-value">{data.datos.cedula_pasajero}</span>
                </div>
              )}
              <div className="verificar-row">
                <span className="verificar-label"><MapPin size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Ruta</span>
                <span className="verificar-value">
                  {data.datos.origen} → {data.datos.destino}
                </span>
              </div>
              <div className="verificar-row">
                <span className="verificar-label"><Calendar size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Fecha</span>
                <span className="verificar-value">
                  {new Date(data.datos.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                    day: 'numeric', month: 'long', year: 'numeric',
                  })}
                </span>
              </div>
              <div className="verificar-row">
                <span className="verificar-label"><Clock size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Hora</span>
                <span className="verificar-value">{data.datos.hora_salida?.slice(0, 5)}</span>
              </div>
              <div className="verificar-row">
                <span className="verificar-label"><Bus size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Autobús</span>
                <span className="verificar-value">{data.datos.autobus}</span>
              </div>
              <div className="verificar-row">
                <span className="verificar-label"><Armchair size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Asiento</span>
                <span className="verificar-value">
                  #{data.datos.numero_asiento} — Piso {data.datos.piso_asiento}
                </span>
              </div>
              {data.datos.para_otra_persona && data.datos.nombre_asignado && (
                <>
                  <div className="verificar-row" style={{ borderTop: '2px solid var(--blue-100)', paddingTop: '0.5rem' }}>
                    <span className="verificar-label" style={{ color: 'var(--blue-600)' }}><User size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Asignado a</span>
                    <span className="verificar-value">{data.datos.nombre_asignado}</span>
                  </div>
                  {data.datos.cedula_asignado && (
                    <div className="verificar-row">
                      <span className="verificar-label"><CreditCard size={14} style={{ marginRight: 4, verticalAlign: 'middle' }} />Cédula asignado</span>
                      <span className="verificar-value">{data.datos.cedula_asignado}</span>
                    </div>
                  )}
                </>
              )}
              {(data.datos.es_menor_edad || data.datos.viaja_con_animal || data.datos.es_discapacitado) && (
                <div className="ticket-permisos" style={{ padding: '0.75rem 0 0', borderTop: 'none' }}>
                  <span className="ticket-permisos-title">Condiciones</span>
                  <div className="ticket-permisos-list">
                    {data.datos.es_menor_edad && (
                      <div className="ticket-permiso-badge ticket-permiso-menor">
                        <span className="ticket-permiso-icon">👶</span>
                        <div><strong>Menor de edad</strong></div>
                      </div>
                    )}
                    {data.datos.viaja_con_animal && (
                      <div className="ticket-permiso-badge ticket-permiso-animal">
                        <span className="ticket-permiso-icon">🐾</span>
                        <div><strong>Viaja con animal</strong></div>
                      </div>
                    )}
                    {data.datos.es_discapacitado && (
                      <div className="ticket-permiso-badge ticket-permiso-discapacidad">
                        <span className="ticket-permiso-icon">♿</span>
                        <div><strong>Persona con discapacidad</strong></div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {!data.datos && (
            <div style={{ padding: '1.5rem', color: 'var(--text-muted)' }}>
              <p>{data.mensaje}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
