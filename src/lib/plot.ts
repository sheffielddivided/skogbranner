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
  return (figur as unknown as Element).outerHTML;
}
