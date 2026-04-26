import {
  Bus, MapPin, Clock, Phone, Shield, Users, Star,
  Building2, Route, Award, Armchair, Accessibility,
  Wifi, Zap, ArrowRight, CheckCircle2, Target, Eye,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import '../styles/nosotros.css';

// Scroll to hash on mount
function useScrollToHash() {
  const { hash } = useLocation();
  useEffect(() => {
    if (hash) {
      setTimeout(() => {
        const el = document.querySelector(hash);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [hash]);
}

const OBJETIVOS = [
  'Brindar un servicio de transporte terrestre seguro, cómodo y puntual en todas nuestras rutas nacionales.',
  'Mantener y renovar continuamente nuestra flota de autobuses con vehículos de alta tecnología y confort.',
  'Garantizar la satisfacción del pasajero mediante un trato amable, profesional y personalizado.',
  'Expandir nuestras rutas para conectar más ciudades y comunidades de Venezuela.',
  'Promover la capacitación continua de nuestro personal operativo y administrativo.',
  'Operar bajo estándares de calidad, eficiencia y responsabilidad social en cada viaje.',
];

const RUTAS = [
  { codigo: '001', destinos: 'Mérida / El Vigía / Maracaibo y viceversa', horario: 'Ida: 08:30 PM — Regreso: 08:30 PM' },
  { codigo: '002', destinos: 'Maracay / Valencia / El Vigía / Mérida y viceversa', horario: 'Ida: 05:30 PM — Regreso: 06:15 PM' },
  { codigo: '003', destinos: 'Mérida, El Vigía, Tucaní, Caja Seca, Valencia, Maracay, Los Teques, Terminal La Bandera y viceversa', horario: 'Ida: 06:00 PM — Regreso: 04:00 PM' },
  { codigo: '004', destinos: 'Maracay, Valencia, Barinas, Socopó, Santa Bárbara, San Cristóbal, San Antonio y viceversa', horario: 'Ida: 05:45 PM — Regreso: 06:15 PM' },
  { codigo: '005', destinos: 'Maracay, Valencia, Maracaibo y viceversa', horario: 'Ida: 06:00 PM — Regreso: 06:30 PM' },
  { codigo: '006', destinos: 'Terminal La Bandera, Maracay, Valencia, Barinas, Socopó, Santa Bárbara, El Piñal, San Cristóbal y viceversa', horario: 'Ida: 03:00–07:30 PM — Regreso: 03:00–07:30 PM' },
  { codigo: '007', destinos: 'Terminal La Bandera, Maracay, Valencia, Barquisimeto, Maracaibo y viceversa', horario: 'Ida: 09:00 AM / 07:00 PM — Regreso: 09:00 AM / 07:00 PM' },
  { codigo: '008', destinos: 'Maracaibo, Barquisimeto, Valencia, Maracay, Terminal La Bandera, Terminal Puerto La Cruz y viceversa', horario: 'Ida: 05:00 PM — Regreso: 11:30 PM' },
  { codigo: '009', destinos: 'San Antonio, San Cristóbal, El Piñal, Santa Bárbara, Socopó, Barinas, Valencia, Maracay, Los Teques, Terminal La Bandera, Terminal Puerto La Cruz y viceversa', horario: 'Ida: 11:00 AM — Regreso: 11:00 AM' },
  { codigo: '010', destinos: 'Terminal La Bandera, Maracay, Valencia, Trujillo, Valera y viceversa', horario: 'Ida: 05:00 PM — Regreso: 05:00 PM' },
];

const FLEET_FEATURES = [
  { icon: Armchair, title: 'Asientos Buscama', desc: 'Primer y segundo piso con máxima comodidad' },
  { icon: Star, title: 'Poltrona Premium', desc: 'Asientos premium en primer piso disponibles' },
  { icon: Accessibility, title: 'Accesibilidad', desc: 'Asientos especiales para personas con discapacidad en 1er piso' },
  { icon: Shield, title: 'Baño a bordo', desc: 'Un piso: al final — Doble piso: en la entrada' },
  { icon: Wifi, title: 'Wi-Fi', desc: 'Conectado durante todo tu viaje' },
  { icon: Zap, title: 'Cargadores USB', desc: 'Mantén tus dispositivos cargados' },
];

export default function NosotrosPage() {
  const navigate = useNavigate();
  useScrollToHash();

  return (
    <div className="page page-nosotros">
      {/* ── Hero ── */}
      <section className="nosotros-hero">
        <div className="nosotros-hero-bg" />
        <div className="container nosotros-hero-content">
          <span className="nosotros-overline">Acerca de</span>
          <h1 className="nosotros-hero-title">Quienes Somos</h1>
          <p className="nosotros-hero-subtitle">Aerorutas de Venezuela, C.A.</p>
        </div>
      </section>

      {/* ── Quienes Somos (Desc + MV) ── */}
      <section id="quienes-somos" className="nosotros-about-section">
        <div className="container">
          <div className="nosotros-about-card">
            
            {/* The descriptive paragraph */}
            <div className="nosotros-about-desc">
              <p>
                Empresa de transporte terrestre que opera en las principales rutas del territorio venezolano.
                <strong> Aerorutas de Venezuela, C.A.</strong> (RIF: J-50079785-0) se encarga de ofrecer
                servicios de transporte de pasajeros a nivel nacional, con una moderna flota de
                <strong> 29 unidades</strong> — incluyendo 7 autobuses de un piso (42-46 puestos) y
                21 autobuses doble piso (60 puestos) — desde su domicilio fiscal en la Carretera
                Panamericana, Sector Sabana Grande, Trujillo.
              </p>
            </div>

            <div className="nosotros-mv-divider" />

            {/* Mision and Vision inside the card */}
            <div className="nosotros-mv-grid">
              <div className="nosotros-mv-item">
                <div className="nosotros-mv-icon">
                  <Target size={28} strokeWidth={1.5} />
                </div>
                <h2>Misión</h2>
                <p>
                  Prestar un servicio de transporte terrestre de pasajeros en las modalidades
                  interurbano y especial, con vehículos modernos de alta tecnología, asientos
                  buscama y poltrona premium, conectando las principales ciudades de Venezuela
                  con total seguridad, puntualidad y confort para nuestros pasajeros.
                </p>
              </div>
              <div className="nosotros-mv-item">
                <div className="nosotros-mv-icon nosotros-mv-icon-vision">
                  <Eye size={28} strokeWidth={1.5} />
                </div>
                <h2>Visión</h2>
                <p>
                  Ser la empresa líder de transporte terrestre en Venezuela, con alcance nacional,
                  orientada a la prestación de un servicio de calidad, con responsabilidad social
                  y compromiso con el bienestar del pasajero, contribuyendo a mejorar la
                  conectividad y calidad de vida del pueblo venezolano.
                </p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── Objetivos ── */}
      <section id="objetivos" className="nosotros-objetivos">
        <div className="container">
          <div className="nosotros-obj-divider" />
          <h2 className="nosotros-obj-title">Objetivos</h2>
          <div className="nosotros-obj-grid">
            {OBJETIVOS.map((obj, i) => (
              <div key={i} className="nosotros-obj-item">
                <div className="nosotros-obj-icon">
                  <CheckCircle2 size={22} strokeWidth={2.5} />
                </div>
                <p>{obj}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Fleet Features ── */}
      <section id="flota" className="nosotros-fleet">
        <div className="container">
          <div className="nosotros-obj-divider" />
          <h2 className="nosotros-obj-title">Nuestra Flota</h2>
          <p className="nosotros-fleet-sub">29 unidades equipadas con la mejor tecnología y confort</p>
          <div className="nosotros-fleet-grid">
            {FLEET_FEATURES.map((f, i) => (
              <div key={i} className="nosotros-fleet-card">
                <div className="nosotros-fleet-icon">
                  <f.icon size={24} strokeWidth={1.5} />
                </div>
                <h4>{f.title}</h4>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="nosotros-cta">
        <div className="container">
          <div className="nosotros-cta-card">
            <h2>¿Listo para viajar con nosotros?</h2>
            <p>Reserva tu puesto ahora mismo de forma rápida y segura</p>
            <button className="btn btn-lg btn-accent" onClick={() => navigate('/viajes')}>
              Buscar viajes <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
