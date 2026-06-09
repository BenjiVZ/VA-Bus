import { useState, useEffect } from 'react';
import { MapPin, Search, Armchair, Loader2 } from 'lucide-react';
import { getAerorutasOficinas, getAerorutasRutas, getAerorutasPuestos } from '../services/api';

/**
 * Búsqueda de viajes en vivo desde Aerorutas:
 *   oficinas → rutas (con precio) → puestos disponibles (un solo piso).
 * La reserva/pago se conectará después (decisión pendiente).
 */
export default function BuscarAerorutasPage() {
  const [oficinas, setOficinas] = useState([]);
  const [inicio, setInicio] = useState('');
  const [fin, setFin] = useState('');
  const [fecha, setFecha] = useState('');

  const [rutas, setRutas] = useState([]);
  const [rutaSel, setRutaSel] = useState(null);
  const [puestos, setPuestos] = useState([]);
  const [seleccion, setSeleccion] = useState([]);

  const [cargandoRutas, setCargandoRutas] = useState(false);
  const [cargandoPuestos, setCargandoPuestos] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getAerorutasOficinas().then(res => setOficinas(res.data)).catch(() => {});
  }, []);

  const buscarRutas = async () => {
    if (!inicio || !fin || !fecha) { setError('Elige origen, destino y fecha.'); return; }
    setError(''); setCargandoRutas(true);
    setRutas([]); setRutaSel(null); setPuestos([]); setSeleccion([]);
    try {
      const { data } = await getAerorutasRutas(inicio, fin, fecha);
      setRutas(data);
      if (data.length === 0) setError('No hay rutas para esa combinación.');
    } catch (e) {
      setError(e.response?.data?.error || 'No se pudieron consultar las rutas.');
    } finally {
      setCargandoRutas(false);
    }
  };

  const elegirRuta = async (ruta) => {
    setRutaSel(ruta); setPuestos([]); setSeleccion([]); setCargandoPuestos(true); setError('');
    try {
      const { data } = await getAerorutasPuestos(inicio, ruta.codrut, fecha);
      setPuestos(data);
      if (data.length === 0) setError('Esta ruta no tiene puestos disponibles.');
    } catch (e) {
      setError(e.response?.data?.error || 'No se pudieron consultar los puestos.');
    } finally {
      setCargandoPuestos(false);
    }
  };

  const toggleSeat = (numero) => {
    setSeleccion(prev =>
      prev.includes(numero) ? prev.filter(n => n !== numero) : [...prev, numero]);
  };

  const precio = rutaSel ? Number(rutaSel.precio || 0) : 0;
  const total = precio * seleccion.length;

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 720 }}>
        <h1 style={{ marginBottom: 4 }}>Buscar viaje</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
          Disponibilidad en vivo de Aerorutas.
        </p>

        {/* Buscador */}
        <div className="card" style={{ padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={lbl}><MapPin size={14} /> Origen</label>
              <select className="form-control" value={inicio} onChange={e => setInicio(e.target.value)}>
                <option value="">Selecciona…</option>
                {oficinas.map(o => <option key={o.codofi} value={o.codofi}>{o.desofi}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}><MapPin size={14} /> Destino</label>
              <select className="form-control" value={fin} onChange={e => setFin(e.target.value)}>
                <option value="">Selecciona…</option>
                {oficinas.map(o => <option key={o.codofi} value={o.codofi}>{o.desofi}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={lbl}>Fecha de viaje</label>
            <input type="date" className="form-control" value={fecha} onChange={e => setFecha(e.target.value)} />
          </div>
          <button className="btn btn-primary" style={{ width: '100%', marginTop: 16 }}
            onClick={buscarRutas} disabled={cargandoRutas}>
            {cargandoRutas ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            {cargandoRutas ? ' Buscando…' : ' Buscar rutas'}
          </button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {/* Rutas */}
        {rutas.map(r => (
          <button key={r.codrut} onClick={() => elegirRuta(r)}
            className="card" style={{
              width: '100%', textAlign: 'left', padding: 16, marginBottom: 10, cursor: 'pointer',
              border: rutaSel?.codrut === r.codrut ? '2px solid var(--blue-500)' : '1px solid var(--border)',
            }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700 }}>{r.desrut}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Salida: {r.hora}</div>
              </div>
              <div style={{ fontWeight: 700, color: 'var(--blue-700)' }}>${r.precio}</div>
            </div>
          </button>
        ))}

        {/* Puestos (un solo piso) */}
        {rutaSel && (
          <div className="card" style={{ padding: 16, marginTop: 8 }}>
            <h3 style={{ marginTop: 0 }}><Armchair size={18} /> Puestos disponibles</h3>
            {cargandoPuestos ? (
              <p style={{ color: 'var(--text-secondary)' }}>Cargando puestos…</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(56px, 1fr))', gap: 8 }}>
                {puestos.map(p => {
                  const num = p.puesto;
                  const sel = seleccion.includes(num);
                  return (
                    <button key={num} onClick={() => toggleSeat(num)}
                      style={{
                        padding: '12px 0', borderRadius: 8, fontWeight: 700, cursor: 'pointer',
                        border: '1.5px solid ' + (sel ? 'var(--blue-700)' : 'var(--border-strong, #c1c7d0)'),
                        background: sel ? 'var(--blue-500)' : '#fff',
                        color: sel ? '#fff' : 'var(--text-primary)',
                      }}>
                      {num}
                    </button>
                  );
                })}
              </div>
            )}

            {seleccion.length > 0 && (
              <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    {seleccion.length} puesto(s): {seleccion.join(', ')}
                  </div>
                  <div style={{ fontWeight: 700 }}>Total: ${total.toFixed(2)}</div>
                </div>
                <button className="btn btn-accent" disabled
                  title="La reserva/pago se conectará en el siguiente paso">
                  Continuar
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const lbl = {
  display: 'flex', alignItems: 'center', gap: 4,
  fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4,
};
