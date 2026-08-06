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
 */
export function tilCsv(observasjoner: Observasjon[]): string {
  const rader = observasjoner.map((o) =>
    KOLONNER.map((kolonne) =>
      celle(
        kolonne === "footnotes" ? o.footnotes.join(";") : (o[kolonne] as string | number),
      ),
    ).join(","),
  );
  return [KOLONNER.join(","), ...rader].join("\n") + "\n";
}
