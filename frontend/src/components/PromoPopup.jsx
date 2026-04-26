import { useState, useEffect } from 'react';
import { X, Award, Star, Trophy, Gem, Gift, ChevronRight, Sparkles } from 'lucide-react';
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

/**
 * PromoPopup – 3 modes:
 *  1. "popup"  → initial auto-popup on first visit
 *  2. "banner" → after popup is closed, a horizontal banner stays on the page
 *  3. "modal"  → clicking the banner re-opens the full info as a floating window
 */
export default function PromoPopup() {
  const [mode, setMode] = useState('hidden'); // hidden | popup | banner | modal
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    const shown = sessionStorage.getItem('promo_shown');
    if (shown) {
      // Already seen popup → show banner directly
      setMode('banner');
      return;
    }
    const timer = setTimeout(() => setMode('popup'), 1200);
    return () => clearTimeout(timer);
  }, []);

  const handleClosePopup = () => {
    setClosing(true);
    sessionStorage.setItem('promo_shown', '1');
    setTimeout(() => {
      setMode('banner');
      setClosing(false);
    }, 300);
  };

  const handleOpenModal = () => {
    setMode('modal');
  };

  const handleCloseModal = () => {
    setClosing(true);
    setTimeout(() => {
      setMode('banner');
      setClosing(false);
    }, 300);
  };

  /* ── Popup Content (shared between popup & modal) ── */
  const PromoContent = ({ onClose, isModal }) => (
    <div className={`promo-popup ${closing ? 'promo-popup-closing' : ''}`} onClick={(e) => e.stopPropagation()}>
      <button className="promo-close" onClick={onClose}>
        <X size={18} />
      </button>

      <div className="promo-header">
        <div className="promo-bg-decor" />
        <span className="promo-label">✨ PROGRAMA DE LEALTAD</span>
        <h2 className="promo-title">Pasajero Frecuente</h2>
        <p className="promo-subtitle">
          Viaja con nosotros, sube de nivel y desbloquea descuentos exclusivos.
        </p>
      </div>

      <div className="promo-tiers">
        {TIERS.map((tier) => {
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

      <div className="promo-free-trip">
        <Gift size={18} />
        <span>¡Acumula viajes y obtén <strong>viajes GRATIS</strong>! Tu fidelidad tiene recompensa.</span>
      </div>

      <button className="promo-cta" onClick={onClose}>
        {isModal ? 'Cerrar' : '¡Entendido, quiero viajar!'}
      </button>
    </div>
  );

  return (
    <>
      {/* ── Initial Popup ── */}
      {mode === 'popup' && (
        <div className={`promo-overlay ${closing ? 'promo-closing' : ''}`} onClick={handleClosePopup}>
          <PromoContent onClose={handleClosePopup} isModal={false} />
        </div>
      )}

      {/* ── Banner (after popup is closed) ── */}
      {mode === 'banner' && (
        <div className="promo-banner" onClick={handleOpenModal}>
          <div className="promo-banner-inner">
            <div className="promo-banner-left">
              <div className="promo-banner-icon-group">
                <div className="promo-banner-icon promo-banner-icon-1">
                  <Award size={20} color="#CD7F32" />
                </div>
                <div className="promo-banner-icon promo-banner-icon-2">
                  <Star size={20} color="#9CA3AF" />
                </div>
                <div className="promo-banner-icon promo-banner-icon-3">
                  <Trophy size={20} color="#F59E0B" />
                </div>
                <div className="promo-banner-icon promo-banner-icon-4">
                  <Gem size={20} color="#8B5CF6" />
                </div>
              </div>
              <div className="promo-banner-text">
                <strong>Programa Pasajero Frecuente</strong>
                <span>Acumula viajes y desbloquea hasta <em>20% de descuento</em> + viajes gratis</span>
              </div>
            </div>
            <button className="promo-banner-btn">
              <Sparkles size={14} />
              Más información
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ── Modal (re-open from banner) ── */}
      {mode === 'modal' && (
        <div className={`promo-overlay ${closing ? 'promo-closing' : ''}`} onClick={handleCloseModal}>
          <PromoContent onClose={handleCloseModal} isModal={true} />
        </div>
      )}
    </>
  );
}
