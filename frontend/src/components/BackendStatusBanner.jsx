import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { getConfiguracion } from '../services/api';

/**
 * Banner global que aparece cuando no se puede contactar al backend
 * (servidor caído, sin internet, etc.). Escucha el evento `backend-status`
 * que emite la capa de API (src/services/api.js) y se oculta solo cuando
 * vuelve la conexión.
 */
function BackendStatusBanner() {
  const [offline, setOffline] = useState(false);
  const [reintentando, setReintentando] = useState(false);
  const [cerradoManual, setCerradoManual] = useState(false);

  useEffect(() => {
    const onStatus = (e) => {
      const online = e.detail?.online;
      if (online) {
        setOffline(false);
        setCerradoManual(false);
      } else {
        setOffline(true);
      }
    };
    window.addEventListener('backend-status', onStatus);
    return () => window.removeEventListener('backend-status', onStatus);
  }, []);

  const reintentar = async () => {
    setReintentando(true);
    try {
      // Endpoint público y liviano; si responde, el interceptor de la API
      // emitirá `backend-status: online` y este banner se ocultará solo.
      await getConfiguracion();
    } catch {
      // Sigue sin conexión: el banner permanece visible.
    } finally {
      setReintentando(false);
    }
  };

  if (!offline || cerradoManual) return null;

  return (
    <div role="alert" style={styles.bar}>
      <AlertTriangle size={18} style={{ flexShrink: 0 }} />
      <span style={styles.text}>
        Sin conexión con el servidor. No pudimos contactar el sistema de Aerorutas.
        Verifica tu conexión a internet o inténtalo de nuevo.
      </span>
      <button onClick={reintentar} disabled={reintentando} style={styles.retry}>
        {reintentando ? 'Reintentando…' : 'Reintentar'}
      </button>
      <button
        onClick={() => setCerradoManual(true)}
        aria-label="Cerrar aviso"
        style={styles.close}
      >
        <X size={16} />
      </button>
    </div>
  );
}

const styles = {
  bar: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 16px',
    background: '#b91c1c',
    color: '#fff',
    fontSize: '0.9rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
  },
  text: { flex: 1, lineHeight: 1.3 },
  retry: {
    background: '#fff',
    color: '#b91c1c',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  close: {
    background: 'transparent',
    border: 'none',
    color: '#fff',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    padding: '2px',
  },
};

export default BackendStatusBanner;
