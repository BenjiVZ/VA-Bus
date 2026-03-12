import { useState, useEffect } from 'react';
import { getTasaCambio } from '../services/api';

export default function PriceDisplay({ priceUsd, className = '' }) {
  const [tasa, setTasa] = useState(null);

  useEffect(() => {
    getTasaCambio()
      .then((res) => setTasa(res.data.tasa_bcv))
      .catch(() => setTasa(null));
  }, []);

  const priceBs = tasa ? (priceUsd * tasa).toFixed(2) : null;

  return (
    <div className={`price-display ${className}`}>
      <span className="price-usd">${Number(priceUsd).toFixed(2)}</span>
      {priceBs && (
        <span className="price-bs">Bs. {Number(priceBs).toLocaleString('es-VE')}</span>
      )}
    </div>
  );
}
