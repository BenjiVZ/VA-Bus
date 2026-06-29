import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAsientos, getAsientosLocal, crearReserva, subirDocumentosMenor, subirDocVacunacion, subirDocDiscapacidad, getTasaCambio, bloquearAsiento, liberarAsiento } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useAsientosWebSocket } from '../hooks/useAsientosWebSocket';
import SeatMap from '../components/SeatMap';
import PriceDisplay from '../components/PriceDisplay';
import AtencionModal from '../components/AtencionModal';
import { ClipboardList, User, Armchair, Baby, UserPlus, AlertTriangle, Clock, PawPrint, Accessibility, ShieldCheck, FileText, Camera, CreditCard, ChevronDown, ChevronRight, CheckCircle } from 'lucide-react';

export default function AsientosPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  // Viaje de Aerorutas: id compuesto (ej "001_02_11_2026-06-03"). No soporta
  // bloqueo/WS en el servidor: la selección es solo local.
  const esAerorutas = String(id).includes('_');

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

  // Per-seat files for minors: { seatKey: { partida: File, foto: File, cedula_rep: File } }
  const [seatFiles, setSeatFiles] = useState({});

  // Track which doc sections are expanded per seat: { seatKey: { minor: bool, animal: bool, disability: bool } }
  const [expandedDocs, setExpandedDocs] = useState({});

  // Track seats where user toggled "menor" on then off (fraud detection)
  const [menorToggled, setMenorToggled] = useState({});

  // ── Timer de selección (máximo 10 minutos) ──
  const [selectionStart, setSelectionStart] = useState(null);
  const [remainingTime, setRemainingTime] = useState(null);
  const MAX_SELECTION_MINUTES = 10;

  // AtencionModal state
  const [showAtencion, setShowAtencion] = useState(false);

  // Warnings overlay state (floating doc islands)
  const [showWarnings, setShowWarnings] = useState(false);

  const selectedSeatsRef = useRef([]);

  useEffect(() => {
    selectedSeatsRef.current = selectedSeats;
  }, [selectedSeats]);

  // Iniciar/detener timer cuando se selecciona/deselecciona el primer asiento
  useEffect(() => {
    if (selectedSeats.length > 0 && !selectionStart) {
      setSelectionStart(Date.now());
    } else if (selectedSeats.length === 0) {
      setSelectionStart(null);
      setRemainingTime(null);
    }
  }, [selectedSeats.length, selectionStart]);

  const cargarAsientos = useCallback(() => {
    // Aerorutas: id compuesto → endpoint de Aerorutas. Local (id entero, incluye
    // los de prueba) → endpoint local, que sí soporta reservar/bloquear/pagar.
    (esAerorutas ? getAsientos(id) : getAsientosLocal(id))
      .then((asientosRes) => {
        const newData = asientosRes.data;
        setData(newData);

        // Auto-deseleccionar asientos que otro usuario ya tomó
        if (newData?.pisos_config) {
          const ocupados = new Set();
          const bloqueadosMios = [];
          newData.pisos_config.forEach((piso) => {
            (piso.layout || []).forEach((row) => {
              row.forEach((cell) => {
                if (cell.type === 'seat' && cell.number && !cell.disponible) {
                  ocupados.add(`${piso.numero_piso}-${cell.number}`);
                }
                if (cell.type === 'seat' && cell.number && cell.bloqueado_por_mi) {
                  bloqueadosMios.push({
                    numero: cell.number,
                    piso: piso.numero_piso,
                  });
                }
              });
            });
          });
          setSelectedSeats((prev) => {
            const filtrados = prev.filter((s) => !ocupados.has(`${s.piso}-${s.numero}`));
            const existentes = new Set(filtrados.map((s) => `${s.piso}-${s.numero}`));

            // Rehidrata selección tras refresh usando bloqueos activos del usuario.
            bloqueadosMios.forEach((seat) => {
              const seatKey = `${seat.piso}-${seat.numero}`;
              if (!existentes.has(seatKey)) {
                filtrados.push(seat);
                existentes.add(seatKey);
              }
            });

            if (filtrados.length < prev.length) {
              setSeatOptions((opts) => {
                const copy = { ...opts };
                prev.forEach((s) => {
                  const key = `${s.piso}-${s.numero}`;
                  if (ocupados.has(key)) delete copy[key];
                });
                return copy;
              });
            }
            return filtrados;
          });
        }

        // Pre-fill passenger info from user profile (only first load)
        if (user) {
          const nombreCompleto = `${user.first_name || ''} ${user.last_name || ''}`.trim();
          if (nombreCompleto) {
            setNombre((prev) => prev || nombreCompleto);
          }
          const rawCedula = user.cedula || '';
          const match = rawCedula.match(/^([VJE])-?(.*)$/i);
          if (match && !cedula) {
            setCedulaTipo(match[1].toUpperCase());
            setCedula(match[2]);
          } else if (!cedula) {
            setCedula((prev) => prev || rawCedula);
          }
        }
      })
      .catch(() => setError('Error al cargar los asientos.'))
      .finally(() => setLoading(false));
  }, [id, user, cedula, esAerorutas]);

  useEffect(() => {
    cargarAsientos();

    // Cargar tasa de cambio por separado (no bloquea carga de asientos)
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => null);

    // Fallback de polling cada 30s (el WebSocket cubre el tiempo real).
    // Renovamos los bloqueos que tenemos seleccionados — el backend los
    // mantiene 2min, así que 30s sigue siendo cómodo y mucho más liviano.
    const interval = setInterval(() => {
      cargarAsientos();
      if (!esAerorutas && user && selectedSeatsRef.current.length > 0) {
        selectedSeatsRef.current.forEach((s) => {
          bloquearAsiento(Number(id), s.numero, s.piso).catch((err) => {
            if (err.response?.data?.sesion_expirada) {
              setSelectedSeats([]);
              setSeatOptions({});
              setSelectionStart(null);
              setRemainingTime(null);
              setMenorToggled({});
              setError('⏰ Tu tiempo de selección ha expirado (10 minutos). Los asientos fueron liberados.');
              cargarAsientos();
            }
          });
        });
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [id, user, cargarAsientos]);

  // ── WebSocket: actualizar el mapa en tiempo real cuando otros usuarios
  // bloquean/liberan/reservan asientos. Si el cambio fue mío (mismo user.id),
  // lo ignoramos porque el estado local ya está al día.
  useAsientosWebSocket({
    viajeId: Number(id),
    enabled: !!id && !esAerorutas,
    onSeatChanged: useCallback((evt) => {
      if (evt.usuario_id && user && evt.usuario_id === user.id) return;
      // Refrescar el mapa — la fuente de verdad sigue siendo el GET.
      cargarAsientos();
    }, [user, cargarAsientos]),
  });

  // Countdown timer — libera asientos al expirar
  useEffect(() => {
    if (!selectionStart) return;

    const tick = () => {
      const elapsed = Date.now() - selectionStart;
      const total = MAX_SELECTION_MINUTES * 60 * 1000;
      const remaining = total - elapsed;

      if (remaining <= 0) {
        if (!esAerorutas) selectedSeatsRef.current.forEach(s => {
          liberarAsiento(Number(id), s.numero, s.piso).catch(() => null);
        });
        setSelectedSeats([]);
        setSeatOptions({});
        setSelectionStart(null);
        setRemainingTime(null);
        setMenorToggled({});
        setError('⏰ Tu tiempo de selección ha expirado (10 minutos). Los asientos fueron liberados. Puedes seleccionar nuevamente.');
        cargarAsientos();
        return;
      }

      setRemainingTime(remaining);
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [selectionStart, id, cargarAsientos]);

  useEffect(() => () => {
    if (!user || esAerorutas) return;
    const seats = selectedSeatsRef.current;
    seats.forEach((s) => {
      liberarAsiento(Number(id), s.numero, s.piso).catch(() => null);
    });
  }, [id, user, esAerorutas]);

  const getSeatKey = (seat) => `${seat.piso}-${seat.numero}`;

  // Viaje expirado: ya pasó su fecha + hora de salida.
  const expirado = (() => {
    const v = data?.viaje;
    if (!v?.fecha_salida) return false;
    const salida = new Date(`${v.fecha_salida}T${v.hora_salida || '00:00:00'}`);
    return salida.getTime() < Date.now();
  })();

  const handleToggleSeat = async (seat) => {
    if (expirado) {
      setError('⏰ Este viaje ya salió. No se pueden seleccionar puestos.');
      return;
    }
    if (!user) {
      navigate('/login');
      return;
    }

    const key = getSeatKey(seat);
    const exists = selectedSeats.some((s) => s.numero === seat.numero && s.piso === seat.piso);

    if (exists) {
      setSelectedSeats((prev) => prev.filter((s) => !(s.numero === seat.numero && s.piso === seat.piso)));
      setSeatOptions((opts) => {
        const copy = { ...opts };
        delete copy[key];
        return copy;
      });
      if (!esAerorutas) liberarAsiento(Number(id), seat.numero, seat.piso).catch(() => null);
      return;
    }

    // Aerorutas: selección solo local (sin bloqueo en servidor).
    if (!esAerorutas) {
      try {
        await bloquearAsiento(Number(id), seat.numero, seat.piso);
      } catch (err) {
        setError(err.response?.data?.error || 'Este asiento ya fue tomado por otro usuario.');
        cargarAsientos();
        return;
      }
    }

    setError('');
    setSeatOptions((opts) => ({
      ...opts,
      [key]: { es_menor: false, para_otra: false, viaja_con_animal: false, es_discapacitado: false, nombre_asignado: '', cedula_asignado: '', cedula_tipo_asignado: 'V' },
    }));
    setSelectedSeats((prev) => [...prev, seat]);
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

  // Check if all minor seats have their 3 required documents uploaded
  const minorDocsComplete = selectedSeats.every((s) => {
    const key = getSeatKey(s);
    const opts = seatOptions[key] || {};
    if (!opts.es_menor) return true;
    const files = seatFiles[key] || {};
    return files.partida && files.foto && files.cedula_rep;
  });

  // Check if any seat had minor toggled on then off
  const hasMinorWarning = selectedSeats.some((s) => menorToggled[getSeatKey(s)]);

  // Check if any seat has animal without vaccination or missing tipo_mascota
  const hasAnimalPending = selectedSeats.some((s) => {
    const key = getSeatKey(s);
    const opts = seatOptions[key] || {};
    if (!opts.viaja_con_animal) return false;
    const files = seatFiles[key] || {};
    return !files.vacunacion || !opts.tipo_mascota;
  });

  // Check if any seat has disability without document
  const hasDisabilityPending = selectedSeats.some((s) => {
    const key = getSeatKey(s);
    const opts = seatOptions[key] || {};
    if (!opts.es_discapacitado) return false;
    const files = seatFiles[key] || {};
    return !files.discapacidad;
  });

  // Check if there are any pending warnings/docs to show
  const hasPendingWarnings = (hasMinorSelected && !minorDocsComplete) || hasAnimalPending || hasDisabilityPending || hasMinorWarning;

  // ── Helpers del timer ──
  const formatTime = (ms) => {
    if (!ms || ms <= 0) return '0:00';
    const totalSec = Math.ceil(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const timerPercent = remainingTime !== null
    ? (remainingTime / (MAX_SELECTION_MINUTES * 60 * 1000)) * 100
    : 100;

  const timerClass = remainingTime !== null
    ? remainingTime < 60000 ? 'timer-danger' : remainingTime < 120000 ? 'timer-warning' : ''
    : '';

  const totalUsd = data ? selectedSeats.length * Number(data.viaje.precio_usd) : 0;
  const totalBs = tasa ? totalUsd * tasa : null;

  // Step 1: Validate and show warnings overlay or Atencion modal
  const handleReservarClick = () => {
    // Viajes de Aerorutas (id compuesto, ej "001_02_04_2026-06-03"): la reserva/pago
    // está en integración. Evita romper el flujo hasta definir reserva/pago.
    if (String(id).includes('_')) {
      setError('🚧 La reserva de viajes de Aerorutas estará disponible muy pronto. Por ahora solo puedes ver la disponibilidad.');
      return;
    }

    if (!user) {
      navigate('/login');
      return;
    }

    if (!user.cedula) {
      setError('⚠️ Debes registrar tu cédula antes de reservar. Ve a tu perfil para completarla.');
      setTimeout(() => navigate('/perfil'), 2500);
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

    setError('');

    // If there are any pending doc islands/warnings, show the warnings overlay
    if (hasPendingWarnings) {
      setShowWarnings(true);
      return;
    }

    // No warnings pending, go straight to Atencion modal
    setShowAtencion(true);
  };

  // Step 2: User accepted terms, execute the actual reservation
  const handleReservar = async () => {
    setShowAtencion(false);

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
            viaja_con_animal: opts.viaja_con_animal || false,
            tipo_mascota: opts.tipo_mascota || '',
            es_discapacitado: opts.es_discapacitado || false,
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

      // Upload documents for each seat (minor docs + animal vaccination)
      const reservasCreadas = res.data.reservas || [];
      const uploadPromises = [];

      for (const reserva of reservasCreadas) {
        const matchKey = `${reserva.piso_asiento}-${reserva.numero_asiento}`;
        const files = seatFiles[matchKey];
        if (!files) continue;

        // Minor documents
        if (reserva.es_menor_edad && files.partida) {
          const formData = new FormData();
          if (files.partida) formData.append('doc_partida_nacimiento', files.partida);
          if (files.foto) formData.append('doc_foto_menor', files.foto);
          if (files.cedula_rep) formData.append('doc_cedula_representante', files.cedula_rep);

          uploadPromises.push(
            subirDocumentosMenor(reserva.id, formData).catch((uploadErr) => {
              console.error(`Error subiendo docs menor para reserva ${reserva.id}:`, uploadErr);
            })
          );
        }

        // Animal vaccination document
        if (reserva.viaja_con_animal && files.vacunacion) {
          const formData = new FormData();
          formData.append('doc_vacunacion_animal', files.vacunacion);

          uploadPromises.push(
            subirDocVacunacion(reserva.id, formData).catch((uploadErr) => {
              console.error(`Error subiendo vacunación para reserva ${reserva.id}:`, uploadErr);
            })
          );
        }

        // Disability document
        if (reserva.es_discapacitado && files.discapacidad) {
          const formData = new FormData();
          formData.append('doc_discapacidad', files.discapacidad);

          uploadPromises.push(
            subirDocDiscapacidad(reserva.id, formData).catch((uploadErr) => {
              console.error(`Error subiendo doc discapacidad para reserva ${reserva.id}:`, uploadErr);
            })
          );
        }
      }

      // Wait for all uploads before navigating
      if (uploadPromises.length > 0) {
        await Promise.all(uploadPromises);
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
      <div className="asientos-page-container">
        <div className="asientos-page-header">
          <h2>Selecciona tus Asientos</h2>
          <p>
            {viaje.ruta.origen} → {viaje.ruta.destino} · {new Date(viaje.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', { weekday: 'long', day: 'numeric', month: 'long' })} · {viaje.hora_salida?.slice(0, 5)}
          </p>
        </div>

        {expirado && (
          <div className="alert alert-error" style={{ fontWeight: 700 }}>
            ⏰ Este viaje ya salió ({viaje.hora_salida?.slice(0, 5)}). Expiró — no se pueden seleccionar puestos.
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}

        {/* ── Top Row: Seat Map + Summary Sidebar ── */}
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
            {remainingTime !== null && (
              <div className={`selection-timer ${timerClass}`}>
                <div className="selection-timer-content">
                  <Clock size={16} />
                  <span>
                    {remainingTime < 60000 ? '¡Apresúrate! ' : 'Tiempo restante: '}
                    <strong>{formatTime(remainingTime)}</strong>
                  </span>
                </div>
                <div className="timer-bar">
                  <div className="timer-bar-fill" style={{ width: `${timerPercent}%` }} />
                </div>
              </div>
            )}
            <div className="floating-card">
              <h4 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <ClipboardList size={16} /> Resumen
              </h4>
              <div className="confirmation-details">
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
          </div>
        </div>

        {/* ── Bottom Row: Buyer Data + Seat Options (floating cards) ── */}
        {selectedSeats.length > 0 && (
          <div className="buyer-options-section">
            <div className="buyer-options-grid">
              {/* Left card: Buyer info */}
              <div className="floating-card buyer-card">
                <h4>
                  <User size={16} /> Datos del Comprador
                </h4>
                <div className="buyer-fields-grid">
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
                </div>

                {/* ── Datos del asignado (por asiento con "para_otra") ── */}
                {selectedSeats.filter(s => seatOptions[getSeatKey(s)]?.para_otra).map((seat) => {
                  const key = getSeatKey(seat);
                  const opts = seatOptions[key] || {};
                  return (
                    <div key={key} className="assignee-section" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px dashed var(--border-color, #e2e4e9)' }}>
                      <h4 style={{ fontSize: '0.85rem', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <UserPlus size={15} /> Persona Asignada — Asiento #{seat.numero}
                      </h4>
                      <div className="buyer-fields-grid">
                        <div className="form-group">
                          <label>Nombre del asignado</label>
                          <input
                            type="text"
                            className="form-control"
                            value={opts.nombre_asignado}
                            onChange={(e) => updateSeatOption(key, 'nombre_asignado', e.target.value)}
                            placeholder="Nombre y apellido"
                          />
                        </div>
                        <div className="form-group">
                          <label>Cédula del asignado</label>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <select
                              className="form-control"
                              value={opts.cedula_tipo_asignado || 'V'}
                              onChange={(e) => updateSeatOption(key, 'cedula_tipo_asignado', e.target.value)}
                              style={{ width: '70px', flexShrink: 0 }}
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
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Right card: Seat options */}
              <div className="floating-card seat-options-area">
                <h4>
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

                      {/* ── Permisos para viajar ── */}
                      <div className="seat-permisos-section">
                        <div className="seat-permisos-header">
                          <ShieldCheck size={14} />
                          <span>Permisos para viajar</span>
                        </div>

                        <div className="seat-permisos-checkboxes">
                          <label className="seat-checkbox">
                            <input type="checkbox" checked={opts.es_menor || false} onChange={(e) => updateSeatOption(key, 'es_menor', e.target.checked)} />
                            <Baby size={14} /><span>Es menor de edad</span>
                          </label>
                          <label className="seat-checkbox">
                            <input type="checkbox" checked={opts.viaja_con_animal || false} onChange={(e) => updateSeatOption(key, 'viaja_con_animal', e.target.checked)} />
                            <PawPrint size={14} /><span>Viaja con animal</span>
                          </label>
                          <label className="seat-checkbox">
                            <input type="checkbox" checked={opts.para_otra || false} onChange={(e) => updateSeatOption(key, 'para_otra', e.target.checked)} />
                            <UserPlus size={14} /><span>Asignar a otra persona</span>
                          </label>
                          <label className="seat-checkbox">
                            <input type="checkbox" checked={opts.es_discapacitado || false} onChange={(e) => updateSeatOption(key, 'es_discapacitado', e.target.checked)} />
                            <Accessibility size={14} /><span>Persona con discapacidad</span>
                          </label>
                        </div>

                        {/* ── Compact status badges (docs handled in floating overlay) ── */}
                        {opts.es_menor && (() => {
                          const files = seatFiles[key] || {};
                          const uploaded = [files.partida, files.foto, files.cedula_rep].filter(Boolean).length;
                          return (
                            <div className="doc-status-badge minor">
                              <Baby size={13} />
                              <span>Menor de edad — Docs: {uploaded}/3</span>
                              {uploaded === 3 && <CheckCircle size={13} className="doc-island-check" />}
                            </div>
                          );
                        })()}
                        {!opts.es_menor && menorToggled[key] && (
                          <div className="doc-status-badge warning">
                            <AlertTriangle size={13} />
                            <span>Verificar si es menor</span>
                          </div>
                        )}
                        {opts.viaja_con_animal && (() => {
                          const files = seatFiles[key] || {};
                          const done = !!(files.vacunacion && opts.tipo_mascota);
                          return (
                            <div className="doc-status-badge animal">
                              <PawPrint size={13} />
                              <span>Mascota — {done ? 'Completo' : 'Pendiente'}</span>
                              {done && <CheckCircle size={13} className="doc-island-check" />}
                            </div>
                          );
                        })()}
                        {opts.es_discapacitado && (() => {
                          const files = seatFiles[key] || {};
                          return (
                            <div className="doc-status-badge disability">
                              <Accessibility size={13} />
                              <span>Discapacidad — {files.discapacidad ? 'Completo' : 'Pendiente'}</span>
                              {files.discapacidad && <CheckCircle size={13} className="doc-island-check" />}
                            </div>
                          );
                        })()}

                        {opts.para_otra && (
                          <div className="seat-assign-fields" style={{ animation: 'fadeIn 0.2s ease', padding: '0.5rem 0.75rem', background: 'var(--bg-light, #f0f4ff)', borderRadius: '0.5rem', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                              <UserPlus size={13} /> Los datos del asignado se encuentran debajo de <strong>Datos del Comprador</strong>
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="reserve-action-bar" style={{ gridColumn: '1 / -1' }}>
              <button
                className="btn btn-success btn-lg"
                style={{ width: '100%' }}
                onClick={handleReservarClick}
                disabled={submitting || selectedSeats.length === 0}
              >
                {submitting ? 'Reservando...' : (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Armchair size={16} />
                    {`Reservar ${selectedSeats.length} asiento${selectedSeats.length > 1 ? 's' : ''}`}
                  </span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ── Floating Warnings Overlay (doc islands) ── */}
        {showWarnings && (
          <div className="warnings-overlay" onClick={() => setShowWarnings(false)}>
            <div className="warnings-modal" onClick={(e) => e.stopPropagation()}>
              <div className="warnings-modal-header">
                <AlertTriangle size={20} />
                <h3>Documentos y Advertencias</h3>
                <button className="warnings-close" onClick={() => setShowWarnings(false)}>✕</button>
              </div>
              <div className="warnings-modal-body">
                {selectedSeats.map((seat) => {
                  const key = getSeatKey(seat);
                  const opts = seatOptions[key] || {};
                  const hasAny = opts.es_menor || opts.viaja_con_animal || opts.es_discapacitado || (!opts.es_menor && menorToggled[key]);
                  if (!hasAny) return null;
                  return (
                    <div key={key} className="warnings-seat-section">
                      <h4>Asiento #{seat.numero} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>· Piso {seat.piso}</span></h4>

                      {opts.es_menor && (
                        <div className="seat-minor-warning" style={{ marginBottom: '0.5rem' }}>
                          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                          <div>
                            <strong>⚠️ IMPORTANTE</strong>
                            <p style={{ fontSize: '0.75rem', lineHeight: '1.4', marginTop: '0.2rem' }}>
                              El Usuario que vaya a utilizar el servicio acompañado de niños o adolescentes, debe presentar al momento de comprar el boleto de viaje; la autorización del padre, madre o representante legal, debidamente expedido por la autoridad administrativa competente.
                            </p>
                          </div>
                        </div>
                      )}
                      {opts.es_menor && (() => {
                        const files = seatFiles[key] || {};
                        const uploaded = [files.partida, files.foto, files.cedula_rep].filter(Boolean).length;
                        const total = 3;
                        const isOpen = expandedDocs[key]?.minor !== false;
                        return (
                          <div className={`doc-island ${uploaded === total ? 'complete' : ''}`}>
                            <div className="doc-island-header" onClick={() => setExpandedDocs(prev => ({ ...prev, [key]: { ...prev[key], minor: !isOpen } }))}>
                              <div className="doc-island-left">
                                <Baby size={15} />
                                <div>
                                  <strong>Documentos del menor</strong>
                                  <span className="doc-island-counter">{uploaded}/{total} archivos</span>
                                </div>
                              </div>
                              <div className="doc-island-right">
                                {uploaded === total && <CheckCircle size={14} className="doc-island-check" />}
                                {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </div>
                            </div>
                            {isOpen && (
                              <div className="doc-island-body">
                                <label className="file-upload-field">
                                  <FileText size={15} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Partida de nacimiento</span>
                                    <span className="file-upload-hint">{files.partida ? files.partida.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], partida: file } })); }} />
                                  <span className={`file-upload-btn ${files.partida ? 'uploaded' : ''}`}>{files.partida ? '✓' : 'Subir'}</span>
                                </label>
                                <label className="file-upload-field">
                                  <Camera size={15} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Foto del menor</span>
                                    <span className="file-upload-hint">{files.foto ? files.foto.name : 'JPG, PNG o WEBP (máx. 5MB)'}</span>
                                  </div>
                                  <input type="file" accept=".jpg,.jpeg,.png,.webp" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], foto: file } })); }} />
                                  <span className={`file-upload-btn ${files.foto ? 'uploaded' : ''}`}>{files.foto ? '✓' : 'Subir'}</span>
                                </label>
                                <label className="file-upload-field">
                                  <CreditCard size={15} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Cédula del representante</span>
                                    <span className="file-upload-hint">{files.cedula_rep ? files.cedula_rep.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], cedula_rep: file } })); }} />
                                  <span className={`file-upload-btn ${files.cedula_rep ? 'uploaded' : ''}`}>{files.cedula_rep ? '✓' : 'Subir'}</span>
                                </label>
                                <div className="docs-physical-notice">
                                  <AlertTriangle size={13} />
                                  <span>Llevar documentos <strong>en físico</strong> al abordar.</span>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {!opts.es_menor && menorToggled[key] && (
                        <div className="seat-minor-warning">
                          <AlertTriangle size={16} />
                          <div>
                            <strong>⚠️ IMPORTANTE</strong>
                            <p>Si el pasaje es para un menor y no fue comprado en taquilla, se aplicarán <strong>cargos adicionales</strong> y la reserva podría ser <strong>anulada</strong>.</p>
                          </div>
                        </div>
                      )}

                      {opts.viaja_con_animal && (() => {
                        const files = seatFiles[key] || {};
                        const uploaded = [files.vacunacion].filter(Boolean).length + (opts.tipo_mascota ? 1 : 0);
                        const total = 2;
                        const isOpen = expandedDocs[key]?.animal !== false;
                        return (
                          <div className={`doc-island animal ${uploaded === total ? 'complete' : ''}`}>
                            <div className="doc-island-header" onClick={() => setExpandedDocs(prev => ({ ...prev, [key]: { ...prev[key], animal: !isOpen } }))}>
                              <div className="doc-island-left">
                                <PawPrint size={15} />
                                <div>
                                  <strong>Datos de la mascota</strong>
                                  <span className="doc-island-counter">{uploaded}/{total} completados</span>
                                </div>
                              </div>
                              <div className="doc-island-right">
                                {uploaded === total && <CheckCircle size={14} className="doc-island-check" />}
                                {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </div>
                            </div>
                            {isOpen && (
                              <div className="doc-island-body">
                                <div className="pet-type-selector">
                                  <label style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.25rem', display: 'block' }}>Tipo de mascota</label>
                                  <select className="form-control" value={opts.tipo_mascota || ''} onChange={(e) => updateSeatOption(key, 'tipo_mascota', e.target.value)} style={{ fontSize: '0.85rem' }}>
                                    <option value="">Seleccione...</option>
                                    <option value="perro">🐕 Perro</option>
                                    <option value="gato">🐈 Gato</option>
                                    <option value="ave">🐦 Ave</option>
                                    <option value="conejo">🐰 Conejo</option>
                                    <option value="hamster">🐹 Hámster</option>
                                    <option value="otro">🐾 Otro</option>
                                  </select>
                                </div>
                                <label className="file-upload-field" style={{ marginTop: '0.4rem' }}>
                                  <FileText size={15} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Tarjeta de vacunación</span>
                                    <span className="file-upload-hint">{files.vacunacion ? files.vacunacion.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], vacunacion: file } })); }} />
                                  <span className={`file-upload-btn ${files.vacunacion ? 'uploaded' : ''}`}>{files.vacunacion ? '✓' : 'Subir'}</span>
                                </label>
                                {!opts.tipo_mascota && (
                                  <p style={{ fontSize: '0.72rem', color: '#dc2626', margin: '0.3rem 0 0' }}>⚠ Seleccione el tipo de mascota</p>
                                )}
                                <div className="docs-physical-notice">
                                  <AlertTriangle size={13} />
                                  <span>Llevar tarjeta de vacunación <strong>en físico</strong> al abordar.</span>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {opts.es_discapacitado && (() => {
                        const files = seatFiles[key] || {};
                        const uploaded = files.discapacidad ? 1 : 0;
                        const total = 1;
                        const isOpen = expandedDocs[key]?.disability !== false;
                        return (
                          <div className={`doc-island disability ${uploaded === total ? 'complete' : ''}`}>
                            <div className="doc-island-header" onClick={() => setExpandedDocs(prev => ({ ...prev, [key]: { ...prev[key], disability: !isOpen } }))}>
                              <div className="doc-island-left">
                                <Accessibility size={15} />
                                <div>
                                  <strong>Documento de discapacidad</strong>
                                  <span className="doc-island-counter">{uploaded}/{total} archivo</span>
                                </div>
                              </div>
                              <div className="doc-island-right">
                                {uploaded === total && <CheckCircle size={14} className="doc-island-check" />}
                                {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </div>
                            </div>
                            {isOpen && (
                              <div className="doc-island-body">
                                <label className="file-upload-field">
                                  <FileText size={15} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Certificado médico / RCP</span>
                                    <span className="file-upload-hint">{files.discapacidad ? files.discapacidad.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], discapacidad: file } })); }} />
                                  <span className={`file-upload-btn ${files.discapacidad ? 'uploaded' : ''}`}>{files.discapacidad ? '✓' : 'Subir'}</span>
                                </label>
                                <div className="docs-physical-notice">
                                  <AlertTriangle size={13} />
                                  <span>Llevar documento <strong>en físico</strong> al abordar.</span>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  );
                })}
              </div>
              <div className="warnings-modal-footer">
                <button className="btn btn-outline" onClick={() => setShowWarnings(false)}>Cerrar y completar</button>
                <button
                  className="btn btn-success"
                  disabled={hasPendingWarnings && (hasMinorSelected && !minorDocsComplete)}
                  onClick={() => { setShowWarnings(false); setShowAtencion(true); }}
                >
                  Continuar con la reserva
                </button>
              </div>
            </div>
          </div>
        )}

        <AtencionModal
          visible={showAtencion}
          onClose={() => setShowAtencion(false)}
          onAccept={handleReservar}
          viajeInfo={data?.viaje ? {
            origen: data.viaje.ruta.origen,
            destino: data.viaje.ruta.destino,
            fecha: data.viaje.fecha_salida,
            cantidad: selectedSeats.length,
          } : null}
        />
      </div>
    </div>
  );
}
