/**
 * S3, figur 7 — sesongprofilen per verdensdel (CLAUDE.md § 8).
 *
 * Median brent areal per uke i året, verdensdel for verdensdel, over de
 * fullstendige årene. Kurvene kommer fra sesongprofil-avledningen i
 * insights.json — figuren regner ingenting selv (P3, § 7).
 *
 * Hver rute har sin egen loddrette skala. Formen kan sammenlignes mellom
 * verdensdeler, høyden kan ikke, og det står i teksten under figuren.
 */

import * as Plot from "@observablehq/plot";
import {
  avledning,
  serieAar,
  observasjoner as alle,
  alleFotnoter,
  entitetsnavn,
  type Avledning,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall } from "../lib/format";

const SERIE = "gwis_weekly_burned_area";

/** Verdensdelene, i den rekkefølgen rutene står. */
const REGIONER = ["AFR", "SAM", "ASI", "OCE", "NAC", "EUR"];

export const ID = "figur-sesongprofil";

interface Ukepunkt {
  uke: number;
  verdi: number;
  region: string;
}

function tegn(id: string, punkter: Ukepunkt[], bredde: number, hoyde: number) {
  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 70,
    marginBottom: 40,
    marginTop: 20,
    style: { background: "transparent", fontSize: "12px" },
    // Hver verdensdel får sin egen rute og sin egen y-skala: Afrika brenner i
    // en helt annen størrelsesorden enn Europa, og en felles skala ville gjort
    // de minste kurvene til flate streker.
    facet: { data: punkter, y: "region", marginRight: 90 },
    fy: { label: null, domain: REGIONER.map((r) => entitetsnavn(r)) },
    y: { label: "km² per uke (median)", grid: true, tickFormat: (d: number) => tall(d) },
    x: { label: "Uke i året", domain: [1, 52], ticks: [1, 10, 20, 30, 40, 50] },
    marks: [
      Plot.areaY(punkter, {
        x: "uke",
        y: "verdi",
        fy: "region",
        fill: "var(--farge-serie)",
        fillOpacity: 0.15,
      }),
      Plot.line(punkter, {
        x: "uke",
        y: "verdi",
        fy: "region",
        stroke: "var(--farge-serie)",
        strokeWidth: 1.75,
      }),
      Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ],
  });
}

export function sesongprofil() {
  const profiler = REGIONER.map((kode) => ({
    kode,
    navn: entitetsnavn(kode),
    a: avledning(`season_week.${SERIE}.${kode}`) as Avledning,
  }));

  const punkter: Ukepunkt[] = profiler.flatMap((p) =>
    (p.a.weeks as { week: number; median: number }[]).map((u) => ({
      uke: u.week,
      verdi: u.median,
      region: p.navn,
    })),
  );

  const grunnlagsaar = profiler[0]!.a.basis_years as number[];
  const fra = Math.min(...grunnlagsaar);
  const til = Math.max(...grunnlagsaar);

  // Figurens egne rader: ukesobservasjonene medianene er regnet av.
  const observasjoner: Observasjon[] = alle.filter(
    (o) =>
      o.series_id === SERIE &&
      REGIONER.includes(o.entity) &&
      !o.footnotes.includes("f_incomplete_year"),
  );

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const perUke = new Map<number, Map<string, number>>();
  for (const p of punkter) {
    if (!perUke.has(p.uke)) perUke.set(p.uke, new Map());
    perUke.get(p.uke)!.set(p.region, p.verdi);
  }

  return {
    id: ID,
    tittel: `Brent areal per uke gjennom året, per verdensdel, ${fra}–${til}`,
    svg: tegn(ID, punkter, 760, 620),
    svgMobil: tegn(`${ID}-mobil`, punkter, 360, 560),
    grafBeskrivelse:
      `Seks kurver, én per verdensdel, som viser median brent areal i ` +
      `kvadratkilometer for hver uke i året over årene ${fra}–${til}. ` +
      `Hver kurve har sin egen loddrette skala. Tallene står i tabellen under.`,
    kildeIder: ["K2"],
    dekningPerKilde: { K2: { fra, til } },
    fotnoter,
    tabell: {
      beskrivelse: `Median brent areal per uke i km², over de ${grunnlagsaar.length} fullstendige årene ${fra}–${til}. Tallene er de samme som kurvene er tegnet av.`,
      kolonner: ["Uke", ...profiler.map((p) => `${p.navn} (km²)`)],
      rader: [...perUke.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([uke, per]) => [
          String(uke),
          ...profiler.map((p) => {
            const v = per.get(p.navn);
            return v === undefined ? "ingen data" : tall(v);
          }),
        ]),
    },
    observasjoner,
    csvFil: `${ID}.csv`,
    grunnlagsaar,
  };
}
