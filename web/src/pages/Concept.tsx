import { BrandCta } from "../components/concept/BrandCta";
import { ConceptHero } from "../components/concept/ConceptHero";
import { QuoteBand } from "../components/concept/QuoteBand";
import { ValueGrid } from "../components/concept/ValueGrid";
import { useSession } from "../session";
import { useTitle } from "../ui";

const VALUES = [
  {
    title: "Fait maison",
    body: "Recettes des repas de famille, des moments entre amis et des grandes occasions.",
  },
  {
    title: "Des plats de caractère",
    body: "Viandes braisées, marinades travaillées, sauces parfumées.",
  },
  {
    title: "Un univers actuel",
    body: "La qualité, la régularité et le plaisir de chaque bouchée.",
  },
] as const;

export function Concept() {
  useTitle("Concept");
  const { session } = useSession();
  const restaurant = session?.restaurant;
  const address = restaurant?.address || "24 rue Emmanuel Arago, 93130 Noisy-le-Sec";
  const maps =
    restaurant?.maps ||
    "https://www.google.com/maps/dir/?api=1&destination=24+rue+Emmanuel+Arago+93130+Noisy-le-Sec";

  return (
    <article className="min-w-0 overflow-x-clip bg-paper text-ink">
      <ConceptHero
        title="Le goût voyage autrement"
        lead="ALLOKODRONE, c'est une cuisine africaine faite maison, inspirée des repas de famille et des grandes occasions."
        imageAlt="Bowl AlloKoDrone avec poulet effiloché, oignons caramélisés, riz et plantains frits"
      />
      <ValueGrid values={VALUES} />
      <QuoteBand>
        Pour certains, un <span className="text-terracotta">souvenir familier</span>. Pour d&apos;autres, une porte
        d&apos;entrée vers une <span className="text-terracotta">cuisine encore méconnue</span>. Une cuisine authentique
        dans un <span className="text-terracotta">univers actuel</span>.
      </QuoteBand>
      <BrandCta
        slogan="ALLOKODRONE, la cuisine africaine d'aujourd'hui."
        address={address}
        mapsUrl={maps}
      />
    </article>
  );
}
