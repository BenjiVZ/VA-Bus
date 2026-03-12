import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminGetViajes } from '../services/api';
import { ClipboardList, Bus, ArrowRight, Users, CheckCircle, Clock } from 'lucide-react';

export default function AdminPanelPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [viajes, setViajes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.is_staff) {
      navigate('/');
      return;
    }
    adminGetViajes()
      .then((res) => setViajes(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="page">
        <div className="container">
          <div className="loading"><div className="spinner" /></div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="container">
        <div className="admin-header">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ClipboardList size={24} /> Panel de Administración
          </h2>
          <div className="admin-nav-tabs">
            <button className="admin-tab active" onClick={() => navigate('/admin/panel')}>
              <ClipboardList size={16} /> Viajes
            </button>
            <button className="admin-tab" onClick={() => navigate('/admin/buses')}>
              <Bus size={16} /> Autobuses
            </button>
          </div>
        </div>

        <div className="admin-viajes-grid">
          {viajes.map((v) => (
            <div
              key={v.id}
              className="admin-viaje-card"
              onClick={() => navigate(`/admin/viajes/${v.id}`)}
            >
              <div className="admin-viaje-route">
                <span className="admin-route-text">
                  {v.ruta}
                </span>
                <span className="admin-viaje-bus">{v.autobus}</span>
              </div>
              <div className="admin-viaje-date">
                {new Date(v.fecha_salida + 'T00:00:00').toLocaleDateString('es-VE', {
                  weekday: 'short', day: 'numeric', month: 'short',
                })} · {v.hora_salida?.slice(0, 5)}
              </div>
              <div className="admin-viaje-stats">
                <div className="admin-stat">
                  <Users size={16} style={{ marginRight: '4px', color: 'var(--blue-600)' }} />
                  <span className="admin-stat-num">{v.total_reservas}</span>
                  <span className="admin-stat-label">/{v.capacidad}</span>
                </div>
                <div className="admin-badges">
                  {v.confirmadas > 0 && (
                    <span className="badge badge-success">
                      <CheckCircle size={12} style={{ marginRight: '3px' }} />
                      {v.confirmadas}
                    </span>
                  )}
                  {v.pendientes > 0 && (
                    <span className="badge badge-warning">
                      <Clock size={12} style={{ marginRight: '3px' }} />
                      {v.pendientes}
                    </span>
                  )}
                  {v.total_reservas === 0 && (
                    <span className="badge badge-neutral">Sin reservas</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {viajes.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-tertiary)' }}>
            No hay viajes activos.
          </div>
        )}
      </div>
    </div>
  );
}
