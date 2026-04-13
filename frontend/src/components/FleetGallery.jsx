import { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

// Auto-detect: solo muestra las imágenes que existan en /public/flota/
const imageModules = import.meta.glob('/public/flota/bus-*.jpg', { eager: true });
const photos = Object.keys(imageModules)
  .sort()
  .map((path, i) => ({
    src: path.replace('/public', ''),
    alt: `Autobús Aerorutas de Venezuela #${i + 1}`,
  }));

export default function FleetGallery() {
  const [current, setCurrent] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const trackRef = useRef(null);
  const timerRef = useRef(null);

  // Auto-play
  useEffect(() => {
    if (!isAutoPlaying) return;
    timerRef.current = setInterval(() => {
      setCurrent(prev => (prev + 1) % photos.length);
    }, 4000);
    return () => clearInterval(timerRef.current);
  }, [isAutoPlaying]);

  const go = (dir) => {
    setIsAutoPlaying(false);
    setCurrent(prev => {
      if (dir === 'next') return (prev + 1) % photos.length;
      return (prev - 1 + photos.length) % photos.length;
    });
    // Resume auto-play after 8s of inactivity
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setIsAutoPlaying(true), 8000);
  };

  const goTo = (idx) => {
    setIsAutoPlaying(false);
    setCurrent(idx);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setIsAutoPlaying(true), 8000);
  };

  return (
    <section className="fleet-gallery">
      <h3 className="fleet-gallery-title">Nuestra Flota</h3>

      <div className="fleet-carousel">
        <button className="fleet-arrow fleet-arrow-left" onClick={() => go('prev')} aria-label="Anterior">
          <ChevronLeft size={28} />
        </button>

        <div className="fleet-viewport">
          <div
            className="fleet-track"
            ref={trackRef}
            style={{ transform: `translateX(-${current * 100}%)` }}
          >
            {photos.map((photo, i) => (
              <div className="fleet-slide" key={i}>
                <img
                  src={photo.src}
                  alt={photo.alt}
                  loading={i < 3 ? 'eager' : 'lazy'}
                />
              </div>
            ))}
          </div>
        </div>

        <button className="fleet-arrow fleet-arrow-right" onClick={() => go('next')} aria-label="Siguiente">
          <ChevronRight size={28} />
        </button>
      </div>

      {/* Dots */}
      <div className="fleet-dots">
        {photos.map((_, i) => (
          <button
            key={i}
            className={`fleet-dot ${i === current ? 'fleet-dot-active' : ''}`}
            onClick={() => goTo(i)}
            aria-label={`Foto ${i + 1}`}
          />
        ))}
      </div>

      <div className="fleet-counter">
        {current + 1} / {photos.length}
      </div>
    </section>
  );
}
