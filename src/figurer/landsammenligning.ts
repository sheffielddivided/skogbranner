/**
 * S4, figur 10 — sammenligning av land over tid (CLAUDE.md § 8).
 *
 * Begge EFFIS-seriene tegnes: K4, som er satellittkartlagt (heltrukket), og
 * K3, som er landenes egne innrapporterte tall (stiplet). De skjøtes aldri
 * sammen — det er to målemetoder, ikke én måling (§ 6).
 *
 * Alle landene tegnes blekt. De leseren krysser av for, tegnes med farge og
 * navn. Avkryssingen er avkryssingsbokser og CSS, uten skript; hvert lands
 * kurver ligger ferdig tegnet i SVG-en og slås av og på med regler som
 * Sammenligning.astro skriver ut.
 *
 * Utvalget som er krysset av på forhånd, er maskinelt: landene med størst
 * brent areal i det siste året som er omme.
 */

import * as Plot from "@observablehq/plot";
import {
  observasjoner as alle,
  grunnlag,
  alleFotnoter,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall } from "../lib/format";

const MAALT_SERIE = "effis_rda_annual_burned_area";
const RAPPORTERT_SERIE = "effis_annual_country_totals";

/** Hvor mange land som er krysset av når siden åpnes. */
const FORHANDSVALGTE = 5;

/**
 * Fargene de valgte landene tegnes med, tildelt etter plass i lista.
 *
 * Paletten er kortere enn landlista, så to land langt fra hverandre i
 * alfabetet kan få samme farge. Hver kurve bærer derfor landets navn ved
 * enden: fargen er ikke den eneste måten å skille dem på, som § 9 krever.
 */
const PALETT = 6;

function farge(i: number): string {
  return `var(--farge-land-${(i % PALETT) + 1})`;
}

export const ID = "figur-landsammenligning";

interface Punkt {
  aar: number;
  verdi: number;
  entity: string;
  navn: string;
  serie: string;
}

function punkter(seriesId: string): Punkt[] {
  return alle
    .filter((o) => o.series_id === seriesId && o.level === "country")
    .map((o) => ({
      aar: Number(o.period),
      verdi: o.value,
      entity: o.entity,
      navn: o.entity_name,
      serie: seriesId,
    }))
    .sort((a, b) => a.aar - b.aar);
}

function tegn(
  id: string,
  maalt: Punkt[],
  rapportert: Punkt[],
  koder: string[],
  bredde: number,
  hoyde: number,
) {
  const bakgrunn = [
    // Alle land, blekt og uten navn. De valgte landene skal kunne leses mot
    // resten, ikke mot en tom flate.
    Plot.line(maalt, {
      x: "aar",
      y: "verdi",
      z: "entity",
      stroke: "var(--farge-ingen-data)",
      strokeWidth: 0.75,
    }),
  ];

  // Ett merke per land og serie, med egen klasse. Klassen er det CSS slår av
  // og på — figuren tegnes én gang, og valget koster ingen ny tegning.
  const valgte = koder.flatMap((kode, i) => [
    Plot.line(
      rapportert.filter((p) => p.entity === kode),
      {
        x: "aar",
        y: "verdi",
        stroke: farge(i),
        strokeWidth: 1.75,
        strokeDasharray: "5,3",
        className: `land-serie land-${kode}`,
      },
    ),
    Plot.line(
      maalt.filter((p) => p.entity === kode),
      {
        x: "aar",
        y: "verdi",
        stroke: farge(i),
        strokeWidth: 2.25,
        className: `land-serie land-${kode}`,
      },
    ),
    Plot.text(
      maalt.filter((p) => p.entity === kode).slice(-1),
      {
        x: "aar",
        y: "verdi",
        text: "navn",
        textAnchor: "start",
        dx: 6,
        fill: farge(i),
        className: `land-serie land-${kode}`,
      },
    ),
  ]);

  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 78,
    marginRight: 96,
    marginBottom: 44,
    marginTop: 16,
    style: { background: "transparent", fontSize: "13px" },
    x: { label: "År", tickFormat: (d: number) => String(d) },
    y: {
      label: "Brent areal (km²)",
      grid: true,
      tickFormat: (d: number) => tall(d),
    },
    marks: [
      ...bakgrunn,
      ...valgte,
      Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ],
  });
}

