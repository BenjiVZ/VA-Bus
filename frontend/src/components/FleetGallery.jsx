import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Bus } from 'lucide-react';

// Photos in /public/flota/ — referenced by direct URL (no import)
const BUS_NUMBERS = ['01','02','03','04','05','06','07','09'];
const photos = BUS_NUMBERS.map((num, i) => ({
  src: `/flota/bus-${num}.jpg`,
  alt: `Autobús Aerorutas de Venezuela #${num}`,
  number: num,
  label: `Unidad ${num}`,
}));

const AUTOPLAY_MS = 4000;
const RESUME_DELAY_MS = 8000;

export default function FleetGallery() {
  const [current, setCurrent] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const [progressWidth, setProgressWidth] = useState(0);
  const [progressAnimating, setProgressAnimating] = useState(false);

  const timerRef = useRef(null);
  const resumeRef = useRef(null);
  const touchStartX = useRef(null);
  const thumbsRef = useRef(null);

  // ── Auto-play logic ──
  useEffect(() => {
    if (!isAutoPlaying) {
      setProgressAnimating(false);
      setProgressWidth(0);
      return;
    }

    // Kick off progress animation
    setProgressWidth(0);
    // Force reflow so the browser registers 0% before animating to 100%
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setProgressAnimating(true);
        setProgressWidth(100);
      });
    });

    timerRef.current = setInterval(() => {
      setCurrent(prev => (prev + 1) % photos.length);
      // Reset progress
      setProgressAnimating(false);
      setProgressWidth(0);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setProgressAnimating(true);
          setProgressWidth(100);
        });
      });
    }, AUTOPLAY_MS);

    return () => {
      clearInterval(timerRef.current);
      cancelAnimationFrame(raf);
    };
  }, [isAutoPlaying]);

  // ── Manual navigation helpers ──
  const pauseAutoPlay = useCallback(() => {
    setIsAutoPlaying(false);
    clearTimeout(resumeRef.current);
    resumeRef.current = setTimeout(() => setIsAutoPlaying(true), RESUME_DELAY_MS);
  }, []);

  const go = useCallback((dir) => {
    pauseAutoPlay();
    setCurrent(prev => {
      if (dir === 'next') return (prev + 1) % photos.length;
      return (prev - 1 + photos.length) % photos.length;
    });
  }, [pauseAutoPlay]);

  const goTo = useCallback((idx) => {
    pauseAutoPlay();
    setCurrent(idx);
  }, [pauseAutoPlay]);

  // ── Hover pause ──
  const handleMouseEnter = () => {
    if (isAutoPlaying) {
      clearInterval(timerRef.current);
      setProgressAnimating(false);
    }
  };

  const handleMouseLeave = () => {
    if (isAutoPlaying) {
      // Restart the auto-play cycle
      setProgressWidth(0);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setProgressAnimating(true);
          setProgressWidth(100);
        });
      });
      timerRef.current = setInterval(() => {
        setCurrent(prev => (prev + 1) % photos.length);
        setProgressAnimating(false);
        setProgressWidth(0);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setProgressAnimating(true);
            setProgressWidth(100);
          });
        });
      }, AUTOPLAY_MS);
    }
  };

  // ── Touch / Swipe support ──
  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e) => {
    if (touchStartX.current === null) return;
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) {
      go(diff > 0 ? 'next' : 'prev');
    }
    touchStartX.current = null;
  };

  // ── Keyboard navigation ──
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowLeft') go('prev');
    if (e.key === 'ArrowRight') go('next');
  };

  // ── Scroll active thumb into view (without moving the page) ──
  useEffect(() => {
    const container = thumbsRef.current;
    if (container) {
      const activeThumb = container.children[current];
      if (activeThumb) {
        const thumbLeft = activeThumb.offsetLeft;
        const thumbWidth = activeThumb.offsetWidth;
        const containerWidth = container.offsetWidth;
        const scrollTarget = thumbLeft - containerWidth / 2 + thumbWidth / 2;
        container.scrollTo({ left: scrollTarget, behavior: 'smooth' });
      }
    }
  }, [current]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      clearTimeout(resumeRef.current);
    };
  }, []);

  return (
    <section className="fleet-gallery">
      {/* Section header */}
      <span className="section-label">
        <Bus size={14} />
        NUESTRA FLOTA
      </span>
      <h3 className="fleet-gallery-title">Conoce nuestros autobuses</h3>
      <p className="fleet-gallery-subtitle">
        Viaja con comodidad y seguridad en unidades modernas
      </p>

      {/* Carousel */}
      <div
        className="fleet-carousel"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="region"
        aria-label="Galería de autobuses"
        aria-roledescription="carousel"
      >
        {/* Counter badge */}
        <div className="fleet-counter-badge">
          {current + 1} / {photos.length}
        </div>

        {/* Arrows */}
        <button
          className="fleet-arrow fleet-arrow-left"
          onClick={() => go('prev')}
          aria-label="Foto anterior"
        >
          <ChevronLeft size={22} />
        </button>

        {/* Viewport with crossfade slides */}
        <div className="fleet-viewport">
          {photos.map((photo, i) => (
            <div
              className={`fleet-slide ${i === current ? 'fleet-slide-active' : ''}`}
              key={i}
              role="group"
              aria-roledescription="slide"
              aria-label={`${i + 1} de ${photos.length}`}
              aria-hidden={i !== current}
            >
              <div
                className="fleet-slide-bg"
                style={{ backgroundImage: `url(${photo.src})` }}
              />
              <img
                src={photo.src}
                alt={photo.alt}
                loading={i < 3 ? 'eager' : 'lazy'}
                draggable={false}
              />
              {/* Bus badge overlay */}
              <div className="fleet-badge">
                <span className="fleet-badge-icon">
                  <Bus size={16} />
                </span>
                <span className="fleet-badge-text">
                  <span className="fleet-badge-number">Bus #{photo.number}</span>
                  <span className="fleet-badge-label">Aerorutas de Venezuela</span>
                </span>
              </div>
            </div>
          ))}
        </div>

        <button
          className="fleet-arrow fleet-arrow-right"
          onClick={() => go('next')}
          aria-label="Foto siguiente"
        >
          <ChevronRight size={22} />
        </button>

        {/* Progress bar */}
        <div className="fleet-progress-bar">
          <div
            className={`fleet-progress-fill ${progressAnimating ? 'fleet-progress-animating' : ''}`}
            style={{ width: `${progressWidth}%` }}
          />
        </div>
      </div>

      {/* Thumbnails strip */}
      <div className="fleet-thumbs" ref={thumbsRef}>
        {photos.map((photo, i) => (
          <button
            key={i}
            className={`fleet-thumb ${i === current ? 'fleet-thumb-active' : ''}`}
            onClick={() => goTo(i)}
            aria-label={`Ver bus #${photo.number}`}
          >
            <img
              src={photo.src}
              alt=""
              loading="lazy"
              draggable={false}
            />
          </button>
        ))}
      </div>
    </section>
  );
}
