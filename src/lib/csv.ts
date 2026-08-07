/**
 * Figurens egen CSV.
 *
 * P5 krever at kildelinjen lenker til en CSV med nøyaktig de radene figuren
 * tegner. De kanoniske filene under data/processed/ bærer flere serier og er
 * derfor ikke den filen — de lenkes fra S6 i stedet.
 *
 * Kolonnene er de samme som i de kanoniske filene, slik at en leser som laster
 * ned begge, kjenner igjen formen (§ 6).
 */

import type { Observasjon } from "./data";

const KOLONNER = [
  "entity",
  "entity_name",
  "level",
  "period",
  "indicator",
  "value",
  "unit",
  "source_id",
  "series_id",
  "quality",
  "footnotes",
] as const;

function celle(verdi: string | number): string {
  const tekst = String(verdi);
  return /[",\n]/.test(tekst) ? `"${tekst.replace(/"/g, '""')}"` : tekst;
}

/**
 * Observasjonene som CSV, i den rekkefølgen figuren tegner dem.
 *
 * Fotnotene skilles med semikolon, som i de kanoniske filene, fordi komma
 * allerede skiller kolonnene.
 *
 * ``n_series`` er et valgfritt felt som bare noen kilder fører (§ 6). Kolonnen
 * legges til bakerst når figuren faktisk har den — som i den kanoniske filen —
 * og utelates ellers, slik at den ikke står tom for alle de andre figurene.
 */
export function tilCsv(observasjoner: Observasjon[]): string {
  const harSerieantall = observasjoner.some((o) => o.n_series !== undefined);
  const kolonner = harSerieantall ? [...KOLONNER, "n_series"] : [...KOLONNER];

  const rader = observasjoner.map((o) =>
    kolonner
      .map((kolonne) =>
        celle(
          kolonne === "footnotes"
            ? o.footnotes.join(";")
            : ((o[kolonne as keyof Observasjon] ?? "") as string | number),
        ),
      )
      .join(","),
  );
  return [kolonner.join(","), ...rader].join("\n") + "\n";
}
