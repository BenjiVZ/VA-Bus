import { useState, useEffect } from 'react';
import { CreditCard, Smartphone, DollarSign, Wallet, TrendingUp } from 'lucide-react';
import { getTasaCambio, getMetodosPago } from '../services/api';

export default function TickerBar() {
  const [tasa, setTasa] = useState(null);
  const [metodos, setMetodos] = useState([]);

  useEffect(() => {
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => {});

    getMetodosPago()
      .then((res) => setMetodos(res.data))
      .catch(() => {});
  }, []);

  const getIconForTipo = (tipo) => {
    switch (tipo) {
      case 'transferencia': return <CreditCard size={13} />;
      case 'pago_movil': return <Smartphone size={13} />;
      case 'divisas': return <DollarSign size={13} />;
      case 'zinli': case 'zelle': case 'binance': return <Wallet size={13} />;
      default: return <CreditCard size={13} />;
    }
  };

  const tickerItems = [];

  if (tasa) {
    tickerItems.push(
      <span key="tasa" className="ticker-item ticker-tasa">
        <TrendingUp size={13} />
        <span>Tasa BCV del día: <strong>Bs. {Number(tasa).toFixed(2)}</strong> / $1 USD</span>
      </span>
    );
  }

  metodos.forEach((m) => {
    tickerItems.push(
      <span key={`m-${m.id}`} className="ticker-item">
        {getIconForTipo(m.tipo)}
        <span>{m.nombre}</span>
        <small className="ticker-moneda">{m.moneda === 'USD' ? 'USD' : 'Bs'}</small>
      </span>
    );
  });

  if (tickerItems.length === 0) return null;

  return (
    <div className="ticker-bar">
      <div className="ticker-track">
        {tickerItems.map((item, i) => (
          <span key={`a-${i}`}>{item}<span className="ticker-dot">•</span></span>
        ))}
        {tickerItems.map((item, i) => (
          <span key={`b-${i}`}>{item}<span className="ticker-dot">•</span></span>
        ))}
      </div>
    </div>
  );
}
