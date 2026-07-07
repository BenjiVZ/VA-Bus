import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAerorutasOficinas, getStats, getConfiguracion } from '../services/api';
import { buildWhatsAppUrl } from '../utils/whatsapp';
import {
  Search, Armchair, MessageCircle, CheckCircle, MapPin, Calendar,
  ShieldCheck, Clock, Users, Star, Bus, Route, CreditCard,
  ChevronRight, Phone, Mail, ArrowRight, Zap, Award, Heart,
  MapPinned, Headphones, Wifi, Umbrella,
} from 'lucide-react';
import FleetGallery from '../components/FleetGallery';
import PromoPopup from '../components/PromoPopup';
import Flatpickr from "react-flatpickr";
import "flatpickr/dist/themes/material_blue.css";
import { Spanish } from "flatpickr/dist/l10n/es.js";
import '../styles/FleetGallery.css';

const HERO_IMAGES = [
  '/flota/bus-01.jpg',
  '/flota/bus-04.jpg',
  '/flota/bus-08.jpg',
  '/flota/bus-14.jpg',
  '/flota/bus-18.jpg',
];

/* ── Animated counter hook ── */
function useCounter(target, duration = 2000, enabled = true) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const started = useRef(false);
  const prevTarget = useRef(target);

  // Reset animation flag when target changes (e.g., API data arrived)
  useEffect(() => {
    if (prevTarget.current !== target) {
      started.current = false;
      prevTarget.current = target;
    }
  }, [target]);

  useEffect(() => {
    if (!enabled || target === 0) return;

    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const start = performance.now();
          const step = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const value = eased * target;
            setCount(Number.isInteger(target) ? Math.floor(value) : Math.round(value * 10) / 10);
            if (progress < 1) requestAnimationFrame(step);
          };
          requestAnimationFrame(step);
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration, enabled]);

  return { count, ref };
}

