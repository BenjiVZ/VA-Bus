import { useState } from 'react';
import { DoorOpen, ArrowUpCircle, UserCog } from 'lucide-react';

/* ── Inline SVG seat icon ── */
function SeatIcon({ number, state, onClick, title }) {
  const colors = {
    available: { fill: '#ffffff', stroke: '#c1c7d0', text: '#42526e', headrest: '#dfe1e6' },
    selected:  { fill: '#0052cc', stroke: '#003380', text: '#ffffff', headrest: '#0043a6' },
    occupied:  { fill: '#fef9e7', stroke: '#f0d264', text: '#b8960c', headrest: '#fae8a0' },
    moving:    { fill: '#ff8f00', stroke: '#e65100', text: '#ffffff', headrest: '#f57c00' },
  };
  const c = colors[state] || colors.available;
  const cursor = (state === 'occupied' || state === 'moving') ? 'not-allowed' : 'pointer';

  return (
    <svg
      width="48" height="52" viewBox="0 0 48 52"
      className={`seat-svg seat-svg-${state}`}
      onClick={(state !== 'occupied' && state !== 'moving') ? onClick : undefined}
      style={{ cursor }}
      role="button"
      aria-label={title}
    >
      <title>{title}</title>
      {/* Headrest */}
      <rect x="8" y="0" width="32" height="10" rx="5" ry="5"
        fill={c.headrest} stroke={c.stroke} strokeWidth="1.5" />
      {/* Seat back */}
      <rect x="4" y="8" width="40" height="30" rx="4" ry="4"
        fill={c.fill} stroke={c.stroke} strokeWidth="1.5" />
      {/* Seat cushion */}
      <rect x="2" y="36" width="44" height="14" rx="4" ry="4"
        fill={c.fill} stroke={c.stroke} strokeWidth="1.5" />
      {/* Armrests */}
      <rect x="0" y="28" width="5" height="16" rx="2.5" ry="2.5"
        fill={c.headrest} stroke={c.stroke} strokeWidth="1" />
      <rect x="43" y="28" width="5" height="16" rx="2.5" ry="2.5"
        fill={c.headrest} stroke={c.stroke} strokeWidth="1" />
      {/* Number */}
      <text x="24" y="28" textAnchor="middle" dominantBaseline="central"
        fill={c.text} fontSize="13" fontWeight="700" fontFamily="Inter, sans-serif">
        {number}
      </text>
    </svg>
  );
}

/* ── Door cell ── */
function DoorCell() {
  return (
    <div className="layout-cell layout-cell-door" title="Puerta">
      <DoorOpen size={24} strokeWidth={1.8} color="#e65100" />
    </div>
  );
}

/* ── Stairs cell ── */
function StairsCell() {
  return (
    <div className="layout-cell layout-cell-stairs" title="Escalera">
      <ArrowUpCircle size={24} strokeWidth={1.8} color="#2e7d32" />
    </div>
  );
}

/* ── Driver cell ── */
function DriverCell() {
  return (
    <div className="layout-cell layout-cell-driver" title="Chofer">
      <UserCog size={24} strokeWidth={1.8} color="#1565c0" />
    </div>
  );
}

export default function SeatMap({ pisosConfig, selectedSeats, onToggleSeat, movingSeatNumber, isMovingMode }) {
  const pisos = pisosConfig.map((p) => p.numero_piso).sort();
  const [activePiso, setActivePiso] = useState(pisos[0] || 1);

  const config = pisosConfig.find((p) => p.numero_piso === activePiso);
  if (!config || !config.layout || config.layout.length === 0) {
    return (
      <div className="seat-map-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-tertiary)' }}>No hay layout configurado para este autobús.</p>
      </div>
    );
  }

  const getSeatState = (number) => {
    if (isMovingMode && movingSeatNumber?.numero === number && movingSeatNumber?.piso === activePiso) return 'moving';
    if (selectedSeats.some((s) => s.numero === number && s.piso === activePiso)) return 'selected';
    return 'available';
  };

  const handleClick = (number, disponible) => {
    if (!disponible) return;
    onToggleSeat({ numero: number, piso: activePiso });
  };

  const columnas = config.columnas || (config.layout[0] ? config.layout[0].length : 5);

  return (
    <div className="seat-map-wrapper">
      {pisos.length > 1 && (
        <div className="floor-tabs">
          {pisos.map((p) => (
            <button
              key={p}
              className={`floor-tab ${activePiso === p ? 'active' : ''}`}
              onClick={() => setActivePiso(p)}
            >
              Piso {p}
            </button>
          ))}
        </div>
      )}

      {/* Bus Outline */}
      <div className="bus-outline">
        {/* Windshield */}
        <div className="bus-windshield">
          <svg width="100%" height="40" viewBox="0 0 300 40" preserveAspectRatio="none">
            <path d="M0,40 Q150,-10 300,40" fill="none" stroke="var(--border-strong)" strokeWidth="2" />
          </svg>
          <div className="bus-windshield-label">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/>
            </svg>
            <span>FRENTE DEL AUTOBÚS</span>
          </div>
        </div>

        {/* Layout Grid */}
        <div
          className="bus-layout-grid"
          style={{ gridTemplateColumns: `repeat(${columnas}, 1fr)` }}
        >
          {config.layout.map((row, rowIdx) =>
            row.map((cell, colIdx) => {
              const type = cell.type || 'empty';
              const number = cell.number || null;
              const disponible = cell.disponible !== false;
              const key = `${rowIdx}-${colIdx}`;

              if (type === 'seat' && number) {
                const state = !disponible ? 'occupied' : getSeatState(number);
                const pulseClass = isMovingMode && state === 'available' ? ' seat-cell-pulse' : '';
                const titleText = state === 'moving' ? `Asiento ${number} - Mover desde aquí`
                  : `Asiento ${number} - ${disponible ? (state === 'selected' ? 'Seleccionado' : (isMovingMode ? 'Clic para mover aquí' : 'Disponible')) : 'Ocupado'}`;
                return (
                  <div key={key} className={`layout-cell layout-cell-seat${pulseClass}`}>
                    <SeatIcon
                      number={number}
                      state={state}
                      onClick={() => handleClick(number, disponible)}
                      title={titleText}
                    />
                  </div>
                );
              }

              if (type === 'door') return <DoorCell key={key} />;
              if (type === 'stairs') return <StairsCell key={key} />;
              if (type === 'driver') return <DriverCell key={key} />;
              if (type === 'aisle') return <div key={key} className="layout-cell layout-cell-aisle" />;

              // empty
              return <div key={key} className="layout-cell layout-cell-empty" />;
            })
          )}
        </div>

        {/* Bus rear */}
        <div className="bus-rear" />
      </div>

      {/* Legend */}
      <div className="seat-legend">
        <div className="seat-legend-item">
          <SeatIcon number="" state="available" onClick={() => {}} title="Disponible" />
          <span>Disponible</span>
        </div>
        <div className="seat-legend-item">
          <SeatIcon number="" state="occupied" onClick={() => {}} title="Ocupado" />
          <span>Ocupado</span>
        </div>
        <div className="seat-legend-item">
          <SeatIcon number="" state="selected" onClick={() => {}} title="Seleccionado" />
          <span>Seleccionado</span>
        </div>
      </div>
    </div>
  );
}
