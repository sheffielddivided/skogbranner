/**
 * S4, figur 9 — kartet over EFFIS-området (CLAUDE.md § 8).
 *
 * Brent areal per land for siste fullstendige år, tegnet på den finere
 * geometrien i data/geo/europa.json. Kilden er K4, EFFIS' egen
 * satellittkartlegging — ikke de nasjonalt rapporterte tallene i K3.
 *
 * Kartet har to tilstander som bryteren over det velger mellom: brent areal i
 * km², og brent areal som andel av landarealet. Begge tegnes ved bygging.
 *
 * Land uten rad i kilden tegnes som «ingen data», aldri som null (§ 6).
 */

import * as Plot from "@observablehq/plot";
import {
  serieAar,
  grunnlag,
  alleFotnoter,
  geometriEuropa,
  entitetsnavn,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { utsnittsflate } from "../lib/kartutsnitt";
import { tall, desimaltall } from "../lib/format";
import type { Visning } from "./kartBrentAreal";

const AREAL_SERIE = "effis_rda_annual_burned_area";
const ANDEL_SERIE = "effis_rda_annual_burned_area_share_land";

export const ID = "figur-kart-europa";

/**
 * Utsnittet kartet tegner, i grader.
 *
 * EFFIS fører også noen oversjøiske områder — Réunion, Mayotte, Guadeloupe,
 * Martinique, Saint-Martin og Guyana. De ligger på hver sin kant av kloden, og
 * et kart som skulle rommet dem alle, ville vært et verdenskart der Europa var
 * for lite til å leses. Hvilke entiteter som faller utenfor utsnittet, regnes
 * av geometrien ved bygging og sies i klartekst under kartet.
 */
const UTSNITT = { vest: -26, sor: 11, ost: 62, nord: 72 };

function utenforUtsnittet(): string[] {
  return geometriEuropa()
    .features.filter((f) => {
      const punkter = f.geometry.coordinates.flat(2);
      const x = punkter.map((p) => p[0]!);
      const y = punkter.map((p) => p[1]!);
      return (
        Math.max(...x) < UTSNITT.vest ||
        Math.min(...x) > UTSNITT.ost ||
        Math.max(...y) < UTSNITT.sor ||
        Math.min(...y) > UTSNITT.nord
      );
    })
    .map((f) => f.properties.entity);
}

function farger(verdier: number[]) {
  // Kvantiler framfor lineær skala, av samme grunn som på verdenskartet:
  // brent areal er svært skjevfordelt. Skalaen er enkeltfarget og stigende,
  // slik at den kan leses ved fargeblindhet (§ 9).
  const sortert = verdier.filter((v) => v > 0).sort((a, b) => a - b);
  const brudd: number[] = [];
  for (const andel of [0.2, 0.4, 0.6, 0.8, 0.95]) {
    const v = sortert[Math.floor(sortert.length * andel)];
    if (v !== undefined && !brudd.includes(v)) brudd.push(v);
  }
  return brudd;
}

function tegn(
  id: string,
  observasjoner: Observasjon[],
  format: (verdi: number) => string,
  merkeformat: (verdi: number) => string,
  skalatekst: string,
  bredde: number,
  hoyde: number,
) {
  const verdier = new Map(observasjoner.map((o) => [o.entity, o.value]));
  const utenfor = new Set(utenforUtsnittet());
  const flater = geometriEuropa().features.filter(
    (f) => !utenfor.has(f.properties.entity),
  );
  const brudd = farger([...verdier.values()]);

  const data = flater.map((f) => ({
    ...f,
    entity: f.properties.entity,
    verdi: verdier.get(f.properties.entity),
  }));

  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    margin: 0,
    style: { background: "transparent", fontSize: "12px" },
    // Utsnittet er fast, ikke tilpasset dataene: kartet skal se likt ut fra år
    // til år, slik at to årganger kan sammenlignes. Ruten bygges av
    // utsnittsflate(), som vikler den slik tegneren forventer.
    projection: {
      type: "conic-conformal",
      domain: utsnittsflate(UTSNITT),
    },
    color: {
      type: "threshold",
      domain: brudd,
      range: [
        "var(--farge-kart-1)",
        "var(--farge-kart-2)",
        "var(--farge-kart-3)",
        "var(--farge-kart-4)",
        "var(--farge-kart-5)",
        "var(--farge-kart-6)",
      ].slice(0, brudd.length + 1),
      legend: true,
      label: skalatekst,
      tickFormat: (d: number) => merkeformat(d),
    },
    marks: [
      // Alle land tegnes først i «ingen data»-flaten. Et land uten måling skal
      // ikke se ut som et land med lav verdi (§ 6).
      Plot.geo(data, {
        fill: "var(--farge-ingen-data)",
        stroke: "var(--farge-kant)",
        strokeWidth: 0.3,
      }),
      Plot.geo(
        data.filter((d) => d.verdi !== undefined),
        {
          fill: (d: { verdi: number }) => d.verdi,
          stroke: "var(--farge-kant)",
          strokeWidth: 0.3,
          title: (d: { entity: string; verdi: number }) =>
            `${entitetsnavn(d.entity)}: ${format(d.verdi)}`,
        },
      ),
    ],
  });
}

