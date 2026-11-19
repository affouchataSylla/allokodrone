import { Link } from "react-router";
import { btn, btnLine } from "../../ui";
import { PinMark } from "./icons";

type BrandCtaProps = {
  slogan: string;
  address: string;
  mapsUrl?: string;
};

function Slogan({ text }: { text: string }) {
  const match = text.match(/^(ALLOKODRONE)([,\s].*)$/i);
  if (!match) {
    return <>{text}</>;
  }
  return (
    <>
      <span className="text-terracotta">{match[1]}</span>
      {match[2]}
    </>
  );
}

export function BrandCta({ slogan, address, mapsUrl }: BrandCtaProps) {
  return (
    <section className="mx-auto max-w-[68rem] px-4 pb-8 pt-5 sm:px-6 sm:pb-10 sm:pt-7 lg:px-8 lg:py-10">
      <div className="flex items-center gap-4 sm:gap-6 lg:gap-7">
        <img
          className="h-14 w-auto max-w-[7.5rem] shrink-0 object-contain object-left sm:h-20 sm:max-w-[13rem] lg:h-24 lg:max-w-[15rem]"
          src={`${import.meta.env.BASE_URL}images/logo-dark.png`}
          width={532}
          height={299}
          alt="ALLOKODRONE"
          decoding="async"
          loading="lazy"
        />
        <span className="h-12 w-px shrink-0 bg-terracotta sm:h-16" aria-hidden="true" />
        <p className="min-w-0 font-display text-[1.25rem] font-semibold leading-[1.25] tracking-[-0.02em] text-ink sm:text-[1.85rem] lg:text-[2.05rem]">
          <Slogan text={slogan} />
        </p>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:mt-6 sm:flex-row sm:flex-wrap">
        <Link className={`${btn} w-full sm:w-auto`} to="/carte">
          Voir la carte →
        </Link>
        <Link className={`${btnLine} w-full border-ink/25 bg-cream sm:w-auto`} to="/contact">
          Nous trouver
        </Link>
      </div>

      {mapsUrl ? (
        <a
          className="mt-4 inline-flex max-w-full items-start gap-2.5 text-[0.92rem] leading-snug text-ink transition-colors hover:text-terracotta"
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          <PinMark className="mt-0.5 h-4 w-4 shrink-0 text-terracotta" />
          <span className="min-w-0">{address}</span>
        </a>
      ) : (
        <p className="mt-4 flex max-w-full items-start gap-2.5 text-[0.92rem] leading-snug text-ink">
          <PinMark className="mt-0.5 h-4 w-4 shrink-0 text-terracotta" />
          <span className="min-w-0">{address}</span>
        </p>
      )}
    </section>
  );
}
