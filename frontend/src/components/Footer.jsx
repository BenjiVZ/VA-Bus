import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Phone, Mail, Clock, Facebook, Instagram, ChevronRight } from 'lucide-react';
import { getConfiguracion } from '../services/api';

const EMAIL_CONTACTO = 'aerorutasdevenezuela@gmail.com';

// Formatea un número internacional (ej 584121234567) a +58 412-1234567.
function formatTelefono(raw) {
  if (!raw) return '';
  const d = String(raw).replace(/\D/g, '');
  if (d.startsWith('58') && d.length === 12) {
    return `+58 ${d.slice(2, 5)}-${d.slice(5)}`;
  }
  if (d.length === 11) { // 04121234567
    return `${d.slice(0, 4)}-${d.slice(4)}`;
  }
  return raw;
}

export default function Footer() {
  const [telefono, setTelefono] = useState('');

  useEffect(() => {
    getConfiguracion()
      .then((res) => {
        const c = res.data || {};
        setTelefono(c.telefono_contacto || c.whatsapp_vendedor || '');
      })
      .catch(() => {});
  }, []);

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          {/* Brand Column */}
          <div className="footer-col footer-col-brand">
            <Link to="/" className="footer-brand">
              <img src="/logo.svg" alt="Aerorutas" className="footer-logo" />
              <div>
                <strong>Aerorutas</strong>
                <small>de Venezuela</small>
              </div>
            </Link>
            <p className="footer-about">
              Tu empresa de transporte de confianza. Viaja seguro y cómodo por las mejores rutas nacionales de Venezuela.
            </p>
            <div className="footer-socials">
              <a href="https://www.facebook.com/share/1JwqfkzsQd/?mibextid=wwXIfr"
                target="_blank" rel="noopener noreferrer"
                aria-label="Facebook" className="footer-social"><Facebook size={18} /></a>
              <a href="https://www.instagram.com/aerorutas.venezuela?igsh=aGppZGV0eG56cXA2"
                target="_blank" rel="noopener noreferrer"
                aria-label="Instagram" className="footer-social"><Instagram size={18} /></a>
            </div>
          </div>

          {/* Quick Links */}
          <div className="footer-col">
            <h4 className="footer-col-title">Navegación</h4>
            <ul className="footer-links">
              <li><Link to="/"><ChevronRight size={14} /> Inicio</Link></li>
              <li><Link to="/viajes"><ChevronRight size={14} /> Buscar viajes</Link></li>
              <li><Link to="/mis-reservas"><ChevronRight size={14} /> Mis reservas</Link></li>
              <li><Link to="/perfil"><ChevronRight size={14} /> Mi perfil</Link></li>
            </ul>
          </div>

          {/* Contact */}
          <div className="footer-col">
            <h4 className="footer-col-title">Contacto</h4>
            <ul className="footer-contact">
              {telefono && (
                <li>
                  <Phone size={15} />
                  <a href={`tel:${String(telefono).replace(/\D/g, '')}`}>{formatTelefono(telefono)}</a>
                </li>
              )}
              <li>
                <Mail size={15} />
                <a href={`mailto:${EMAIL_CONTACTO}`}>{EMAIL_CONTACTO}</a>
              </li>
              <li>
                <MapPin size={15} />
                <span>Venezuela</span>
              </li>
              <li>
                <Clock size={15} />
                <span>Lun-Dom: 6am - 10pm</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} Aerorutas de Venezuela — Sistema de Reservas de Autobuses</p>
          <p className="footer-legal">Todos los derechos reservados</p>
        </div>
      </div>
    </footer>
  );
}
