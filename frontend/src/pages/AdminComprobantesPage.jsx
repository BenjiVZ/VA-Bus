import { useState, useEffect } from 'react';
import { adminGetComprobantes, adminValidarComprobante } from '../services/api';
import {
  CheckCircle, XCircle, Clock, Eye, Search, Filter,
  User, CreditCard, Image as ImageIcon, MessageSquare,
} from 'lucide-react';

const API_URL = 'http://localhost:8000';

export default function AdminComprobantesPage() {
  const [comprobantes, setComprobantes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('pendiente');
  const [pendientesCount, setPendientesCount] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [nota, setNota] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [imgModal, setImgModal] = useState(null);

  const fetchComprobantes = (estado) => {
    setLoading(true);
    adminGetComprobantes(estado || undefined).then(res => {
      setComprobantes(res.data.comprobantes || []);
      setPendientesCount(res.data.pendientes || 0);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchComprobantes(filtro);
  }, [filtro]);

  const handleValidar = async (id, estado) => {
    setProcesando(true);
    try {
      await adminValidarComprobante(id, estado, nota);
      setNota('');
      setSelectedId(null);
      fetchComprobantes(filtro);
    } catch (err) {
      alert(err.response?.data?.error || 'Error al procesar.');
    } finally {
      setProcesando(false);
    }
  };

  const getEstadoIcon = (estado) => {
    switch (estado) {
      case 'pendiente': return <Clock size={14} />;
      case 'aprobado': return <CheckCircle size={14} />;
      case 'rechazado': return <XCircle size={14} />;
      default: return null;
    }
  };

  const getEstadoClass = (estado) => {
    switch (estado) {
      case 'pendiente': return 'badge-warning';
      case 'aprobado': return 'badge-success';
      case 'rechazado': return 'badge-error';
      default: return '';
    }
  };

  return (
    <div className="page">
      <div className="container">
        <div style={{ marginBottom: '1.5rem' }}>
          <h2>Comprobantes de Pago</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {pendientesCount} comprobante{pendientesCount !== 1 ? 's' : ''} pendiente{pendientesCount !== 1 ? 's' : ''} de revisión
          </p>
        </div>

        {/* Filters */}
        <div className="comp-filters">
          {[
            { val: 'pendiente', label: 'Pendientes' },
            { val: 'aprobado', label: 'Aprobados' },
            { val: 'rechazado', label: 'Rechazados' },
            { val: '', label: 'Todos' },
          ].map(f => (
            <button
              key={f.val}
              className={`comp-filter-btn ${filtro === f.val ? 'active' : ''}`}
              onClick={() => setFiltro(f.val)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading && (
          <div className="loading"><div className="spinner" /></div>
        )}

        {!loading && comprobantes.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3>No hay comprobantes {filtro ? filtro + 's' : ''}</h3>
          </div>
        )}

        {!loading && comprobantes.map(comp => (
          <div key={comp.id} className="comp-card">
            <div className="comp-header">
              <div className="comp-header-left">
                <span className={`badge ${getEstadoClass(comp.estado)}`}>
                  {getEstadoIcon(comp.estado)} {comp.estado_display}
                </span>
                <span className="comp-date">
                  {new Date(comp.fecha_creacion).toLocaleString('es-VE', {
                    day: '2-digit', month: '2-digit', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </span>
              </div>
              <div className="comp-id">#{String(comp.id).slice(0, 8)}</div>
            </div>

            <div className="comp-body">
              {/* User Info */}
              <div className="comp-section">
                <div className="comp-section-title"><User size={14} /> Cliente</div>
                <div className="comp-info">{comp.usuario_info?.nombre}</div>
                <div className="comp-info-sub">
                  {comp.usuario_info?.email} · CI: {comp.usuario_info?.cedula} · Tel: {comp.usuario_info?.telefono}
                </div>
              </div>

              {/* Payment Info */}
              <div className="comp-section">
                <div className="comp-section-title"><CreditCard size={14} /> Pago</div>
                <div className="comp-info">
                  {comp.metodo_pago_nombre} · <strong>
                    {comp.moneda === 'USD' ? `$${Number(comp.monto).toFixed(2)}` : `Bs. ${Number(comp.monto).toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                  </strong>
                </div>
                {comp.numero_referencia && (
                  <div className="comp-info-sub">Ref: {comp.numero_referencia}</div>
                )}
              </div>

              {/* Reservas */}
              <div className="comp-section">
                <div className="comp-section-title">💺 Reservas</div>
                {comp.reservas_info?.map((r, i) => (
                  <div key={i} className="comp-info-sub">
                    Asiento #{r.asiento} (P{r.piso}) · {r.ruta} · {r.fecha} · {r.nombre_pasajero} · Estado: {r.estado}
                  </div>
                ))}
              </div>

              {/* Proof Image */}
              <div className="comp-section">
                <div className="comp-section-title"><ImageIcon size={14} /> Comprobante</div>
                {comp.imagen && (
                  <img
                    src={comp.imagen.startsWith('http') ? comp.imagen : `${API_URL}${comp.imagen}`}
                    alt="Comprobante"
                    className="comp-image"
                    onClick={() => setImgModal(comp.imagen.startsWith('http') ? comp.imagen : `${API_URL}${comp.imagen}`)}
                  />
                )}
              </div>
            </div>

            {/* Actions — only for pending */}
            {comp.estado === 'pendiente' && (
              <div className="comp-actions">
                {selectedId === comp.id ? (
                  <div className="comp-nota-form">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Nota (opcional, ej: motivo de rechazo)"
                      value={nota}
                      onChange={(e) => setNota(e.target.value)}
                    />
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                      <button
                        className="btn btn-success"
                        disabled={procesando}
                        onClick={() => handleValidar(comp.id, 'aprobado')}
                      >
                        <CheckCircle size={14} /> Aprobar
                      </button>
                      <button
                        className="btn btn-error"
                        disabled={procesando}
                        onClick={() => handleValidar(comp.id, 'rechazado')}
                      >
                        <XCircle size={14} /> Rechazar
                      </button>
                      <button className="btn btn-secondary" onClick={() => setSelectedId(null)}>
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <button className="btn btn-primary" onClick={() => setSelectedId(comp.id)}>
                    <Eye size={14} /> Revisar
                  </button>
                )}
              </div>
            )}

            {/* Show admin note if rejected/approved */}
            {comp.nota_admin && comp.estado !== 'pendiente' && (
              <div className="comp-admin-note">
                <MessageSquare size={14} /> <strong>Nota admin:</strong> {comp.nota_admin}
              </div>
            )}
          </div>
        ))}

        {/* Image Modal */}
        {imgModal && (
          <div className="pago-img-modal" onClick={() => setImgModal(null)}>
            <img src={imgModal} alt="Comprobante ampliado" />
          </div>
        )}
      </div>
    </div>
  );
}
