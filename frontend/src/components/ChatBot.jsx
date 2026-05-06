import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, Bot, User, ExternalLink, ChevronRight, Sparkles, RotateCcw } from 'lucide-react';
import '../styles/ChatBot.css';

/* ══════════════════════════════════════════════
   Knowledge base – preguntas y respuestas
   ══════════════════════════════════════════════ */
const FAQ_DATA = [
  {
    question: '¿Cómo reservo un pasaje?',
    keywords: ['reservo', 'reservar', 'comprar', 'pasaje', 'boleto', 'compro', 'sacar', 'ticket'],
    answer: 'Es muy fácil: 1️⃣ Busca tu viaje por origen, destino y fecha. 2️⃣ Selecciona tu asiento en el mapa. 3️⃣ Confirma tu reserva y coordina el pago por WhatsApp. ¡Listo!',
    followUp: '¿Te gustaría saber sobre los métodos de pago o los documentos necesarios?',
  },
  {
    question: '¿Qué métodos de pago aceptan?',
    keywords: ['pago', 'pagar', 'transferencia', 'movil', 'efectivo', 'zelle', 'binance', 'zinli', 'divisa', 'dolar', 'bolivar', 'banco', 'metodo'],
    answer: 'Aceptamos varios métodos:\n\n💳 Transferencia bancaria\n📱 Pago móvil\n💵 Efectivo en divisas\n🔗 Zelle, Binance y Zinli\n\nUna vez que reserves, podrás seleccionar tu método preferido y subir el comprobante desde la página de pago.',
  },
  {
    question: '¿Puedo cancelar mi reserva?',
    keywords: ['cancelar', 'cancelacion', 'devolver', 'reembolso', 'anular', 'devolucion'],
    answer: 'Sí, puedes cancelar tu reserva desde la sección "Mis Reservas" en tu perfil. Ten en cuenta que las cancelaciones están sujetas a las políticas de la empresa según la proximidad de la fecha de viaje.',
  },
  {
    question: '¿Qué documentos necesito para viajar?',
    keywords: ['documento', 'cedula', 'identidad', 'papeles', 'requisito', 'necesito', 'llevar', 'partida', 'nacimiento'],
    answer: 'Los documentos dependen de tu situación:\n\n🪪 Adultos: Cédula de identidad vigente\n👶 Menores: Partida de nacimiento + cédula del representante + foto del menor\n🐾 Mascotas: Tarjeta de vacunación vigente\n♿ Discapacidad: Certificado o documento que lo acredite',
  },
  {
    question: '¿Puedo viajar con mascotas?',
    keywords: ['mascota', 'perro', 'gato', 'animal', 'mascota', 'vacunacion', 'veterinario'],
    answer: '¡Sí! 🐾 Aceptamos mascotas a bordo. Solo necesitas:\n\n✅ Tarjeta de vacunación vigente\n✅ Seleccionar la opción "Viaja con animal" al reservar\n✅ Indicar el tipo de mascota\n\nAceptamos perros, gatos, aves, conejos, hámsters y otros.',
  },
  {
    question: '¿Qué es el programa VIP?',
    keywords: ['vip', 'frecuente', 'descuento', 'programa', 'lealtad', 'plata', 'oro', 'platino', 'beneficio'],
    answer: 'Nuestro programa de Pasajero Frecuente tiene 3 niveles:\n\n🥈 Plata — Beneficios básicos\n🥇 Oro — Beneficios premium\n💎 Platino — Máximos beneficios\n\nMientras más viajes con nosotros, ¡mejores serán tus ventajas!',
  },
  {
    question: '¿Cuáles son los horarios de salida?',
    keywords: ['horario', 'hora', 'salida', 'cuando', 'sale', 'viaje', 'disponible', 'proximo'],
    answer: 'Los horarios varían según la ruta. Puedes consultar todos los viajes disponibles en nuestra sección de "Viajes" 🚍\n\nAhí podrás filtrar por origen, destino y fecha para encontrar el horario que mejor te convenga.',
  },
  {
    question: '¿Cuánto cuesta el pasaje?',
    keywords: ['precio', 'cuesta', 'costo', 'cuanto', 'tarifa', 'vale'],
    answer: 'Los precios varían según la ruta y se muestran en dólares (USD). Al buscar viajes verás el precio por asiento junto con su equivalente en bolívares según la tasa BCV del día.\n\n💡 Puedes ver los precios actualizados en la sección de Viajes.',
  },
  {
    question: '¿Cómo verifico mi ticket?',
    keywords: ['verificar', 'ticket', 'codigo', 'qr', 'boleto', 'validar', 'comprobar'],
    answer: 'Tu ticket digital incluye un código QR y un código único de 8 caracteres. Puedes verificarlo de dos formas:\n\n📱 Escaneando el QR desde la app\n🔗 Ingresando el código en la sección de verificación\n\nAccede a tus tickets desde "Mis Reservas".',
  },
  {
    question: '¿Cómo creo mi cuenta?',
    keywords: ['registrar', 'cuenta', 'crear', 'registro', 'inscribir', 'google', 'login', 'iniciar', 'sesion'],
    answer: 'Puedes crear tu cuenta de dos formas:\n\n1️⃣ Con email y contraseña — recibirás un código de verificación\n2️⃣ Con Google — inicio rápido con un solo clic\n\nUna vez registrado, completa tu perfil con tu cédula para poder reservar.',
  },
  {
    question: '¿Puedo reservar para otra persona?',
    keywords: ['otra persona', 'asignar', 'alguien', 'amigo', 'familiar', 'otro', 'tercero', 'nombre'],
    answer: 'Sí, al seleccionar un asiento puedes activar la opción "Asignar a otra persona" ✅\n\nSolo necesitas ingresar el nombre y cédula de la persona que viajará. Tú seguirás siendo el comprador responsable del pago.',
  },
  {
    question: '¿Qué rutas tienen disponibles?',
    keywords: ['ruta', 'destino', 'origen', 'donde', 'ciudad', 'viajan', 'van', 'recorrido'],
    answer: 'Puedes ver todas nuestras rutas disponibles en la sección de "Viajes". Ofrecemos viajes de ida y de ida y vuelta entre varias ciudades de Venezuela 🇻🇪\n\nFiltra por tu ciudad de origen y destino para ver las opciones.',
  },
];