export function kartEuropa() {
  const aar = grunnlag(AREAL_SERIE).last_complete_year;
  const periode = String(aar);

  const areal = serieAar(AREAL_SERIE, periode, "country");
  const andel = serieAar(ANDEL_SERIE, periode, "country");

  const visninger: Visning[] = [
    {
      nokkel: "km2",
      merkelapp: "Brent areal (km²)",
      enhet: "km²",
      skalatekst: "Brent areal (km²)",
      svg: tegn(
        `${ID}-km2`,
        areal,
        (v) => `${tall(v)} km²`,
        (v) => tall(v),
        "Brent areal (km²)",
        760,
        460,
      ),
      svgMobil: tegn(
        `${ID}-km2-mobil`,
        areal,
        (v) => `${tall(v)} km²`,
        (v) => tall(v),
        "Brent areal (km²)",
        360,
        330,
      ),
      grafBeskrivelse: `Kart over EFFIS-området som viser brent areal i kvadratkilometer per land i ${aar}. Land uten data er tegnet uten farge. Tallene står i tabellen under kartet.`,
    },
    {
      nokkel: "andel",
      merkelapp: "Andel av landarealet",
      enhet: "prosent",
      skalatekst: "Andel av landarealet (prosent)",
      svg: tegn(
        `${ID}-andel`,
        andel,
        (v) => `${desimaltall(v * 100)} %`,
        (v) => desimaltall(v * 100),
        "Andel av landarealet (prosent)",
        760,
        460,
      ),
      svgMobil: tegn(
        `${ID}-andel-mobil`,
        andel,
        (v) => `${desimaltall(v * 100)} %`,
        (v) => desimaltall(v * 100),
        "Andel av landarealet (prosent)",
        360,
        330,
      ),
      grafBeskrivelse: `Kart over EFFIS-området som viser brent areal som andel av landarealet per land i ${aar}. Land uten data er tegnet uten farge. Tallene står i tabellen under kartet.`,
    },
  ];

  const observasjoner = [...areal, ...andel];
  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const andelPer = new Map(andel.map((o) => [o.entity, o.value]));
  const tabell = {
    beskrivelse: `Brent areal per land i ${aar}, i kvadratkilometer og som andel av landarealet. «Ingen data» betyr at kilden ikke fører landet dette året. Tallene er de samme som kartet er tegnet med.`,
    kolonner: ["Land", "Brent areal (km²)", "Andel av landarealet"],
    rader: [...areal]
      .sort((a, b) => b.value - a.value || a.entity.localeCompare(b.entity))
      .map((o) => {
        const a = andelPer.get(o.entity);
        return [
          o.entity_name,
          tall(o.value),
          a === undefined ? "ingen data" : `${desimaltall(a * 100)} %`,
        ];
      }),
  };

  return {
    id: ID,
    tittel: `Brent areal per land, ${aar}`,
    aar,
    visninger,
    kildeIder: ["K4"],
    dekningPerKilde: { K4: { fra: aar, til: aar } },
    fotnoter,
    tabell,
    observasjoner,
    csvFil: `${ID}.csv`,
    // Entiteter kilden fører, men som ligger utenfor utsnittet. Settet regnes
    // av geometrien ved bygging, ikke skrevet som en liste (§ 7).
    utenGeometri: utenforUtsnittet()
      .filter((kode) => areal.some((o) => o.entity === kode))
      .map((kode) => entitetsnavn(kode))
      .sort(),
  };
}
