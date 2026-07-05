import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Bot, User, ExternalLink, ChevronRight, Sparkles, RotateCcw, ArrowLeft, Home } from 'lucide-react';
import { getConfiguracion } from '../services/api';
import { buildWhatsAppUrl } from '../utils/whatsapp';
import '../styles/ChatBot.css';

/* ══════════════════════════════════════════════════════════════════════════
   Árbol de decisión guiado — sin IA, solo botones.
   Cada nodo tiene:
     - text:    mensaje del bot
     - options: array de botones { label, next?, whatsapp?, link? }
   Nodos terminales (hojas) usan leafOptions() para volver al padre / inicio
   o saltar a WhatsApp.
   ══════════════════════════════════════════════════════════════════════════ */

const WHATSAPP_DEFAULT_MSG = 'Hola, tengo una consulta sobre Aerorutas:';

/** Devuelve las opciones estándar al final de una respuesta hoja. */
const leafOptions = (parent, { showAgent = true, agentMsg } = {}) => [
  { label: 'Ver más opciones de este tema', next: parent, icon: 'back' },
  { label: 'Volver al inicio', next: 'root', icon: 'home' },
  ...(showAgent
    ? [{ label: 'Hablar con un agente por WhatsApp', whatsapp: true, whatsappMsg: agentMsg, icon: 'wa' }]
    : []),
];