/* ── Respuestas para cuando no entiende ── */
const FALLBACK_RESPONSES = [
  'Hmm, no estoy seguro de entender tu pregunta. ¿Podrías reformularla? También puedes elegir una de las preguntas frecuentes que te muestro abajo. 👇',
  'No encontré una respuesta exacta para eso. ¿Quizás te refieres a alguno de estos temas?',
  'Esa pregunta me queda un poco difícil 😅 Prueba a preguntarme sobre reservas, pagos, documentos o rutas.',
];

/* ── Respuestas conversacionales ── */
const CONVERSATIONAL = {
  greeting: {
    patterns: ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'que tal', 'saludos', 'hi', 'hello'],
    responses: [
      '¡Hola! 👋 ¿En qué puedo ayudarte hoy? Puedes preguntarme sobre viajes, reservas, pagos y más.',
      '¡Buenas! 😊 Soy el asistente de Aerorutas. ¿Qué necesitas saber?',
      '¡Hola! Bienvenido/a. Estoy aquí para ayudarte con cualquier duda sobre nuestros viajes. 🚍',
    ],
  },
  thanks: {
    patterns: ['gracias', 'gracia', 'thank', 'genial', 'excelente', 'perfecto', 'entendido', 'vale', 'ok', 'listo'],
    responses: [
      '¡De nada! 😊 Si tienes alguna otra pregunta, aquí estoy.',
      '¡Con gusto! No dudes en preguntar si necesitas algo más. 🙌',
      '¡Para eso estamos! ¿Hay algo más en lo que pueda ayudarte?',
    ],
  },
  goodbye: {
    patterns: ['adios', 'chao', 'bye', 'hasta luego', 'nos vemos', 'me voy'],
    responses: [
      '¡Hasta luego! 👋 Que tengas un excelente viaje. ¡Nos vemos a bordo!',
      '¡Chao! 🚍 Recuerda que siempre puedes volver a escribirme. ¡Buen viaje!',
    ],
  },
  help: {
    patterns: ['ayuda', 'ayudar', 'help', 'necesito', 'como funciona', 'que puedo hacer'],
    responses: [
      'Puedo ayudarte con:\n\n🎟️ Reservar pasajes\n💳 Métodos de pago\n📄 Documentos necesarios\n🐾 Viajar con mascotas\n⭐ Programa VIP\n🕐 Horarios y rutas\n\n¿Sobre cuál te gustaría saber?',
    ],
  },
};

const WELCOME_MESSAGE = {
  type: 'bot',
  text: '¡Hola! 👋 Soy el asistente virtual de Aerorutas. ¿En qué puedo ayudarte hoy?',
};

