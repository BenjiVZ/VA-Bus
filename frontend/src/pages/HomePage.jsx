import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRutas } from '../services/api';
import { Search, Armchair, MessageCircle, CheckCircle, MapPin, Calendar, ShieldCheck, Clock, Users, Star } from 'lucide-react';
import FleetGallery from '../components/FleetGallery';
import PromoPopup from '../components/PromoPopup';
import '../styles/FleetGallery.css';

export default function HomePage() {
  const navigate = useNavigate();
  const [rutas, setRutas] = useState([]);
  const [origen, setOrigen] = useState('');
  const [destino, setDestino] = useState('');
  const [fecha, setFecha] = useState('');

  useEffect(() => {
    getRutas()
      .then((res) => setRutas(res.data))
      .catch(() => {});
  }, []);

  const origenes = [...new Set(rutas.map((r) => r.origen))].sort();
  const destinos = [...new Set(rutas.map((r) => r.destino))].sort();

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (origen) params.set('origen', origen);
    if (destino) params.set('destino', destino);
    if (fecha) params.set('fecha', fecha);
    navigate(`/viajes?${params.toString()}`);
  };

  const steps = [
    { Icon: Search, title: 'Busca tu viaje', desc: 'Selecciona origen, destino y fecha', color: '#3b82f6' },
    { Icon: Armchair, title: 'Elige tu asiento', desc: 'Visualiza el mapa del autobús', color: '#8b5cf6' },
    { Icon: MessageCircle, title: 'Coordina por WhatsApp', desc: 'Confirma tu pago con el vendedor', color: '#22c55e' },
    { Icon: CheckCircle, title: '¡Viaja tranquilo!', desc: 'Tu puesto queda reservado', color: '#f59e0b' },
  ];

  const trustItems = [
    { Icon: ShieldCheck, text: 'Reserva segura' },
    { Icon: Clock, text: 'Confirmación al instante' },
    { Icon: Users, text: '+1,000 pasajeros confían' },
    { Icon: Star, text: 'Flota moderna' },
  ];

  return (
    <div className="page page-home">
      <PromoPopup />

      {/* ── HERO SECTION ── */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-content">
          <span className="hero-badge">🚌 La mejor forma de viajar por Venezuela</span>
          <h1 className="hero-title">
            Viaja con <span className="hero-brand">Aerorutas</span>
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
                onChange={(e) => setOrigen(e.target.value)}
              >
                <option value="">Todas las ciudades</option>
                {origenes.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <MapPin size={14} /> Destino
              </label>
              <select
                className="form-control"
                value={destino}
                onChange={(e) => setDestino(e.target.value)}
              >
                <option value="">Todas las ciudades</option>
                {destinos.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <Calendar size={14} /> Fecha
              </label>
              <input
                type="date"
                className="form-control"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
              />
            </div>

            <button type="submit" className="btn btn-primary btn-lg"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
              <Search size={18} />
              Buscar
            </button>
          </form>
        </div>
      </section>

      <div className="container">
        <FleetGallery />

        {/* ── HOW IT WORKS ── */}
        <section className="how-section">
          <div className="how-section-header">
            <span className="how-section-label">PASO A PASO</span>
            <h3 className="how-section-title">¿Cómo funciona?</h3>
            <p className="how-section-desc">Reservar tu viaje es fácil, rápido y seguro</p>
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
                {i < steps.length - 1 && <div className="how-connector" />}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
