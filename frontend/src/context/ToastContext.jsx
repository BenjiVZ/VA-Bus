import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import '../styles/Toast.css';

/*
 * Notificaciones flotantes tipo "isla" (toast).
 *
 * Siempre visibles: fijas arriba-centro de la PANTALLA (no de la página),
 * por encima de todo, con animación de entrada y auto-cierre. Resuelven el
 * problema de los errores renderizados arriba del contenido que no se ven
 * cuando el usuario está scrolleado (ej. mapa de asientos).
 *
 * Uso:
 *   const toast = useToast();
 *   toast.error('No se pudo reservar');
 *   toast.success('¡Reserva creada!');
 *   toast.info('Te enviamos un código');
 */

const ToastContext = createContext(null);

const ICONS = {
  error: <AlertTriangle size={18} />,
  success: <CheckCircle size={18} />,
  info: <Info size={18} />,
};

let nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    // marca "saliendo" para la animación de salida y luego remueve
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, saliendo: true } : t)));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 260);
  }, []);

  const show = useCallback((tipo, mensaje, duracion) => {
    const texto = String(mensaje);
    // Duración proporcional al largo del mensaje (5s a 10s)
    const dur = duracion ?? Math.min(10000, Math.max(5000, 3000 + texto.length * 45));
    const id = nextId++;

    setToasts((prev) => {
      // Si el mismo mensaje ya está visible, no apilar: se reinicia su tiempo.
      const repetido = prev.find((t) => t.mensaje === texto && t.tipo === tipo && !t.saliendo);
      if (repetido) {
        clearTimeout(timers.current[repetido.id]);
        timers.current[repetido.id] = setTimeout(() => dismiss(repetido.id), dur);
        // remonta el nodo (key nueva) para que la barra de progreso rearranque
        return prev.map((t) => (t.id === repetido.id ? { ...t, renderKey: id } : t));
      }
      return [...prev.slice(-2), { id, tipo, mensaje: texto, dur, renderKey: id }];
    });
    timers.current[id] = setTimeout(() => dismiss(id), dur);
    return id;
  }, [dismiss]);

  const api = useMemo(() => ({
    show,
    error: (m, d) => show('error', m, d),
    success: (m, d) => show('success', m, d),
    info: (m, d) => show('info', m, d),
  }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tipo} ${t.saliendo ? 'toast-out' : ''}`}>
            <span className={`toast-icon toast-icon-${t.tipo}`}>{ICONS[t.tipo] || ICONS.info}</span>
            <span className="toast-msg">{t.mensaje}</span>
            <button className="toast-close" onClick={() => dismiss(t.id)} aria-label="Cerrar">
              <X size={15} />
            </button>
            {!t.saliendo && (
              <span className="toast-progress" style={{ animationDuration: `${t.dur}ms` }} />
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  // Fallback inofensivo si algún componente se renderiza fuera del provider
  return ctx || { show: () => {}, error: () => {}, success: () => {}, info: () => {} };
}