const FLOW = {
  /* ── RAÍZ ───────────────────────────────────────────────────────── */
  root: {
    text: '¡Hola! 👋 Soy el asistente de Aerorutas. ¿Sobre qué tema necesitas ayuda?',
    options: [
      { label: '🎟️  Reservas y compras', next: 'reservas' },
      { label: '💳  Pagos y comprobantes', next: 'pagos' },
      { label: '📄  Documentos para viajar', next: 'documentos' },
      { label: '🚍  Viajes y rutas', next: 'viajes' },
      { label: '🎫  Mi ticket y verificación', next: 'tickets' },
      { label: '👤  Mi cuenta y perfil', next: 'cuenta' },
      { label: '⭐  Programa VIP', next: 'vip' },
      { label: '💬  Hablar con un agente', whatsapp: true, icon: 'wa' },
    ],
  },

  /* ── RESERVAS ───────────────────────────────────────────────────── */
  reservas: {
    text: '🎟️ Reservas y compras — escoge una pregunta:',
    options: [
      { label: '¿Cómo reservo un pasaje?', next: 'reservas_como' },
      { label: '¿Cuánto tiempo dura mi reserva?', next: 'reservas_tiempo' },
      { label: '¿Puedo reservar para otra persona?', next: 'reservas_otro' },
      { label: '¿Puedo viajar con mascota?', next: 'reservas_mascota' },
      { label: '¿Cómo cancelo o cambio mi reserva?', next: 'reservas_cancelar' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  reservas_como: {
    text:
      'Es muy fácil 👇\n\n1️⃣ Busca tu viaje por origen, destino y fecha\n2️⃣ Selecciona tu asiento en el mapa del autobús\n3️⃣ Confirma y elige tu método de pago\n4️⃣ Sube el comprobante de pago\n5️⃣ Espera la validación y recibe tu boleto por email 📧',
    options: leafOptions('reservas'),
  },
  reservas_tiempo: {
    text:
      '⏱️ Tienes **15 minutos** para completar el pago desde que reservas el asiento.\n\nSi no subes el comprobante en ese tiempo, el asiento se libera automáticamente para que otra persona pueda comprarlo.',
    options: leafOptions('reservas'),
  },
  reservas_otro: {
    text:
      '✅ Sí, puedes reservar para otra persona.\n\nAl seleccionar un asiento, activa la opción "Asignar a otra persona" e ingresa el nombre y cédula del pasajero real. Tú quedas como comprador responsable del pago.',
    options: leafOptions('reservas'),
  },
  reservas_mascota: {
    text:
      '🐾 ¡Sí! Aceptamos mascotas a bordo.\n\nAl reservar, marca "Viaja con animal" e indica el tipo (perro, gato, ave, conejo, hámster u otro). Necesitarás subir la tarjeta de vacunación vigente del animal.',
    options: leafOptions('reservas'),
  },
  reservas_cancelar: {
    text:
      '🔄 Para cancelar o cambiar tu reserva:\n\n1️⃣ Ve a "Mis Reservas" desde tu perfil\n2️⃣ Selecciona la reserva\n3️⃣ Las políticas de reembolso varían según la cercanía al viaje\n\nPara cambios o reembolsos contáctanos directamente — un agente te ayudará más rápido.',
    options: leafOptions('reservas', {
      agentMsg: 'Hola, necesito cancelar/cambiar una reserva.',
    }),
  },

  /* ── PAGOS ──────────────────────────────────────────────────────── */
  pagos: {
    text: '💳 Pagos y comprobantes — escoge una pregunta:',
    options: [
      { label: '¿Qué métodos de pago aceptan?', next: 'pagos_metodos' },
      { label: '¿En qué moneda pago?', next: 'pagos_moneda' },
      { label: '¿Cómo subo el comprobante?', next: 'pagos_comprobante' },
      { label: '¿Cuánto tarda en validarse?', next: 'pagos_tiempo' },
      { label: 'No pude subir mi comprobante', next: 'pagos_problema' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  pagos_metodos: {
    text:
      'Aceptamos estos métodos:\n\n💳 Transferencia bancaria (Bs)\n📱 Pago móvil (Bs)\n💵 Efectivo en divisas (USD)\n🌐 Zelle (USD)\n🔗 Binance (USDT)\n💸 Zinli (USD)\n\nLos datos exactos (banco, número, RIF) los verás al elegir el método en la página de pago.',
    options: leafOptions('pagos'),
  },
  pagos_moneda: {
    text:
      '💵 Los precios se publican en **dólares (USD)**.\n\nSi pagas en bolívares, el monto se calcula con la tasa BCV del día (la verás indicada en la página de pago).',
    options: leafOptions('pagos'),
  },
  pagos_comprobante: {
    text:
      'En la página de pago:\n\n1️⃣ Elige el método con el que pagaste\n2️⃣ Ingresa el número de referencia y el monto\n3️⃣ Sube la **captura del pago** (imagen)\n4️⃣ Si es divisas/efectivo, sube también la **foto del billete**\n5️⃣ Envía el comprobante 📤',
    options: leafOptions('pagos'),
  },
  pagos_tiempo: {
    text:
      '⏳ El equipo administrativo valida los comprobantes manualmente. Normalmente toma entre **15 minutos y unas horas**, según la hora del día.\n\nMientras tanto tu asiento queda **apartado** (nadie más puede tomarlo). Cuando se apruebe, te llegará un email con tu boleto y QR.',
    options: leafOptions('pagos'),
  },
  pagos_problema: {
    text:
      '⚠️ Si tuviste problemas para subir tu comprobante, escríbenos por WhatsApp y un agente lo procesará manualmente. Ten a mano:\n\n• Captura del pago\n• Número de referencia\n• Asiento y fecha del viaje',
    options: leafOptions('pagos', {
      agentMsg: 'Hola, tuve un problema subiendo mi comprobante de pago.',
    }),
  },

  /* ── DOCUMENTOS ─────────────────────────────────────────────────── */
  documentos: {
    text: '📄 ¿Qué documentos necesitas? Escoge tu caso:',
    options: [
      { label: 'Adulto sin acompañantes', next: 'doc_adulto' },
      { label: 'Viajo con un menor de edad', next: 'doc_menor' },
      { label: 'Viajo con mi mascota', next: 'doc_mascota' },
      { label: 'Persona con discapacidad', next: 'doc_discapacidad' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  doc_adulto: {
    text:
      '🪪 **Adultos:**\n\n• Cédula de identidad vigente (obligatoria)\n• Boleto digital o impreso con el código QR\n\nEso es todo. Te recomendamos llegar 30 minutos antes de la salida.',
    options: leafOptions('documentos'),
  },
  doc_menor: {
    text:
      '👶 **Menores de edad:**\n\n• Partida de nacimiento\n• Cédula del representante legal\n• Foto reciente del menor (tipo carnet o selfie)\n\nAl reservar marca "Es menor de edad" y sube esos documentos en la sección correspondiente.\n\n⚠️ Si el menor **no es tu hijo/a**, marca también esa casilla y sube el **permiso de viaje** (autorización expedida por la autoridad competente).',
    options: leafOptions('documentos'),
  },
  doc_mascota: {
    text:
      '🐾 **Mascotas:**\n\n• Tarjeta de vacunación vigente del animal\n• Indicar el tipo de mascota al reservar\n\nAceptamos perros, gatos, aves, conejos, hámsters y otros pequeños animales.',
    options: leafOptions('documentos'),
  },
  doc_discapacidad: {
    text:
      '♿ **Persona con discapacidad:**\n\n• Certificado médico o documento que acredite la discapacidad\n\nAl reservar marca "Persona con discapacidad" y sube el documento. Esto nos permite asignarte un asiento adecuado.',
    options: leafOptions('documentos'),
  },

  /* ── VIAJES Y RUTAS ─────────────────────────────────────────────── */
  viajes: {
    text: '🚍 Viajes y rutas — escoge una pregunta:',
    options: [
      { label: '¿Qué rutas tienen disponibles?', next: 'viajes_rutas' },
      { label: '¿Cuáles son los horarios?', next: 'viajes_horarios' },
      { label: '¿Hacen viajes de ida y vuelta?', next: 'viajes_ida_vuelta' },
      { label: '¿Cuánto cuesta un pasaje?', next: 'viajes_precio' },
      { label: '¿Cuántos puestos tiene el bus?', next: 'viajes_capacidad' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  viajes_rutas: {
    text:
      '🗺️ Cubrimos varias rutas entre ciudades de Venezuela.\n\nLa forma más fácil de ver las rutas disponibles es ir a la sección **Viajes** del menú principal y filtrar por tu origen y destino.',
    options: leafOptions('viajes'),
  },
  viajes_horarios: {
    text:
      '🕐 Los horarios dependen de cada ruta y fecha.\n\nEn la sección **Viajes** puedes seleccionar la fecha y verás todas las salidas disponibles ese día con su hora exacta.',
    options: leafOptions('viajes'),
  },
  viajes_ida_vuelta: {
    text:
      '🔁 Sí, ofrecemos viajes de **ida** y de **ida y vuelta**.\n\nAl buscar viajes verás un sello "IDA Y VUELTA" en los que aplican. La fecha de regreso se muestra al seleccionarlo.',
    options: leafOptions('viajes'),
  },
  viajes_precio: {
    text:
      '💰 Los precios varían según la ruta y se muestran en USD.\n\nEn la sección **Viajes** verás el precio de cada salida junto con su equivalente en bolívares al cambio del día.',
    options: leafOptions('viajes'),
  },
  viajes_capacidad: {
    text:
      '🚍 Cada autobús tiene una capacidad distinta y puede tener uno o varios pisos.\n\nAl seleccionar un viaje, verás el mapa exacto de asientos del autobús asignado y los puestos disponibles en tiempo real.',
    options: leafOptions('viajes'),
  },

  /* ── TICKETS ────────────────────────────────────────────────────── */
  tickets: {
    text: '🎫 Mi ticket — escoge una pregunta:',
    options: [
      { label: '¿Dónde está mi ticket?', next: 'ticket_donde' },
      { label: '¿Cómo verifico mi QR?', next: 'ticket_qr' },
      { label: '¿Puedo imprimir mi boleto?', next: 'ticket_imprimir' },
      { label: 'No me llegó el email', next: 'ticket_email' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  ticket_donde: {
    text:
      '🎫 Tu ticket aparece en **dos lugares**:\n\n1️⃣ Te llega por email cuando se valida el pago (PDF adjunto)\n2️⃣ También puedes verlo entrando a "Mis Reservas" → "Ver ticket"\n\nIncluye un código QR y un código único de 8 caracteres.',
    options: leafOptions('tickets'),
  },
  ticket_qr: {
    text:
      '📲 El conductor escaneará tu QR al abordar. También puedes verificar el ticket tú mismo:\n\n• Escanea el QR con la cámara de tu teléfono\n• O ingresa el código de 8 caracteres en la página de verificación\n\nSi es válido, verás los datos del pasajero y el viaje.',
    options: leafOptions('tickets'),
  },
  ticket_imprimir: {
    text:
      '🖨️ Sí, puedes imprimir el PDF que te llegó por email. También basta con mostrarlo desde tu teléfono al momento de abordar.',
    options: leafOptions('tickets'),
  },
  ticket_email: {
    text:
      '📭 Si no te llegó el email:\n\n• Revisa la carpeta de **spam** o **promociones**\n• Confirma que el email en tu perfil sea correcto\n• El email se envía solo cuando se aprueba el comprobante, no antes\n\nSi ya pasó tiempo y nada, contáctanos.',
    options: leafOptions('tickets', {
      agentMsg: 'Hola, no me llegó el email con mi ticket.',
    }),
  },

  /* ── CUENTA ─────────────────────────────────────────────────────── */
  cuenta: {
    text: '👤 Mi cuenta — escoge una pregunta:',
    options: [
      { label: '¿Cómo creo una cuenta?', next: 'cuenta_crear' },
      { label: 'No me llegó el código de verificación', next: 'cuenta_verificar' },
      { label: 'Olvidé mi contraseña', next: 'cuenta_password' },
      { label: '¿Cómo edito mi perfil?', next: 'cuenta_editar' },
      { label: 'Iniciar sesión con Google', next: 'cuenta_google' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  cuenta_crear: {
    text:
      '🆕 Para crear tu cuenta:\n\n1️⃣ Ve a "Registrarse" en el menú\n2️⃣ Ingresa nombre, email, cédula y contraseña\n3️⃣ Te enviaremos un código de 6 dígitos a tu email\n4️⃣ Ingrésalo para activar la cuenta\n\nO usa el botón de **Google** para crear cuenta al instante.',
    options: leafOptions('cuenta'),
  },
  cuenta_verificar: {
    text:
      '📧 Si no recibiste el código:\n\n• Revisa **spam** y **promociones**\n• Confirma que escribiste bien el email\n• En la pantalla de verificación toca "Reenviar código"\n• El código expira a los 15 minutos — si pasó más, pide uno nuevo',
    options: leafOptions('cuenta'),
  },
  cuenta_password: {
    text:
      '🔑 Para recuperar tu contraseña:\n\n1️⃣ Toca "¿Olvidaste tu contraseña?" en la pantalla de login\n2️⃣ Ingresa tu email\n3️⃣ Te enviaremos un código de recuperación\n4️⃣ Úsalo para crear una nueva contraseña',
    options: leafOptions('cuenta'),
  },
  cuenta_editar: {
    text:
      '✏️ Para editar tu perfil:\n\n1️⃣ Inicia sesión\n2️⃣ Ve a "Perfil" en el menú\n3️⃣ Actualiza nombre, cédula, teléfono o fecha de nacimiento\n\nEl email no se puede cambiar (es tu identificador de cuenta).',
    options: leafOptions('cuenta'),
  },
  cuenta_google: {
    text:
      '🔵 Puedes iniciar sesión o crear cuenta con un solo clic usando Google.\n\nToca el botón "Continuar con Google" en la pantalla de Login o Registro.',
    options: leafOptions('cuenta'),
  },

  /* ── VIP ────────────────────────────────────────────────────────── */
  vip: {
    text: '⭐ Programa Pasajero Frecuente — escoge una pregunta:',
    options: [
      { label: '¿Qué es el programa VIP?', next: 'vip_que_es' },
      { label: '¿Cuáles son los niveles?', next: 'vip_niveles' },
      { label: '¿Cómo subo de nivel?', next: 'vip_subir' },
      { label: '¿Cómo verifico mi nivel?', next: 'vip_ver' },
      { label: 'Volver al inicio', next: 'root', icon: 'home' },
    ],
  },
  vip_que_es: {
    text:
      '⭐ Es nuestro programa de lealtad. Mientras más viajes con Aerorutas, más beneficios desbloqueas: prioridad en abordaje, asientos preferenciales, descuentos y atención preferente.',
    options: leafOptions('vip'),
  },
  vip_niveles: {
    text:
      'Tenemos 3 niveles:\n\n🥈 **Plata** — Beneficios básicos\n🥇 **Oro** — Beneficios premium\n💎 **Platino** — Beneficios máximos\n\nLos beneficios específicos de cada nivel los anunciamos en redes y por email.',
    options: leafOptions('vip'),
  },
  vip_subir: {
    text:
      '📈 Subes de nivel acumulando viajes confirmados. El equipo administrativo revisa periódicamente y actualiza tu nivel.\n\nSi crees que ya calificas para el siguiente nivel, contáctanos por WhatsApp.',
    options: leafOptions('vip', {
      agentMsg: 'Hola, quiero saber si califico para subir de nivel VIP.',
    }),
  },
  vip_ver: {
    text:
      '👀 Tu nivel VIP aparece en tu perfil cuando inicias sesión, con un sello dorado debajo de tu nombre. Si no aparece, todavía no estás inscrito en el programa.',
    options: leafOptions('vip'),
  },
};

/* ══════════════════════════════════════════════════════════════════
   Motor de comprensión (sin IA): relaciona lo que el usuario ESCRIBE
   con la mejor respuesta del FAQ. Normaliza acentos, tokeniza y puntúa
   contra palabras clave/sinónimos. Si acierta, responde en lenguaje
   natural; si no, ofrece temas + agente. Esto es lo que hace que el
   asistente "entienda" en vez de rebotar todo a WhatsApp.
   ══════════════════════════════════════════════════════════════════ */

/** minúsculas, sin acentos, solo letras/números → base para comparar. */
const normalize = (str) =>
  str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

/* Palabras clave por respuesta. Las frases (con espacio) valen más que
   los tokens sueltos, así una pregunta específica gana a una genérica. */
const KB = [
  { node: 'reservas_como', kw: ['como reservo', 'como reservar', 'como compro', 'como comprar', 'hago una reserva', 'reservar un pasaje', 'comprar pasaje', 'comprar boleto', 'sacar pasaje', 'proceso de compra', 'pasos para reservar', 'reservar', 'comprar', 'adquirir'] },
  { node: 'reservas_tiempo', kw: ['cuanto dura', 'cuanto tiempo', 'dura mi reserva', 'se libera', 'se vence', '15 minutos', 'tiempo para pagar', 'tiempo de reserva', 'expira', 'caduca', 'libera', 'minutos'] },
  { node: 'reservas_otro', kw: ['otra persona', 'reservar para otro', 'para un familiar', 'a nombre de', 'asignar a otra', 'comprar para alguien', 'para mi mama', 'para mi esposo', 'tercero', 'familiar'] },
  { node: 'reservas_mascota', kw: ['viajar con mascota', 'llevar mi perro', 'con mi gato', 'mascota a bordo', 'puedo llevar animal', 'viajar con animal', 'mascota', 'perro', 'gato', 'animal'] },
  { node: 'reservas_cancelar', kw: ['cancelar', 'cancelacion', 'cambiar mi reserva', 'cambiar de viaje', 'reembolso', 'devolucion', 'anular', 'modificar reserva', 'me devuelven'] },

  { node: 'pagos_metodos', kw: ['metodos de pago', 'formas de pago', 'como pago', 'con que pago', 'como puedo pagar', 'medios de pago', 'aceptan zelle', 'pago movil', 'transferencia', 'zelle', 'binance', 'zinli', 'efectivo', 'divisas', 'metodo'] },
  { node: 'pagos_moneda', kw: ['en que moneda', 'que moneda', 'bolivares o dolares', 'tasa bcv', 'precio en dolares', 'pago en bolivares', 'cambio del dia', 'moneda', 'dolares', 'bolivares', 'bcv'] },
  { node: 'pagos_comprobante', kw: ['como subo el comprobante', 'subir comprobante', 'subir el pago', 'adjuntar comprobante', 'enviar captura', 'subir captura', 'donde subo el pago', 'comprobante', 'captura', 'adjuntar'] },
  { node: 'pagos_tiempo', kw: ['cuanto tarda', 'cuanto demora', 'validar el pago', 'aprobar el pago', 'tarda en aprobarse', 'revisan el pago', 'cuando aprueban', 'validacion', 'validar', 'demora', 'aprobar', 'aprobacion'] },
  { node: 'pagos_problema', kw: ['no pude subir', 'no puedo subir', 'error al subir', 'problema con el pago', 'no me deja subir', 'no carga el comprobante', 'falla el comprobante', 'error de pago'] },

  { node: 'doc_adulto', kw: ['documentos adulto', 'que documentos necesito', 'que necesito para viajar', 'que debo llevar', 'requisitos para viajar', 'documentos para viajar', 'cedula', 'requisitos', 'documentos', 'documento'] },
  { node: 'doc_menor', kw: ['viajo con un menor', 'menor de edad', 'con un nino', 'partida de nacimiento', 'representante legal', 'documentos nino', 'viaja un menor', 'llevar un menor', 'menor', 'nino', 'partida'] },
  { node: 'doc_mascota', kw: ['documentos mascota', 'papeles de mi perro', 'tarjeta de vacunacion', 'requisitos mascota', 'que necesita mi mascota', 'vacunacion', 'vacuna'] },
  { node: 'doc_discapacidad', kw: ['persona con discapacidad', 'silla de ruedas', 'certificado medico', 'movilidad reducida', 'discapacidad', 'discapacitado'] },

  { node: 'viajes_rutas', kw: ['que rutas', 'rutas disponibles', 'a donde viajan', 'hacia donde', 'que destinos', 'que ciudades', 'cobertura', 'viajan a', 'rutas', 'destinos', 'destino'] },
  { node: 'viajes_horarios', kw: ['horarios', 'a que hora', 'hora de salida', 'a que horas', 'que salidas hay', 'frecuencia', 'horario', 'salidas', 'salida'] },
  { node: 'viajes_ida_vuelta', kw: ['ida y vuelta', 'ida y regreso', 'viaje redondo', 'boleto de regreso', 'round trip', 'vuelta', 'regreso', 'retorno'] },
  { node: 'viajes_precio', kw: ['cuanto cuesta', 'precio del pasaje', 'cuanto vale', 'cuanto sale', 'costo del boleto', 'que precio', 'tarifa', 'precio', 'cuesta', 'costo'] },
  { node: 'viajes_capacidad', kw: ['cuantos puestos', 'cuantos asientos', 'capacidad del bus', 'cuantas personas', 'tamano del autobus', 'puestos', 'asientos', 'capacidad', 'pisos'] },

  { node: 'ticket_donde', kw: ['donde esta mi ticket', 'donde veo mi boleto', 'ver mi ticket', 'encontrar mi ticket', 'descargar ticket', 'donde esta mi boleto', 'mi pasaje', 'ticket', 'boleto'] },
  { node: 'ticket_qr', kw: ['codigo qr', 'verificar qr', 'como verifico', 'validar ticket', 'escanear', 'codigo de 8', 'verificar mi boleto', 'qr', 'escanear'] },
  { node: 'ticket_imprimir', kw: ['imprimir boleto', 'puedo imprimir', 'imprimir mi ticket', 'imprimo', 'impreso', 'imprimir', 'pdf'] },
  { node: 'ticket_email', kw: ['no me llego el email', 'no llego mi ticket', 'no recibi el correo', 'no me llega el correo', 'no me llego el boleto', 'email con ticket', 'no me llego'] },

  { node: 'cuenta_crear', kw: ['crear cuenta', 'crear una cuenta', 'como me registro', 'quiero registrarme', 'abrir cuenta', 'nueva cuenta', 'registrarme', 'registro', 'registrar'] },
  { node: 'cuenta_verificar', kw: ['codigo de verificacion', 'no me llego el codigo', 'verificar cuenta', 'activar cuenta', 'codigo de 6', 'reenviar codigo', 'verificacion'] },
  { node: 'cuenta_password', kw: ['olvide mi contrasena', 'recuperar contrasena', 'cambiar contrasena', 'resetear clave', 'olvide mi clave', 'nueva contrasena', 'contrasena', 'clave', 'password'] },
  { node: 'cuenta_editar', kw: ['editar perfil', 'cambiar mis datos', 'actualizar perfil', 'modificar mi cuenta', 'cambiar mi telefono', 'editar mi informacion', 'perfil', 'actualizar'] },
  { node: 'cuenta_google', kw: ['iniciar sesion con google', 'entrar con google', 'login con google', 'cuenta de google', 'boton de google', 'google'] },

  { node: 'vip_que_es', kw: ['que es vip', 'que es el programa', 'programa vip', 'pasajero frecuente', 'beneficios vip', 'programa de lealtad', 'lealtad', 'frecuente'] },
  { node: 'vip_niveles', kw: ['niveles vip', 'que niveles', 'plata oro platino', 'categorias vip', 'niveles', 'plata', 'platino'] },
  { node: 'vip_subir', kw: ['subir de nivel', 'como subo de nivel', 'ascender de nivel', 'mejorar mi nivel', 'como califico', 'subir', 'ascender', 'calificar'] },
  { node: 'vip_ver', kw: ['ver mi nivel', 'cual es mi nivel', 'donde veo mi vip', 'verificar mi nivel', 'mi nivel actual', 'que nivel tengo'] },
];

const GREETINGS = ['hola', 'holaa', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos', 'que tal', 'hey', 'ola'];
const THANKS = ['gracias', 'muchas gracias', 'mil gracias', 'thank', 'ok gracias', 'perfecto gracias', 'excelente gracias'];

/** Frases de enganche que preceden a la respuesta (se sienten humanas). */
const LEADS = ['¡Claro! 👇', '¡Buena pregunta! 👇', 'Con gusto te ayudo 👇', 'Entiendo, mira 👇', '¡Por supuesto! 👇'];

/** ¿El texto contiene alguna de estas frases como token/subcadena? */
const hasAny = (qNorm, qTokens, list) =>
  list.some((w) => (w.includes(' ') ? qNorm.includes(w) : qTokens.includes(w)));

/** Puntúa una lista de keywords contra la pregunta normalizada. */
const scoreKeywords = (qNorm, qTokens, keywords) => {
  let score = 0;
  for (const kw of keywords) {
    if (kw.includes(' ')) {
      if (qNorm.includes(kw)) score += 3; // frase específica → peso alto
    } else if (qTokens.includes(kw)) {
      score += 2; // token exacto
    } else if (kw.length >= 5 && qNorm.includes(kw)) {
      score += 1; // coincidencia parcial (plurales, conjugaciones)
    }
  }
  return score;
};

/** Devuelve el id del mejor nodo del FAQ, o null si nada supera el umbral. */
const findBestMatch = (rawText) => {
  const qNorm = normalize(rawText);
  if (!qNorm) return null;
  const qTokens = qNorm.split(' ');
  let best = null;
  let bestScore = 0;
  for (const entry of KB) {
    const score = scoreKeywords(qNorm, qTokens, entry.kw);
    if (score > bestScore) {
      bestScore = score;
      best = entry.node;
    }
  }
  return bestScore >= 2 ? best : null; // umbral: al menos un token sólido
};

/* ══════════════════════════════════════════════════════════════════ */

const ICONS = {
  back: <ArrowLeft size={14} />,
  home: <Home size={14} />,
  wa: <span className="chat-wa-dot" />,
  default: <ChevronRight size={14} />,
};

const WELCOME = { type: 'bot', text: FLOW.root.text, node: 'root' };

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [currentNode, setCurrentNode] = useState('root');
  const [isTyping, setIsTyping] = useState(false);
  const [showInput, setShowInput] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const messagesEndRef = useRef(null);
  const chatWindowRef = useRef(null);

  // Número de WhatsApp oficial (panel admin). Con fallback interno del helper.
  useEffect(() => {
    getConfiguracion()
      .then((res) => setWhatsapp(res.data?.whatsapp_vendedor || ''))
      .catch(() => {});
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Click outside to close
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e) => {
      if (
        chatWindowRef.current &&
        !chatWindowRef.current.contains(e.target) &&
        !e.target.closest('.chat-fab')
      ) {
        setIsOpen(false);
      }
    };
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const goToNode = (nodeId, userLabel) => {
    const node = FLOW[nodeId];
    if (!node) return;

    // Mensaje del usuario (su selección)
    if (userLabel) {
      setMessages((prev) => [...prev, { type: 'user', text: userLabel }]);
    }

    // Typing indicator + respuesta del bot
    setIsTyping(true);
    setTimeout(() => {
      setMessages((prev) => [...prev, { type: 'bot', text: node.text, node: nodeId }]);
      setCurrentNode(nodeId);
      setIsTyping(false);
    }, 500);
  };

  const handleOptionClick = (option) => {
    if (option.whatsapp) {
      setMessages((prev) => [
        ...prev,
        { type: 'user', text: option.label },
        {
          type: 'bot',
          text: 'Te conecto con un agente por WhatsApp 👇',
          whatsappMsg: option.whatsappMsg || WHATSAPP_DEFAULT_MSG,
        },
      ]);
      return;
    }
    if (option.next) {
      goToNode(option.next, option.label);
    }
  };

  const handleReset = () => {
    setMessages([WELCOME]);
    setCurrentNode('root');
    setShowInput(false);
    setInputValue('');
  };

  const handleSendCustom = () => {
    const text = inputValue.trim();
    if (!text) return;

    // 1) Muestra la pregunta del usuario y limpia el input
    setMessages((prev) => [...prev, { type: 'user', text }]);
    setInputValue('');
    setShowInput(false);

    // 2) Interpreta lo escrito (saludo, agradecimiento o pregunta del FAQ)
    const qNorm = normalize(text);
    const qTokens = qNorm.split(' ');

    setIsTyping(true);
    setTimeout(() => {
      // Saludo → responde y reabre los temas
      if (hasAny(qNorm, qTokens, GREETINGS) && qTokens.length <= 4) {
        setMessages((prev) => [
          ...prev,
          { type: 'bot', text: '¡Hola! 👋 ¿Sobre qué tema necesitas ayuda? Puedes escribir tu pregunta o elegir una opción:', node: 'root' },
        ]);
        setCurrentNode('root');
        setIsTyping(false);
        return;
      }

      // Agradecimiento → cierre amable y reabre los temas
      if (hasAny(qNorm, qTokens, THANKS)) {
        setMessages((prev) => [
          ...prev,
          { type: 'bot', text: '¡De nada! 😊 ¿Hay algo más en lo que pueda ayudarte?', node: 'root' },
        ]);
        setCurrentNode('root');
        setIsTyping(false);
        return;
      }

      // Pregunta → busca la mejor respuesta del FAQ
      const match = findBestMatch(text);
      if (match) {
        const node = FLOW[match];
        const lead = LEADS[messages.length % LEADS.length];
        setMessages((prev) => [
          ...prev,
          { type: 'bot', text: `${lead}\n\n${node.text}`, node: match },
        ]);
        setCurrentNode(match);
      } else {
        // No entendió → ofrece temas + agente (sin fingir que sabe)
        setMessages((prev) => [
          ...prev,
          {
            type: 'bot',
            text: 'Mmm, no estoy seguro de haber entendido bien 🤔. Puedes reformular la pregunta, elegir uno de los temas de abajo, o hablar con un agente:',
            node: 'root',
            whatsappMsg: `Hola, tengo esta consulta: ${text}`,
          },
        ]);
        setCurrentNode('root');
      }
      setIsTyping(false);
    }, 600);
  };

  const openWhatsApp = (text) => {
    window.open(buildWhatsAppUrl(whatsapp, text), '_blank');
  };

  // Opciones del nodo actual (último mensaje del bot)
  const lastBotMsg = [...messages].reverse().find((m) => m.type === 'bot');
  const currentOptions = lastBotMsg?.node ? FLOW[lastBotMsg.node]?.options ?? [] : [];

  return (
    <>
      {/* Floating Button */}
      <button
        className={`chat-fab ${isOpen ? 'chat-fab-hidden' : ''}`}
        onClick={() => setIsOpen(true)}
        aria-label="Abrir chat de ayuda"
      >
        <div className="chat-fab-pulse" />
        <MessageCircle size={24} />
      </button>

      {/* Chat Window */}
      <div
        ref={chatWindowRef}
        className={`chat-window ${isOpen ? 'chat-window-open' : ''}`}
      >
        <div className="chat-header">
          <div className="chat-header-info">
            <div className="chat-avatar">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="chat-header-name">Asistente Aerorutas</div>
              <div className="chat-header-status">
                <span className="chat-status-dot" />
                En línea
              </div>
            </div>
          </div>
          <div className="chat-header-actions">
            <button className="chat-header-btn" onClick={handleReset} title="Reiniciar chat">
              <RotateCcw size={14} />
            </button>
            <button className="chat-header-btn" onClick={() => setIsOpen(false)} title="Cerrar">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-msg chat-msg-${msg.type}`}>
              {msg.type === 'bot' && (
                <div className="chat-msg-avatar">
                  <Bot size={14} />
                </div>
              )}
              <div className="chat-msg-bubble">
                {msg.text.split('\n').map((line, li) => (
                  <span key={li}>
                    {renderMarkdown(line)}
                    {li < msg.text.split('\n').length - 1 && <br />}
                  </span>
                ))}
                {msg.whatsappMsg && (
                  <button
                    className="chat-whatsapp-btn"
                    onClick={() => openWhatsApp(msg.whatsappMsg)}
                    style={{ marginTop: '0.5rem' }}
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                    </svg>
                    Abrir WhatsApp
                    <ExternalLink size={12} />
                  </button>
                )}
              </div>
              {msg.type === 'user' && (
                <div className="chat-msg-avatar chat-msg-avatar-user">
                  <User size={14} />
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="chat-msg chat-msg-bot">
              <div className="chat-msg-avatar">
                <Bot size={14} />
              </div>
              <div className="chat-msg-bubble chat-typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          {/* Botones de opciones del nodo actual */}
          {!isTyping && currentOptions.length > 0 && (
            <div className="chat-faqs">
              {currentOptions.map((opt, i) => (
                <button
                  key={`${currentNode}-${i}`}
                  className="chat-faq-btn"
                  onClick={() => handleOptionClick(opt)}
                >
                  {ICONS[opt.icon] || ICONS.default}
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Footer: o el input personalizado, o el botón para abrirlo */}
        <div className="chat-input-bar">
          {showInput ? (
            <>
              <input
                type="text"
                className="chat-input"
                placeholder="Escribe tu consulta…"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSendCustom();
                  if (e.key === 'Escape') {
                    setShowInput(false);
                    setInputValue('');
                  }
                }}
                autoFocus
              />
              <button
                className="chat-send-btn"
                onClick={handleSendCustom}
                disabled={!inputValue.trim()}
                title="Enviar a WhatsApp"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
              </button>
            </>
          ) : (
            <button
              className="chat-custom-question-btn"
              onClick={() => setShowInput(true)}
            >
              ¿No encontraste tu pregunta? Escríbela aquí
            </button>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Markdown mínimo: convierte **texto** en <strong>texto</strong> ── */
function renderMarkdown(line) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
