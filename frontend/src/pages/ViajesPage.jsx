import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { buscarViajes, getTasaCambio, getRutas } from '../services/api';
import PriceDisplay from '../components/PriceDisplay';
import { Bus, ArrowRight, Armchair, Search, MapPin, Calendar, X, SlidersHorizontal, Clock } from 'lucide-react';

export default function ViajesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [viajes, setViajes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tasa, setTasa] = useState(null);
  const [rutas, setRutas] = useState([]);

  // Filter state from URL
  const origen = searchParams.get('origen') || '';
  const destino = searchParams.get('destino') || '';
  const fecha = searchParams.get('fecha') || '';

  // Local filter state (for controlled inputs)
  const [filtroOrigen, setFiltroOrigen] = useState(origen);
  const [filtroDestino, setFiltroDestino] = useState(destino);
  const [filtroFecha, setFiltroFecha] = useState(fecha);

  // Sync local state when URL changes externally
  useEffect(() => {
    setFiltroOrigen(origen);
    setFiltroDestino(destino);
    setFiltroFecha(fecha);
  }, [origen, destino, fecha]);

  // Load rutas for dropdown options
  useEffect(() => {
    getRutas()
      .then((res) => setRutas(res.data))
      .catch(() => {});
  }, []);

  // Unique cities for dropdowns
  const ciudadesOrigen = useMemo(() => {
    const set = new Set(rutas.map((r) => r.origen));
    return [...set].sort();
  }, [rutas]);

  const ciudadesDestino = useMemo(() => {
    let filtered = rutas;
    if (filtroOrigen) {
      filtered = rutas.filter((r) => r.origen === filtroOrigen);
    }
    const set = new Set(filtered.map((r) => r.destino));
    return [...set].sort();
  }, [rutas, filtroOrigen]);

  // Fetch viajes
  useEffect(() => {
    setLoading(true);
    const params = {};
    if (origen) params.origen = origen;
    if (destino) params.destino = destino;
    if (fecha) params.fecha = fecha;

    buscarViajes(params)
      .then((viajesRes) => {
        setViajes(viajesRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    // Tasa de cambio carga aparte (no bloquea el listado)
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => null);
  }, [origen, destino, fecha]);

  const activeFilterCount = [origen, destino, fecha].filter(Boolean).length;

  const handleBuscar = (e) => {
    e.preventDefault();
    const params = {};
    if (filtroOrigen) params.origen = filtroOrigen;
    if (filtroDestino) params.destino = filtroDestino;
    if (filtroFecha) params.fecha = filtroFecha;
    setSearchParams(params);
  };

  const handleLimpiar = () => {
    setFiltroOrigen('');
    setFiltroDestino('');
    setFiltroFecha('');
    setSearchParams({});
  };

  return (
    <div className="page">
      <div className="container">
        {/* ── Filter Bar ── */}
        <div className="viajes-filter-bar">
          <form className="viajes-filter-form" onSubmit={handleBuscar}>
            <div className="viajes-filter-field">
              <label htmlFor="filtro-origen">
                <MapPin size={14} /> Origen
              </label>
              <select
                id="filtro-origen"
                className="form-control"
                value={filtroOrigen}
                onChange={(e) => {
                  setFiltroOrigen(e.target.value);
                  // Reset destino if origin changes
                  if (filtroDestino) {
                    const validDestinos = rutas
                      .filter((r) => r.origen === e.target.value)
                      .map((r) => r.destino);
                    if (!validDestinos.includes(filtroDestino)) {
                      setFiltroDestino('');
                    }
                  }
                }}
              >
                <option value="">Todos los orígenes</option>
                {ciudadesOrigen.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="viajes-filter-field">
              <label htmlFor="filtro-destino">
                <MapPin size={14} /> Destino
              </label>
              <select
                id="filtro-destino"
                className="form-control"
                value={filtroDestino}
                onChange={(e) => setFiltroDestino(e.target.value)}
              >
                <option value="">Todos los destinos</option>
                {ciudadesDestino.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="viajes-filter-field">
              <label htmlFor="filtro-fecha">
                <Calendar size={14} /> Fecha
              </label>
              <input
                id="filtro-fecha"
                type="date"
                className="form-control"
                value={filtroFecha}
                onChange={(e) => setFiltroFecha(e.target.value)}
              />
            </div>

            <div className="viajes-filter-actions">
              <button type="submit" className="btn btn-primary">
                <Search size={16} /> Buscar
              </button>
              {activeFilterCount > 0 && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={handleLimpiar}>
                  <X size={14} /> Limpiar
                </button>
              )}
            </div>
          </form>

          {activeFilterCount > 0 && (
            <div className="viajes-active-filters">
              <SlidersHorizontal size={14} />
              <span>{activeFilterCount} filtro{activeFilterCount !== 1 ? 's' : ''} activo{activeFilterCount !== 1 ? 's' : ''}</span>
              {origen && <span className="viajes-filter-tag">Origen: {origen} <X size={12} onClick={() => { setFiltroOrigen(''); const p = new URLSearchParams(searchParams); p.delete('origen'); setSearchParams(p); }} /></span>}
              {destino && <span className="viajes-filter-tag">Destino: {destino} <X size={12} onClick={() => { setFiltroDestino(''); const p = new URLSearchParams(searchParams); p.delete('destino'); setSearchParams(p); }} /></span>}
              {fecha && <span className="viajes-filter-tag">Fecha: {fecha} <X size={12} onClick={() => { setFiltroFecha(''); const p = new URLSearchParams(searchParams); p.delete('fecha'); setSearchParams(p); }} /></span>}
            </div>
          )}
        </div>

        {/* ── Header ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2>Viajes Disponibles</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              {viajes.length} viaje{viajes.length !== 1 ? 's' : ''} encontrado{viajes.length !== 1 ? 's' : ''}
            </p>
          </div>
          {tasa && (
            <div style={{ textAlign: 'right', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Tasa BCV: <strong style={{ color: 'var(--primary-400)' }}>Bs. {Number(tasa).toFixed(2)}</strong> / $1
            </div>
          )}
        </div>

        {/* ── Results ── */}
        {loading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : viajes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><Bus size={48} strokeWidth={1.5} /></div>
            <h3>No hay viajes disponibles</h3>
            <p style={{ marginTop: '0.5rem' }}>Intenta con otra fecha o ruta</p>
            {activeFilterCount > 0 && (
              <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={handleLimpiar}>
                <X size={16} /> Limpiar filtros
              </button>
            )}
          </div>
        ) : (
          <div className="trips-grid">
            {viajes.map((viaje) => {
              const busNoDisponible = viaje.autobus.disponible === false;
              return (
              <div key={viaje.id} className={`trip-card ${busNoDisponible ? 'trip-card-unavailable' : ''}`}>
                <div className="trip-main">
                  <div className="trip-route-section">
                    <div className="trip-route">
                      <div className="trip-city">
                        <div className="trip-city-name">{viaje.ruta.origen}</div>
                        <div className="trip-city-label">Origen</div>
                      </div>
                      <div className="trip-arrow">
                        {viaje.tipo_viaje === 'ida_vuelta' ? '⇄' : <ArrowRight size={20} />}
                      </div>
                      <div className="trip-city">
                        <div className="trip-city-name">{viaje.ruta.destino}</div>
                        <div className="trip-city-label">Destino</div>
                      </div>
                      {viaje.tipo_viaje === 'ida_vuelta' && (
                        <div className="trip-type-badge">Ida y Vuelta</div>
                      )}
                    </div>
                  </div>

                  <div className="trip-info">
                    <div className="trip-detail">
                      <div className="trip-detail-label">Fecha Ida</div>
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
                    {viaje.tipo_viaje === 'ida_vuelta' && viaje.fecha_vuelta && (
                      <div className="trip-detail">
                        <div className="trip-detail-label">Vuelta</div>
                        <div className="trip-detail-value">
                          {new Date(viaje.fecha_vuelta + 'T00:00:00').toLocaleDateString('es-VE', {
                            day: 'numeric',
                            month: 'short',
                          })}
                          {viaje.hora_vuelta && ` ${viaje.hora_vuelta.slice(0, 5)}`}
                        </div>
                      </div>
                    )}
                    <div className="trip-detail">
                      <div className="trip-detail-label">Autobús</div>
                      <div className="trip-detail-value">{viaje.autobus.nombre}</div>
                    </div>
                  </div>
                </div>

                <div className="trip-action">
                  {busNoDisponible ? (
                    <div className="bus-unavailable-banner">
                      <strong>🚫 Autobús no disponible</strong>
                      {viaje.autobus.motivo_no_disponible && (
                        <span>{viaje.autobus.motivo_no_disponible}</span>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="trip-seats-available">
                        {viaje.asientos_disponibles} puestos disponibles
                      </div>
                      {viaje.fecha_fin_venta && (
                        <div className="trip-closing-date">
                          <Clock size={12} />
                          Cierra {new Date(viaje.fecha_fin_venta + 'T00:00:00').toLocaleDateString('es-VE', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </div>
                      )}
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
                    </>
                  )}
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
