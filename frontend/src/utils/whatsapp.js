// Utilidades para armar enlaces de WhatsApp con un único número de origen.
//
// El número "oficial" vive en el panel admin (Configuracion.whatsapp_vendedor)
// y llega a la web vía getConfiguracion(). Este módulo centraliza cómo se
// construye el enlace para que todos los sitios (Home, ChatBot, etc.) usen el
// mismo número y nunca vuelva a quedar un placeholder roto.

// Respaldo si la config del backend aún no cargó o viene vacía (0422-7779152).
export const WHATSAPP_FALLBACK = '584227779152';

/** Deja solo dígitos: wa.me no acepta '+', espacios ni guiones. */
export const soloDigitos = (n) => String(n ?? '').replace(/\D/g, '');

/**
 * Construye el enlace wa.me con el número dado (o el de respaldo) y texto opcional.
 * @param {string} numero  Número en cualquier formato (se normaliza a dígitos).
 * @param {string} [text]  Mensaje prellenado opcional.
 */
export function buildWhatsAppUrl(numero, text) {
  const num = soloDigitos(numero) || WHATSAPP_FALLBACK;
  const base = `https://wa.me/${num}`;
  return text ? `${base}?text=${encodeURIComponent(text)}` : base;
}
