/**
 * S3, figur 8 — den kumulative kurven med sesongbånd (CLAUDE.md § 8).
 *
 * Brent areal lagt sammen uke for uke gjennom året, for verden. Båndet dekker
 * SEASON_BAND_PCT av de fullstendige årene, med medianen inni. Inneværende år
 * tegnes for seg og inngår ikke i båndet (§ 7).
 *
 * Alle tall kommer fra sesongbånd-avledningen i insights.json. Figuren regner
 * ingenting selv (P3).
 */

import * as Plot from "@observablehq/plot";
import {
  avledning,
  observasjoner as alle,
  alleFotnoter,
  type Avledning,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall } from "../lib/format";

const SERIE = "gwis_weekly_burned_area";
const ENTITET = "WLD";

export const ID = "figur-kumulativ-uke";

interface Baandpunkt {
  uke: number;
  median: number;
  lav: number;
  hoy: number;
}

interface Aarspunkt {
  uke: number;
  verdi: number;
}

interface Kant {
  ranks: number[];
  interpolated: boolean;
  from: "low" | "high";
}

/** «det nest laveste», «det tredje høyeste» — ordenstall fra nærmeste ende. */
const ORDENSTALL = ["", "", "nest ", "tredje ", "fjerde ", "femte "];

function kantOrd(kant: Kant): string {
  const ende = kant.from === "low" ? "laveste" : "høyeste";
  const ord = kant.ranks.map(
    (r) => `det ${ORDENSTALL[r] ?? `${r}. `}${ende}`,
  );
  return ord.join(" og ");
}

function tegn(
  id: string,
  band: Baandpunkt[],
  iaar: Aarspunkt[],
  bredde: number,
  hoyde: number,
) {
  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 88,
    marginBottom: 44,
    marginTop: 16,
    style: { background: "transparent", fontSize: "13px" },
    x: { label: "Uke i året", domain: [1, 52], ticks: [1, 10, 20, 30, 40, 50] },
    y: {
      label: "Brent areal hittil i året (km²)",
      grid: true,
      tickFormat: (d: number) => tall(d),
    },
    marks: [
      Plot.areaY(band, {
        x: "uke",
        y1: "lav",
        y2: "hoy",
        fill: "var(--farge-serie)",
        fillOpacity: 0.16,
      }),
      Plot.line(band, {
        x: "uke",
        y: "median",
        stroke: "var(--farge-serie)",
        strokeWidth: 1.5,
        strokeDasharray: "5,3",
      }),
      // Inneværende år er tykkere og heltrukket, og stopper der målingene
      // stopper — ikke ved årsslutt (§ 6).
      Plot.line(iaar, {
        x: "uke",
        y: "verdi",
        stroke: "var(--farge-serie-b)",
        strokeWidth: 2.75,
      }),
      Plot.dot(iaar.slice(-1), {
        x: "uke",
        y: "verdi",
        fill: "var(--farge-serie-b)",
        r: 4,
      }),
      Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ],
  });
}

export function kumulativUke() {
  const a = avledning(`season_band.${SERIE}.${ENTITET}`) as Avledning;

  const band: Baandpunkt[] = (
    a.weeks as { week: number; median: number; low: number; high: number }[]
  ).map((u) => ({ uke: u.week, median: u.median, lav: u.low, hoy: u.high }));

  const ufullstendig = a.incomplete_year as {
    year: number;
    last_week: number;
    weeks: { week: number; value: number }[];
  } | null;

  const iaar: Aarspunkt[] = (ufullstendig?.weeks ?? []).map((u) => ({
    uke: u.week,
    verdi: u.value,
  }));

  const kanter = a.band_edges as { low: Kant; high: Kant };
  const grunnlagsaar = a.basis_years as number[];
  const fra = Math.min(...grunnlagsaar);
  const til = Math.max(...grunnlagsaar);
  const [lav, hoy] = a.band_pct as number[];

  const observasjoner: Observasjon[] = alle.filter(
    (o) => o.series_id === SERIE && o.entity === ENTITET,
  );

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  const iaarPerUke = new Map(iaar.map((p) => [p.uke, p.verdi]));

  return {
    id: ID,
    tittel: "Brent areal gjennom året, kumulativt, verden",
    svg: tegn(ID, band, iaar, 760, 420),
    svgMobil: tegn(`${ID}-mobil`, band, iaar, 360, 360),
    grafBeskrivelse:
      `Kumulativ kurve som viser brent areal i verden lagt sammen uke for uke. ` +
      `Båndet dekker fra ${lav}. til ${hoy}. persentil av årene ${fra}–${til}, ` +
      `med medianen som stiplet linje inni. Den heltrukne linjen er ${
        ufullstendig?.year ?? "inneværende år"
      }, som ikke er omme. Tallene står i tabellen under.`,
    kildeIder: ["K2"],
    dekningPerKilde: { K2: { fra, til: ufullstendig?.year ?? til } },
    fotnoter,
    tegnforklaring: [
      {
        merke: "maalt-b",
        tekst: `${ufullstendig?.year ?? "Inneværende år"}: brent areal hittil i året. Året er ikke omme, og kurven stopper der målingene stopper.`,
      },
      {
        merke: "median",
        tekst: `Median for ${fra}–${til}: den midterste av årene, uke for uke.`,
      },
      {
        merke: "band",
        tekst: `Persentilbånd: ${lav}. til ${hoy}. persentil av de ${grunnlagsaar.length} hele årene. Ett år av ti ligger over båndet, ett av ti under.`,
      },
    ],
    tabell: {
      beskrivelse: `Kumulativt brent areal i km² per uke: median og persentilbånd over ${fra}–${til}, og ${ufullstendig?.year ?? "inneværende år"} så langt.`,
      kolonner: [
        "Uke",
        "Median (km²)",
        `${lav}. persentil`,
        `${hoy}. persentil`,
        `${ufullstendig?.year ?? "Inneværende år"} (km²)`,
      ],
      rader: band.map((u) => {
        const v = iaarPerUke.get(u.uke);
        return [
          String(u.uke),
          tall(u.median),
          tall(u.lav),
          tall(u.hoy),
          v === undefined ? "ingen data" : tall(v),
        ];
      }),
    },
    observasjoner,
    csvFil: `${ID}.csv`,
    grunnlagsaar,
    inneverendeAar: ufullstendig?.year ?? null,
    bandPct: [lav, hoy] as [number, number],
    // Hva kantene av båndet hviler på. Med få år ligger de mellom to enkeltår,
    // og båndet er ikke fastere enn de to tillater (§ 7).
    bandKanter: {
      interpolert: kanter.low.interpolated || kanter.high.interpolated,
      nedre: kantOrd(kanter.low),
      ovre: kantOrd(kanter.high),
    },
  };
}
