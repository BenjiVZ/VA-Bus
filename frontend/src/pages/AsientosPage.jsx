import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAsientos, crearReserva, getTasaCambio } from '../services/api';
import { useAuth } from '../context/AuthContext';
import SeatMap from '../components/SeatMap';
import PriceDisplay from '../components/PriceDisplay';
import { ClipboardList, User, Armchair, Baby, UserPlus, AlertTriangle } from 'lucide-react';

export default function AsientosPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [tasa, setTasa] = useState(null);
  const [nombre, setNombre] = useState('');
  const [cedula, setCedula] = useState('');
  const [cedulaTipo, setCedulaTipo] = useState('V');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Per-seat options: { seatKey: { es_menor, para_otra, nombre_asignado, cedula_asignado, cedula_tipo_asignado } }
  const [seatOptions, setSeatOptions] = useState({});

  // Track seats where user toggled "menor" on then off (fraud detection)
  const [menorToggled, setMenorToggled] = useState({});

  useEffect(() => {
    Promise.all([
      getAsientos(id),
      getTasaCambio().catch(() => ({ data: { tasa_bcv: null } })),
    ])
      .then(([asientosRes, tasaRes]) => {
        setData(asientosRes.data);
        setTasa(tasaRes.data.tasa_bcv);
        // Pre-fill passenger info from user profile
        if (user) {
          setNombre(`${user.first_name || ''} ${user.last_name || ''}`.trim());
          const rawCedula = user.cedula || '';
          const match = rawCedula.match(/^([VJE])-?(.*)$/i);
          if (match) {
            setCedulaTipo(match[1].toUpperCase());
            setCedula(match[2]);
          } else {
            setCedula(rawCedula);
          }
        }
      })
      .catch(() => setError('Error al cargar los asientos.'))
      .finally(() => setLoading(false));
  }, [id, user]);

  const getSeatKey = (seat) => `${seat.piso}-${seat.numero}`;

  const handleToggleSeat = (seat) => {
    const key = getSeatKey(seat);
    setSelectedSeats((prev) => {
      const exists = prev.some((s) => s.numero === seat.numero && s.piso === seat.piso);
      if (exists) {
        // Remove seat options too
        setSeatOptions((opts) => {
          const copy = { ...opts };
          delete copy[key];
          return copy;
        });
        return prev.filter((s) => !(s.numero === seat.numero && s.piso === seat.piso));
      }
      // Initialize seat options
      setSeatOptions((opts) => ({
        ...opts,
        [key]: { es_menor: false, para_otra: false, nombre_asignado: '', cedula_asignado: '', cedula_tipo_asignado: 'V' },
      }));
      return [...prev, seat];
    });
  };

  const updateSeatOption = (key, field, value) => {
    // Track if user toggled "es_menor" on then off
    if (field === 'es_menor') {
      const currentlyMinor = seatOptions[key]?.es_menor || false;
      if (currentlyMinor && !value) {
        // User is unchecking minor → flag this seat
        setMenorToggled((prev) => ({ ...prev, [key]: true }));
      }
    }
    setSeatOptions((opts) => ({
      ...opts,
      [key]: { ...opts[key], [field]: value },
    }));
  };

  // Check if any seat currently has es_menor checked
  const hasMinorSelected = selectedSeats.some((s) => {
    const opts = seatOptions[getSeatKey(s)] || {};
    return opts.es_menor;
  });

  // Check if any seat had minor toggled on then off
  const hasMinorWarning = selectedSeats.some((s) => menorToggled[getSeatKey(s)]);

  const totalUsd = data ? selectedSeats.length * Number(data.viaje.precio_usd) : 0;
  const totalBs = tasa ? totalUsd * tasa : null;

  const handleReservar = async () => {
    if (!user) {
      navigate('/login');
      return;
    }

    if (selectedSeats.length === 0) return;

    // Validate: if para_otra, must have nombre_asignado
    for (const seat of selectedSeats) {
      const key = getSeatKey(seat);
      const opts = seatOptions[key] || {};
      if (opts.para_otra && !opts.nombre_asignado.trim()) {
        setError(`Asiento #${seat.numero}: Debes ingresar el nombre de la persona asignada.`);
        return;
      }
    }

    setSubmitting(true);
    setError('');

    try {
      const res = await crearReserva({
        viaje_id: Number(id),
        asientos: selectedSeats.map((s) => {
          const key = getSeatKey(s);
          const opts = seatOptions[key] || {};
          return {
            numero: s.numero,
            piso: s.piso,
            es_menor: opts.es_menor || false,
            para_otra: opts.para_otra || false,
            nombre_asignado: opts.nombre_asignado || '',
            cedula_asignado: opts.cedula_asignado
              ? `${opts.cedula_tipo_asignado || 'V'}-${opts.cedula_asignado}`
              : '',
          };
        }),
        nombre_pasajero: nombre,
        cedula_pasajero: cedula ? `${cedulaTipo}-${cedula}` : '',
      });

      // Check anti-spam block
      if (res.data.bloqueado) {
        setError(res.data.error);
        return;
      }

      navigate('/pago', {
        state: {
          reservas: res.data.reservas,
          grupo_pago: res.data.grupo_pago,
          fecha_expiracion: res.data.fecha_expiracion,
          viaje_info: res.data.viaje_info,
        },
      });
    } catch (err) {
      const msg = err.response?.data?.error || 'Error al crear la reserva.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="container">
          <div className="loading"><div className="spinner" /></div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page">
        <div className="container">
          <div className="alert alert-error">{error || 'Viaje no encontrado.'}</div>
        </div>
      </div>
    );
  }

  const { viaje, pisos_config } = data;

  return (
    <div className="page">
      <div className="container">
        <div style={{ marginBottom: '2rem' }}>
          <h2>Selecciona tus Asientos</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {viaje.ruta.origen} → {viaje.ruta.destino} · {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', { weekday: 'long', day: 'numeric', month: 'long' })} · {viaje.hora_salida?.slice(0, 5)}
          </p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="alert alert-info" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          👶 <strong>Nota:</strong> Los menores de edad deben viajar acompañados por un adulto responsable.
        </div>

        <div className="asientos-layout">
          <div>
            <div className="seat-map-container">
              <SeatMap
                pisosConfig={pisos_config}
                selectedSeats={selectedSeats}
                onToggleSeat={handleToggleSeat}
              />
            </div>
          </div>

          <div className="selection-sidebar">
            <div className="card" style={{ marginBottom: '1rem' }}>
              <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <ClipboardList size={16} /> Resumen
              </h4>

              <div className="confirmation-details" style={{ margin: 0 }}>
                <div className="confirmation-row">
                  <span className="confirmation-label">Ruta</span>
                  <span className="confirmation-value">{viaje.ruta.origen} → {viaje.ruta.destino}</span>
                </div>
                <div className="confirmation-row">
                  <span className="confirmation-label">Autobús</span>
                  <span className="confirmation-value">{viaje.autobus.nombre}</span>
                </div>
                <div className="confirmation-row">
                  <span className="confirmation-label">Precio/asiento</span>
                  <span className="confirmation-value">
                    <PriceDisplay priceUsd={viaje.precio_usd} />
                  </span>
                </div>
                <div className="confirmation-row">
                  <span className="confirmation-label">Asientos</span>
                  <span className="confirmation-value">
                    {selectedSeats.length > 0
                      ? selectedSeats.map((s) => `#${s.numero}`).join(', ')
                      : 'Ninguno seleccionado'}
                  </span>
                </div>
                <div className="confirmation-row" style={{ borderBottom: 'none' }}>
                  <span className="confirmation-label" style={{ fontWeight: '700', color: 'var(--text-primary)' }}>Total</span>
                  <span className="confirmation-value">
                    {selectedSeats.length > 0 ? (
                      <PriceDisplay priceUsd={totalUsd} />
                    ) : (
                      '--'
                    )}
                  </span>
                </div>
              </div>
            </div>

            {selectedSeats.length > 0 && (
              <div className="card" style={{ animation: 'fadeIn 0.3s ease' }}>
                <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <User size={16} /> Datos del Comprador
                </h4>
                <div className="form-group">
                  <label>Nombre Completo</label>
                  <input
                    type="text"
                    className="form-control"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder="Nombre y apellido"
                  />
                </div>
                <div className="form-group">
                  <label>Cédula</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <select
                      className="form-control"
                      value={cedulaTipo}
                      onChange={(e) => setCedulaTipo(e.target.value)}
                      style={{ width: '70px', flexShrink: 0 }}
                    >
                      <option value="V">V</option>
                      <option value="J">J</option>
                      <option value="E">E</option>
                    </select>
                    <input
                      type="text"
                      className="form-control"
                      value={cedula}
                      onChange={(e) => setCedula(e.target.value.replace(/\D/g, ''))}
                      placeholder="12345678"
                      inputMode="numeric"
                    />
                  </div>
                </div>

                {/* Per-seat options */}
                {selectedSeats.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h4 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.9rem' }}>
                      <Armchair size={16} /> Opciones por Asiento
                    </h4>
                    {selectedSeats.map((seat) => {
                      const key = getSeatKey(seat);
                      const opts = seatOptions[key] || {};
                      return (
                        <div key={key} className="seat-options-card">
                          <div className="seat-options-header">
                            Asiento #{seat.numero} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>· Piso {seat.piso}</span>
                          </div>

                          <label className="seat-checkbox">
                            <input
                              type="checkbox"
                              checked={opts.es_menor || false}
                              onChange={(e) => updateSeatOption(key, 'es_menor', e.target.checked)}
                            />
                            <Baby size={14} />
                            <span>Es menor de edad</span>
                          </label>

                          {opts.es_menor && (
                            <div className="seat-minor-block">
                              <Baby size={16} />
                              <div>
                                <strong>Pasaje de menor de edad</strong>
                                <p>Los pasajes para menores de edad deben ser adquiridos únicamente en taquilla. No es posible comprar este asiento en línea para un menor.</p>
                              </div>
                            </div>
                          )}

                          {!opts.es_menor && menorToggled[key] && (
                            <div className="seat-minor-warning">
                              <AlertTriangle size={16} />
                              <div>
                                <strong>⚠️ IMPORTANTE</strong>
                                <p>En caso de que el pasaje de este asiento sea para un menor de edad y no haya sido comprado en taquilla, se aplicarán <strong>cargos adicionales</strong> y la reserva podría ser <strong>anulada</strong> al momento del abordaje.</p>
                              </div>
                            </div>
                          )}

                          <label className="seat-checkbox">
                            <input
                              type="checkbox"
                              checked={opts.para_otra || false}
                              onChange={(e) => updateSeatOption(key, 'para_otra', e.target.checked)}
                            />
                            <UserPlus size={14} />
                            <span>Asignar a otra persona</span>
                          </label>

                          {opts.para_otra && (
                            <div className="seat-assign-fields" style={{ animation: 'fadeIn 0.2s ease' }}>
                              <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                                <label style={{ fontSize: '0.75rem' }}>Nombre del asignado</label>
                                <input
                                  type="text"
                                  className="form-control"
                                  value={opts.nombre_asignado}
                                  onChange={(e) => updateSeatOption(key, 'nombre_asignado', e.target.value)}
                                  placeholder="Nombre y apellido"
                                  style={{ fontSize: '0.85rem' }}
                                />
                              </div>
                              <div className="form-group" style={{ marginBottom: '0.25rem' }}>
                                <label style={{ fontSize: '0.75rem' }}>Cédula del asignado</label>
                                <div style={{ display: 'flex', gap: '0.4rem' }}>
                                  <select
                                    className="form-control"
                                    value={opts.cedula_tipo_asignado || 'V'}
                                    onChange={(e) => updateSeatOption(key, 'cedula_tipo_asignado', e.target.value)}
                                    style={{ width: '60px', flexShrink: 0, fontSize: '0.85rem' }}
                                  >
                                    <option value="V">V</option>
                                    <option value="J">J</option>
                                    <option value="E">E</option>
                                  </select>
                                  <input
                                    type="text"
                                    className="form-control"
                                    value={opts.cedula_asignado}
                                    onChange={(e) => updateSeatOption(key, 'cedula_asignado', e.target.value.replace(/\D/g, ''))}
                                    placeholder="12345678"
                                    inputMode="numeric"
                                    style={{ fontSize: '0.85rem' }}
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {hasMinorWarning && !hasMinorSelected && (
                  <div className="seat-minor-warning" style={{ marginTop: '0.75rem' }}>
                    <AlertTriangle size={16} />
                    <div>
                      <strong>⚠️ ADVERTENCIA GENERAL</strong>
                      <p>Si alguno de los pasajes adquiridos es utilizado por un menor de edad sin haber sido comprado en taquilla, se aplicarán <strong>cargos adicionales</strong> y la reserva podría ser <strong>anulada</strong>.</p>
                    </div>
                  </div>
                )}

                <button
                  className="btn btn-success btn-lg"
                  style={{ width: '100%', marginTop: '1rem' }}
                  onClick={handleReservar}
                  disabled={submitting || selectedSeats.length === 0 || hasMinorSelected}
                >
                  {hasMinorSelected ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Baby size={16} />
                      Compra en taquilla requerida
                    </span>
                  ) : submitting ? 'Reservando...' : (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Armchair size={16} />
                      {`Reservar ${selectedSeats.length} asiento${selectedSeats.length > 1 ? 's' : ''}`}
                    </span>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
