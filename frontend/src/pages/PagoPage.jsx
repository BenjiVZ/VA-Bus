import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ChevronRight, ChevronLeft, AlertTriangle, Clock, Copy, CheckCircle,
  Upload, CreditCard, Shield, Image as ImageIcon,
} from 'lucide-react';
import { getMetodosPago, crearComprobante, getEstadoComprobante, getTasaCambio } from '../services/api';

const STORAGE_KEY = 'aerorutas_pago_progreso';

function saveProgress(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}
function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
function clearProgress() {
  localStorage.removeItem(STORAGE_KEY);
}

export default function PagoPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // Try to load from navigation state or localStorage
  const navState = location.state;
  const savedProgress = loadProgress();

  const [paso, setPaso] = useState(1);
  const [grupoPago, setGrupoPago] = useState(null);
  const [reservas, setReservas] = useState([]);
  const [viajeInfo, setViajeInfo] = useState(null);
  const [fechaExpiracion, setFechaExpiracion] = useState(null);
  const [metodos, setMetodos] = useState([]);
  const [metodoSeleccionado, setMetodoSeleccionado] = useState(null);
  const [tasa, setTasa] = useState(null);
  const [timeLeft, setTimeLeft] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  // Upload form
  const [numeroRef, setNumeroRef] = useState('');
  const [imagen, setImagen] = useState(null);
  const [imagenPreview, setImagenPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [comprobanteEnviado, setComprobanteEnviado] = useState(false);

  // Initialize data
  useEffect(() => {
    if (navState?.grupo_pago) {
      setGrupoPago(navState.grupo_pago);
      setReservas(navState.reservas || []);
      setViajeInfo(navState.viaje_info || null);
      setFechaExpiracion(navState.fecha_expiracion || null);
      setPaso(1);
      saveProgress({
        grupo_pago: navState.grupo_pago,
        reservas: navState.reservas,
        viaje_info: navState.viaje_info,
        fecha_expiracion: navState.fecha_expiracion,
        paso_actual: 1,
        metodo_seleccionado: null,
      });
    } else if (savedProgress?.grupo_pago) {
      setGrupoPago(savedProgress.grupo_pago);
      setReservas(savedProgress.reservas || []);
      setViajeInfo(savedProgress.viaje_info || null);
      setFechaExpiracion(savedProgress.fecha_expiracion || null);
      setPaso(savedProgress.paso_actual || 1);
      if (savedProgress.metodo_seleccionado) {
        setMetodoSeleccionado(savedProgress.metodo_seleccionado);
      }
    } else {
      navigate('/');
      return;
    }

    // Fetch payment methods and exchange rate
    getMetodosPago().then(res => setMetodos(res.data)).catch(() => {});
    getTasaCambio().then(res => setTasa(res.data.tasa_bcv)).catch(() => {});
  }, []);

  // Check if comprobante already exists
  useEffect(() => {
    if (grupoPago) {
      getEstadoComprobante(grupoPago).then(res => {
        if (res.data.existe) {
          setComprobanteEnviado(true);
          setPaso(5); // Done state
        }
      }).catch(() => {});
    }
  }, [grupoPago]);

  // Timer countdown
  useEffect(() => {
    if (!fechaExpiracion || comprobanteEnviado) return;
    const target = new Date(fechaExpiracion).getTime();

    const interval = setInterval(() => {
      const now = Date.now();
      const diff = Math.max(0, Math.floor((target - now) / 1000));
      setTimeLeft(diff);
      if (diff <= 0) {
        clearInterval(interval);
        clearProgress();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fechaExpiracion, comprobanteEnviado]);

  // Save progress on step changes
  useEffect(() => {
    if (grupoPago) {
      saveProgress({
        grupo_pago: grupoPago,
        reservas,
        viaje_info: viajeInfo,
        fecha_expiracion: fechaExpiracion,
        paso_actual: paso,
        metodo_seleccionado: metodoSeleccionado,
      });
    }
  }, [paso, metodoSeleccionado]);

  const formatTime = (secs) => {
    if (secs === null) return '--:--';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const totalUsd = viajeInfo ? reservas.length * Number(viajeInfo.precio_usd) : 0;
  const totalBs = tasa ? totalUsd * Number(tasa) : null;

  const getMonto = (metodo) => {
    if (!metodo) return { valor: totalUsd, texto: `$${totalUsd.toFixed(2)}` };
    if (metodo.moneda === 'USD') return { valor: totalUsd, texto: `$${totalUsd.toFixed(2)}` };
    if (totalBs) return { valor: totalBs, texto: `Bs. ${totalBs.toLocaleString('es-VE', { minimumFractionDigits: 2 })}` };
    return { valor: totalUsd, texto: `$${totalUsd.toFixed(2)}` };
  };

  const handleCopy = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch { /* fallback */ }
  };

  const handleCopyAll = () => {
    if (!metodoSeleccionado) return;
    const allText = metodoSeleccionado.datos.map(d => `${d.etiqueta}: ${d.valor}`).join('\n') + 
      `\nMonto: ${getMonto(metodoSeleccionado).texto}`;
    handleCopy(allText, 'all');
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImagen(file);
      setImagenPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmitComprobante = async () => {
    if (!imagen) {
      setError('Debes subir la captura del pago.');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('grupo_pago', grupoPago);
      formData.append('metodo_pago_id', metodoSeleccionado.id);
      formData.append('imagen', imagen);
      formData.append('monto', Number(getMonto(metodoSeleccionado).valor).toFixed(2));
      formData.append('moneda', metodoSeleccionado.moneda);
      if (numeroRef) formData.append('numero_referencia', numeroRef);

      await crearComprobante(formData);
      setComprobanteEnviado(true);
      setPaso(5);
      clearProgress();
    } catch (err) {
      const data = err.response?.data;
      let msg = 'Error al enviar el comprobante.';
      if (data?.error) msg = data.error;
      if (data?.detalles) {
        const details = Object.entries(data.detalles)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('; ');
        msg += ` (${details})`;
      }
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const goBack = () => {
    if (paso > 1) setPaso(paso - 1);
  };

  // ── Expired state ──
  if (timeLeft !== null && timeLeft <= 0 && !comprobanteEnviado) {
    return (
      <div className="page">
        <div className="container">
          <div className="pago-card pago-card-center">
            <AlertTriangle size={48} style={{ color: 'var(--red-500)' }} />
            <h2 style={{ marginTop: '1rem' }}>Orden expirada</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
              Han pasado los 15 minutos y tu orden fue cancelada automáticamente.
              Puedes volver a reservar tus asientos.
            </p>
            <button className="btn btn-primary" style={{ marginTop: '1.5rem' }}
              onClick={() => { clearProgress(); navigate('/viajes'); }}>
              Buscar viajes
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: '600px' }}>
        {/* Timer bar */}
        {!comprobanteEnviado && timeLeft !== null && (
          <div className="pago-timer-bar">
            <Clock size={16} />
            <span>Tiempo restante: <strong>{formatTime(timeLeft)}</strong></span>
          </div>
        )}

        {/* ═══ STEP 1: Select Payment Method ═══ */}
        {paso === 1 && (
          <div className="pago-step">
            <h2>¿Cómo vas a pagar?</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Selecciona tu método de pago preferido
            </p>

            <div className="pago-methods-list">
              {metodos.map(m => (
                <button
                  key={m.id}
                  className="pago-method-card"
                  onClick={() => { setMetodoSeleccionado(m); setPaso(2); }}
                >
                  <div>
                    <div className="pago-method-name">{m.nombre}</div>
                    {m.descripcion && (
                      <span className="pago-method-badge">{m.descripcion}</span>
                    )}
                  </div>
                  <ChevronRight size={20} style={{ color: 'var(--text-muted)' }} />
                </button>
              ))}
            </div>

            {metodos.length === 0 && (
              <div className="pago-empty">No hay métodos de pago disponibles.</div>
            )}

            <div className="pago-summary-bar">
              <div>
                <span className="pago-summary-label">Monto total</span>
                <span className="pago-summary-amount">
                  ${totalUsd.toFixed(2)} USD
                  {totalBs && <span className="pago-summary-bs"> / Bs. {totalBs.toLocaleString('es-VE', { minimumFractionDigits: 2 })}</span>}
                </span>
              </div>
              <span className="pago-summary-seats">
                {reservas.length} asiento{reservas.length > 1 ? 's' : ''}
              </span>
            </div>
          </div>
        )}

        {/* ═══ STEP 2: Payment Warning / Info ═══ */}
        {paso === 2 && metodoSeleccionado && (
          <div className="pago-step">
            <button className="pago-back-btn" onClick={goBack}>
              <ChevronLeft size={18} /> Volver
            </button>

            <h2>Información de tu pago</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Antes de pagar, revisa que los datos del banco de destino y el monto sean los correctos.
            </p>

            <div className="pago-warnings">
              <div className="pago-warning-item">
                <AlertTriangle size={18} />
                <span>Los datos de la cuenta de destino <strong>pueden cambiar</strong>. Verifica siempre antes de realizar el pago.</span>
              </div>
              <div className="pago-warning-item">
                <Shield size={18} />
                <span>Después de pagar, <strong>copia tu número de comprobante</strong> y tenlo listo para ingresarlo en el siguiente paso.</span>
              </div>
              <div className="pago-warning-item">
                <Clock size={18} />
                <span>Tienes <strong>15 minutos</strong> desde que creaste la orden. Si no subes el comprobante a tiempo, se cancela automáticamente y los puestos se liberan.</span>
              </div>
            </div>

            <div className="pago-info-card">
              <CreditCard size={24} style={{ color: 'var(--blue-500)' }} />
              <div className="pago-info-method">{metodoSeleccionado.nombre}</div>
              <div className="pago-info-amount">
                <span className="pago-info-label">Monto</span>
                <span className="pago-info-value">{getMonto(metodoSeleccionado).texto}</span>
              </div>
            </div>

            <button className="btn btn-primary btn-lg" style={{ width: '100%', marginTop: '1rem' }}
              onClick={() => setPaso(3)}>
              Continuar
            </button>
          </div>
        )}

        {/* ═══ STEP 3: Copyable Data ═══ */}
        {paso === 3 && metodoSeleccionado && (
          <div className="pago-step">
            <button className="pago-back-btn" onClick={goBack}>
              <ChevronLeft size={18} /> Volver
            </button>

            <h2>Paga a la tienda</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Los datos bancarios son únicos. Asegúrate de hacer tu pago correctamente.
            </p>

            <div className="pago-data-card">
              <div className="pago-data-badge">
                <CheckCircle size={14} /> Cuenta actualizada
              </div>

              {metodoSeleccionado.datos.map((d) => (
                <div className="pago-data-row" key={d.id}>
                  <div>
                    <div className="pago-data-label">{d.etiqueta}</div>
                    <div className="pago-data-value">{d.valor}</div>
                  </div>
                  <button
                    className="pago-copy-btn"
                    onClick={() => handleCopy(d.valor, d.id)}
                    title={`Copiar ${d.etiqueta}`}
                  >
                    {copiedField === d.id ? <CheckCircle size={18} /> : <Copy size={18} />}
                  </button>
                </div>
              ))}

              {/* Monto row */}
              <div className="pago-data-row">
                <div>
                  <div className="pago-data-label">Monto</div>
                  <div className="pago-data-value pago-data-value-bold">
                    {getMonto(metodoSeleccionado).texto}
                  </div>
                </div>
                <button
                  className="pago-copy-btn"
                  onClick={() => handleCopy(String(getMonto(metodoSeleccionado).valor), 'monto')}
                >
                  {copiedField === 'monto' ? <CheckCircle size={18} /> : <Copy size={18} />}
                </button>
              </div>

              <button className="pago-copy-all-btn" onClick={handleCopyAll}>
                <Copy size={16} />
                {copiedField === 'all' ? 'Datos copiados ✓' : 'Copiar todos los datos'}
              </button>
            </div>

            <button className="btn btn-accent btn-lg" style={{ width: '100%', marginTop: '1rem' }}
              onClick={() => setPaso(4)}>
              Ya pagué
            </button>
          </div>
        )}

        {/* ═══ STEP 4: Upload Proof ═══ */}
        {paso === 4 && (
          <div className="pago-step">
            <button className="pago-back-btn" onClick={goBack}>
              <ChevronLeft size={18} /> Volver
            </button>

            <h2>Enviar comprobante</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Sube la captura de tu pago para que podamos verificarlo.
            </p>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="pago-upload-form">
              <div className="form-group">
                <label>Número de referencia / comprobante (opcional)</label>
                <input
                  type="text"
                  className="form-control"
                  value={numeroRef}
                  onChange={(e) => setNumeroRef(e.target.value)}
                  placeholder="Ej: 123456789"
                />
              </div>

              <div className="form-group">
                <label>Captura del pago *</label>
                <div
                  className={`pago-upload-area ${imagenPreview ? 'pago-upload-area-has-file' : ''}`}
                  onClick={() => document.getElementById('pago-file-input').click()}
                >
                  {imagenPreview ? (
                    <img src={imagenPreview} alt="Preview" className="pago-upload-preview" />
                  ) : (
                    <>
                      <ImageIcon size={32} style={{ color: 'var(--text-muted)' }} />
                      <span>Toca aquí para subir la captura</span>
                      <small>JPG, PNG o PDF</small>
                    </>
                  )}
                  <input
                    id="pago-file-input"
                    type="file"
                    accept="image/*,.pdf"
                    onChange={handleImageChange}
                    style={{ display: 'none' }}
                  />
                </div>
              </div>

              <button
                className="btn btn-primary btn-lg"
                style={{ width: '100%' }}
                onClick={handleSubmitComprobante}
                disabled={submitting || !imagen}
              >
                {submitting ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Upload size={16} className="spin" /> Enviando...
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Upload size={16} /> Enviar comprobante
                  </span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ═══ STEP 5: Confirmation ═══ */}
        {paso === 5 && comprobanteEnviado && (
          <div className="pago-step">
            <div className="pago-card pago-card-center">
              <CheckCircle size={48} style={{ color: 'var(--green-500)' }} />
              <h2 style={{ marginTop: '1rem' }}>¡Comprobante enviado!</h2>
              <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', textAlign: 'center' }}>
                Tu puesto está <strong>apartado</strong>. Un administrador revisará tu pago.
                Te notificaremos cuando sea aprobado.
              </p>
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button className="btn btn-primary" onClick={() => navigate('/mis-reservas')}>
                  Ver mis reservas
                </button>
                <button className="btn btn-secondary" onClick={() => navigate('/')}>
                  Ir al inicio
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
