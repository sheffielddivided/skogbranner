/**
 * Leser de ferdige datafilene i repoet.
 *
 * Alt skjer ved bygging. Nettleseren gjør ingen kall (CLAUDE.md T2, T3).
 *
 * Feltnavnene følger den kanoniske datamodellen i CLAUDE.md § 6 og er derfor
 * engelske, mens alt leseren ser er norsk.
 */

import burnedAreaJson from "../../data/processed/burned_area.json";
import shareLandJson from "../../data/processed/burned_area_share_land.json";
import fireCountJson from "../../data/processed/fire_count.json";
import firecciJson from "../../data/processed/burned_area_firecci_lt11.json";
import gfed5Json from "../../data/processed/burned_area_gfed5.json";
import charcoalJson from "../../data/processed/charcoal_composite_gcd.json";
import ukeJson from "../../data/processed/burned_area_weekly.json";
import avledningerJson from "../../data/processed/insights.json";
import kilderJson from "../../data/_sources.json";
import geometriJson from "../../data/geo/verden.json";
import europaJson from "../../data/geo/europa.json";
import landJson from "../../data/geo/land_no.json";
import fotnoterJson from "../../data/_footnotes.json";
import statusJson from "../../data/_status.json";

// Regelen for å avgrense en kompositt ved den yngste enden bor i sin egen rene
// modul, slik at den kan testes uten Astro og uten datafilene. Se § 9.
export { visningsgrense, visningspunkter } from "./visning.ts";

export interface Observasjon {
  entity: string;
  entity_name: string;
  level: string;
  period: string;
  indicator: string;
  value: number;
  unit: string;
  source_id: string;
  series_id: string;
  quality: string;
  footnotes: string[];
  /** Valgfritt: antall serier bak punktet, for kilder som fører det (§ 6). */
  n_series?: number;
}

export interface Kilde {
  source_id: string;
  name: string;
  publisher: string;
  url: string;
  download_url: string;
  license: string;
  license_url: string;
  attribution: string;
  coverage_start: string;
  coverage_end: string;
  quality: string;
  downloaded_at: string;
  processed_files: string[];
  footnotes: string[];
  /** Feltene S6 trenger i tillegg, og som ikke alle kilder har. */
  geography?: string;
  temporal_resolution?: string;
  requires_agreement?: boolean;
  agreement_accepted?: string;
  series?: string[];
  notes?: string;
}

/**
 * En maskinell avledning fra data/processed/insights.json.
 *
 * Feltene varierer med hva slags avledning det er — se CLAUDE.md § 7. Id-en er
 * verdien setningen bærer i data-derivation, slik at leseren kan spore tallet.
 */
export interface Avledning {
  kind: string;
  series_id?: string;
  source_id?: string;
  entity?: string;
  entity_name?: string;
  unit?: string;
  period?: string;
  [felt: string]: unknown;
}

export interface Kildestatus {
  status: string;
  last_attempt: string;
  last_success: string | null;
  message: string;
}

/**
 * Alle observasjoner siden kan tegne, uansett hvilken kanonisk fil de ligger
 * i. Hvilken fil en serie havner i, står i PROCESSED_FILE i etl/schema.py — de
 * statiske kildene har hver sin (§ 4).
 */
export const observasjoner = [
  ...burnedAreaJson,
  ...shareLandJson,
  ...fireCountJson,
  ...firecciJson,
  ...gfed5Json,
  ...charcoalJson,
  ...ukeJson,
] as Observasjon[];

const kilder = kilderJson.sources as unknown as Record<string, Kilde>;
const fotnotetekster = fotnoterJson.footnotes as Record<string, string>;
const status = statusJson.sources as unknown as Record<string, Kildestatus>;

/**
 * Alle kildene, sortert på kodens tall.
 *
 * S6 lister dem, og sidefoten attribuerer dem. En ny kilde i _sources.json
 * dukker begge steder opp av seg selv — lista skrives ikke for hånd.
 */
export function alleKilder(): Kilde[] {
  return Object.values(kilder).sort((a, b) =>
    a.source_id.localeCompare(b.source_id, "nb", { numeric: true }),
  );
}

/** Kildemetadata for en kildekode. Kaster hvis koden ikke finnes. */
export function kilde(sourceId: string): Kilde {
  const treff = kilder[sourceId];
  if (!treff) {
    throw new Error(
      `Kilden ${sourceId} står ikke i data/_sources.json. Kildelinjen kan ikke bygges.`,
    );
  }
  return treff;
}

/** Forenklet kartgeometri, bygget av etl/geo.py og kjørt i Actions (T4). */
export interface Kartgeometri {
  summary: { entities: number; missing_geometry: string[]; unknown_entities: string[] };
  features: {
    type: string;
    id: string;
    properties: { entity: string };
    geometry: { type: string; coordinates: number[][][][] };
  }[];
}

