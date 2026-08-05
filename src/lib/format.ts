/** Norsk tallformatering. Alt leseren ser er norsk (CLAUDE.md § 1). */

const heltall = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 });

/** Tall med norsk tusenskille, uten desimaler. */
export function tall(verdi: number): string {
  return heltall.format(verdi);
}

const maaneder = [
  "januar",
  "februar",
  "mars",
  "april",
  "mai",
  "juni",
  "juli",
  "august",
  "september",
  "oktober",
  "november",
  "desember",
];

/**
 * ISO-dato til norsk form: «5. august 2026».
 *
 * Skrevet ut for hånd framfor Intl.DateTimeFormat, slik at bygget gir samme
 * resultat uansett tidssone på byggemaskinen (T3).
 */
export function dato(iso: string): string {
  const [aar, maaned, dag] = iso.slice(0, 10).split("-").map(Number);
  if (!aar || !maaned || !dag) return iso;
  return `${dag}. ${maaneder[maaned - 1]} ${aar}`;
}

/** Året i en ISO 8601-periode: «2026-W31» og «2026» gir begge 2026. */
export function aarstall(periode: string): number {
  return Number(periode.slice(0, 4));
}