export function landsammenligning() {
  const maalt = punkter(MAALT_SERIE);
  const rapportert = punkter(RAPPORTERT_SERIE);

  const maaltGrunnlag = grunnlag(MAALT_SERIE);
  const rapportertGrunnlag = grunnlag(RAPPORTERT_SERIE);
  const sisteHele = maaltGrunnlag.last_complete_year;

  // Landene i figuren er de K4 fører. K3 dekker et mindre utvalg, og et land
  // uten K3-rader får bare den heltrukne linjen.
  const navn = new Map(maalt.map((p) => [p.entity, p.navn]));
  const koder = [...navn.keys()].sort((a, b) =>
    (navn.get(a) ?? a).localeCompare(navn.get(b) ?? b, "nb"),
  );

  const sisteAar = new Map(
    maalt.filter((p) => p.aar === sisteHele).map((p) => [p.entity, p.verdi]),
  );
  const forhandsvalgt = new Set(
    [...sisteAar.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, FORHANDSVALGTE)
      .map(([kode]) => kode),
  );

  const observasjoner: Observasjon[] = alle.filter(
    (o) =>
      (o.series_id === MAALT_SERIE || o.series_id === RAPPORTERT_SERIE) &&
      o.level === "country",
  );

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const aarene = [...new Set(observasjoner.map((o) => Number(o.period)))].sort(
    (a, b) => a - b,
  );
  const perAar = new Map<number, Map<string, string>>();
  for (const p of [...maalt, ...rapportert]) {
    if (!perAar.has(p.aar)) perAar.set(p.aar, new Map());
    perAar.get(p.aar)!.set(`${p.entity}:${p.serie}`, tall(p.verdi));
  }

  // Tabellen viser de forhåndsvalgte landene. Alle landene ligger i figurens
  // CSV, som lenken under figuren peker til (P5).
  const tabellKoder = koder.filter((kode) => forhandsvalgt.has(kode));

  return {
    id: ID,
    tittel: "Brent areal per år, valgte land",
    svg: tegn(ID, maalt, rapportert, koder, 760, 460),
    svgMobil: tegn(`${ID}-mobil`, maalt, rapportert, koder, 360, 380),
    grafBeskrivelse:
      `Linjediagram med brent areal i kvadratkilometer per land og år. ` +
      `Heltrukket linje er EFFIS' satellittkartlegging ${maaltGrunnlag.first_year}–${sisteHele}, ` +
      `stiplet linje er landenes egne innrapporterte tall ${rapportertGrunnlag.first_year}–${rapportertGrunnlag.last_complete_year}. ` +
      `Landene som er krysset av, tegnes med farge og navn; de øvrige ligger blekt i bakgrunnen. ` +
      `Tallene står i tabellen under.`,
    kildeIder: ["K4", "K3"],
    dekningPerKilde: {
      K4: { fra: maaltGrunnlag.first_year, til: sisteHele },
      K3: {
        fra: rapportertGrunnlag.first_year,
        til: rapportertGrunnlag.last_complete_year,
      },
    },
    fotnoter,
    tegnforklaring: [
      {
        merke: "maalt",
        tekst: `Satellittkartlagt av EFFIS, ${maaltGrunnlag.first_year}–${sisteHele}. Én definisjon for alle land.`,
      },
      {
        merke: "rapportert",
        tekst: `Rapportert av landet selv, ${rapportertGrunnlag.first_year}–${rapportertGrunnlag.last_complete_year}. Hvert land følger sine egne definisjoner.`,
      },
      {
        merke: "bakgrunn",
        tekst: "De øvrige landene, uten navn.",
      },
    ],
    // Avkryssingslista. Rekkefølgen er alfabetisk på norsk navn, slik at et
    // land kan finnes uten å vite hvor stort det er.
    land: koder.map((kode) => ({
      kode,
      navn: navn.get(kode) ?? kode,
      valgt: forhandsvalgt.has(kode),
    })),
    maksValgte: FORHANDSVALGTE,
    tabell: {
      beskrivelse: `Brent areal i km² per år for landene som er krysset av. «Ingen data» betyr at serien ikke fører landet det året. Hele utvalget ligger i figurens CSV.`,
      kolonner: [
        "År",
        ...tabellKoder.flatMap((kode) => [
          `${navn.get(kode)} — satellitt`,
          `${navn.get(kode)} — rapportert`,
        ]),
      ],
      rader: aarene.map((aar) => [
        String(aar),
        ...tabellKoder.flatMap((kode) => [
          perAar.get(aar)?.get(`${kode}:${MAALT_SERIE}`) ?? "ingen data",
          perAar.get(aar)?.get(`${kode}:${RAPPORTERT_SERIE}`) ?? "ingen data",
        ]),
      ]),
    },
    observasjoner,
    csvFil: `${ID}.csv`,
  };
}
