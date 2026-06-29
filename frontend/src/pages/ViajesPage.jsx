import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { buscarViajes, getViajesLocales, getTasaCambio, getAerorutasOficinas } from '../services/api';
import { useAuth } from '../context/AuthContext';
import PriceDisplay from '../components/PriceDisplay';
import { Bus, ArrowRight, Armchair, Search, MapPin, Calendar, X, Clock } from 'lucide-react';
import Flatpickr from "react-flatpickr";
import "flatpickr/dist/themes/material_blue.css";
import { Spanish } from "flatpickr/dist/l10n/es.js";

export default function ViajesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const esStaff = !!user?.is_staff;  // solo el staff ve los viajes de prueba locales
  const [viajes, setViajes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tasa, setTasa] = useState(null);
  const [oficinas, setOficinas] = useState([]);

  // Rango permitido: HOY hasta HOY+15 días (lo precargado). Se recalcula en cada carga.
  const hoy = new Date().toLocaleDateString('en-CA');
  const _max = new Date();
  _max.setDate(_max.getDate() + 15);
  const fechaMax = _max.toLocaleDateString('en-CA');

  // Filtros desde la URL (origen/destino = codofi). Por defecto: HOY.
  const origen = searchParams.get('origen') || '';
  const destino = searchParams.get('destino') || '';
  let fecha = searchParams.get('fecha') || hoy;
  if (fecha < hoy) fecha = hoy;          // nunca fechas pasadas
  if (fecha > fechaMax) fecha = fechaMax; // ni más allá del rango precargado

  const [filtroOrigen, setFiltroOrigen] = useState(origen);
  const [filtroDestino, setFiltroDestino] = useState(destino);
  const [filtroFecha, setFiltroFecha] = useState(fecha);

  useEffect(() => {
    setFiltroOrigen(origen);
    setFiltroDestino(destino);
    setFiltroFecha(fecha);
  }, [origen, destino, fecha]);

  // Oficinas en vivo desde Aerorutas (para los desplegables)
  useEffect(() => {
    getAerorutasOficinas().then((res) => setOficinas(res.data)).catch(() => {});
    getTasaCambio().then((res) => setTasa(res.data.tasa_bcv)).catch(() => null);
  }, []);

  const oficinasDestino = useMemo(
    () => oficinas.filter((o) => o.codofi !== filtroOrigen),
    [oficinas, filtroOrigen]
  );

  const busquedaCompleta = !!fecha; // basta la fecha; origen/destino son filtros opcionales

  // Buscar viajes: con solo fecha, el backend barre TODAS las rutas del día.
  useEffect(() => {
    if (!busquedaCompleta) {
      setViajes([]);
      return;
    }
    setLoading(true);
    const params = { fecha };
    if (origen && destino) { params.origen = origen; params.destino = destino; }
    const norm = (res) => res.data?.results || res.data || [];
    Promise.all([
      buscarViajes(params).then(norm).catch(() => []),
      // Viajes locales (incluye los de PRUEBA). Solo el staff los ve, así no
      // aparecen a los clientes. Sin filtro de fecha para que siempre se vean.
      esStaff ? getViajesLocales().then(norm).catch(() => []) : Promise.resolve([]),
    ])
      .then(([aero, locales]) => setViajes([...locales, ...aero]))
      .catch(() => setViajes([]))
      .finally(() => setLoading(false));
  }, [origen, destino, fecha, busquedaCompleta, esStaff]);

  const handleBuscar = (e) => {
    e.preventDefault();
    if (!filtroFecha) return;
    const params = { fecha: filtroFecha };
    if (filtroOrigen && filtroDestino) { params.origen = filtroOrigen; params.destino = filtroDestino; }
    setSearchParams(params);
  };

  const handleLimpiar = () => {
    setFiltroOrigen('');
    setFiltroDestino('');
    setFiltroFecha(hoy);
    setSearchParams({}); // vuelve a HOY (valor por defecto)
  };

  const nombreOficina = (codofi) => oficinas.find((o) => o.codofi === codofi)?.desofi || codofi;

  return (
    <div className="page">
      <div className="container">
        {/* ── Filtros ── */}
        <div className="viajes-filter-bar">
          <form className="viajes-filter-form" onSubmit={handleBuscar}>
            <div className="viajes-filter-field">
              <label htmlFor="filtro-origen"><MapPin size={14} /> Origen</label>
              <select
                id="filtro-origen"
                className="form-control"
                value={filtroOrigen}
                onChange={(e) => {
                  setFiltroOrigen(e.target.value);
                  if (e.target.value === filtroDestino) setFiltroDestino('');
                }}
              >
                <option value="">Selecciona origen…</option>
                {oficinas.map((o) => (
                  <option key={o.codofi} value={o.codofi}>{o.desofi}</option>
                ))}
              </select>
            </div>

            <div className="viajes-filter-field">
              <label htmlFor="filtro-destino"><MapPin size={14} /> Destino</label>
              <select
                id="filtro-destino"
                className="form-control"
                value={filtroDestino}
                onChange={(e) => setFiltroDestino(e.target.value)}
              >
                <option value="">Selecciona destino…</option>
                {oficinasDestino.map((o) => (
                  <option key={o.codofi} value={o.codofi}>{o.desofi}</option>
                ))}
              </select>
            </div>

            <div className="viajes-filter-field">
              <label htmlFor="filtro-fecha"><Calendar size={14} /> Fecha</label>
              <Flatpickr
                id="filtro-fecha"
                className="form-control"
                value={filtroFecha}
                onChange={(dates, dateStr) => setFiltroFecha(dateStr)}
                options={{ locale: Spanish, dateFormat: "Y-m-d", disableMobile: true, minDate: "today", maxDate: fechaMax }}
                placeholder="Seleccionar fecha"
              />
            </div>

            <div className="viajes-filter-actions">
              <button type="submit" className="btn btn-primary" disabled={!filtroFecha}>
                <Search size={16} /> Buscar
              </button>
              {busquedaCompleta && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={handleLimpiar}>
                  <X size={14} /> Limpiar
                </button>
              )}
            </div>
          </form>
        </div>

        {/* ── Header ── */}
        <div className="viajes-header">
          <div>
            <h2 className="viajes-header-title">
              <Bus size={22} strokeWidth={2} /> Viajes Disponibles
            </h2>
            {busquedaCompleta && (
              <p className="viajes-header-count">
                {origen && destino ? `${nombreOficina(origen)} → ${nombreOficina(destino)} · ` : ''}{fecha} — {viajes.length} viaje{viajes.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          {tasa && (
            <div className="viajes-header-tasa">
              Tasa BCV: <strong>Bs. {Number(tasa).toFixed(2)}</strong> / $1
            </div>
          )}
        </div>

        {/* ── Resultados ── */}
        {!busquedaCompleta ? (
          <div className="empty-state">
            <div className="empty-state-icon"><Search size={48} strokeWidth={1.5} /></div>
            <h3>Elige una fecha</h3>
            <p style={{ marginTop: '0.5rem' }}>Te mostramos todos los viajes disponibles de ese día. (Origen y destino son opcionales para filtrar.)</p>
          </div>
        ) : loading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : viajes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><Bus size={48} strokeWidth={1.5} /></div>
            <h3>No hay viajes para esa ruta y fecha</h3>
            <p style={{ marginTop: '0.5rem' }}>Prueba con otra fecha.</p>
          </div>
        ) : (
          <div className="trips-grid">
            {viajes.map((viaje) => (
              <div key={viaje.id} className="trip-card">
                <div className="trip-main">
                  <div className="trip-route-section">
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
                  </div>

                  <div className="trip-info">
                    <div className="trip-detail">
                      <div className="trip-detail-label">Fecha</div>
                      <div className="trip-detail-value">
                        {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                          day: 'numeric', month: 'short',
                        })}
                      </div>
                    </div>
                    <div className="trip-detail">
                      <div className="trip-detail-label">Hora</div>
                      <div className="trip-detail-value">{viaje.hora_salida?.slice(0, 5)}</div>
                    </div>
                    <div className="trip-detail">
                      <div className="trip-detail-label">Ruta</div>
                      <div className="trip-detail-value">{viaje.autobus.nombre}</div>
                    </div>
                  </div>
                </div>

                <div className="trip-action">
                  <div className="trip-seats-available">
                    {viaje.asientos_disponibles} puestos disponibles
                  </div>
                  <div className="trip-price">
                    {Number(viaje.precio_usd) > 0 ? (
                      <PriceDisplay priceUsd={viaje.precio_usd} />
                    ) : (
                      <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Precio a consultar</span>
                    )}
                  </div>
                  <button
                    className="btn btn-primary btn-select-trip"
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
