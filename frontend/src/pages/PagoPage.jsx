import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ChevronRight, ChevronLeft, AlertTriangle, Clock, Copy, CheckCircle,
  Upload, CreditCard, Shield, Image as ImageIcon,
  Wallet, Landmark, Smartphone, DollarSign, Zap
} from 'lucide-react';

const getPaymentIcon = (nombre) => {
  const nameLower = nombre.toLowerCase();
  if (nameLower.includes('zelle') || nameLower.includes('dolar') || nameLower.includes('usd') || nameLower.includes('efectivo')) return <DollarSign size={24} />;
  if (nameLower.includes('pago movil') || nameLower.includes('pago móvil') || nameLower.includes('movil')) return <Smartphone size={24} />;
  if (nameLower.includes('transferencia') || nameLower.includes('banco') || nameLower.includes('bs')) return <Landmark size={24} />;
  if (nameLower.includes('binance') || nameLower.includes('crypto') || nameLower.includes('usdt')) return <Wallet size={24} />;
  return <CreditCard size={24} />;
};
import {
  getMetodosPago, crearComprobante, getEstadoComprobante, getTasaCambio,
  getBancos, r4GenerarOtp, r4ConfirmarDebito, r4EstadoOperacion, r4ConsultarOperacion,
} from '../services/api';
import { useAuth } from '../context/AuthContext';

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
  const { user } = useAuth();

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
  const [fotoBillete, setFotoBillete] = useState(null);
  const [fotoBilletePreview, setFotoBilletePreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [comprobanteEnviado, setComprobanteEnviado] = useState(false);

  // ── Cobro Inmediato (Débito con OTP) ──
  const [ciCedula, setCiCedula] = useState('');
  const [ciTelefono, setCiTelefono] = useState('');
  const [ciNombre, setCiNombre] = useState('');
  const [ciBanco, setCiBanco] = useState('');
  const [bancos, setBancos] = useState([]);
  const [bancoFiltro, setBancoFiltro] = useState('');
  const [ciConcepto, setCiConcepto] = useState('');
  const [ciOperacionId, setCiOperacionId] = useState(null);
  const [ciOtp, setCiOtp] = useState('');
  const [ciComprobante, setCiComprobante] = useState(null);
  const [ciComprobantePreview, setCiComprobantePreview] = useState(null);
  const [ciEstado, setCiEstado] = useState('idle'); // idle|otp_enviado|en_espera|rechazada
  const [ciLoading, setCiLoading] = useState(false);
  const [ciError, setCiError] = useState('');

  // Candado anti doble-envío (evita pagos duplicados por doble click / doble tap).
  const submitLockRef = useRef(false);

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
      // Restaurar un débito (R4) en curso para no reiniciarlo (evita duplicados).
      if (savedProgress.ci_operacion_id) setCiOperacionId(savedProgress.ci_operacion_id);
      if (savedProgress.ci_estado) setCiEstado(savedProgress.ci_estado);
      if (savedProgress.ci_telefono) setCiTelefono(savedProgress.ci_telefono);
    } else {
      navigate('/');
      return;
    }

    // Fetch payment methods, exchange rate and bank list
    getMetodosPago().then(res => setMetodos(res.data)).catch(() => {});
    getTasaCambio().then(res => setTasa(res.data.tasa_bcv)).catch(() => {});
    getBancos().then(res => setBancos(res.data)).catch(() => {});
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
      // Mientras el banco valida (AC00 / "en espera") el reloj se CONGELA: la orden
      // no debe expirar mientras esperamos la confirmación del banco. Solo vuelve a
      // correr si la operación se rechaza (es decir, si hubo un error).
      if (ciEstado === 'en_espera') return;
      const now = Date.now();
      const diff = Math.max(0, Math.floor((target - now) / 1000));
      setTimeLeft(diff);
      if (diff <= 0) {
        clearInterval(interval);
        clearProgress();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fechaExpiracion, comprobanteEnviado, ciEstado]);

  // Save progress on step changes (incluye el estado del débito R4 en curso)
  useEffect(() => {
    if (grupoPago) {
      saveProgress({
        grupo_pago: grupoPago,
        reservas,
        viaje_info: viajeInfo,
        fecha_expiracion: fechaExpiracion,
        paso_actual: paso,
        metodo_seleccionado: metodoSeleccionado,
        ci_operacion_id: ciOperacionId,
        ci_estado: ciEstado,
        ci_telefono: ciTelefono,
      });
    }
  }, [paso, metodoSeleccionado, ciOperacionId, ciEstado]);

  // ── Evitar perder el pago / volver atrás mientras hay una operación en curso ──
  const pagoEnCurso = !comprobanteEnviado && (
    submitting || ciLoading ||
    (metodoSeleccionado?.tipo === 'cobro_inmediato' &&
      (ciEstado === 'otp_enviado' || ciEstado === 'en_espera'))
  );

  useEffect(() => {
    if (!pagoEnCurso) return;

    // 1) Avisar antes de cerrar/recargar la pestaña.
    const onBeforeUnload = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', onBeforeUnload);

    // 2) Bloquear el botón "atrás" del navegador: re-empuja el estado y avisa.
    window.history.pushState(null, '', window.location.href);
    const onPop = () => {
      window.history.pushState(null, '', window.location.href);
      setCiError('Tienes un pago en curso. No salgas de esta pantalla hasta que termine.');
    };
    window.addEventListener('popstate', onPop);

    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      window.removeEventListener('popstate', onPop);
    };
  }, [pagoEnCurso]);

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

  const handleFotoBilleteChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFotoBillete(file);
      setFotoBilletePreview(URL.createObjectURL(file));
    }
  };

  const handleSubmitComprobante = async () => {
    if (!imagen) {
      setError('Debes subir la captura del pago.');
      return;
    }
    if (submitLockRef.current) return;   // ya hay un envío en curso
    submitLockRef.current = true;
    setSubmitting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('grupo_pago', grupoPago);
      formData.append('metodo_pago_id', metodoSeleccionado.id);
      formData.append('imagen', imagen);
      if (fotoBillete) formData.append('foto_billete', fotoBillete);
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
      submitLockRef.current = false;
    }
  };

  const goBack = () => {
    if (paso > 1) setPaso(paso - 1);
  };

  // ════════ Cobro Inmediato (Débito con OTP) ════════
  const seleccionarCobroInmediato = (metodo) => {
    setMetodoSeleccionado(metodo);
    setCiCedula(user?.cedula || '');
    setCiTelefono(user?.telefono || '');
    setCiNombre([user?.first_name, user?.last_name].filter(Boolean).join(' ').trim() || user?.username || '');
    setCiBanco(''); setBancoFiltro(''); setCiConcepto('');
    setCiOtp(''); setCiComprobante(null); setCiComprobantePreview(null);
    setCiEstado('idle'); setCiError('');
    setPaso(3);
  };

  const handleGenerarOtp = async () => {
    // El banco/validador esperan la cédula como letra + dígitos, SIN guion ni
    // espacios (ej: "V30719983"). El perfil la guarda como "V-30719983".
    const cedulaLimpia = ciCedula.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!/^\d{4}$/.test(ciBanco)) { setCiError('Selecciona tu banco.'); return; }
    if (!/^[VEJP]\d{6,9}$/.test(cedulaLimpia)) { setCiError('Cédula inválida. Ej: V12345678.'); return; }
    if (!/^\d{11}$/.test(ciTelefono)) { setCiError('El teléfono debe tener 11 dígitos (ej: 04141234567).'); return; }
    if (submitLockRef.current) return;   // evita generar dos OTP / operaciones
    submitLockRef.current = true;
    setCiLoading(true); setCiError('');
    try {
      const { data } = await r4GenerarOtp({
        grupo_pago: grupoPago,
        banco: ciBanco,
        cedula: cedulaLimpia,
        telefono: ciTelefono.trim(),
        nombre: ciNombre.trim(),
        concepto: ciConcepto.trim() || 'pago',
      });
      if (data.otp_enviado) {
        setCiOperacionId(data.operacion_id);
        setCiEstado('otp_enviado');
        setPaso(4);
      } else {
        setCiError(data.message || 'El banco no envió el OTP. Verifica los datos.');
      }
    } catch (err) {
      setCiError(err.response?.data?.error || 'No se pudo generar el OTP. Intenta de nuevo.');
    } finally {
      setCiLoading(false);
      submitLockRef.current = false;
    }
  };

  const handleCiComprobanteChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCiComprobante(file);
      setCiComprobantePreview(URL.createObjectURL(file));
    }
  };

  const aplicarEstadoCi = (estado) => {
    if (estado === 'aceptada') {
      setComprobanteEnviado(true);
      setPaso(5);
      clearProgress();
    } else if (estado === 'en_espera') {
      setCiEstado('en_espera');
    } else {
      setCiEstado('rechazada');
      setCiError('El pago fue rechazado por el banco. Verifica tu saldo/datos e inténtalo de nuevo.');
    }
  };

  const handleConfirmarDebito = async () => {
    if (!/^\d{1,8}$/.test(ciOtp)) { setCiError('Ingresa el OTP recibido (numérico).'); return; }
    if (submitLockRef.current) return;   // evita confirmar el débito dos veces
    submitLockRef.current = true;
    setCiLoading(true); setCiError('');
    try {
      const fd = new FormData();
      fd.append('operacion_id', ciOperacionId);
      fd.append('otp', ciOtp.trim());
      if (ciComprobante) fd.append('comprobante', ciComprobante);
      const { data } = await r4ConfirmarDebito(fd);
      aplicarEstadoCi(data.estado);
    } catch (err) {
      setCiError(err.response?.data?.error || 'No se pudo procesar el débito.');
    } finally {
      setCiLoading(false);
      submitLockRef.current = false;
    }
  };

  // Polling mientras la operación queda "en espera" (AC00). Le PREGUNTA al banco
  // (ConsultarOperaciones) en cada ciclo para resolver a aprobada/rechazada, sin
  // depender de un proceso de fondo.
  useEffect(() => {
    if (ciEstado !== 'en_espera' || !ciOperacionId) return;
    let activo = true;
    let iv;
    const stop = () => { activo = false; if (iv) clearInterval(iv); };
    const consultar = async () => {
      if (!activo) return;
      try {
        const { data } = await r4ConsultarOperacion(ciOperacionId);
        if (!activo) return;
        if (data.estado === 'aceptada') {
          stop();
          setComprobanteEnviado(true); setPaso(5); clearProgress();
        } else if (data.estado === 'rechazada') {
          stop();
          setCiEstado('rechazada');
          setCiError('El pago fue rechazado por el banco.');
        }
      } catch { /* reintentar en el siguiente ciclo */ }
    };
    consultar();                       // primera consulta inmediata
    iv = setInterval(consultar, 8000);
    return stop;
  }, [ciEstado, ciOperacionId]);

  const bancosFiltrados = bancos.filter(b =>
    `${b.codigo} ${b.nombre}`.toLowerCase().includes(bancoFiltro.toLowerCase()));

  // Nombre del banco elegido (para mostrarlo en la pantalla del OTP).
  const bancoNombre = bancos.find(b => b.codigo === ciBanco)?.nombre || '';

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

            <div className="pago-methods-grid">
              {metodos.map(m => {
                const esCI = m.tipo === 'cobro_inmediato';
                return (
                  <button
                    key={m.id}
                    className="pago-method-card"
                    onClick={() => esCI ? seleccionarCobroInmediato(m) : (setMetodoSeleccionado(m), setPaso(2))}
                    style={esCI ? { borderColor: 'var(--blue-500)' } : undefined}
                  >
                    <div className="pago-method-icon">
                      {esCI ? <Zap size={24} /> : getPaymentIcon(m.nombre)}
                    </div>
                    <div className="pago-method-info">
                      <div className="pago-method-name">{m.nombre}</div>
                      {m.descripcion && (
                        <span className="pago-method-badge">{m.descripcion}</span>
                      )}
                    </div>
                  </button>
                );
              })}
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

        {/* ═══ COBRO INMEDIATO · Paso A: Confirmar datos + banco ═══ */}
        {paso === 3 && metodoSeleccionado?.tipo === 'cobro_inmediato' && (
          <div className="pago-step">
            <button className="pago-back-btn" onClick={() => setPaso(1)}>
              <ChevronLeft size={18} /> Volver
            </button>

            <h2>Confirma tus datos</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              Recibirás un código (OTP) en tu teléfono para autorizar el débito. Verifica que tus datos sean correctos.
            </p>

            {ciError && <div className="alert alert-error">{ciError}</div>}

            <div className="pago-upload-form">
              <div className="form-group">
                <label>Cédula</label>
                <input className="form-control" value={ciCedula}
                  onChange={(e) => setCiCedula(e.target.value)} placeholder="V12345678" />
              </div>
              <div className="form-group">
                <label>Teléfono (11 dígitos)</label>
                <input className="form-control" value={ciTelefono} maxLength={11}
                  onChange={(e) => setCiTelefono(e.target.value.replace(/\D/g, ''))} placeholder="04141234567" />
              </div>
              <div className="form-group">
                <label>Nombre</label>
                <input className="form-control" value={ciNombre}
                  onChange={(e) => setCiNombre(e.target.value)} placeholder="Nombre y apellido" />
              </div>
              <div className="form-group">
                <label>Banco</label>
                <input className="form-control" value={bancoFiltro} style={{ marginBottom: 8 }}
                  onChange={(e) => {
                    const val = e.target.value;
                    setBancoFiltro(val);
                    // Auto-selecciona el primer banco que coincide con el filtro,
                    // así no hay que abrir el desplegable. Si no hay match, limpia.
                    const q = val.toLowerCase();
                    const match = bancos.find(b => `${b.codigo} ${b.nombre}`.toLowerCase().includes(q));
                    setCiBanco(match ? match.codigo : '');
                  }}
                  placeholder="Buscar por nombre o código…" />
                <select className="form-control" value={ciBanco} onChange={(e) => setCiBanco(e.target.value)}>
                  <option value="">Selecciona tu banco…</option>
                  {bancosFiltrados.map(b => (
                    <option key={b.codigo} value={b.codigo}>{b.codigo} — {b.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Concepto (opcional)</label>
                <input className="form-control" value={ciConcepto} maxLength={30}
                  onChange={(e) => setCiConcepto(e.target.value)} placeholder="Pago de pasaje" />
              </div>

              <div className="pago-info-card" style={{ marginTop: '0.5rem' }}>
                <Zap size={24} style={{ color: 'var(--blue-500)' }} />
                <div className="pago-info-method">Monto a debitar</div>
                <div className="pago-info-amount">
                  <span className="pago-info-label">Total</span>
                  <span className="pago-info-value">
                    {totalBs ? `Bs. ${totalBs.toLocaleString('es-VE', { minimumFractionDigits: 2 })}` : 'Calculando…'}
                  </span>
                </div>
              </div>

              <button className="btn btn-primary btn-lg" style={{ width: '100%', marginTop: '1rem' }}
                onClick={handleGenerarOtp} disabled={ciLoading}>
                {ciLoading ? 'Enviando OTP…' : 'Generar OTP'}
              </button>
            </div>
          </div>
        )}

        {/* ═══ COBRO INMEDIATO · Paso B: OTP + comprobante opcional + espera ═══ */}
        {paso === 4 && metodoSeleccionado?.tipo === 'cobro_inmediato' && (
          <div className="pago-step">
            {/* Sin botón "Volver": ya se generó el OTP/operación. Volver crearía un
                pago duplicado. El usuario completa el OTP o la orden expira (15 min). */}

            {ciEstado === 'en_espera' ? (
              <div className="pago-card pago-card-center">
                <Clock size={48} style={{ color: 'var(--blue-500)' }} className="spin" />
                <h2 style={{ marginTop: '1rem' }}>Validando tu pago…</h2>
                <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', textAlign: 'center' }}>
                  El banco está procesando la operación. Tu silla queda reservada y se
                  confirmará automáticamente en cuanto el banco apruebe — el tiempo no
                  corre mientras validamos.
                </p>

                {ciError && (
                  <div className="alert alert-error" style={{ marginTop: '1rem', width: '100%' }}>{ciError}</div>
                )}

                {/* OTP editable por si el banco se tarda o quedó pendiente: el cliente
                    puede corregir el código y volver a validar la operación. */}
                <div className="pago-upload-form" style={{ marginTop: '1.25rem', width: '100%' }}>
                  <div className="form-group">
                    <label>Código OTP</label>
                    <input className="form-control" value={ciOtp} maxLength={8}
                      onChange={(e) => setCiOtp(e.target.value.replace(/\D/g, ''))}
                      placeholder="Ej: 19807849" inputMode="numeric" />
                  </div>
                  <button className="btn btn-primary btn-lg" style={{ width: '100%' }}
                    onClick={handleConfirmarDebito} disabled={ciLoading}>
                    {ciLoading ? 'Validando…' : 'Volver a validar'}
                  </button>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: '0.75rem' }}>
                    Estamos consultando al banco automáticamente. Usa este botón solo si
                    el pago tarda demasiado.
                  </p>
                </div>
              </div>
            ) : (
              <>
                <h2>Ingresa el código OTP</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  Enviamos un código a tu teléfono. Ingrésalo para autorizar el débito.
                </p>

                {/* Resumen: a qué teléfono y banco se hizo la solicitud */}
                <div className="otp-resumen">
                  <div className="otp-resumen-item">
                    <Smartphone size={16} />
                    <div>
                      <span className="otp-resumen-label">Teléfono</span>
                      <span className="otp-resumen-value">{ciTelefono || '—'}</span>
                    </div>
                  </div>
                  <div className="otp-resumen-item">
                    <Landmark size={16} />
                    <div>
                      <span className="otp-resumen-label">Banco</span>
                      <span className="otp-resumen-value">{bancoNombre || ciBanco || '—'}</span>
                    </div>
                  </div>
                </div>

                {ciError && <div className="alert alert-error">{ciError}</div>}

                <div className="pago-upload-form">
                  <div className="form-group">
                    <label>Código OTP</label>
                    <input className="form-control" value={ciOtp} maxLength={8}
                      onChange={(e) => setCiOtp(e.target.value.replace(/\D/g, ''))}
                      placeholder="Ej: 19807849" inputMode="numeric" />
                  </div>

                  <div className="form-group">
                    <label>Comprobante (opcional)</label>
                    <div
                      className={`pago-upload-area ${ciComprobantePreview ? 'pago-upload-area-has-file' : ''}`}
                      onClick={() => document.getElementById('ci-comprobante-input').click()}
                    >
                      {ciComprobantePreview ? (
                        <img src={ciComprobantePreview} alt="Comprobante" className="pago-upload-preview" />
                      ) : (
                        <>
                          <ImageIcon size={32} style={{ color: 'var(--text-muted)' }} />
                          <span>Adjuntar captura (opcional)</span>
                          <small>JPG, PNG o WebP</small>
                        </>
                      )}
                      <input id="ci-comprobante-input" type="file" accept="image/*"
                        onChange={handleCiComprobanteChange} style={{ display: 'none' }} />
                    </div>
                  </div>

                  <button className="btn btn-primary btn-lg" style={{ width: '100%' }}
                    onClick={handleConfirmarDebito} disabled={ciLoading}>
                    {ciLoading ? 'Procesando…' : 'Confirmar pago'}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* ═══ STEP 3: Copyable Data ═══ */}
        {paso === 3 && metodoSeleccionado && metodoSeleccionado.tipo !== 'cobro_inmediato' && (
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
        {paso === 4 && metodoSeleccionado?.tipo !== 'cobro_inmediato' && (
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

              {/* Foto billete when required */}
              {metodoSeleccionado?.requiere_foto_billete && (
                <div className="form-group">
                  <label>Foto del billete *</label>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 0.5rem' }}>
                    Sube una foto clara del billete con el que estás pagando
                  </p>
                  <div
                    className={`pago-upload-area ${fotoBilletePreview ? 'pago-upload-area-has-file' : ''}`}
                    onClick={() => document.getElementById('pago-billete-input').click()}
                  >
                    {fotoBilletePreview ? (
                      <img src={fotoBilletePreview} alt="Billete" className="pago-upload-preview" />
                    ) : (
                      <>
                        <ImageIcon size={32} style={{ color: 'var(--text-muted)' }} />
                        <span>Toca aquí para subir la foto del billete</span>
                        <small>JPG, PNG o WebP</small>
                      </>
                    )}
                    <input
                      id="pago-billete-input"
                      type="file"
                      accept="image/*"
                      onChange={handleFotoBilleteChange}
                      style={{ display: 'none' }}
                    />
                  </div>
                </div>
              )}

              <button
                className="btn btn-primary btn-lg"
                style={{ width: '100%' }}
                onClick={handleSubmitComprobante}
                disabled={submitting || !imagen || (metodoSeleccionado?.requiere_foto_billete && !fotoBillete)}
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
              {metodoSeleccionado?.tipo === 'cobro_inmediato' ? (
                <>
                  <h2 style={{ marginTop: '1rem' }}>¡Pago aprobado!</h2>
                  <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', textAlign: 'center' }}>
                    Tu pago fue confirmado por el banco y tu puesto quedó <strong>confirmado</strong>.
                    Te enviamos tu boleto por correo.
                  </p>
                </>
              ) : (
                <>
                  <h2 style={{ marginTop: '1rem' }}>¡Comprobante enviado!</h2>
                  <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', textAlign: 'center' }}>
                    Tu puesto está <strong>apartado</strong>. Un administrador revisará tu pago.
                    Te notificaremos cuando sea aprobado.
                  </p>
                </>
              )}
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                {metodoSeleccionado?.tipo === 'cobro_inmediato' && grupoPago && (
                  <button className="btn btn-success" onClick={() => navigate(`/ticket/${grupoPago}`)}>
                    🎫 Descargar boleto
                  </button>
                )}
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
