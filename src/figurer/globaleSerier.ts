/**
 * S5, figur 12 — de globale satellittproduktene, hver for seg (CLAUDE.md § 8).
 *
 * Tre produkter i hver sin rute, med hver sin loddrette skala. De legges aldri
 * oppå hverandre: det er S1s oversiktsfigur som viser dem sammen, med synlige
 * brudd, og S5 skal ikke gjenta den (§ 8).
 *
 * Tidsaksen er felles, slik at ulik dekningsperiode blir synlig i seg selv —
 * hver kurve strekker seg bare over de årene produktet faktisk dekker.
 *
 * Kvaliteten styrer strekformen (§ 6): K8 er merket beta av produsenten og
 * tegnes med redusert opasitet, K9 og K1 er measured og tegnes heltrukket.
 */

import * as Plot from "@observablehq/plot";
import {
  serie,
  grunnlag,
  alleFotnoter,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { aarstall, tall } from "../lib/format";

const ENTITET = "WLD";

/** Seriene, i den rekkefølgen rutene står: eldste dekning øverst. */
const SERIER = [
  {
    id: "firecci_lt11_annual_burned_area",
    navn: "FireCCILT11",
    kilde: "K8",
    beta: true,
  },
  {
    id: "gfed5_annual_burned_area",
    navn: "GFED5",
    kilde: "K9",
    beta: false,
  },
  {
    id: "owid_annual_area_burnt",
    navn: "Our World in Data",
    kilde: "K1",
    beta: false,
  },
];

export const ID = "figur-globale-serier";

interface Punkt {
  aar: number;
  /** null der året mangler helt i kilden — se hullene under. */
  verdi: number | null;
  serie: string;
  ufullstendig: boolean;
}

function punkter(): Punkt[] {
  return SERIER.flatMap((s) => {
    const kjente: Punkt[] = serie(s.id, ENTITET).map((o) => ({
      aar: aarstall(o.period),
      verdi: o.value,
      serie: s.navn,
      ufullstendig: o.footnotes.includes("f_incomplete_year"),
    }));

    // Et år som mangler helt i kilden, tegnes som brudd i linjen — aldri som
    // null og aldri interpolert (§ 9). Et hull i punktene gir bruddet.
    // FireCCILT11 mangler 1994.
    const fra = kjente[0]!.aar;
    const til = kjente[kjente.length - 1]!.aar;
    const perAar = new Map(kjente.map((p) => [p.aar, p]));
    const medHull: Punkt[] = [];
    for (let aar = fra; aar <= til; aar++) {
      medHull.push(
        perAar.get(aar) ?? {
          aar,
          verdi: null,
          serie: s.navn,
          ufullstendig: false,
        },
      );
    }
    return medHull;
  });
}

function tegn(id: string, alle: Punkt[], bredde: number, hoyde: number) {
  // Hullene blir med i linjen, som da brytes der de står, men holdes utenfor
  // punktene — et hull har ingen verdi å tegne et punkt på.
  const hele = alle.filter((p) => !p.ufullstendig);
  const malte = hele.filter((p) => p.verdi !== null);
  const ufullstendige = alle.filter((p) => p.ufullstendig);

  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 84,
    marginRight: 24,
    marginBottom: 40,
    marginTop: 16,
    style: { background: "transparent", fontSize: "12px" },
    // Hvert produkt får sin egen rute og sin egen y-skala. Produktene ligger
    // på ulikt nivå, og en felles skala ville presset de laveste flate.
    facet: { data: alle, y: "serie", marginRight: 96 },
    fy: { label: null, domain: SERIER.map((s) => s.navn) },
    y: {
      label: "Brent areal (km²)",
      grid: true,
      tickFormat: (d: number) => tall(d),
    },
    x: { label: "År", tickFormat: (d: number) => String(d) },
    marks: [
      Plot.line(hele, {
        x: "aar",
        y: "verdi",
        fy: "serie",
        stroke: "var(--farge-serie)",
        // Produsentens beta-merking vises som svakere strek (§ 6). Merkingen
        // er produsentens, ikke vår vurdering, og forklares i tegnforklaringen.
        strokeOpacity: (d: { serie: string }) =>
          SERIER.find((s) => s.navn === d.serie)?.beta ? 0.5 : 1,
        strokeWidth: 1.75,
      }),
      // Et manglende år skal vises som brudd i kurven, ikke som null og ikke
      // som en beregnet mellomverdi (§ 9). Punktene gjør bruddet lesbart.
      Plot.dot(malte, {
        x: "aar",
        y: "verdi",
        fy: "serie",
        fill: "var(--farge-serie)",
        fillOpacity: (d: { serie: string }) =>
          SERIER.find((s) => s.navn === d.serie)?.beta ? 0.5 : 1,
        r: 1.6,
      }),
      // Inneværende år tegnes åpent, slik at det ikke leses som et helt år.
      Plot.dot(ufullstendige, {
        x: "aar",
        y: "verdi",
        fy: "serie",
        stroke: "var(--farge-serie)",
        fill: "var(--farge-flate)",
        strokeDasharray: "2,2",
        r: 3.5,
      }),
      Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ],
  });
}

