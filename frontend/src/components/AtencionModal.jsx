import { useState, useEffect } from 'react';
import { AlertTriangle, X, ChevronDown, ShieldCheck, FileText, Baby, Globe, CreditCard } from 'lucide-react';

export default function AtencionModal({ visible, onAccept, onClose, viajeInfo }) {
  const [accepted, setAccepted] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    if (visible) {
      setAccepted(false);
      // Trigger entrance animation
      requestAnimationFrame(() => setAnimateIn(true));
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      setAnimateIn(false);
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [visible]);

  if (!visible) return null;

  return (
    <div className={`atencion-overlay ${animateIn ? 'atencion-overlay-visible' : ''}`} onClick={onClose}>
      <div className={`atencion-modal ${animateIn ? 'atencion-modal-visible' : ''}`} onClick={(e) => e.stopPropagation()}>

        {/* Close button */}
        <button className="atencion-close" onClick={onClose} aria-label="Cerrar">
          <X size={20} />
        </button>

        {/* Header with route info */}
        <div className="atencion-header">
          <div className="atencion-route">
            {viajeInfo && (
              <>
                <div className="atencion-route-points">
                  <div className="atencion-route-point">
                    <div className="atencion-route-dot" />
                    <span>{viajeInfo.origen}</span>
                  </div>
                  <div className="atencion-route-line" />
                  <div className="atencion-route-point">
                    <div className="atencion-route-dot atencion-route-dot-end" />
                    <span>{viajeInfo.destino}</span>
                  </div>
                </div>
                <div className="atencion-route-meta">
                  <span>📅 {new Date(viajeInfo.fecha + 'T00:00:00').toLocaleDateString('es-VE', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                  <span>🎟️ {viajeInfo.cantidad} {viajeInfo.cantidad === 1 ? 'Boleto' : 'Boletos'}</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Floating exclamation icon */}
        <div className="atencion-icon-float">
          <div className="atencion-icon-circle">
            <span>!</span>
          </div>
        </div>

        {/* Body */}
        <div className="atencion-body">
          <h2 className="atencion-title">¡Atencion!</h2>
          <p className="atencion-subtitle">
            Todos los pasajeros deben presentarse <strong>al menos 1 hora antes</strong> del viaje por taquilla con:
          </p>

          <div className="atencion-requirements">
            <div className="atencion-req-item">
              <div className="atencion-req-icon">
                <ShieldCheck size={18} />
              </div>
              <div>
                <strong>Venezolano:</strong>
                <p>- Cedula de identidad original o pasaporte.</p>
              </div>
            </div>

            <div className="atencion-req-item">
              <div className="atencion-req-icon atencion-req-icon-baby">
                <Baby size={18} />
              </div>
              <div>
                <strong>Menores de edad:</strong>
                <p>- Documentacion y permisos de viaje del CPNNA.</p>
              </div>
            </div>

            <div className="atencion-req-item">
              <div className="atencion-req-icon atencion-req-icon-globe">
                <Globe size={18} />
              </div>
              <div>
                <strong>Extranjero:</strong>
                <p>- Pasaporte sellado con entrada al pais y vigencia de 90 dias.</p>
              </div>
            </div>
          </div>

          {/* Important box */}
          <div className="atencion-important">
            <div className="atencion-important-title">
              <AlertTriangle size={16} />
              ¡Importante!
            </div>
            <ul>
              <li>La tasa de salida no esta incluida en el costo del boleto. El costo de este pago dependera del terminal de salida.</li>
              <li>Los boletos de tercera edad pueden tener un recargo adicional.</li>
              <li>Una vez confirmada la compra, los cambios estan sujetos a disponibilidad.</li>
            </ul>
          </div>

          {/* Terms link */}
          <button className="atencion-terms-link">
            <FileText size={14} />
            Condiciones de transporte
            <ChevronDown size={14} />
          </button>

          {/* Checkbox */}
          <label className="atencion-checkbox">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
            />
            <span className="atencion-checkmark" />
            <span>He leido y acepto los terminos y condiciones de transporte de <strong>Aerorutas de Venezuela</strong></span>
          </label>

          {/* CTA */}
          <button
            className={`atencion-cta ${accepted ? 'atencion-cta-active' : ''}`}
            disabled={!accepted}
            onClick={onAccept}
          >
            <CreditCard size={18} />
            Continuar con la Reserva
          </button>
        </div>
      </div>
    </div>
  );
}
