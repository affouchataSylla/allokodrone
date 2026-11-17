type ConceptHeroProps = {
  eyebrow?: string;
  title: string;
  lead: string;
  imageAlt: string;
  imageSrc?: string;
  imageWidth?: number;
  imageHeight?: number;
};

const ALT_DEFAULT =
  "Bowl AlloKoDrone avec poulet effiloché, oignons caramélisés, riz et plantains frits";

export function ConceptHero({
  eyebrow = "Notre concept",
  title,
  lead,
  imageAlt = ALT_DEFAULT,
  imageSrc = `${import.meta.env.BASE_URL}images/bowl-concept.png`,
  imageWidth = 1024,
  imageHeight = 603,
}: ConceptHeroProps) {
  const titleId = "concept-title";

  return (
    <section className="concept-reveal bg-paper" aria-labelledby={titleId}>
      {/* Mobile : image plein cadre comme la maquette */}
      <figure className="m-0 lg:hidden">
        <img
          className="block h-auto w-full object-cover object-center"
          src={imageSrc}
          width={imageWidth}
          height={imageHeight}
          alt={imageAlt}
          decoding="async"
          fetchPriority="high"
        />
      </figure>

      <div className="mx-auto grid max-w-[78rem] items-center gap-8 px-4 py-7 sm:px-6 sm:py-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.25fr)] lg:gap-10 lg:px-8 lg:py-12 xl:gap-12">
        <div className="min-w-0">
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-terracotta">
            {eyebrow}
          </p>
          <h1
            id={titleId}
            className="mt-2 max-w-[16ch] font-display text-[clamp(2.05rem,7.5vw,3.15rem)] font-semibold leading-[0.95] tracking-[-0.03em] text-ink"
          >
            {title === "Le goût voyage autrement" ? (
              <>
                Le goût voyage
                <br />
                autrement
              </>
            ) : (
              title
            )}
          </h1>
          <p className="mt-4 max-w-[32rem] text-[0.98rem] leading-[1.6] text-ink sm:text-base">
            {lead}
          </p>
        </div>

        <figure className="m-0 hidden w-full overflow-visible justify-self-stretch lg:block">
          <img
            className="concept-bowl-img"
            src={imageSrc}
            width={imageWidth}
            height={imageHeight}
            alt=""
            decoding="async"
            aria-hidden="true"
          />
        </figure>
      </div>
    </section>
  );
}
