import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { adminGetClientesDashboard, adminGetClientes, adminToggleVip } from '../services/api';
import {
  ClipboardList, Bus, Users, Crown, TrendingUp, Search,
  Star, Award, Diamond, UserCheck, Receipt,
} from 'lucide-react';

const VIP_BADGES = {
  ninguno: { label: '—', className: 'vip-badge-none' },
  plata: { label: '🥈 Plata', className: 'vip-badge-plata' },
  oro: { label: '🥇 Oro', className: 'vip-badge-oro' },
  platino: { label: '💎 Platino', className: 'vip-badge-platino' },
};

export default function AdminClientesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [clientes, setClientes] = useState([]);
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.is_staff) { navigate('/'); return; }
    adminGetClientesDashboard()
      .then((res) => setDashboard(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const buscarClientes = async (e) => {
    e?.preventDefault();
    setSearching(true);
    try {
      const res = await adminGetClientes(query);
      setClientes(res.data);
    } catch { /* ignore */ }
    setSearching(false);
  };

  const handleToggleVip = async (clienteId, updates) => {
    try {
      const res = await adminToggleVip(clienteId, updates);
      // Update in top pasajeros
      if (dashboard) {
        setDashboard({
          ...dashboard,
          vip_activos: dashboard.vip_activos + (updates.es_vip === true ? 1 : updates.es_vip === false ? -1 : 0),
          top_pasajeros: dashboard.top_pasajeros.map((p) =>
            p.id === clienteId ? res.data : p
          ),
        });
      }
      // Update in search results
      setClientes((prev) => prev.map((c) => (c.id === clienteId ? res.data : c)));
    } catch { /* ignore */ }
  };

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
        {/* ── Header + Nav ── */}
        <div className="admin-header">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ClipboardList size={24} /> Panel de Administración
          </h2>
          <div className="admin-nav-tabs">
            <button className="admin-tab" onClick={() => navigate('/admin/panel')}>
              <ClipboardList size={16} /> Viajes
            </button>
            <button className="admin-tab" onClick={() => navigate('/admin/buses')}>
              <Bus size={16} /> Autobuses
            </button>
            <button className="admin-tab" onClick={() => navigate('/admin/comprobantes')}>
              <Receipt size={16} /> Comprobantes
            </button>
            <button className="admin-tab active" onClick={() => navigate('/admin/clientes')}>
              <Users size={16} /> Clientes
            </button>
          </div>
        </div>

        {/* ── Dashboard Stats ── */}
        {dashboard && (
          <>
            <div className="clientes-stats-grid">
              <div className="clientes-stat-card">
                <div className="clientes-stat-icon" style={{ background: 'var(--blue-50)', color: 'var(--blue-600)' }}>
                  <Users size={24} />
                </div>
                <div>
                  <div className="clientes-stat-num">{dashboard.total_clientes}</div>
                  <div className="clientes-stat-label">Clientes registrados</div>
                </div>
              </div>
              <div className="clientes-stat-card">
                <div className="clientes-stat-icon" style={{ background: 'var(--green-50)', color: 'var(--green-500)' }}>
                  <UserCheck size={24} />
                </div>
                <div>
                  <div className="clientes-stat-num">{dashboard.compradores}</div>
                  <div className="clientes-stat-label">Han comprado</div>
                </div>
              </div>
              <div className="clientes-stat-card">
                <div className="clientes-stat-icon" style={{ background: '#fef3c7', color: '#d97706' }}>
                  <Crown size={24} />
                </div>
                <div>
                  <div className="clientes-stat-num">{dashboard.vip_activos}</div>
                  <div className="clientes-stat-label">VIP activos</div>
                </div>
              </div>
              <div className="clientes-stat-card">
                <div className="clientes-stat-icon" style={{ background: '#ede9fe', color: '#7c3aed' }}>
                  <TrendingUp size={24} />
                </div>
                <div>
                  <div className="clientes-stat-num">
                    {dashboard.top_pasajeros[0]
                      ? `${dashboard.top_pasajeros[0].first_name || ''} ${dashboard.top_pasajeros[0].last_name || ''}`.trim() || dashboard.top_pasajeros[0].username
                      : '—'}
                  </div>
                  <div className="clientes-stat-label">Pasajero más frecuente</div>
                </div>
              </div>
            </div>

            {/* ── Top 10 ── */}
            <div className="clientes-section">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Award size={20} /> Pasajeros Frecuentes — Top 10
              </h3>
              <div className="table-responsive">
                <table className="clientes-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Cliente</th>
                      <th>Cédula</th>
                      <th>Email</th>
                      <th>Viajes</th>
                      <th>Último viaje</th>
                      <th>VIP</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.top_pasajeros.map((c, i) => (
                      <ClienteRow key={c.id} cliente={c} rank={i + 1} onToggleVip={handleToggleVip} />
                    ))}
                    {dashboard.top_pasajeros.length === 0 && (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                          Sin pasajeros con viajes confirmados aún.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ── Búsqueda ── */}
        <div className="clientes-section">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Search size={20} /> Buscar Cliente
          </h3>
          <form className="clientes-search-form" onSubmit={buscarClientes}>
            <input
              type="text"
              className="form-control"
              placeholder="Nombre, cédula o email..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className="btn btn-primary" disabled={searching}>
              <Search size={16} />
              {searching ? 'Buscando...' : 'Buscar'}
            </button>
          </form>

          {clientes.length > 0 && (
            <div className="table-responsive" style={{ marginTop: '1rem' }}>
              <table className="clientes-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Cédula</th>
                    <th>Email</th>
                    <th>Teléfono</th>
                    <th>Viajes</th>
                    <th>Último viaje</th>
                    <th>VIP</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {clientes.map((c) => (
                    <ClienteRow key={c.id} cliente={c} onToggleVip={handleToggleVip} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


/* ── Fila de cliente reutilizable ── */
function ClienteRow({ cliente, rank, onToggleVip }) {
  const [editingVip, setEditingVip] = useState(false);
  const [nivel, setNivel] = useState(cliente.servicio_vip || 'ninguno');
  const nombre = `${cliente.first_name || ''} ${cliente.last_name || ''}`.trim() || cliente.username;

  const handleSaveVip = () => {
    const esVip = nivel !== 'ninguno';
    onToggleVip(cliente.id, { es_vip: esVip, servicio_vip: nivel });
    setEditingVip(false);
  };

  const badge = VIP_BADGES[cliente.servicio_vip] || VIP_BADGES.ninguno;

  return (
    <tr>
      {rank !== undefined && (
        <td style={{ fontWeight: 700, fontSize: '1.1rem', color: rank <= 3 ? '#d97706' : 'var(--text-secondary)' }}>
          {rank <= 3 ? ['🥇', '🥈', '🥉'][rank - 1] : rank}
        </td>
      )}
      <td>
        <div style={{ fontWeight: 600 }}>{nombre}</div>
      </td>
      <td>{cliente.cedula || '—'}</td>
      <td style={{ fontSize: '0.82rem' }}>{cliente.email}</td>
      {rank !== undefined ? null : <td>{cliente.telefono || '—'}</td>}
      <td>
        <span style={{ fontWeight: 700, color: 'var(--blue-600)' }}>{cliente.total_viajes || 0}</span>
      </td>
      <td style={{ fontSize: '0.82rem' }}>
        {cliente.ultimo_viaje
          ? new Date(cliente.ultimo_viaje + 'T00:00:00').toLocaleDateString('es-VE', { day: 'numeric', month: 'short', year: 'numeric' })
          : '—'}
      </td>
      <td>
        <span className={`vip-badge ${badge.className}`}>{badge.label}</span>
      </td>
      <td>
        {editingVip ? (
          <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
            <select
              value={nivel}
              onChange={(e) => setNivel(e.target.value)}
              style={{ fontSize: '0.8rem', padding: '0.2rem 0.4rem', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
            >
              <option value="ninguno">Ninguno</option>
              <option value="plata">🥈 Plata</option>
              <option value="oro">🥇 Oro</option>
              <option value="platino">💎 Platino</option>
            </select>
            <button
              className="btn btn-sm btn-primary"
              style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
              onClick={handleSaveVip}
            >
              ✓
            </button>
            <button
              className="btn btn-sm"
              style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem', background: 'var(--gray-100)' }}
              onClick={() => { setEditingVip(false); setNivel(cliente.servicio_vip || 'ninguno'); }}
            >
              ✕
            </button>
          </div>
        ) : (
          <button
            className="btn btn-sm"
            style={{
              fontSize: '0.75rem', padding: '0.25rem 0.6rem',
              background: cliente.es_vip ? '#fef3c7' : 'var(--gray-50)',
              color: cliente.es_vip ? '#92400e' : 'var(--text-secondary)',
              border: `1px solid ${cliente.es_vip ? '#fde68a' : 'var(--border-standard)'}`,
            }}
            onClick={() => setEditingVip(true)}
          >
            <Crown size={12} style={{ marginRight: '3px' }} />
            {cliente.es_vip ? 'Editar VIP' : 'Asignar VIP'}
          </button>
        )}
      </td>
    </tr>
  );
}
