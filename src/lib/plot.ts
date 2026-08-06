/**
 * Rendrer Observable Plot til statisk SVG ved bygging.
 *
 * Grafene tegnes i Node, ikke i nettleseren. Da slipper leseren å laste et
 * grafbibliotek, og figurene vises også uten JavaScript (CLAUDE.md § 9).
 *
 * Biblioteket er en byggeavhengighet. Ingenting av det havner i det som
 * sendes til leseren (T2).
 */

import * as Plot from "@observablehq/plot";
import { parseHTML } from "linkedom";

type Plotopsjoner = Parameters<typeof Plot.plot>[0];

/**
 * Runder av koordinatene i tegneinstruksjonene.
 *
 * Plot skriver koordinater med full flyttallspresisjon. En tidel av en piksel
 * er under det en skjerm kan vise, og resten er tegn leseren laster ned uten å
 * se forskjell. Kartene er de tyngste figurene, og der er dette mange hundre
 * kilobyte.
 *
 * Bare attributtene som inneholder tegneinstruksjoner røres. Tekst, klasser og
 * tall leseren faktisk ser, står i andre attributter og er urørt.
 */
function rundKoordinater(svg: string): string {
  return svg.replace(
    /\s(d|points)="([^"]+)"/g,
    (_treff, attributt: string, verdi: string) =>
      ` ${attributt}="${verdi.replace(/-?\d+\.\d+/g, (n) =>
        String(Math.round(Number(n) * 10) / 10),
      )}"`,
  );
}

/**
 * @param id Stabil identifikator for figuren. Brukes som CSS-klasse i SVG-en,
 *   slik at bygget er deterministisk — Plot lager ellers et tilfeldig navn (T3).
 */
export function tilSvg(id: string, opsjoner: Plotopsjoner): string {
  const { document } = parseHTML("<!doctype html><html><body></body></html>");
  const figur = Plot.plot({
    ...opsjoner,
    document: document as unknown as Document,
    className: `graf-${id}`,
  });
  return rundKoordinater((figur as unknown as Element).outerHTML);
}
