import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { buscarViajes, getTasaCambio, getRutas } from '../services/api';
import PriceDisplay from '../components/PriceDisplay';
import { Bus, ArrowRight, Armchair, Search, MapPin, Calendar, X, SlidersHorizontal, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import Flatpickr from "react-flatpickr";
import "flatpickr/dist/themes/material_blue.css";
import { Spanish } from "flatpickr/dist/l10n/es.js";

export default function ViajesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [viajes, setViajes] = useState([]);
  const [allViajes, setAllViajes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tasa, setTasa] = useState(null);
  const [rutas, setRutas] = useState([]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const PAGE_SIZE = 20;

  // City search state
  const [cityQuery, setCityQuery] = useState(searchParams.get('ciudad') || '');
  const [cityActive, setCityActive] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef(null);

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

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Load rutas for dropdown options
  useEffect(() => {
    getRutas()
      .then((res) => setRutas(res.data))
      .catch(() => {});
  }, []);

  // All unique cities (for autocomplete)
  const allCities = useMemo(() => {
    const set = new Set();
    rutas.forEach((r) => {
      set.add(r.origen);
      set.add(r.destino);
    });
    return [...set].sort();
  }, [rutas]);

  // Filtered suggestions based on query
  const suggestions = useMemo(() => {
    if (!cityQuery || cityQuery.length < 1) return [];
    const q = cityQuery.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return allCities.filter((c) => {
      const normalized = c.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      return normalized.includes(q);
    });
  }, [cityQuery, allCities]);

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
    params.page = currentPage;

    buscarViajes(params)
      .then((viajesRes) => {
        const data = viajesRes.data;
        // Handle paginated response format: { count, next, previous, results }
        if (data.results) {
          setAllViajes(data.results);
          setViajes(data.results);
          setTotalCount(data.count || 0);
          setTotalPages(Math.ceil((data.count || 0) / PAGE_SIZE));
        } else {
          // Fallback for non-paginated response
          setAllViajes(data);
          setViajes(data);
          setTotalCount(data.length);
          setTotalPages(1);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    // Tasa de cambio carga aparte (no bloquea el listado)
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => null);
  }, [origen, destino, fecha, currentPage]);

  // Apply city filter on top of fetched results
  useEffect(() => {
    if (cityActive) {
      const q = cityActive.toLowerCase();
      const filtered = allViajes.filter(
        (v) => v.ruta.origen.toLowerCase() === q || v.ruta.destino.toLowerCase() === q
      );
      setViajes(filtered);
    } else {
      setViajes(allViajes);
    }
  }, [cityActive, allViajes]);

  const activeFilterCount = [origen, destino, fecha].filter(Boolean).length;
  const totalActiveFilters = activeFilterCount + (cityActive ? 1 : 0);

  const handleCitySelect = (city) => {
    setCityQuery(city);
    setCityActive(city);
    setShowSuggestions(false);
  };

  const handleClearCity = () => {
    setCityQuery('');
    setCityActive('');
    setShowSuggestions(false);
  };

  const handleBuscar = (e) => {
    e.preventDefault();
    setCurrentPage(1);
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
    setCityQuery('');
    setCityActive('');
    setCurrentPage(1);
    setSearchParams({});
  };

  // Pagination helpers
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  };

  return (
    <div className="page">
      <div className="container">
        {/* ── City Search Bar ── */}
        <div className="city-search-wrapper" ref={searchRef}>
          <div className="city-search-bar">
            <Search size={18} className="city-search-icon" />
            <input
              type="text"
              className="city-search-input"
              placeholder="Buscar ciudad..."
              value={cityQuery}
              onChange={(e) => {
                setCityQuery(e.target.value);
                setShowSuggestions(true);
                if (!e.target.value) {
                  setCityActive('');
                }
              }}
              onFocus={() => cityQuery && setShowSuggestions(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && suggestions.length > 0) {
                  e.preventDefault();
                  handleCitySelect(suggestions[0]);
                }
              }}
            />
            {cityQuery && (
              <button className="city-search-clear" onClick={handleClearCity} type="button">
                <X size={16} />
              </button>
            )}
          </div>
          {showSuggestions && suggestions.length > 0 && (
            <div className="city-suggestions">
              {suggestions.map((city) => {
                const routeCount = allViajes.filter(
                  (v) => v.ruta.origen.toLowerCase() === city.toLowerCase() || v.ruta.destino.toLowerCase() === city.toLowerCase()
                ).length;
                return (
                  <button
                    key={city}
                    className={`city-suggestion-item ${cityActive === city ? 'active' : ''}`}
                    onClick={() => handleCitySelect(city)}
                  >
                    <MapPin size={14} />
                    <span className="city-suggestion-name">{city}</span>
                    <span className="city-suggestion-count">{routeCount} viaje{routeCount !== 1 ? 's' : ''}</span>
                  </button>
                );
              })}
            </div>
          )}
          {showSuggestions && cityQuery.length >= 1 && suggestions.length === 0 && (
            <div className="city-suggestions">
              <div className="city-suggestion-empty">No se encontraron ciudades</div>
            </div>
          )}
          {cityActive && (
            <div className="city-active-badge">
              <MapPin size={13} />
              Mostrando viajes de/hacia <strong>{cityActive}</strong>
              <X size={14} className="city-active-close" onClick={handleClearCity} />
            </div>
          )}
        </div>

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
              <Flatpickr
                id="filtro-fecha"
                className="form-control"
                value={filtroFecha}
                onChange={(dates, dateStr) => setFiltroFecha(dateStr)}
                options={{
                  locale: Spanish,
                  dateFormat: "Y-m-d",
                  disableMobile: false
                }}
                placeholder="Seleccionar fecha"
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
        <div className="viajes-header">
          <div>
            <h2 className="viajes-header-title">
              <Bus size={22} strokeWidth={2} /> Viajes Disponibles
            </h2>
            <p className="viajes-header-count">
              {totalCount} viaje{totalCount !== 1 ? 's' : ''} encontrado{totalCount !== 1 ? 's' : ''}
              {totalPages > 1 && <span> — Página {currentPage} de {totalPages}</span>}
            </p>
          </div>
          {tasa && (
            <div className="viajes-header-tasa">
              Tasa BCV: <strong>Bs. {Number(tasa).toFixed(2)}</strong> / $1
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
                        className="btn btn-primary btn-select-trip"
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

        {/* ── Pagination ── */}
        {!loading && totalPages > 1 && (
          <div className="pagination-bar">
            <button
              className="pagination-btn"
              disabled={currentPage <= 1}
              onClick={() => { setCurrentPage(currentPage - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
            >
              <ChevronLeft size={16} /> Anterior
            </button>

            <div className="pagination-pages">
              {getPageNumbers()[0] > 1 && (
                <>
                  <button className="pagination-num" onClick={() => { setCurrentPage(1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>1</button>
                  {getPageNumbers()[0] > 2 && <span className="pagination-dots">…</span>}
                </>
              )}
              {getPageNumbers().map((p) => (
                <button
                  key={p}
                  className={`pagination-num ${p === currentPage ? 'active' : ''}`}
                  onClick={() => { setCurrentPage(p); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                >
                  {p}
                </button>
              ))}
              {getPageNumbers()[getPageNumbers().length - 1] < totalPages && (
                <>
                  {getPageNumbers()[getPageNumbers().length - 1] < totalPages - 1 && <span className="pagination-dots">…</span>}
                  <button className="pagination-num" onClick={() => { setCurrentPage(totalPages); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>{totalPages}</button>
                </>
              )}
            </div>

            <button
              className="pagination-btn"
              disabled={currentPage >= totalPages}
              onClick={() => { setCurrentPage(currentPage + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
            >
              Siguiente <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
