/** Norsk tallformatering. Alt leseren ser er norsk (CLAUDE.md § 1). */

const heltall = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 });

/** Tall med norsk tusenskille, uten desimaler. */
export function tall(verdi: number): string {
  return heltall.format(verdi);
}

const desimaler = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 2 });

/** Tall med norsk desimalkomma, inntil to desimaler. */
export function desimaltall(verdi: number): string {
  return desimaler.format(verdi);
}

/**
 * P-verdien slik den skal leses.
 *
 * Under en tusendel skrives den som en grense i stedet for som et tall med
 * mange nuller. «p under 0,001» sier det samme som «p = 0,000014», og sier det
 * på en måte leseren kan bruke.
 */
export function pverdi(verdi: number): string {
  if (verdi < 0.001) return "p under 0,001";
  return `p = ${pdesimaler.format(verdi)}`;
}

const pdesimaler = new Intl.NumberFormat("nb-NO", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

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

/**
 * Året i en ISO 8601-periode: «2026-W31» og «2026» gir begge 2026.
 *
 * Årstallet kan bære fortegn — proxyen i K10 rekker ned før år null, og
 * «-0500» er år 500 fvt (§ 6). Fortegnet må derfor være med i utsnittet.
 */
export function aarstall(periode: string): number {
  const negativt = periode.startsWith("-");
  return Number(periode.slice(0, negativt ? 5 : 4));
}

/**
 * Årstallet slik leseren ser det: «6050 fvt» for negative år, ellers tallet.
 *
 * Oversettelsen fra kodeverdi til lesbar norsk tekst hører hjemme i
 * visningslaget, ikke i dataene (§ 1).
 */
export function aarstallTekst(aar: number): string {
  return aar < 0 ? `${Math.abs(aar)} fvt` : String(aar);
}
