import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminGetBuses } from '../services/api';
import SeatMap from '../components/SeatMap';
import { ClipboardList, Bus, ChevronUp, ChevronDown } from 'lucide-react';

export default function AdminBusesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [buses, setBuses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedBus, setExpandedBus] = useState(null);

  useEffect(() => {
    if (!user?.is_staff) { navigate('/'); return; }
    adminGetBuses()
      .then((res) => setBuses(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="page"><div className="container">
        <div className="loading"><div className="spinner" /></div>
      </div></div>
    );
  }

  return (
    <div className="page">
      <div className="container">
        <div className="admin-header">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bus size={24} /> Panel de Administración
          </h2>
          <div className="admin-nav-tabs">
            <button className="admin-tab" onClick={() => navigate('/admin/panel')}>
              <ClipboardList size={16} /> Viajes
            </button>
            <button className="admin-tab active" onClick={() => navigate('/admin/buses')}>
              <Bus size={16} /> Autobuses
            </button>
          </div>
        </div>

        <div className="admin-buses-grid">
          {buses.map((bus) => {
            const isExpanded = expandedBus === bus.id;
            const pisosConfig = bus.pisos_config?.map((p) => ({
              ...p,
              layout: p.layout || [],
            })) || [];

            const pisosWithAvailability = pisosConfig.map((p) => ({
              ...p,
              layout: (p.layout || []).map((row) =>
                row.map((cell) => ({
                  ...cell,
                  disponible: cell.type === 'seat' ? true : undefined,
                }))
              ),
            }));

            return (
              <div key={bus.id} className="admin-bus-card">
                <div className="admin-bus-header" onClick={() => setExpandedBus(isExpanded ? null : bus.id)}>
                  <div>
                    <h3 className="admin-bus-name">{bus.nombre}</h3>
                    <span className="admin-bus-meta">
                      Placa: {bus.placa} · {bus.pisos} piso{bus.pisos > 1 ? 's' : ''} · {bus.capacidad_total} asientos
                    </span>
                  </div>
                  <span className="admin-bus-toggle">
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </span>
                </div>
                {isExpanded && pisosWithAvailability.length > 0 && (
                  <div className="admin-bus-preview">
                    <SeatMap
                      pisosConfig={pisosWithAvailability}
                      selectedSeats={[]}
                      onToggleSeat={() => {}}
                    />
                  </div>
                )}
                {isExpanded && pisosWithAvailability.length === 0 && (
                  <div className="admin-bus-preview" style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '2rem' }}>
                    No hay layout configurado. Configúralo en el Admin de Django.
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {buses.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-tertiary)' }}>
            No hay autobuses registrados.
          </div>
        )}
      </div>
    </div>
  );
}
