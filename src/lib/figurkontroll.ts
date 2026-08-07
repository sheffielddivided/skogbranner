/**
 * Kontroll av figurene ved bygging (CLAUDE.md § 6).
 *
 * Kvalitetsregelen håndheves i to lag, fordi ingen av dem ser hele bildet
 * alene. `validate.py` ser dataene og kontrollerer at hver serie har én
 * `quality`. Den kan ikke se hva som havner i samme figur. Det er denne
 * kontrollens oppgave: **ingen figur skal tegne flere `quality`-verdier uten
 * at bruddet er markert.**
 *
 * En figur som blander kvaliteter, må derfor oppgi `kvalitetsforklaring` — én
 * tekst per kvalitet den tegner — og hver av dem må faktisk stå i figurens
 * tegnforklaring. En erklæring som ikke når leseren, er ingen markering.
 *
 * Modulen er ren og importerer ingen data, slik at den kan testes uten Astro.
 */

export interface Kontrollerbar {
  id: string;
  observasjoner: { quality: string }[];
  tegnforklaring?: { merke: string; tekst: string }[];
  /** Kvalitet → teksten som forklarer hvordan den er skilt ut i figuren. */
  kvalitetsforklaring?: Record<string, string>;
}

export class Figurfeil extends Error {}

/** Kvalitetene en figur faktisk tegner, i alfabetisk rekkefølge. */
export function kvaliteter(figur: Kontrollerbar): string[] {
  return [...new Set(figur.observasjoner.map((o) => o.quality))].sort();
}

/**
 * Kaster hvis en figur tegner flere kvaliteter uten synlig markering.
 *
 * Kastet stopper bygget. Det er med vilje: en figur som skjuler et
 * kvalitetsbrudd, skal ikke kunne publiseres.
 */
export function kontrollerKvalitetsbrudd(figurer: Kontrollerbar[]): void {
  for (const figur of figurer) {
    const funnet = kvaliteter(figur);
    if (funnet.length < 2) continue;

    const forklaring = figur.kvalitetsforklaring ?? {};
    const mangler = funnet.filter((k) => !forklaring[k]);
    if (mangler.length > 0) {
      throw new Figurfeil(
        `Figuren ${figur.id} tegner kvalitetene ${funnet.join(", ")}, men ` +
          `mangler kvalitetsforklaring for ${mangler.join(", ")}. ` +
          "Serier med ulik quality skal aldri slås sammen uten synlig " +
          "markering av bruddet (CLAUDE.md § 6).",
      );
    }

    const iTegnforklaringen = (figur.tegnforklaring ?? []).map((t) => t.tekst);
    for (const kvalitet of funnet) {
      const tekst = forklaring[kvalitet]!;
      if (!iTegnforklaringen.some((t) => t.includes(tekst))) {
        throw new Figurfeil(
          `Figuren ${figur.id} erklærer at kvaliteten ${kvalitet} er markert ` +
            `med «${tekst}», men den teksten står ikke i figurens ` +
            "tegnforklaring. Markeringen når da ikke leseren (§ 6).",
        );
      }
    }
  }
}
