/**
 * Avgrensning av en kompositt ved den yngste enden.
 *
 * Ren modul, uten import av data. Det er med vilje: regelen skal kunne kjøres
 * av en test uten å dra inn hverken Astro eller datafilene.
 *
 * Regelen og begrunnelsen står i CLAUDE.md § 9. Kort: en kompositt av mange
 * kilder tynnes ut mot slutten når kildene slutter til ulik tid, og for K10
 * skjer det fordi sedimentkjerner slutter ved innsamlingstidspunktet.
 *
 * **Dette er en trimming av halen, ikke et filter.** Se testen i
 * `visning.test.ts`, som feiler hvis noen gjør den symmetrisk.
 */

/**
 * Sammenligner to ISO 8601-perioder i tidsrekkefølge.
 *
 * Årstallet kan bære fortegn — K10 rekker ned før år null (§ 6) — så perioden
 * kan ikke sammenlignes som streng: «-6050» kommer da etter «-10», og «990»
 * havner sist av alle. Året leses derfor som tall, og resten av perioden
 * («-W31», «-08») avgjør bare når årene er like.
 *
 * Funksjonen bor her fordi denne modulen er ren, og fordi det skal finnes
 * nøyaktig én slik sammenligner: data.ts bruker den samme.
 */
export function sammenlignPeriode(a: string, b: string): number {
  const aar = (p: string) => Number(p.slice(0, p.startsWith("-") ? 5 : 4));
  const rest = (p: string) => p.slice(p.startsWith("-") ? 5 : 4);
  return aar(a) - aar(b) || rest(a).localeCompare(rest(b));
}

/** Det minste et punkt trenger å bære for å kunne avgrenses. */
export interface Punkt {
  period: string;
  n_series?: number;
}

/**
 * Siste periode kompositten kan vises fram til.
 *
 * Går fra det yngste punktet og bakover så lenge punktene ligger under
 * terskelen, og stopper ved det første som er over. Returnerer null hvis ingen
 * punkter har ``n_series``, eller hvis alle ligger under terskelen.
 */
export function visningsgrense<T extends Punkt>(
  punkter: T[],
  minsteAndel: number,
): string | null {
  const sortert = sorterEtterPeriode(punkter);
  if (sortert.length === 0) return null;

  const grense = minsteAndel * Math.max(...sortert.map((p) => p.n_series!));

  let siste = sortert.length - 1;
  while (siste >= 0 && sortert[siste].n_series! < grense) siste -= 1;
  return siste < 0 ? null : sortert[siste].period;
}

/**
 * Punktene som skal vises: alt fra og med det eldste, til og med grensen.
 *
 * Den eldste enden trimmes aldri. Den er også tynn, men tynn på en annen måte
 * — se CLAUDE.md § 9.
 */
export function visningspunkter<T extends Punkt>(
  punkter: T[],
  minsteAndel: number,
): T[] {
  const grense = visningsgrense(punkter, minsteAndel);
  if (grense === null) return [];
  return sorterEtterPeriode(punkter).filter(
    (p) => Number(p.period) <= Number(grense),
  );
}

function sorterEtterPeriode<T extends Punkt>(punkter: T[]): T[] {
  return punkter
    .filter((p) => typeof p.n_series === "number")
    .slice()
    .sort((a, b) => sammenlignPeriode(a.period, b.period));
}
