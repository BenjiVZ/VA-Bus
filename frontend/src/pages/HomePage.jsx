import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRutas } from '../services/api';
import { Search, Armchair, MessageCircle, CheckCircle, MapPin, Calendar } from 'lucide-react';

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
    { Icon: Search, title: 'Busca tu viaje', desc: 'Selecciona origen, destino y fecha' },
    { Icon: Armchair, title: 'Elige tu asiento', desc: 'Visualiza el mapa del autobús' },
    { Icon: MessageCircle, title: 'Coordina por WhatsApp', desc: 'Confirma tu pago con el vendedor' },
    { Icon: CheckCircle, title: '¡Viaja tranquilo!', desc: 'Tu puesto queda reservado' },
  ];

  return (
    <div className="page">
      <div className="container">
        <section className="hero">
          <h1>Viaja con Aerorutas de Venezuela</h1>{/* Aerorutas */}
          <p>
            Reserva tu puesto de autobús de forma rápida y segura.
            Encuentra las mejores rutas en Venezuela.
          </p>

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
        </section>

        <section style={{ marginTop: '4rem', textAlign: 'center' }}>
          <h3 style={{ marginBottom: '2rem', color: 'var(--text-secondary)' }}>
            ¿Cómo funciona?
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
            {steps.map((step, i) => (
              <div key={i} className="card how-it-works-card" style={{ textAlign: 'center', padding: '2rem' }}>
                <div className="how-icon-wrap">
                  <step.Icon size={32} strokeWidth={1.8} />
                </div>
                <h4 style={{ marginBottom: '0.5rem' }}>{step.title}</h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{step.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