export default function HomePage() {
  const navigate = useNavigate();
  // Oficinas reales de Aerorutas (mismo origen que la página de Viajes).
  const [oficinas, setOficinas] = useState([]);
  const [origen, setOrigen] = useState('');   // guarda el codofi, no el nombre
  const [destino, setDestino] = useState('');
  const [fecha, setFecha] = useState('');

  const flatpickrOptions = useMemo(() => ({
    locale: Spanish,
    dateFormat: "Y-m-d",
    minDate: "today",
    disableMobile: true,
    static: false,
    onOpen: () => {
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.width = '100%';
      document.body.style.top = `-${window.scrollY}px`;
      document.body.dataset.scrollY = window.scrollY;
    },
    onClose: () => {
      const scrollY = document.body.dataset.scrollY || '0';
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.width = '';
      document.body.style.top = '';
      window.scrollTo(0, parseInt(scrollY));
    },
  }), []);
  const [heroIdx, setHeroIdx] = useState(0);
  const [dbStats, setDbStats] = useState({ rutas: 0, buses: 0, pasajeros: 0 });
  const [promoShown, setPromoShown] = useState(() => !!sessionStorage.getItem('promo_shown'));
  const [whatsapp, setWhatsapp] = useState('');

  useEffect(() => {
    getAerorutasOficinas()
      .then((res) => setOficinas(res.data || []))
      .catch(() => {});
    getStats()
      .then((res) => setDbStats(res.data))
      .catch(() => {});
    getConfiguracion()
      .then((res) => setWhatsapp(res.data?.whatsapp_vendedor || ''))
      .catch(() => {});
  }, []);

  // Hero background slideshow
  useEffect(() => {
    const timer = setInterval(() => {
      setHeroIdx((prev) => (prev + 1) % HERO_IMAGES.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  // Destino: todas las oficinas menos la elegida como origen.
  const oficinasDestino = useMemo(
    () => oficinas.filter((o) => o.codofi !== origen),
    [oficinas, origen]
  );

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (origen) params.set('origen', origen);
    if (destino) params.set('destino', destino);
    if (fecha) params.set('fecha', fecha);
    navigate(`/viajes?${params.toString()}`);
  };

  const steps = [
    { Icon: Search, title: 'Busca tu viaje', desc: 'Selecciona origen, destino y fecha para encontrar tu ruta ideal', color: '#3b82f6' },
    { Icon: Armchair, title: 'Elige tu asiento', desc: 'Visualiza el mapa interactivo del autobús y escoge tu lugar', color: '#8b5cf6' },
    { Icon: CreditCard, title: 'Paga fácilmente', desc: 'Transferencia, pago móvil o Zelle — tú eliges cómo pagar', color: '#22c55e' },
    { Icon: CheckCircle, title: '¡Viaja tranquilo!', desc: 'Recibe tu boleto con QR al email y preséntalo al abordar', color: '#f59e0b' },
  ];

  const trustItems = [
    { Icon: ShieldCheck, text: 'Reserva segura' },
    { Icon: Clock, text: 'Confirmación al instante' },
    { Icon: Users, text: '+1,000 pasajeros confían' },
    { Icon: Star, text: 'Flota moderna' },
  ];

  const features = [
    { Icon: Wifi, title: 'Wi-Fi a bordo', desc: 'Conectado durante todo tu viaje' },
    { Icon: Armchair, title: 'Asientos reclinables', desc: 'Comodidad premium garantizada' },
    { Icon: ShieldCheck, title: 'Seguro de viajero', desc: 'Tu seguridad es lo primero' },
    { Icon: Headphones, title: 'Entretenimiento', desc: 'Pantallas individuales' },
    { Icon: Zap, title: 'Cargadores USB', desc: 'Mantén tus dispositivos cargados' },
    { Icon: Award, title: 'Servicio VIP', desc: 'Atención premium para ti' },
  ];

  const stats = [
    { target: (dbStats.pasajeros || 0) + 15000, label: 'Pasajeros transportados', suffix: '+' },
    { target: dbStats.rutas || 0, label: 'Rutas nacionales', suffix: '' },
    { target: dbStats.buses || 0, label: 'Autobuses operativos', suffix: '' },
    { target: 99.5, label: 'Satisfacción', suffix: '%' },
  ];

  const popularRoutes = [
    { from: 'Caracas', to: 'Maracaibo', time: '~12h', price: 'desde $25' },
    { from: 'Caracas', to: 'Barquisimeto', time: '~5h', price: 'desde $18' },
    { from: 'Valencia', to: 'Mérida', time: '~10h', price: 'desde $22' },
    { from: 'Maracay', to: 'Puerto La Cruz', time: '~6h', price: 'desde $20' },
  ];

  return (
    <div className="page page-home">
      {/* ── HERO SECTION ── */}
      <section className="hero">
        {/* Background Images */}
        <div className="hero-slideshow">
          {HERO_IMAGES.map((src, i) => (
            <div
              key={src}
              className={`hero-slide ${i === heroIdx ? 'hero-slide-active' : ''}`}
              style={{ backgroundImage: `url(${src})` }}
            />
          ))}
          <div className="hero-overlay" />
        </div>

        {/* Animated floating particles */}
        <div className="hero-particles">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="hero-particle" style={{
              '--delay': `${i * 0.8}s`,
              '--x': `${10 + i * 15}%`,
              '--size': `${3 + (i % 3) * 2}px`,
            }} />
          ))}
        </div>

        <div className="hero-content">
          <span className="hero-badge">
            <Zap size={13} />
            La mejor forma de viajar por Venezuela
          </span>
          <h1 className="hero-title">
            VIAJA CON <span className="hero-brand">AERORUTAS</span>
          </h1>
          <p className="hero-desc">
            Reserva tu puesto de autobús de forma rápida y segura.
            Las mejores rutas nacionales a los mejores precios.
          </p>

          {/* Trust badges */}
          <div className="hero-trust">
            {trustItems.map((item, i) => (
              <div key={i} className="hero-trust-item">
                <item.Icon size={16} />
                <span>{item.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Search form card */}
        <div className="container">
          <form className="search-form" onSubmit={handleSearch}>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <MapPin size={14} /> Origen
              </label>
              <select
                className="form-control"
                value={origen}
                onChange={(e) => {
                  setOrigen(e.target.value);
                  if (e.target.value === destino) setDestino('');
                }}
              >
                <option value="">Todas las ciudades</option>
                {oficinas.map((o) => (
                  <option key={o.codofi} value={o.codofi}>{o.desofi}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <MapPinned size={14} /> Destino
              </label>
              <select
                className="form-control"
                value={destino}
                onChange={(e) => setDestino(e.target.value)}
              >
                <option value="">Todas las ciudades</option>
                {oficinasDestino.map((o) => (
                  <option key={o.codofi} value={o.codofi}>{o.desofi}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <Calendar size={14} /> Fecha
              </label>
              <Flatpickr
                className="form-control"
                value={fecha}
                onChange={(dates, dateStr) => setFecha(dateStr)}
                options={flatpickrOptions}
                placeholder="Seleccionar fecha"
              />
            </div>

            <button type="submit" className="btn btn-primary btn-lg search-btn">
              <Search size={18} />
              Buscar viajes
            </button>
          </form>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <section className="stats-section">
        <div className="container">
          <div className="stats-grid">
            {stats.map((stat, i) => {
              const { count, ref } = useCounter(stat.target, 2000, promoShown);
              return (
                <div key={i} className="stat-item" ref={ref}>
                  <span className="stat-number">{count}{stat.suffix}</span>
                  <span className="stat-label">{stat.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>



      {/* ── FLEET GALLERY ── */}
      <div className="container">
        <FleetGallery />
      </div>


      {/* ── SERVICES SECTION ── */}
      <section className="services-section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">
              <Award size={14} />
              NUESTROS SERVICIOS
            </span>
            <h2 className="section-title">Más que solo pasajes</h2>
            <p className="section-desc">Ofrecemos soluciones de transporte para cada necesidad</p>
          </div>
          <div className="services-grid">
            <div className="service-card">
              <Bus size={48} strokeWidth={1.5} className="service-icon" />
              <h3 className="service-title">Servicio Especial</h3>
              <p className="service-desc">
                Prestamos servicios de traslados corporativos, ejecutivos, culturales,
                institucionales, deportivos y recreativos a nivel nacional con total
                seguridad y confort.
              </p>
              <a
                href={buildWhatsAppUrl(whatsapp, 'Hola, me interesa el servicio especial')}
                target="_blank"
                rel="noopener noreferrer"
                className="service-link"
              >
                Solicitar cotización <ArrowRight size={14} />
              </a>
            </div>

            <div className="service-card">
              <Umbrella size={48} strokeWidth={1.5} className="service-icon" />
              <h3 className="service-title">Turismo</h3>
              <p className="service-desc">
                Programación turística desde una región de origen a una región destino
                y conforme a las condiciones del viaje establecidas con el solicitante.
              </p>
              <a
                href={buildWhatsAppUrl(whatsapp, 'Hola, me interesa el servicio de turismo')}
                target="_blank"
                rel="noopener noreferrer"
                className="service-link"
              >
                Consultar paquetes <ArrowRight size={14} />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="how-section-wrapper">
        <div className="container">
          <section className="how-section">
            <div className="section-header">
              <span className="section-label">
                <Zap size={14} />
                PASO A PASO
              </span>
              <h2 className="section-title">¿Cómo funciona?</h2>
              <p className="section-desc">Reservar tu viaje es fácil, rápido y seguro</p>
            </div>
            <div className="how-grid">
              {steps.map((step, i) => (
                <div key={i} className="how-card">
                  <div className="how-step-number">{i + 1}</div>
                  <div className="how-icon-wrap" style={{ background: `${step.color}15`, color: step.color }}>
                    <step.Icon size={28} strokeWidth={1.8} />
                  </div>
                  <h4 className="how-card-title">{step.title}</h4>
                  <p className="how-card-desc">{step.desc}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <div className="container">
        <PromoPopup onClose={() => setPromoShown(true)} />
      </div>

      {/* ── CTA BANNER ── */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-card">
            <div className="cta-content">
              <h2 className="cta-title">¿Listo para tu próximo viaje?</h2>
              <p className="cta-desc">
                Reserva ahora y viaja con la comodidad y seguridad que mereces.
                Miles de pasajeros ya confían en nosotros.
              </p>
              <div className="cta-actions">
                <button
                  className="btn btn-lg cta-btn-primary"
                  onClick={() => navigate('/viajes')}
                >
                  <Search size={18} />
                  Buscar viajes ahora
                </button>
                <a
                  href={buildWhatsAppUrl(whatsapp)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-lg cta-btn-secondary"
                >
                  <Phone size={18} />
                  Contáctanos
                </a>
              </div>
            </div>
            <div className="cta-decoration">
              <Bus size={120} strokeWidth={0.8} />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
