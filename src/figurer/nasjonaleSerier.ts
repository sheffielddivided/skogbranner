/**
 * S5, figur 13 — de to lange nasjonale seriene (CLAUDE.md § 8).
 *
 * USA fra 1983 (K5) og Canada fra 1972 (K7), i hver sin rute med hver sin
 * loddrette skala. De to landene er ulikt store og har ulik natur, og figuren
 * svarer ikke på hvem av dem som brenner mest.
 *
 * Begge er ``reported`` og tegnes stiplet (§ 6). Tallene er landenes egne, med
 * hvert sitt regelverk for hva som telles — ikke satellittmålt areal.
 */

import * as Plot from "@observablehq/plot";
import {
  serie,
  grunnlag,
  alleFotnoter,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall } from "../lib/format";

/** Seriene, i den rekkefølgen rutene står: eldste dekning øverst. */
const SERIER = [
  {
    id: "nbac_annual_burned_area",
    entitet: "CAN",
    navn: "Canada",
    kilde: "K7",
  },
  {
    id: "nifc_annual_burned_area",
    entitet: "USA",
    navn: "USA",
    kilde: "K5",
  },
];

export const ID = "figur-nasjonale-serier";

interface Punkt {
  aar: number;
  verdi: number;
  land: string;
  ufullstendig: boolean;
}

function punkter(): Punkt[] {
  return SERIER.flatMap((s) =>
    serie(s.id, s.entitet).map((o) => ({
      aar: Number(o.period),
      verdi: o.value,
      land: s.navn,
      ufullstendig: o.footnotes.includes("f_incomplete_year"),
    })),
  );
}

function tegn(id: string, alle: Punkt[], bredde: number, hoyde: number) {
  const hele = alle.filter((p) => !p.ufullstendig);
  const ufullstendige = alle.filter((p) => p.ufullstendig);

  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 78,
    marginRight: 24,
    marginBottom: 40,
    marginTop: 16,
    style: { background: "transparent", fontSize: "12px" },
    facet: { data: alle, y: "land", marginRight: 84 },
    fy: { label: null, domain: SERIER.map((s) => s.navn) },
    y: {
      label: "Brent areal (km²)",
      grid: true,
      tickFormat: (d: number) => tall(d),
    },
    x: { label: "År", tickFormat: (d: number) => String(d) },
    marks: [
      // Stiplet: nasjonalt rapportert, ikke satellittmålt (§ 6).
      Plot.line(hele, {
        x: "aar",
        y: "verdi",
        fy: "land",
        stroke: "var(--farge-serie)",
        strokeWidth: 1.75,
        strokeDasharray: "5,3",
      }),
      Plot.dot(hele, {
        x: "aar",
        y: "verdi",
        fy: "land",
        fill: "var(--farge-serie)",
        r: 1.6,
      }),
      Plot.dot(ufullstendige, {
        x: "aar",
        y: "verdi",
        fy: "land",
        stroke: "var(--farge-serie)",
        fill: "var(--farge-flate)",
        strokeDasharray: "2,2",
        r: 3.5,
      }),
      Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ],
  });
}

export function nasjonaleSerier() {
  const alle = punkter();
  const grunnlagPerSerie = SERIER.map((s) => ({ ...s, g: grunnlag(s.id) }));

  const observasjoner: Observasjon[] = SERIER.flatMap((s) =>
    serie(s.id, s.entitet),
  );

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const aarene = [...new Set(alle.map((p) => p.aar))].sort((a, b) => a - b);
  const perAar = new Map<number, Map<string, string>>();
  for (const p of alle) {
    if (!perAar.has(p.aar)) perAar.set(p.aar, new Map());
    perAar.get(p.aar)!.set(p.land, tall(p.verdi));
  }

  return {
    id: ID,
    tittel: "Brent areal per år, USA og Canada",
    svg: tegn(ID, alle, 760, 460),
    svgMobil: tegn(`${ID}-mobil`, alle, 360, 400),
    grafBeskrivelse:
      `To kurver i hver sin rute, som viser nasjonalt rapportert brent areal ` +
      `i kvadratkilometer per år. ${grunnlagPerSerie
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
        merke: "rapportert",
        tekst: "Nasjonalt rapportert brent areal. Hvert land følger sine egne definisjoner av hva som telles.",
      },
      {
        merke: "ufullstendig-punkt",
        tekst: "Åpent punkt: inneværende år, som ikke er omme.",
      },
    ],
    tabell: {
      beskrivelse:
        "Nasjonalt rapportert brent areal i km² per år. «Ingen data» betyr at " +
        "serien ikke dekker året. Tallene er de samme som kurvene er tegnet av.",
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
      entitet: s.entitet,
      seriesId: s.id,
      fra: s.g.first_year,
      til: s.g.last_complete_year,
    })),
  };
}
