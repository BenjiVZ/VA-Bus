import { useState, useEffect } from 'react';
import { getTasaCambio } from '../services/api';

// Cache global: una sola petición compartida entre todas las instancias
let tasaCache = null;
let tasaPromise = null;
let tasaTimestamp = 0;
const CACHE_TTL = 60000; // 60 segundos

function fetchTasaCached() {
  const now = Date.now();
  if (tasaCache !== null && now - tasaTimestamp < CACHE_TTL) {
    return Promise.resolve(tasaCache);
  }
  if (!tasaPromise) {
    tasaPromise = getTasaCambio()
      .then((res) => {
        tasaCache = res.data.tasa_bcv;
        tasaTimestamp = Date.now();
        tasaPromise = null;
        return tasaCache;
      })
      .catch(() => {
        tasaPromise = null;
        return null;
      });
  }
  return tasaPromise;
}

export default function PriceDisplay({ priceUsd, className = '' }) {
  const [tasa, setTasa] = useState(tasaCache);

  useEffect(() => {
    fetchTasaCached().then((t) => setTasa(t));
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
