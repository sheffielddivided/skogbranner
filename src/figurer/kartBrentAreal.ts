/**
 * S2, figur 3 — verdenskartet (CLAUDE.md § 8).
 *
 * Brent areal per land for siste fullstendige år, tegnet på kartenhetene fra
 * K6. Geometrien ligger i repoet og hentes ikke fra en flistjeneste (T2).
 *
 * Kartet har to tilstander, og bryteren over det velger hvilken som vises:
 * brent areal i km², og brent areal som andel av landarealet. Begge tegnes ved
 * bygging; bryteren er radioknapper og CSS, uten skript.
 *
 * Land uten rad i kilden tegnes som «ingen data», aldri som null (§ 6).
 */

import * as Plot from "@observablehq/plot";
import {
  serieAar,
  serie,
  grunnlag,
  alleFotnoter,
  geometri,
  entitetsnavn,
  avledning,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall, desimaltall } from "../lib/format";

const AREAL_SERIE = "owid_annual_area_burnt";
const ANDEL_SERIE = "owid_annual_area_burnt_share_land";

export const ID = "figur-kart-brent-areal";

export interface Visning {
  nokkel: string;
  merkelapp: string;
  enhet: string;
  /** Aksens og fargeskalaens tekst, med enheten indikatortabellen angir (§ 9). */
  skalatekst: string;
  svg: string;
  svgMobil: string;
  grafBeskrivelse: string;
}

function farger(verdier: number[]) {
  // Kvantiler framfor lineær skala: brent areal er svært skjevfordelt, og en
  // lineær skala ville gitt nesten hele verden samme farge. Skalaen er
  // enkeltfarget og stigende, slik at den kan leses ved fargeblindhet (§ 9).
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
  const flater = geometri().features;
  const brudd = farger([...verdier.values()]);

  const data = flater.map((f) => ({
    ...f,
    entity: f.properties.entity,
    verdi: verdier.get(f.properties.entity),
  }));

  // Hvert land tegnes én gang. Et land uten måling får «ingen data»-fargen av
  // fargeskalaens unknown, ikke av et eget lag under — to lag ville lagt de
  // samme banene i dokumentet to ganger uten at leseren så forskjell.
  const marks = [
    Plot.geo(data, {
      fill: (d: { verdi: number | undefined }) => d.verdi,
      stroke: "var(--farge-kant)",
      strokeWidth: 0.3,
      title: (d: { entity: string; verdi: number | undefined }) =>
        d.verdi === undefined
          ? `${entitetsnavn(d.entity)}: ingen data`
          : `${entitetsnavn(d.entity)}: ${format(d.verdi)}`,
    }),
  ];

  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    margin: 0,
    style: { background: "transparent", fontSize: "12px" },
    projection: { type: "equal-earth", rotate: [-10, 0] },
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
      // Fargen et land uten rad får. Den står også i tegnforklaringen, så
      // leseren slipper å slutte seg til hva den blasse flaten betyr (§ 6).
      unknown: "var(--farge-ingen-data)",
      legend: true,
      label: skalatekst,
      // Enheten står i skalateksten. Gjentatt på hvert merke ville merkene
      // lagt seg oppå hverandre.
      tickFormat: (d: number) => merkeformat(d),
    },
    marks,
  });
}

export function kartBrentAreal() {
  const aar = grunnlag(AREAL_SERIE).last_complete_year;
  const periode = String(aar);

  const areal = serieAar(AREAL_SERIE, periode, "country");
  const andel = serieAar(ANDEL_SERIE, periode, "country");
  const verden = serie(AREAL_SERIE, "WLD").find((o) => o.period === periode)!;

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
        380,
      ),
      svgMobil: tegn(
        `${ID}-km2-mobil`,
        areal,
        (v) => `${tall(v)} km²`,
        (v) => tall(v),
        "Brent areal (km²)",
        360,
        260,
      ),
      grafBeskrivelse: `Verdenskart som viser brent areal i kvadratkilometer per land i ${aar}. Land uten data er tegnet uten farge. Tallene står i tabellen under kartet.`,
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
        380,
      ),
      svgMobil: tegn(
        `${ID}-andel-mobil`,
        andel,
        (v) => `${desimaltall(v * 100)} %`,
        (v) => desimaltall(v * 100),
        "Andel av landarealet (prosent)",
        360,
        260,
      ),
      grafBeskrivelse: `Verdenskart som viser brent areal som andel av landarealet per land i ${aar}. Land uten data er tegnet uten farge. Tallene står i tabellen under kartet.`,
    },
  ];

  const observasjoner = [...areal, ...andel];
  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  // Hvor mange land som har tall uten å ha en flate, er en avledning (§ 7).
  // Tallet skrives ikke her — det leses fra insights.json, og setningen bærer
  // id-en (P3).
  const dekningId = `map_area_coverage.${AREAL_SERIE}.${aar}`;
  const kartdekning = avledning(dekningId);

  // Avledningen er regnet mot geometrien slik den lå da ETL kjørte, og
  // geometrien bygges i en egen jobb. Bygges den på nytt uten at derive.py
  // kjøres etterpå, ville setningen fortsatt stå med det gamle tallet. Derfor
  // telles det samme her, av den geometrien figuren faktisk tegner.
  const medFlate = new Set(geometri().features.map((f) => f.properties.entity));
  const utenFlate = areal.filter((o) => !medFlate.has(o.entity)).length;
  if (utenFlate !== kartdekning.entities_without_area) {
    throw new Error(
      `Avledningen ${dekningId} sier ${kartdekning.entities_without_area} land ` +
        `uten flate, men kartet tegner ${utenFlate}. Kjør derive.py på nytt ` +
        "etter at kartgeometrien er bygget.",
    );
  }

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
    kildeIder: [verden.source_id],
    dekningPerKilde: { [verden.source_id]: { fra: aar, til: aar } },
    fotnoter,
    tabell,
    observasjoner,
    csvFil: `${ID}.csv`,
    utenFlate: { avledning: dekningId, dekning: kartdekning },
  };
}
