/**
 * S1 — globalt brent areal per år, fra K1.
 *
 * Bygger graf, tabell og fotnoteliste fra de kanoniske observasjonene. Ingen
 * verdier skrives for hånd, og hvilke fotnoter figuren viser utledes av
 * dataene, ikke av en liste her (CLAUDE.md P3, P6).
 */

import * as Plot from "@observablehq/plot";
import { serie, alleFotnoter } from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall, aarstall } from "../lib/format";

const SERIES_ID = "owid_annual_area_burnt";
const ENTITY = "WLD";

export const ID = "figur-globalt-brent-areal";

const FOTNOTE_UFULLSTENDIG = "f_incomplete_year";

export function globaltBrentAreal() {
  const observasjoner = serie(SERIES_ID, ENTITY);
  if (observasjoner.length === 0) {
    throw new Error(
      `Ingen observasjoner for ${ENTITY} i serien ${SERIES_ID}. Figuren kan ikke bygges.`,
    );
  }

  const rader = observasjoner.map((o) => ({
    aar: aarstall(o.period),
    verdi: o.value,
    ufullstendig: o.footnotes.includes(FOTNOTE_UFULLSTENDIG),
    fotnoter: o.footnotes,
  }));

  const dekning = {
    fra: rader[0]!.aar,
    til: rader[rader.length - 1]!.aar,
  };

  // Fotnotene figuren skal vise er de som faktisk står på observasjonene.
  // Rekkefølgen tas fra data/_footnotes.json, så nummereringen er stabil
  // mellom bygg (T3).
  const brukte = new Set(rader.flatMap((r) => r.fotnoter));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));
  const nummer = new Map(fotnoter.map((kode, i) => [kode, i + 1]));

  const fullstendige = rader.filter((r) => !r.ufullstendig);
  const ufullstendige = rader.filter((r) => r.ufullstendig);

  const marks = [
    Plot.barY(fullstendige, {
      x: "aar",
      y: "verdi",
      fill: "var(--farge-serie)",
      title: (d: { aar: number; verdi: number }) =>
        `${d.aar}: ${tall(d.verdi)} km²`,
    }),
    // Ufullstendig år får både lysere flate og stiplet omriss, slik at det
    // skiller seg fra de hele årene også uten fargesyn (§ 9).
    Plot.barY(ufullstendige, {
      x: "aar",
      y: "verdi",
      fill: "var(--farge-serie-svak)",
      stroke: "var(--farge-serie)",
      strokeWidth: 1.5,
      strokeDasharray: "4,3",
      title: (d: { aar: number; verdi: number }) =>
        `${d.aar}: ${tall(d.verdi)} km², året er ikke omme`,
    }),
    Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
  ];

  const svg = tilSvg(ID, {
    width: 760,
    height: 420,
    marginLeft: 82,
    marginBottom: 48,
    marginTop: 16,
    style: { background: "transparent", fontSize: "13px" },
    x: { label: "År", tickFormat: (d: number) => String(d), labelOffset: 40 },
    y: {
      label: "Brent areal (km²)",
      labelAnchor: "top",
      labelArrow: "none",
      grid: true,
      tickFormat: (d: number) => tall(d),
      labelOffset: 76,
    },
    marks,
  });

  // Eget oppsett for smal skjerm, ikke den samme figuren skalert ned (§ 9):
  // smalere format, årstall annethvert år og på skrå, og færre verdier på
  // y-aksen. Enheten er den samme — km² er primærenheten uansett skjermbredde
  // (T1), så aksen bytter ikke til tusener for å spare plass.
  const svgMobil = tilSvg(`${ID}-mobil`, {
    width: 360,
    height: 400,
    marginLeft: 74,
    marginBottom: 54,
    marginTop: 26,
    style: { background: "transparent", fontSize: "12px" },
    x: {
      label: "År",
      tickFormat: (d: number) => String(d),
      ticks: rader.filter((_, i) => i % 2 === 0).map((r) => r.aar),
      tickRotate: -45,
      labelOffset: 46,
    },
    y: {
      label: "Brent areal (km²)",
      labelAnchor: "top",
      labelArrow: "none",
      grid: true,
      tickFormat: (d: number) => tall(d),
      ticks: 4,
      labelOffset: 68,
    },
    marks,
  });

  const tabell = {
    beskrivelse: `Globalt brent areal per år i km², ${dekning.fra}–${dekning.til}. Tallene i tabellen er de samme som i grafen over.`,
    kolonner: ["År", "Brent areal (km²)", "Forbehold"],
    rader: rader.map((r) => [
      String(r.aar),
      tall(r.verdi),
      r.fotnoter
        .map((kode) => nummer.get(kode))
        .filter((n): n is number => n !== undefined)
        .sort((a, b) => a - b)
        .join(", "),
    ]),
  };

  const tegnforklaring = [
    { merke: "maalt", tekst: "Helt år" },
    {
      merke: "ufullstendig",
      tekst:
        "Året er ikke omme. Søylen viser bare det som er registrert så langt, og kan ikke sammenlignes med et helt år.",
    },
  ];

  return {
    id: ID,
    tittel: `Globalt brent areal per år, ${dekning.fra}–${dekning.til}`,
    svg,
    svgMobil,
    grafBeskrivelse: `Søylediagram som viser globalt brent areal i kvadratkilometer for hvert år fra ${dekning.fra} til ${dekning.til}. Tallene står i tabellen under grafen.`,
    kildeId: observasjoner[0]!.source_id,
    dekning,
    fotnoter,
    tegnforklaring,
    tabell,
  };
}
