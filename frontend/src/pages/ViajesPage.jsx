import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { buscarViajes, getTasaCambio } from '../services/api';
import PriceDisplay from '../components/PriceDisplay';
import { Bus, ArrowRight, Armchair } from 'lucide-react';

export default function ViajesPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [viajes, setViajes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tasa, setTasa] = useState(null);

  const origen = searchParams.get('origen') || '';
  const destino = searchParams.get('destino') || '';
  const fecha = searchParams.get('fecha') || '';

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (origen) params.origen = origen;
    if (destino) params.destino = destino;
    if (fecha) params.fecha = fecha;

    Promise.all([
      buscarViajes(params),
      getTasaCambio().catch(() => ({ data: { tasa_bcv: null } })),
    ])
      .then(([viajesRes, tasaRes]) => {
        setViajes(viajesRes.data);
        setTasa(tasaRes.data.tasa_bcv);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [origen, destino, fecha]);

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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2>Viajes Disponibles</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              {viajes.length} viaje{viajes.length !== 1 ? 's' : ''} encontrado{viajes.length !== 1 ? 's' : ''}
              {origen && ` desde ${origen}`}
              {destino && ` hacia ${destino}`}
              {fecha && ` el ${fecha}`}
            </p>
          </div>
          {tasa && (
            <div style={{ textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Tasa BCV: <strong style={{ color: 'var(--primary-400)' }}>Bs. {Number(tasa).toFixed(2)}</strong> / $1
            </div>
          )}
        </div>

        {viajes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><Bus size={48} strokeWidth={1.5} /></div>
            <h3>No hay viajes disponibles</h3>
            <p style={{ marginTop: '0.5rem' }}>Intenta con otra fecha o ruta</p>
          </div>
        ) : (
          <div className="trips-grid">
            {viajes.map((viaje) => (
              <div key={viaje.id} className="trip-card">
                <div className="trip-main">
                  <div className="trip-route">
                    <div className="trip-city">
                      <div className="trip-city-name">{viaje.ruta.origen}</div>
                      <div className="trip-city-label">Origen</div>
                    </div>
                    <div className="trip-arrow"><ArrowRight size={20} /></div>
                    <div className="trip-city">
                      <div className="trip-city-name">{viaje.ruta.destino}</div>
                      <div className="trip-city-label">Destino</div>
                    </div>
                  </div>

                  <div className="trip-info">
                    <div className="trip-detail">
                      <div className="trip-detail-label">Fecha</div>
                      <div className="trip-detail-value">
                        {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                          day: 'numeric',
                          month: 'short',
                        })}
                      </div>
                    </div>
                    <div className="trip-detail">
                      <div className="trip-detail-label">Hora</div>
                      <div className="trip-detail-value">{viaje.hora_salida?.slice(0, 5)}</div>
                    </div>
                    <div className="trip-detail">
                      <div className="trip-detail-label">Autobús</div>
                      <div className="trip-detail-value">{viaje.autobus.nombre}</div>
                    </div>
                  </div>
                </div>

                <div className="trip-action">
                  <div className="trip-seats-available">
                    {viaje.asientos_disponibles} puestos disponibles
                  </div>
                  <div className="trip-price">
                    <PriceDisplay priceUsd={viaje.precio_usd} />
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ width: '100%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}
                    onClick={() => navigate(`/viajes/${viaje.id}/asientos`)}
                  >
                    <Armchair size={16} /> Seleccionar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
