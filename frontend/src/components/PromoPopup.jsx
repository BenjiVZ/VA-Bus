import { useState, useEffect } from 'react';
import { X, Award, Star, Trophy, Gem, Gift, ChevronRight } from 'lucide-react';
import '../styles/PromoPopup.css';

const TIERS = [
  {
    name: 'Bronce',
    icon: Award,
    gradient: 'linear-gradient(135deg, #CD7F32, #A0522D)',
    labelColor: '#CD7F32',
    descuento: '5%',
    requisito: '5 viajes',
    beneficio: 'Descuento en todos tus pasajes',
  },
  {
    name: 'Plata',
    icon: Star,
    gradient: 'linear-gradient(135deg, #9CA3AF, #6B7280)',
    labelColor: '#9CA3AF',
    descuento: '10%',
    requisito: '15 viajes',
    beneficio: 'Prioridad en selección de asientos',
  },
  {
    name: 'Oro',
    icon: Trophy,
    gradient: 'linear-gradient(135deg, #F59E0B, #D97706)',
    labelColor: '#F59E0B',
    descuento: '15%',
    requisito: '30 viajes',
    beneficio: '1 viaje gratis cada 10 viajes',
  },
  {
    name: 'Diamante',
    icon: Gem,
    gradient: 'linear-gradient(135deg, #8B5CF6, #6D28D9)',
    labelColor: '#A78BFA',
    descuento: '20%',
    requisito: '50 viajes',
    beneficio: '1 viaje gratis cada 5 viajes',
  },
];

export default function PromoPopup() {
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    const shown = sessionStorage.getItem('promo_shown');
    if (shown) return;
    const timer = setTimeout(() => setVisible(true), 1200);
    return () => clearTimeout(timer);
  }, []);

  const handleClose = () => {
    setClosing(true);
    sessionStorage.setItem('promo_shown', '1');
    setTimeout(() => { setVisible(false); setClosing(false); }, 300);
  };

  if (!visible) return null;

  return (
    <div className={`promo-overlay ${closing ? 'promo-closing' : ''}`} onClick={handleClose}>
      <div className={`promo-popup ${closing ? 'promo-popup-closing' : ''}`} onClick={(e) => e.stopPropagation()}>

        {/* Close */}
        <button className="promo-close" onClick={handleClose}>
          <X size={18} />
        </button>

        {/* Header */}
        <div className="promo-header">
          <div className="promo-bg-decor" />
          <span className="promo-label">✨ PROGRAMA DE LEALTAD</span>
          <h2 className="promo-title">Pasajero Frecuente</h2>
          <p className="promo-subtitle">
            Viaja con nosotros, sube de nivel y desbloquea descuentos exclusivos.
          </p>
        </div>

        {/* Tiers */}
        <div className="promo-tiers">
          {TIERS.map((tier, i) => {
            const Icon = tier.icon;
            return (
              <div key={tier.name} className="promo-tier-card">
                <div className="promo-tier-icon" style={{ background: tier.gradient }}>
                  <Icon size={18} color="#fff" strokeWidth={2.2} />
                </div>
                <div className="promo-tier-body">
                  <span className="promo-tier-name" style={{ color: tier.labelColor }}>{tier.name}</span>
                  <span className="promo-tier-benefit">{tier.beneficio}</span>
                </div>
                <div className="promo-tier-right">
                  <span className="promo-tier-pct">{tier.descuento}</span>
                  <span className="promo-tier-req">{tier.requisito}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Free trip */}
        <div className="promo-free-trip">
          <Gift size={18} />
          <span>¡Acumula viajes y obtén <strong>viajes GRATIS</strong>! Tu fidelidad tiene recompensa.</span>
        </div>

        {/* CTA */}
        <button className="promo-cta" onClick={handleClose}>
          ¡Entendido, quiero viajar!
        </button>
      </div>
    </div>
  );
}
