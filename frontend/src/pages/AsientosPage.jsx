import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAsientos, crearReserva, subirDocumentosMenor, subirDocVacunacion, subirDocDiscapacidad, getTasaCambio, bloquearAsiento, liberarAsiento } from '../services/api';
import { useAuth } from '../context/AuthContext';
import SeatMap from '../components/SeatMap';
import PriceDisplay from '../components/PriceDisplay';
import AtencionModal from '../components/AtencionModal';
import { ClipboardList, User, Armchair, Baby, UserPlus, AlertTriangle, Clock, PawPrint, Accessibility, ShieldCheck, Upload, FileText, Camera, CreditCard } from 'lucide-react';

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

  // Per-seat files for minors: { seatKey: { partida: File, foto: File, cedula_rep: File } }
  const [seatFiles, setSeatFiles] = useState({});

  // Track seats where user toggled "menor" on then off (fraud detection)
  const [menorToggled, setMenorToggled] = useState({});

  // ── Timer de selección (máximo 10 minutos) ──
  const [selectionStart, setSelectionStart] = useState(null);
  const [remainingTime, setRemainingTime] = useState(null);
  const MAX_SELECTION_MINUTES = 10;

  // AtencionModal state
  const [showAtencion, setShowAtencion] = useState(false);

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
    getAsientos(id)
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
  }, [id, user, cedula]);

  useEffect(() => {
    cargarAsientos();

    // Cargar tasa de cambio por separado (no bloquea carga de asientos)
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => null);

    // Auto-refresh + renovación del bloqueo para asientos seleccionados
    const interval = setInterval(() => {
      cargarAsientos();
      if (user && selectedSeatsRef.current.length > 0) {
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
    }, 5000);

    return () => clearInterval(interval);
  }, [id, user, cargarAsientos]);

  // Countdown timer — libera asientos al expirar
  useEffect(() => {
    if (!selectionStart) return;

    const tick = () => {
      const elapsed = Date.now() - selectionStart;
      const total = MAX_SELECTION_MINUTES * 60 * 1000;
      const remaining = total - elapsed;

      if (remaining <= 0) {
        selectedSeatsRef.current.forEach(s => {
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
    if (!user) return;
    const seats = selectedSeatsRef.current;
    seats.forEach((s) => {
      liberarAsiento(Number(id), s.numero, s.piso).catch(() => null);
    });
  }, [id, user]);

  const getSeatKey = (seat) => `${seat.piso}-${seat.numero}`;

  const handleToggleSeat = async (seat) => {
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
      liberarAsiento(Number(id), seat.numero, seat.piso).catch(() => null);
      return;
    }

    try {
      await bloquearAsiento(Number(id), seat.numero, seat.piso);
    } catch (err) {
      setError(err.response?.data?.error || 'Este asiento ya fue tomado por otro usuario.');
      cargarAsientos();
      return;
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

  // Step 1: Validate and show the Atencion modal
  const handleReservarClick = () => {
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

                          {/* ── Permisos para viajar ── */}
                          <div className="seat-permisos-section">
                            <div className="seat-permisos-header">
                              <ShieldCheck size={14} />
                              <span>Permisos para viajar</span>
                            </div>

                            {/* Menores */}
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
                              <div className="seat-minor-docs">
                                <div className="seat-minor-docs-header">
                                  <Upload size={16} />
                                  <div>
                                    <strong>Documentos requeridos</strong>
                                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Suba los siguientes documentos para continuar con la reserva del menor.</p>
                                  </div>
                                </div>

                                {/* Partida de nacimiento */}
                                <label className="file-upload-field">
                                  <FileText size={16} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Partida de nacimiento</span>
                                    <span className="file-upload-hint">{seatFiles[key]?.partida ? seatFiles[key].partida.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input
                                    type="file"
                                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                      const file = e.target.files[0];
                                      if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], partida: file } }));
                                    }}
                                  />
                                  <span className={`file-upload-btn ${seatFiles[key]?.partida ? 'uploaded' : ''}`}>
                                    {seatFiles[key]?.partida ? '✓' : 'Subir'}
                                  </span>
                                </label>

                                {/* Foto del menor */}
                                <label className="file-upload-field">
                                  <Camera size={16} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Foto del menor (carnet o selfie)</span>
                                    <span className="file-upload-hint">{seatFiles[key]?.foto ? seatFiles[key].foto.name : 'JPG, PNG o WEBP (máx. 5MB)'}</span>
                                  </div>
                                  <input
                                    type="file"
                                    accept=".jpg,.jpeg,.png,.webp"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                      const file = e.target.files[0];
                                      if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], foto: file } }));
                                    }}
                                  />
                                  <span className={`file-upload-btn ${seatFiles[key]?.foto ? 'uploaded' : ''}`}>
                                    {seatFiles[key]?.foto ? '✓' : 'Subir'}
                                  </span>
                                </label>

                                {/* Cédula del representante */}
                                <label className="file-upload-field">
                                  <CreditCard size={16} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Cédula del representante</span>
                                    <span className="file-upload-hint">{seatFiles[key]?.cedula_rep ? seatFiles[key].cedula_rep.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input
                                    type="file"
                                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                      const file = e.target.files[0];
                                      if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], cedula_rep: file } }));
                                    }}
                                  />
                                  <span className={`file-upload-btn ${seatFiles[key]?.cedula_rep ? 'uploaded' : ''}`}>
                                    {seatFiles[key]?.cedula_rep ? '✓' : 'Subir'}
                                  </span>
                                </label>

                                <div className="docs-physical-notice">
                                  <AlertTriangle size={14} />
                                  <span>Debe llevar estos documentos <strong>en físico</strong> al momento del abordaje.</span>
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

                            {/* Mascotas */}
                            <label className="seat-checkbox">
                              <input
                                type="checkbox"
                                checked={opts.viaja_con_animal || false}
                                onChange={(e) => updateSeatOption(key, 'viaja_con_animal', e.target.checked)}
                              />
                              <PawPrint size={14} />
                              <span>Viaja con animal</span>
                            </label>

                            {opts.viaja_con_animal && (
                              <div className="seat-animal-docs">
                                <div className="seat-animal-docs-header">
                                  <PawPrint size={16} />
                                  <div>
                                    <strong>🐾 Datos de la mascota</strong>
                                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Seleccione el tipo de mascota y suba la tarjeta de vacunación.</p>
                                  </div>
                                </div>

                                {/* Selector de tipo de mascota */}
                                <div className="pet-type-selector">
                                  <label className="file-upload-label" style={{ marginBottom: '0.3rem', display: 'block' }}>Tipo de mascota</label>
                                  <select
                                    className="form-control"
                                    value={opts.tipo_mascota || ''}
                                    onChange={(e) => updateSeatOption(key, 'tipo_mascota', e.target.value)}
                                    style={{ fontSize: '0.85rem' }}
                                  >
                                    <option value="">Seleccione...</option>
                                    <option value="perro">🐕 Perro</option>
                                    <option value="gato">🐈 Gato</option>
                                    <option value="ave">🐦 Ave</option>
                                    <option value="conejo">🐰 Conejo</option>
                                    <option value="hamster">🐹 Hámster</option>
                                    <option value="otro">🐾 Otro</option>
                                  </select>
                                </div>

                                {/* Upload de tarjeta de vacunación */}
                                <label className="file-upload-field" style={{ marginTop: '0.5rem' }}>
                                  <FileText size={16} />
                                  <div className="file-upload-info">
                                    <span className="file-upload-label">Tarjeta de vacunación</span>
                                    <span className="file-upload-hint">{seatFiles[key]?.vacunacion ? seatFiles[key].vacunacion.name : 'PDF o imagen (máx. 5MB)'}</span>
                                  </div>
                                  <input
                                    type="file"
                                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                      const file = e.target.files[0];
                                      if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], vacunacion: file } }));
                                    }}
                                  />
                                  <span className={`file-upload-btn ${seatFiles[key]?.vacunacion ? 'uploaded' : ''}`}>
                                    {seatFiles[key]?.vacunacion ? '✓' : 'Subir'}
                                  </span>
                                </label>

                                {!opts.tipo_mascota && (
                                  <p style={{ fontSize: '0.72rem', color: '#dc2626', margin: '0.35rem 0 0' }}>⚠ Debe seleccionar el tipo de mascota</p>
                                )}

                                <div className="docs-physical-notice">
                                  <AlertTriangle size={14} />
                                  <span>Debe llevar la tarjeta de vacunación <strong>en físico</strong> al momento del abordaje.</span>
                                </div>
                                <div className="docs-disclaimer-notice">
                                  <AlertTriangle size={14} />
                                  <span>Si no presenta la tarjeta de vacunación del animal, la unidad <strong>no se hace responsable</strong> por cualquier inconveniente que pueda surgir durante el viaje.</span>
                                </div>
                              </div>
                            )}
                          </div>

                          <label className="seat-checkbox">
                            <input
                              type="checkbox"
                              checked={opts.es_discapacitado || false}
                              onChange={(e) => updateSeatOption(key, 'es_discapacitado', e.target.checked)}
                            />
                            <Accessibility size={14} />
                            <span>Persona con discapacidad</span>
                          </label>

                          {opts.es_discapacitado && (
                            <div className="seat-disability-docs">
                              <div className="seat-disability-docs-header">
                                <Accessibility size={16} />
                                <div>
                                  <strong>Documento de discapacidad</strong>
                                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Suba un certificado médico, RCP o documento que acredite la condición.</p>
                                </div>
                              </div>

                              <label className="file-upload-field">
                                <FileText size={16} />
                                <div className="file-upload-info">
                                  <span className="file-upload-label">Certificado médico / RCP</span>
                                  <span className="file-upload-hint">{seatFiles[key]?.discapacidad ? seatFiles[key].discapacidad.name : 'PDF o imagen (máx. 5MB)'}</span>
                                </div>
                                <input
                                  type="file"
                                  accept=".jpg,.jpeg,.png,.webp,.pdf"
                                  style={{ display: 'none' }}
                                  onChange={(e) => {
                                    const file = e.target.files[0];
                                    if (file) setSeatFiles(prev => ({ ...prev, [key]: { ...prev[key], discapacidad: file } }));
                                  }}
                                />
                                <span className={`file-upload-btn ${seatFiles[key]?.discapacidad ? 'uploaded' : ''}`}>
                                  {seatFiles[key]?.discapacidad ? '✓' : 'Subir'}
                                </span>
                              </label>

                              <div className="docs-physical-notice">
                                <AlertTriangle size={14} />
                                <span>Debe llevar este documento <strong>en físico</strong> al momento del abordaje.</span>
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
                  onClick={handleReservarClick}
                  disabled={submitting || selectedSeats.length === 0 || (hasMinorSelected && !minorDocsComplete)}
                >
                  {submitting ? 'Reservando...' : (hasMinorSelected && !minorDocsComplete) ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Upload size={16} />
                      Suba los documentos del menor
                    </span>
                  ) : (
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