const kart = geometriJson as unknown as Kartgeometri;
const europa = europaJson as unknown as Kartgeometri;
const entiteter = landJson.entities as unknown as Record<
  string,
  { entity_name: string; level: string; iso3: boolean }
>;

/** Kartgeometrien. Navnene står ikke i den — de bor i land_no.json (§ 6). */
export function geometri(): Kartgeometri {
  return kart;
}

/**
 * Geometrien for Europa-kartet i S4.
 *
 * Samme kilde og samme kartenheter som verdenskartet, men finere forenkling:
 * kartet dekker et mindre område på samme flate, så én piksel er færre grader.
 * Utvalget er entitetene EFFIS fører, og bygges av etl/geo.py.
 */
export function geometriEuropa(): Kartgeometri {
  return europa;
}

/**
 * Det norske navnet på en entitet, fra land_no.json, som er fasit (§ 6).
 *
 * Kartgeometrien kan bære en kode som ikke står der — Antarktis har form, men
 * ingen kilde rapporterer den (§ 5). Da vises koden, framfor å finne på et
 * navn.
 */
export function entitetsnavn(kode: string): string {
  return entiteter[kode]?.entity_name ?? kode;
}

/** Norsk tekst for en fotnotekode. Kaster hvis koden mangler tekst. */
export function fotnotetekst(kode: string): string {
  const tekst = fotnotetekster[kode];
  if (!tekst) {
    throw new Error(
      `Fotnoten ${kode} har ingen tekst i data/_footnotes.json.`,
    );
  }
  return tekst;
}

/** Alle fotnotekoder som finnes, i den rekkefølgen de står i filen. */
export function alleFotnoter(): [string, string][] {
  return Object.entries(fotnotetekster);
}

/** Siste kjørestatus for en kilde, hvis den er registrert. */
export function kildestatus(sourceId: string): Kildestatus | null {
  return status[sourceId] ?? null;
}

const avledninger = avledningerJson.derivations as unknown as Record<
  string,
  Avledning
>;

/** Grunnlaget en serie er regnet over, slik det står i insights.json (§ 7). */
export interface Seriegrunnlag {
  source_id: string;
  quality: string;
  indicator: string;
  unit: string;
  first_year: number;
  last_complete_year: number;
  incomplete_years: number[];
  n_entities: number;
  always_zero_entities: string[];
}

const seriegrunnlag = avledningerJson.series as unknown as Record<
  string,
  Seriegrunnlag
>;

/** Seriens grunnlag. Kaster hvis serien ikke er avledet. */
export function grunnlag(seriesId: string): Seriegrunnlag {
  const treff = seriegrunnlag[seriesId];
  if (!treff) {
    throw new Error(
      `Serien ${seriesId} står ikke under «series» i insights.json.`,
    );
  }
  return treff;
}

/**
 * Én avledning, slått opp på id. Kaster hvis den ikke finnes.
 *
 * Finnes ikke avledningen, skal setningen ikke skrives — da må den
 * implementeres i etl/derive.py først (P3). Derfor er dette en byggefeil og
 * ikke en tom verdi.
 */
export function avledning(id: string): Avledning {
  const treff = avledninger[id];
  if (!treff) {
    throw new Error(
      `Avledningen ${id} finnes ikke i data/processed/insights.json. ` +
        "Setningen kan ikke skrives uten den (P3).",
    );
  }
  return treff;
}

/** Et tallfelt fra en avledning. Kaster hvis feltet mangler eller ikke er tall. */
export function avledetTall(id: string, felt: string): number {
  const verdi = avledning(id)[felt];
  if (typeof verdi !== "number") {
    throw new Error(
      `Avledningen ${id} har ikke tallfeltet ${felt}. Setningen kan ikke fylles.`,
    );
  }
  return verdi;
}

/** Observasjoner for én serie og én entitet, sortert på periode. */
export function serie(seriesId: string, entity: string): Observasjon[] {
  return observasjoner
    .filter((o) => o.series_id === seriesId && o.entity === entity)
    .sort((a, b) => a.period.localeCompare(b.period));
}

/**
 * Alle entiteter i én serie for én periode, sortert på entitetskode.
 *
 * Bare entitetene kilden faktisk fører. Et land uten rad er et land uten
 * måling, og skal vises som «ingen data» — ikke som null (§ 6).
 */
export function serieAar(
  seriesId: string,
  periode: string,
  level?: string,
): Observasjon[] {
  return observasjoner
    .filter(
      (o) =>
        o.series_id === seriesId &&
        o.period === periode &&
        (level === undefined || o.level === level),
    )
    .sort((a, b) => a.entity.localeCompare(b.entity));
}

