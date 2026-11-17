import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api, ApiError } from "../api";
import {
  ArrowMark,
  BagMark,
  CalendarMark,
  InfoMark,
  InstagramMark,
  PinMark,
} from "../components/brand/Marks";
import { ServiceBar } from "../ServiceBar";
import type { Category, HomePayload, HomeReview, Product } from "../types";
import { Alert, btn, btnGhost, btnLine, Pending, Reveal, useTitle } from "../ui";

export function Home() {
  useTitle("Commander");
  const [data, setData] = useState<HomePayload | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (!id) return;
    document.getElementById(id)?.scrollIntoView({ behavior: "instant", block: "start" });
  }, [data]);

  useEffect(() => {
    let cancel = false;
    api<HomePayload>("/api/accueil")
      .then((payload) => {
        if (!cancel) setData(payload);
      })
      .catch((error: unknown) => {
        if (!cancel) setErrors([error instanceof ApiError ? error.message : "Connexion interrompue. Réessayez."]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const loading = !data && !errors.length;
  const featured = data?.featured ?? [];
  const lead = featured.find((item) => item.image) ?? featured[0];
  const categories = data?.categories ?? [];
  const restaurant = data?.restaurant;

  return (
    <>
      <section id="accueil" className="home-hero" aria-labelledby="home-hero-title">
        <div className="home-hero__media" aria-hidden="true">
          <img
            className="home-hero__photo"
            src={`${import.meta.env.BASE_URL}images/burger-hero.jpg`}
            alt=""
            width={1310}
            height={831}
            fetchPriority="high"
            decoding="async"
          />
        </div>
        <div className="home-hero__panel" aria-hidden="true" />

        <div className="home-hero__content">
          <div className="home-hero__copy">
            <p className="home-hero__eyebrow motion-rise">Afro street food · Noisy-le-Sec</p>
            <h1 id="home-hero-title" className="home-hero__title motion-rise motion-d1">
              L&apos;Afrique servie
              <br />
              <span className="home-hero__title-accent">à grande vitesse</span>
            </h1>
            <p className="home-hero__lead motion-rise motion-d2">
              Burgers yassa, bowls à composer, wings et alloko. Vous choisissez, vous personnalisez, vous retirez au comptoir.
            </p>
            <div className="home-hero__actions motion-rise motion-d3">
              <Link className="home-hero__btn home-hero__btn--primary" to="/carte">
                Commander
                <ArrowMark className="h-3.5 w-3.5" />
              </Link>
              <Link className="home-hero__btn home-hero__btn--ghost" to="/signature">
                Les spécialités
              </Link>
            </div>
          </div>
        </div>

        <img
          className="home-hero__photo-mobile"
          src={`${import.meta.env.BASE_URL}images/burger-hero.jpg`}
          alt="Burger yassa ALLOKODRONE"
          width={1310}
          height={831}
          decoding="async"
        />
      </section>

      <ServiceBar />

      <div className="mx-auto max-w-6xl px-4 pt-5 md:px-5">
        <Alert errors={errors} />
        {loading ? <Pending /> : null}
      </div>

      <section id="signatures" className="scroll-mt-24 overflow-x-clip bg-paper text-ink">
        <Reveal className="mx-auto max-w-6xl px-4 py-10 lg:py-14">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">Notre signature</p>
            <h2 className="mt-3 max-w-[16ch] font-display text-[clamp(2.1rem,8vw,3.75rem)] leading-[0.92]">
              Des recettes qui font <span className="italic text-terracotta">voyager</span>
            </h2>
          </div>
          <div className="mt-8 grid min-w-0 items-stretch gap-7 sm:mt-10 sm:gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:gap-12">
            {lead ? <Feature lead={lead} large film={data?.signatureVideo} /> : <div className="bg-paper-2" aria-hidden="true" />}
            <div className="flex min-h-0 min-w-0 flex-col">
              <div className="min-h-0 max-h-[min(24rem,62vh)] flex-1 overflow-y-auto overscroll-contain rounded-xl border border-line bg-cream [scrollbar-color:rgba(37,26,22,0.25)_transparent] [scrollbar-width:thin] sm:max-h-[min(28rem,64vh)] lg:max-h-[min(42rem,82vh)]">
                <ul className="flex flex-col" aria-label="Catégories">
                  {categories.map((category, index) => (
                    <li key={category.slug} className="border-b border-line last:border-b-0">
                      <CategoryRow category={category} index={index} />
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-4 flex justify-end">
                <Link className={`${btn} w-full sm:w-auto`} to="/carte">
                  Voir la carte
                </Link>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      <section id="histoire" className="scroll-mt-24 bg-night text-cream">
        <Reveal className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-10 md:px-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-12 lg:py-14">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">Histoire</p>
            <h2 className="mt-3 font-display text-[clamp(2.1rem,8vw,3.75rem)] leading-[0.92]">
              Le goût voyage <span className="italic text-terracotta">autrement</span>
            </h2>
            <div className="mt-6 space-y-4 text-base leading-relaxed text-cream/75">
              <p>
                ALLOKODRONE, c'est une cuisine africaine faite maison, inspirée des recettes qui accompagnent les repas de famille, les moments entre amis et les grandes occasions.
              </p>
              <p>
                Notre carte met à l'honneur des plats riches en caractère : viandes braisées, marinades travaillées, sauces parfumées et accompagnements emblématiques.
              </p>
            </div>
            <p className="mt-8 font-display text-2xl leading-tight sm:text-3xl">
              ALLOKODRONE, la cuisine africaine d'aujourd'hui.
            </p>
            <Link className={`${btnGhost} mt-8`} to="/concept">Lire l'histoire</Link>
          </div>
          <span className="block overflow-hidden rounded-bl-[2rem] lg:rounded-bl-[3rem]">
            <img
              className="bowl-motion aspect-[5/4] w-full object-cover object-center"
              src={`${import.meta.env.BASE_URL}images/bowl.jpg`}
              alt="Bowl ALLOKODRONE"
              loading="lazy"
            />
          </span>
        </Reveal>
      </section>

      <section id="avis" className="scroll-mt-24 bg-paper-2">
        <Reveal className="mx-auto max-w-6xl px-4 py-10 md:px-5 lg:py-14">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div className="max-w-2xl">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">Avis</p>
              <h2 className="mt-3 font-display text-[clamp(2.1rem,8vw,3.75rem)] leading-[0.92] text-ink">
                Ils ont goûté, <span className="italic text-terracotta">ils témoignent</span>
              </h2>
            </div>
            {data?.avis && data.avis.count > 0 && data.avis.average != null ? (
              <div className="rounded-xl border border-line bg-cream px-5 py-4">
                <p className="font-display text-4xl leading-none text-ink">
                  {String(data.avis.average).replace(".", ",")}
                </p>
                <HomeStars value={Math.round(data.avis.average)} label={`${String(data.avis.average).replace(".", ",")} sur 5`} />
                <p className="mt-2 text-sm text-ink-soft">{data.avis.count} avis</p>
              </div>
            ) : null}
          </div>

          {restaurant ? (
            <div className="mt-10 grid items-stretch gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
              <figure className="flex h-full flex-col rounded-xl border border-line bg-cream px-6 py-8 sm:px-8">
                <p className="text-xs uppercase tracking-[0.16em] text-terracotta">{restaurant.review.source}</p>
                <blockquote className="mt-5 flex-1 border-l-2 border-terracotta pl-5">
                  <p className="font-display text-lg leading-relaxed text-ink sm:text-xl">
                    « {restaurant.review.quote} »
                  </p>
                </blockquote>
                <figcaption className="mt-8 flex flex-wrap items-baseline justify-between gap-3 border-t border-line pt-5 text-sm">
                  <span className="font-medium text-ink">{restaurant.review.author}</span>
                  <span className="text-ink-soft">{restaurant.review.place}</span>
                </figcaption>
              </figure>

              <div className="flex h-full flex-col justify-between gap-6 rounded-xl border border-line bg-cream px-6 py-8 text-ink sm:px-8">
                <div>
                  <h3 className="font-display text-2xl leading-none text-ink">Répartition</h3>
                  <ul className="mt-6 space-y-4" aria-label="Répartition des notes">
                    {(data?.avis?.histogram ?? [5, 4, 3, 2, 1].map((stars) => ({ stars, count: 0 }))).map((item) => {
                      const max = Math.max(1, ...(data?.avis?.histogram ?? []).map((row) => row.count), 1);
                      return (
                        <li key={item.stars} className="flex items-center gap-3">
                          <span className="w-8 shrink-0 text-sm tabular-nums">{item.stars}★</span>
                          <span className="h-1.5 flex-1 overflow-hidden bg-paper-2">
                            <span
                              className="block h-full bg-terracotta transition-[width] duration-700 ease-out"
                              style={{ width: `${item.count ? Math.max(10, (item.count / max) * 100) : 0}%` }}
                            />
                          </span>
                          <span className="w-6 shrink-0 text-right text-sm tabular-nums text-ink-soft">{item.count}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
                <Link className={`${btn} w-full sm:w-auto`} to="/avis">
                  Tous les avis
                </Link>
              </div>
            </div>
          ) : null}

          {data?.avis?.reviews?.length ? (
            <ul className="mt-8 grid gap-4 md:grid-cols-3">
              {data.avis.reviews.map((item) => (
                <li key={item.id}>
                  <HomeReviewCard review={item} />
                </li>
              ))}
            </ul>
          ) : null}
        </Reveal>
      </section>

      {restaurant ? (
        <section id="contact" className="scroll-mt-24 bg-paper">
          <Reveal className="mx-auto max-w-6xl px-4 py-10 sm:py-12 lg:px-8">
            <div className="grid items-center gap-6 md:grid-cols-2 md:gap-8">
              <div className="overflow-hidden rounded-2xl bg-[#1a110d]">
                <img
                  className="aspect-[4/3] w-full object-cover object-center"
                  src={`${import.meta.env.BASE_URL}images/storefront.jpg`}
                  alt="Devanture ALLOKODRONE, 24 rue Emmanuel Arago à Noisy-le-Sec"
                  loading="lazy"
                />
              </div>
              <div className="min-w-0 text-ink lg:py-2">
                <div className="flex items-center gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-terracotta">Contact</p>
                  <span className="h-px w-12 bg-terracotta sm:w-16" aria-hidden="true" />
                </div>
                <h2 className="mt-3 font-display text-3xl leading-[0.92] sm:text-4xl lg:text-5xl">Nous trouver</h2>
                <ul className="mt-7 space-y-3.5 text-[0.95rem] leading-relaxed text-ink">
                  <li className="flex items-start gap-3">
                    <PinMark className="mt-0.5 h-5 w-5 shrink-0 text-terracotta" />
                    <span>{restaurant.address}</span>
                  </li>
                  {(restaurant.hoursLines ?? [restaurant.hoursLabel]).map((line) => (
                    <li key={line} className="flex items-start gap-3">
                      <CalendarMark className="mt-0.5 h-5 w-5 shrink-0 text-terracotta" />
                      <span>{line.replace(/ · /g, " : ")}</span>
                    </li>
                  ))}
                  <li className="flex items-start gap-3">
                    <BagMark className="mt-0.5 h-5 w-5 shrink-0 text-terracotta" />
                    <span>
                      Retrait au comptoir
                      {restaurant.deliveryOpen ? " · Livraison ouverte" : " · Livraison fermée"}
                    </span>
                  </li>
                </ul>
                <div className="mt-8 flex flex-wrap items-center gap-2.5">
                  <a className={`${btn} gap-2`} href={restaurant.maps} target="_blank" rel="noopener noreferrer">
                    Itinéraire
                    <ArrowMark />
                  </a>
                  <span className="inline-flex flex-wrap items-center gap-2.5">
                    <a
                      className={`${btnLine} gap-2`}
                      href={restaurant.instagram}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <InstagramMark />
                      Instagram
                    </a>
                    <Link className={`${btnLine} gap-2`} to="/contact">
                      <InfoMark />
                      Plus d&apos;infos
                    </Link>
                  </span>
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      ) : null}
    </>
  );
}

function HomeStars({ value, label }: { value: number; label: string }) {
  return (
    <span className="mt-2 inline-flex gap-1.5" role="img" aria-label={label}>
      {[1, 2, 3, 4, 5].map((star) => (
        <svg key={star} viewBox="0 0 24 24" className={`h-4 w-4 ${star <= value ? "text-terracotta" : "text-line"}`} aria-hidden="true">
          <path fill="currentColor" d="M12 2.6 14.6 8.7l6.6.6-5 4.3 1.5 6.4L12 16.8 6.3 20l1.5-6.4-5-4.3 6.6-.6L12 2.6z" />
        </svg>
      ))}
    </span>
  );
}

function HomeReviewCard({ review }: { review: HomeReview }) {
  return (
    <article className="flex h-full flex-col rounded-xl border border-line bg-cream px-5 py-6 transition-[border-color,transform] duration-300 hover:-translate-y-0.5 hover:border-terracotta/40">
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-paper-2 font-display text-sm text-terracotta" aria-hidden="true">
            {review.initials}
          </span>
          <div>
            <p className="text-sm font-medium text-ink">{review.author}</p>
            <p className="text-xs text-ink-soft">{review.dateLabel}</p>
          </div>
        </div>
        <HomeStars value={review.stars} label={`${review.stars} sur 5`} />
      </header>
      {review.verified ? (
        <p className="mt-4 inline-flex w-fit border border-line px-2 py-1 text-[0.65rem] uppercase tracking-[0.14em] text-ink-soft">
          Achat vérifié
        </p>
      ) : null}
      <p className="mt-4 flex-1 text-sm leading-relaxed text-ink">« {review.body} »</p>
    </article>
  );
}

function SignatureFilm({ src, poster, label }: { src: string; poster?: string; label: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const node = ref.current;
    if (!node || reduce) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) {
        node.pause();
        return;
      }
      void node.play().catch(() => undefined);
    }, { threshold: 0.45 });
    observer.observe(node);
    return () => observer.disconnect();
  }, [reduce]);

  if (reduce && poster) {
    return <img className="signature-diagonal__media" src={poster} alt={label} />;
  }

  return (
    <video
      ref={ref}
      className="signature-diagonal__media"
      src={src}
      poster={poster}
      muted
      loop
      playsInline
      preload="metadata"
      aria-label={label}
    />
  );
}

const CATEGORY_IMAGES: Record<string, string> = {
  burgers: "/images/burger.jpg",
  bowls: "/images/bowl.jpg",
  sides: "/images/wings.jpg",
  plats: "/images/bowl.jpg",
  boissons: "/images/alloko.jpg",
  desserts: "/images/alloko.jpg",
  midi: "/images/bowl.jpg",
};

function CategoryMark({ flip }: { flip?: boolean }) {
  return (
    <span className={`category-mark ${flip ? "category-mark--flip" : ""}`} aria-hidden="true">
      <svg viewBox="0 0 24 22" className="h-4 w-4 sm:h-[1.15rem] sm:w-[1.15rem]">
        <path
          d="M12 2.8 21.2 18.6H2.8L12 2.8Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}

function CategoryRow({ category, index }: { category: Category; index: number }) {
  const crop = category.slug === "bowls" || category.slug === "plats" || category.slug === "midi" ? "object-[center_22%]" : "object-center";
  const image = category.image || CATEGORY_IMAGES[category.slug] || null;
  const flip = index % 2 === 1;
  return (
    <Link
      className="group flex w-full items-start gap-2.5 px-4 py-4 sm:gap-3.5 sm:px-5"
      to={`/carte?categorie=${category.slug}`}
    >
      <CategoryMark flip={flip} />
      {image ? (
        <span className="mt-0.5 block h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-paper-2 sm:h-16 sm:w-16">
          <img
            className={`h-full w-full object-cover transition duration-700 ease-out group-hover:scale-105 ${crop}`}
            src={image}
            alt=""
            loading="lazy"
          />
        </span>
      ) : (
        <span className="mt-0.5 flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-paper-2 font-display text-xl text-terracotta sm:h-16 sm:w-16" aria-hidden="true">
          {category.name.trim().charAt(0)}
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-3">
          <span className="font-display text-2xl leading-none text-ink transition-colors duration-300 group-hover:text-terracotta sm:text-3xl">
            {category.name}
          </span>
          <span className="w-8 shrink-0 text-right text-xs tabular-nums text-ink-soft transition-colors duration-300 group-hover:text-terracotta">
            {String(index + 1).padStart(2, "0")}
          </span>
        </span>
        {category.description ? (
          <span className="mt-2 block text-sm leading-relaxed text-ink-soft">
            {category.description}
          </span>
        ) : null}
      </span>
    </Link>
  );
}

function Feature({ lead, large = false, film = null }: { lead: Product; large?: boolean; film?: string | null }) {
  const crop = lead.slug === "bowl" ? "object-[center_22%]" : "object-center";
  return (
    <Link
      className={large ? "group block w-full min-w-0" : "group flex w-full items-start gap-3 py-3.5"}
      to={`/produit/${lead.slug}`}
    >
      {large ? (
        <span className="signature-diagonal">
          <span className="signature-diagonal__stage">
            {film ? (
              <SignatureFilm src={film} poster={lead.image ?? undefined} label={lead.name} />
            ) : lead.image ? (
              <img
                className={`signature-diagonal__media ${crop}`}
                src={lead.image}
                alt=""
                loading="lazy"
              />
            ) : null}
          </span>
        </span>
      ) : lead.image ? (
        <span className="block h-14 w-14 shrink-0 overflow-hidden bg-night-2 sm:h-16 sm:w-16">
          <img
            className={`h-full w-full object-cover transition duration-700 ease-out group-hover:scale-105 ${crop}`}
            src={lead.image}
            alt=""
            loading="lazy"
          />
        </span>
      ) : (
        <span className="flex h-14 w-14 shrink-0 items-center justify-center bg-night-2 font-display text-xl text-terracotta sm:h-16 sm:w-16" aria-hidden="true">
          {lead.name.trim().charAt(0)}
        </span>
      )}
      <span className={large ? "mt-4 block min-w-0 px-0.5 sm:mt-5" : "min-w-0 flex-1"}>
        <span className="text-[0.65rem] uppercase tracking-[0.16em] text-terracotta sm:text-xs">{lead.categoryName}</span>
        <span className={`mt-1 block font-display leading-tight text-ink group-hover:text-terracotta ${large ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl"}`}>
          {lead.name}
        </span>
        <span className={`mt-1.5 text-sm leading-relaxed text-ink-soft ${large ? "line-clamp-3" : "line-clamp-2"}`}>{lead.description}</span>
      </span>
    </Link>
  );
}
