/**
 * Leser de ferdige datafilene i repoet.
 *
 * Alt skjer ved bygging. Nettleseren gjør ingen kall (CLAUDE.md T2, T3).
 *
 * Feltnavnene følger den kanoniske datamodellen i CLAUDE.md § 6 og er derfor
 * engelske, mens alt leseren ser er norsk.
 */

import observasjonerJson from "../../data/processed/burned_area.json";
import kilderJson from "../../data/_sources.json";
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
}

export interface Kildestatus {
  status: string;
  last_attempt: string;
  last_success: string | null;
  message: string;
}

export const observasjoner = observasjonerJson as Observasjon[];

const kilder = kilderJson.sources as unknown as Record<string, Kilde>;
const fotnotetekster = fotnoterJson.footnotes as Record<string, string>;
const status = statusJson.sources as unknown as Record<string, Kildestatus>;

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

/** Observasjoner for én serie og én entitet, sortert på periode. */
export function serie(seriesId: string, entity: string): Observasjon[] {
  return observasjoner
    .filter((o) => o.series_id === seriesId && o.entity === entity)
    .sort((a, b) => a.period.localeCompare(b.period));
}

