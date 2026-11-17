import { useEffect } from "react";
import { Link } from "react-router";
import { ContactMap } from "../components/contact/ContactMap";
import { ContactSteps } from "../components/contact/ContactSteps";
import { HoursTicket } from "../components/contact/HoursTicket";
import { InstagramMark } from "../components/brand/Marks";
import { useSession } from "../session";
import { Pending, useTitle } from "../ui";

export function Contact() {
  useTitle("Contact");
  const { session } = useSession();
  const restaurant = session?.restaurant;

  useEffect(() => {
    if (!restaurant || window.location.hash !== "#horaires") return;
    document.getElementById("horaires")?.scrollIntoView();
  }, [restaurant]);

  if (!restaurant) {
    return (
      <div className="mx-auto max-w-3xl px-4">
        <Pending label="Chargement" />
      </div>
    );
  }

  const street = "24 rue Emmanuel Arago";
  const city = "93130 Noisy-le-Sec";
  const deliveryLine = restaurant.deliveryOpen
    ? "Le retrait se fait au comptoir. La livraison est ouverte."
    : "Le retrait se fait au comptoir. La livraison est fermée.";

  return (
    <article className="contact-page">
      <div className="contact-shell">
        <div className="contact-hero-grid">
          <div className="contact-copy">
            <p className="contact-eyebrow">Contact</p>
            <h1 className="contact-kicker">Nous trouver</h1>
            <address className="contact-address">
              <span className="contact-street">{street}</span>
              <span className="contact-city">{city}</span>
            </address>
            <p className="contact-lead">{deliveryLine}</p>
            <div className="contact-actions">
              <a className="contact-btn" href={restaurant.maps} target="_blank" rel="noopener noreferrer">
                Itinéraire
              </a>
              <span className="contact-actions-pair">
                <a
                  className="contact-ig"
                  href={restaurant.instagram}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <InstagramMark className="h-4 w-4" />
                  Instagram
                </a>
                <a className="contact-ig" href="#horaires">
                  Horaires
                </a>
              </span>
            </div>
            <Link className="contact-carte-link" to="/carte">
              Voir la carte →
            </Link>
            <ContactMap />
          </div>
          <HoursTicket deliveryOpen={restaurant.deliveryOpen} />
        </div>

        <ContactSteps />
      </div>
    </article>
  );
}
