import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, ExternalLink, ChevronRight, Sparkles } from 'lucide-react';
import '../styles/ChatBot.css';

const FAQ_DATA = [
  {
    question: '¿Cómo reservo un pasaje?',
    answer: 'Es muy fácil: 1️⃣ Busca tu viaje por origen, destino y fecha. 2️⃣ Selecciona tu asiento en el mapa. 3️⃣ Confirma tu reserva y coordina el pago por WhatsApp. ¡Listo!'
  },
  {
    question: '¿Qué métodos de pago aceptan?',
    answer: 'Aceptamos transferencia bancaria, pago móvil y efectivo. Una vez que reserves, coordinas el pago directamente con nuestro equipo de ventas por WhatsApp.'
  },
  {
    question: '¿Puedo cancelar mi reserva?',
    answer: 'Sí, puedes cancelar tu reserva desde la sección "Mis Reservas". Ten en cuenta que las cancelaciones están sujetas a las políticas de la empresa según la proximidad de la fecha de viaje.'
  },
  {
    question: '¿Qué documentos necesito para viajar?',
    answer: 'Necesitas tu cédula de identidad vigente. Si viajas con menores de edad, debes llevar la partida de nacimiento y cédula del representante. Para mascotas, necesitas la tarjeta de vacunación.'
  },
  {
    question: '¿Puedo viajar con mascotas?',
    answer: 'Sí, aceptamos mascotas (perros, gatos y otros). Debes presentar la tarjeta de vacunación vigente al momento del abordaje. La unidad no se hace responsable si no presentas la documentación.'
  },
  {
    question: '¿Qué es el programa de Pasajero Frecuente?',
    answer: 'Es nuestro programa de lealtad con 4 niveles: Bronce (5%), Plata (10%), Oro (15%) y Diamante (20% de descuento). Mientras más viajes, mejores beneficios y hasta viajes gratis.'
  },
];

const WELCOME_MESSAGE = {
  type: 'bot',
  text: '¡Hola! 👋 Soy el asistente virtual de Aerorutas. ¿En qué puedo ayudarte hoy?',
};

export default function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showFaqs, setShowFaqs] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const addBotMessage = (text, delay = 800) => {
    setIsTyping(true);
    setTimeout(() => {
      setMessages((prev) => [...prev, { type: 'bot', text }]);
      setIsTyping(false);
    }, delay);
  };

  const handleFaqClick = (faq) => {
    setShowFaqs(false);
    setMessages((prev) => [...prev, { type: 'user', text: faq.question }]);
    addBotMessage(faq.answer);
  };

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { type: 'user', text }]);
    setInputValue('');
    setShowFaqs(false);

    // Check if it matches any FAQ keyword
    const matched = FAQ_DATA.find((faq) => {
      const keywords = faq.question.toLowerCase().split(' ').filter(w => w.length > 3);
      return keywords.some((kw) => text.toLowerCase().includes(kw));
    });

    if (matched) {
      addBotMessage(matched.answer);
    } else {
      addBotMessage(
        'Entiendo tu consulta. Para brindarte una mejor atención personalizada, te recomiendo contactar a nuestro equipo por WhatsApp. Ellos podrán ayudarte con más detalle. 😊',
        1000
      );
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { type: 'bot', text: '__WHATSAPP_CTA__' },
        ]);
      }, 2000);
    }
  };

  const handleKeyPress = (e) => {
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
      <div className={`chat-window ${isOpen ? 'chat-window-open' : ''}`}>
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
              ↻
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
                  msg.text
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
              {FAQ_DATA.map((faq, i) => (
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
            onKeyPress={handleKeyPress}
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