/* ══════════════════════════════════════════════
   Componente ChatBot
   ══════════════════════════════════════════════ */
export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showFaqs, setShowFaqs] = useState(true);
  const [fallbackCount, setFallbackCount] = useState(0);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const chatWindowRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // ── Click outside to close ──
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

    // Small delay so the opening click doesn't immediately close
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const addBotMessage = (text, delay = 700) => {
    setIsTyping(true);
    setTimeout(() => {
      setMessages((prev) => [...prev, { type: 'bot', text }]);
      setIsTyping(false);
    }, delay);
  };

  const addBotMessages = (texts, baseDelay = 700) => {
    setIsTyping(true);
    texts.forEach((text, i) => {
      setTimeout(() => {
        setMessages((prev) => [...prev, { type: 'bot', text }]);
        if (i === texts.length - 1) setIsTyping(false);
      }, baseDelay + i * 900);
    });
  };

  const pickRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];

  const handleFaqClick = (faq) => {
    setShowFaqs(false);
    setFallbackCount(0);
    setMessages((prev) => [...prev, { type: 'user', text: faq.question }]);

    const replies = [faq.answer];
    if (faq.followUp) replies.push(faq.followUp);
    addBotMessages(replies);
  };

  const findMatch = useCallback((text) => {
    const lower = text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    // Check conversational patterns first
    for (const [, conv] of Object.entries(CONVERSATIONAL)) {
      if (conv.patterns.some((p) => lower.includes(p))) {
        return { type: 'conversational', response: pickRandom(conv.responses) };
      }
    }

    // Score-based FAQ matching
    let bestMatch = null;
    let bestScore = 0;

    for (const faq of FAQ_DATA) {
      let score = 0;
      for (const kw of faq.keywords) {
        if (lower.includes(kw.toLowerCase())) {
          score += kw.length; // longer keyword matches = higher score
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestMatch = faq;
      }
    }

    if (bestMatch && bestScore >= 4) {
      return { type: 'faq', faq: bestMatch };
    }

    return null;
  }, []);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { type: 'user', text }]);
    setInputValue('');
    setShowFaqs(false);

    const match = findMatch(text);

    if (match?.type === 'conversational') {
      addBotMessage(match.response);
      setFallbackCount(0);
    } else if (match?.type === 'faq') {
      const replies = [match.faq.answer];
      if (match.faq.followUp) replies.push(match.faq.followUp);
      addBotMessages(replies);
      setFallbackCount(0);
    } else {
      // Fallback — show helpful response
      const newCount = fallbackCount + 1;
      setFallbackCount(newCount);

      if (newCount >= 3) {
        // After 3 misses, suggest WhatsApp
        addBotMessages([
          'Parece que no estoy logrando ayudarte con esta consulta. 😔 Te recomiendo contactar a nuestro equipo directamente:',
          '__WHATSAPP_CTA__',
        ]);
        setFallbackCount(0);
      } else {
        const fallbackMsg = FALLBACK_RESPONSES[newCount - 1] || FALLBACK_RESPONSES[0];
        addBotMessage(fallbackMsg, 800);
        // Re-show FAQ suggestions after a fallback
        setTimeout(() => setShowFaqs(true), 1200);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleWhatsApp = () => {
    window.open('https://wa.me/584121234567?text=Hola,%20tengo%20una%20consulta%20sobre%20mis%20viajes', '_blank');
  };

  const handleReset = () => {
    setMessages([WELCOME_MESSAGE]);
    setShowFaqs(true);
    setInputValue('');
    setFallbackCount(0);
  };

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
        {/* Header */}
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
                {msg.text === '__WHATSAPP_CTA__' ? (
                  <button className="chat-whatsapp-btn" onClick={handleWhatsApp}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                    </svg>
                    Contactar por WhatsApp
                    <ExternalLink size={12} />
                  </button>
                ) : (
                  msg.text.split('\n').map((line, li) => (
                    <span key={li}>
                      {line}
                      {li < msg.text.split('\n').length - 1 && <br />}
                    </span>
                  ))
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

          {/* FAQ Suggestions */}
          {showFaqs && (
            <div className="chat-faqs">
              <p className="chat-faqs-label">Preguntas frecuentes:</p>
              {FAQ_DATA.slice(0, 6).map((faq, i) => (
                <button key={i} className="chat-faq-btn" onClick={() => handleFaqClick(faq)}>
                  <ChevronRight size={14} />
                  {faq.question}
                </button>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-bar">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Escribe tu pregunta..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim()}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </>
  );
}
