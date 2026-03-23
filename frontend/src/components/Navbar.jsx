import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Home, MapPin, Ticket, Settings, User,
  LogOut, LogIn, UserPlus, Menu, X, FileCheck,
} from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navRef = useRef(null);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Close mobile menu on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setMobileOpen(false);
      }
    };
    if (mobileOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [mobileOpen]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { to: '/', label: 'Inicio', icon: Home },
    { to: '/viajes', label: 'Viajes', icon: MapPin },
    ...(user ? [{ to: '/mis-reservas', label: 'Mis Reservas', icon: Ticket }] : []),
    ...(user?.is_staff ? [
      { to: '/admin/panel', label: 'Admin', icon: Settings },
      { to: '/admin/comprobantes', label: 'Comprobantes', icon: FileCheck },
    ] : []),
  ];

  return (
    <nav className="navbar" ref={navRef}>
      <div className="container">
        {/* ── Brand ── */}
        <Link to="/" className="navbar-brand">
          <img src="/logo.jpg" alt="Aerorutas de Venezuela" className="navbar-logo" />
          <span className="navbar-brand-text">
            <strong>Aerorutas</strong>
            <small>de Venezuela</small>
          </span>
        </Link>

        {/* ── Desktop Nav ── */}
        <div className="nav-center">
          {navItems.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-pill${isActive(to) ? ' nav-pill-active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </Link>
          ))}
        </div>

        {/* ── Desktop User Area ── */}
        <div className="nav-user-area">
          {user ? (
            <>
              <Link to="/perfil" className="nav-user-badge" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="nav-avatar">
                  {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                </div>
                <span className="nav-user-label">{user.first_name || user.username}</span>
              </Link>
              <button className="nav-icon-btn" onClick={handleLogout} title="Cerrar sesión">
                <LogOut size={18} />
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-sm btn-ghost">
                <LogIn size={15} /> Ingresar
              </Link>
              <Link to="/registro" className="btn btn-sm btn-accent">
                <UserPlus size={15} /> Registrarse
              </Link>
            </>
          )}
        </div>

        {/* ── Hamburger ── */}
        <button
          className="nav-hamburger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* ── Mobile Drawer ── */}
      <div className={`nav-drawer${mobileOpen ? ' nav-drawer-open' : ''}`}>
        <div className="nav-drawer-links">
          {navItems.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-drawer-link${isActive(to) ? ' nav-drawer-link-active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          ))}
        </div>

        <div className="nav-drawer-divider" />

        <div className="nav-drawer-actions">
          {user ? (
            <>
              <Link to="/perfil" className="nav-drawer-user" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="nav-avatar">
                  {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 600 }}>{user.first_name || user.username}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email}</div>
                </div>
              </Link>
              <button className="btn btn-sm btn-ghost" onClick={handleLogout} style={{ width: '100%', justifyContent: 'center' }}>
                <LogOut size={15} /> Cerrar sesión
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost" style={{ width: '100%', justifyContent: 'center' }}>
                <LogIn size={16} /> Ingresar
              </Link>
              <Link to="/registro" className="btn btn-accent" style={{ width: '100%', justifyContent: 'center' }}>
                <UserPlus size={16} /> Registrarse
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