export function globaleSerier() {
  const alle = punkter();

  const grunnlagPerSerie = SERIER.map((s) => ({ ...s, g: grunnlag(s.id) }));
  const fra = Math.min(...grunnlagPerSerie.map((s) => s.g.first_year));
  const til = Math.max(...alle.map((p) => p.aar));

  const observasjoner: Observasjon[] = SERIER.flatMap((s) =>
    serie(s.id, ENTITET),
  );

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const aarene = [...new Set(alle.map((p) => p.aar))].sort((a, b) => a - b);
  const perAar = new Map<number, Map<string, string>>();
  for (const p of alle) {
    if (p.verdi === null) continue;
    if (!perAar.has(p.aar)) perAar.set(p.aar, new Map());
    perAar.get(p.aar)!.set(p.serie, tall(p.verdi));
  }

  return {
    id: ID,
    tittel: "Globalt brent areal per år, én rute per satellittprodukt",
    svg: tegn(ID, alle, 760, 620),
    svgMobil: tegn(`${ID}-mobil`, alle, 360, 540),
    grafBeskrivelse:
      `Tre kurver i hver sin rute, som viser globalt brent areal i ` +
      `kvadratkilometer per år. ${grunnlagPerSerie
        .map((s) => `${s.navn} fra ${s.g.first_year} til ${s.g.last_complete_year}`)
        .join(", ")}. Hver rute har sin egen loddrette skala. ` +
      `Tallene står i tabellen under.`,
    kildeIder: SERIER.map((s) => s.kilde),
    dekningPerKilde: Object.fromEntries(
      grunnlagPerSerie.map((s) => [
        s.kilde,
        { fra: s.g.first_year, til: s.g.last_complete_year },
      ]),
    ),
    fotnoter,
    tegnforklaring: [
      {
        merke: "maalt",
        tekst: "Satellittmålt brent areal. Hver rute har sin egen skala — høyden kan ikke sammenlignes mellom rutene.",
      },
      {
        merke: "beta",
        tekst: "FireCCILT11 er tegnet svakere fordi produsenten selv merker datasettet som foreløpig.",
      },
      {
        merke: "ufullstendig-punkt",
        tekst: "Åpent punkt: inneværende år, som ikke er omme.",
      },
    ],
    tabell: {
      beskrivelse:
        "Globalt brent areal i km² per år og produkt. «Ingen data» betyr at " +
        "produktet ikke dekker året. Tallene er de samme som kurvene er " +
        "tegnet av.",
      kolonner: ["År", ...SERIER.map((s) => `${s.navn} (km²)`)],
      rader: aarene.map((aar) => [
        String(aar),
        ...SERIER.map((s) => perAar.get(aar)?.get(s.navn) ?? "ingen data"),
      ]),
    },
    observasjoner,
    csvFil: `${ID}.csv`,
    serier: grunnlagPerSerie.map((s) => ({
      navn: s.navn,
      seriesId: s.id,
      fra: s.g.first_year,
      til: s.g.last_complete_year,
      aar: s.g.last_complete_year - s.g.first_year + 1,
    })),
    dekning: { fra, til },
  };
}
