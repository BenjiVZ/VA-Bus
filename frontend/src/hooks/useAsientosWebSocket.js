import { useEffect, useRef } from 'react';

/**
 * Hook que escucha eventos en tiempo real de cambios de asientos para un viaje.
 *
 * Eventos recibidos del servidor (formato seat_changed):
 *   { type: 'seat_changed', numero, piso, estado, usuario_id }
 *   estado ∈ 'locked' | 'unlocked' | 'reserved' | 'released'
 *
 * El handler `onSeatChanged` se invoca con el evento. Si el cambio fue
 * originado por el propio usuario (compare contra `currentUserId`), el
 * handler lo recibe igual; la decisión de ignorar queda en el callsite.
 *
 * Reconecta automáticamente con backoff exponencial hasta 30s.
 * Si el navegador no soporta WebSocket o la conexión falla persistente,
 * el polling reducido del componente padre sigue cubriendo.
 */
export function useAsientosWebSocket({ viajeId, enabled = true, onSeatChanged }) {
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const handlerRef = useRef(onSeatChanged);
  const closedByUsRef = useRef(false);

  // Mantener la referencia actualizada sin reconectar al cambiar el handler.
  useEffect(() => {
    handlerRef.current = onSeatChanged;
  }, [onSeatChanged]);

  useEffect(() => {
    if (!enabled || !viajeId) return undefined;

    const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8001/api');
    // Reemplazar http(s):// por ws(s)://, quitar /api del final.
    const wsBase = apiUrl
      .replace(/\/api\/?$/, '')
      .replace(/^http(s?):\/\//, (_m, s) => `ws${s}://`);
    const wsUrl = `${wsBase}/ws/viajes/${viajeId}/asientos/`;

    const connect = () => {
      closedByUsRef.current = false;
      let ws;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data?.type === 'seat_changed' && handlerRef.current) {
            handlerRef.current(data);
          }
        } catch {
          // Mensajes no-JSON se ignoran silenciosamente.
        }
      };

      ws.onerror = () => {
        // Lo manejará onclose de todas formas.
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!closedByUsRef.current) scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      // Backoff: 1s, 2s, 4s, 8s, 16s, capa a 30s.
      const attempt = reconnectAttemptsRef.current;
      const delay = Math.min(30000, 1000 * 2 ** attempt);
      reconnectAttemptsRef.current = attempt + 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    connect();

    return () => {
      closedByUsRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [viajeId, enabled]);
}
