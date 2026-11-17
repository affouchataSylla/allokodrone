import { useEffect, useRef, useState } from "react";

const LAT = 48.8039;
const LON = 2.4638;
const OSM = `https://www.openstreetmap.org/export/embed.html?bbox=${LON - 0.012}%2C${LAT - 0.008}%2C${LON + 0.012}%2C${LAT + 0.008}&layer=mapnik&marker=${LAT}%2C${LON}`;

function DroneGlyph() {
  return (
    <g transform="translate(-18 -10)">
      <path
        d="M2 10h10l3 3h14l3-3h10M6 10 3 5M32 10l3-5M8 5h5M27 5h5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <ellipse cx="20" cy="18" rx="9" ry="5" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </g>
  );
}

export function ContactMap() {
  const bandRef = useRef<HTMLDivElement>(null);
  const [landed, setLanded] = useState(false);
  const [flying, setFlying] = useState(false);

  useEffect(() => {
    const band = bandRef.current;
    if (!band) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setLanded(true);
      return;
    }

    let timer = 0;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setFlying(true);
        timer = window.setTimeout(() => {
          const motion = band.querySelector("animateMotion");
          if (motion instanceof SVGAnimateMotionElement) {
            try {
              motion.beginElement();
            } catch {
              setLanded(true);
            }
          }
        }, 600);
        observer.disconnect();
      },
      { threshold: 0.35 },
    );
    observer.observe(band);
    return () => {
      observer.disconnect();
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <section className="contact-map-band" aria-label="Plan d'accès AlloKoDrone">
      <div
        className={`contact-map-frame${flying ? " is-flying" : ""}${landed ? " is-landed" : ""}`}
        ref={bandRef}
      >
        <div className="contact-map-stage">
          <iframe
            className="contact-map-iframe"
            title="Plan OpenStreetMap — 24 rue Emmanuel Arago, Noisy-le-Sec"
            src={OSM}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
          <div className="contact-map-veil" aria-hidden="true" />

          <svg
            className="contact-map-overlay"
            viewBox="0 0 1000 380"
            role="img"
            aria-label="Trajet du drone jusqu'au restaurant AlloKoDrone"
          >
            <path
              id="contact-drone-path"
              d="M0 210 C 180 210, 260 120, 420 140 S 680 250, 780 200"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray="7 9"
              className="contact-flight-line"
            />
            <g className="contact-pin">
              <circle cx="780" cy="200" r="10" fill="currentColor" />
              <circle cx="780" cy="200" r="18" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.55" />
            </g>
            {landed ? (
              <g className="contact-drone is-visible" aria-hidden="true" transform="translate(780 200)">
                <DroneGlyph />
              </g>
            ) : (
              <g className={`contact-drone${flying ? " is-visible" : ""}`} aria-hidden="true">
                <DroneGlyph />
                <animateMotion
                  dur="5s"
                  begin="indefinite"
                  fill="freeze"
                  rotate="auto"
                  calcMode="spline"
                  keyTimes="0;1"
                  keySplines="0.4 0 0.2 1"
                >
                  <mpath href="#contact-drone-path" />
                </animateMotion>
              </g>
            )}
          </svg>

          <p className="contact-map-tag">
            AlloKoDrone
            <span>24 rue Emmanuel Arago</span>
          </p>
        </div>
        <p className="contact-map-caption">Comptoir ou drone, le bowl arrive chaud jusqu&apos;à vous.</p>
      </div>
    </section>
  );
}
