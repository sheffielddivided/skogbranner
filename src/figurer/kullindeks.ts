/**
 * S5, figur 14 — kullindeksen fra Global Charcoal Database (CLAUDE.md § 8).
 *
 * Kompositten er en z-score, ikke et areal. Den får derfor alltid egen figur og
 * egen akse, og skal aldri stå i samme figur som en km²-serie (§ 6).
 *
 * Den mest sannsynlige feillesningen er å ta kurven for «brent areal over tid».
 * Figuren er bygget for å gjøre det vanskelig: tittelen sier hva verdien er,
 * aksen er navngitt i standardavvik, nullinjen er merket som seriens eget
 * gjennomsnitt, og ingen km²-verdi finnes noe sted i figuren — heller ikke i
 * tabellen eller i tooltipen.
 *
 * Visningen avgrenses ved den yngste enden, der grunnlaget tynnes ut. Regelen
 * bor i visning.ts, terskelen i schema.py, og andelen følger med kilden i
 * data/_sources.json (§ 9).
 */

import * as Plot from "@observablehq/plot";
import {
  serie,
  grunnlag,
  kilde,
  alleFotnoter,
  visningspunkter,
  type Observasjon,
} from "../lib/data";
import { tilSvg } from "../lib/plot";
import { aarstallTekst, desimaltall, tall } from "../lib/format";

const SERIE = "gcd_charcoal_composite";
const ENTITET = "WLD";

export const ID = "figur-kullindeks";

interface Punkt {
  aar: number;
  verdi: number;
  kjerner: number;
}

function tegn(id: string, punkter: Punkt[], bredde: number, hoyde: number) {
  return tilSvg(id, {
    width: bredde,
    height: hoyde,
    marginLeft: 96,
    marginRight: 24,
    marginBottom: 44,
    marginTop: 16,
    style: { background: "transparent", fontSize: "13px" },
    x: { label: "År", tickFormat: (d: number) => aarstallTekst(d) },
    // Aksen bærer enheten indikatortabellen angir: et enhetsløst tall (§ 9).
    // Ingen km² står noe sted i denne figuren.
    y: {
      label: "Standardavvik fra seriens gjennomsnitt (enhetsløst)",
      grid: true,
      tickFormat: (d: number) => desimaltall(d),
    },
    marks: [
      // Nullinjen er seriens eget gjennomsnitt, ikke fravær av brann. Den er
      // tegnet tydeligere enn rutenettet, og forklart i tegnforklaringen.
      Plot.ruleY([0], { stroke: "var(--farge-akse)", strokeWidth: 1.5 }),
      Plot.line(punkter, {
        x: "aar",
        y: "verdi",
        // Egen farge, ikke arealfargen: kurven skal ikke ligne på en km²-serie.
        stroke: "var(--farge-serie-c)",
        strokeWidth: 2,
        title: (d: Punkt) =>
          `${aarstallTekst(d.aar)}: ${desimaltall(d.verdi)} standardavvik, ${tall(
            d.kjerner,
          )} sedimentkjerner`,
      }),
    ],
  });
}

export function kullindeks() {
  const alle = serie(SERIE, ENTITET);
  const g = grunnlag(SERIE);

  // Andelen står i data/_sources.json, fordi byggetrinnet er TypeScript og
  // ikke kan lese schema.py — verdien har fortsatt bare ett hjem (§ 9).
  const k10 = kilde("K10") as unknown as { min_series_share: number };
  const vist = visningspunkter(alle, k10.min_series_share);

  const punkter: Punkt[] = vist.map((o) => ({
    aar: Number(o.period),
    verdi: o.value,
    kjerner: o.n_series ?? 0,
  }));

  const fra = punkter[0]!.aar;
  const til = punkter[punkter.length - 1]!.aar;

  const kjerner = alle.map((o) => o.n_series ?? 0);
  const tetteste = Math.max(...kjerner);
  const yngste = alle[alle.length - 1]!;
  const trimmet = alle.length - vist.length;

  const brukte = new Set(vist.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  return {
    id: ID,
    tittel: `Kullindeks fra innsjøsedimenter, ${aarstallTekst(fra)}–${aarstallTekst(
      til,
    )} — et indirekte spor etter brann, ikke brent areal`,
    svg: tegn(ID, punkter, 760, 400),
    svgMobil: tegn(`${ID}-mobil`, punkter, 360, 340),
    grafBeskrivelse:
      `Én kurve som viser kullindeksen fra innsjøsedimenter, fra ${aarstallTekst(
        fra,
      )} til ${aarstallTekst(til)}. Den loddrette aksen er standardavvik fra ` +
      `seriens eget gjennomsnitt og har ingen enhet — verdiene er ikke ` +
      `kvadratkilometer og ikke brent areal. Tallene står i tabellen under.`,
    kildeIder: ["K10"],
    dekningPerKilde: { K10: { fra, til } },
    fotnoter,
    tegnforklaring: [
      {
        merke: "rekonstruert",
        tekst: "Kullindeks: hvor mye kull som er avsatt i sedimentene, som standardavvik fra seriens eget gjennomsnitt.",
      },
      {
        merke: "nullinje",
        tekst: "Nullinjen er seriens eget gjennomsnitt gjennom hele perioden. Den betyr ikke at ingenting brant.",
      },
    ],
    tabell: {
      beskrivelse:
        `Kullindeksen per punkt, med antall sedimentkjerner bak hvert av dem. ` +
        `Verdien er et enhetsløst tall — standardavvik fra seriens ` +
        `gjennomsnitt — og kan ikke sammenlignes med et areal.`,
      kolonner: ["År", "Kullindeks (standardavvik)", "Sedimentkjerner"],
      rader: punkter.map((p) => [
        aarstallTekst(p.aar),
        desimaltall(p.verdi),
        tall(p.kjerner),
      ]),
    },
    // Figurens egne rader: de punktene kurven faktisk tegner, med n_series.
    // Punktene som er trimmet bort, ligger i den kanoniske filen (§ 9).
    observasjoner: vist as Observasjon[],
    csvFil: `${ID}.csv`,
    fra,
    til,
    // Til teksten under figuren. Alle tallene er lest av datasettet.
    tetteste,
    yngsteAar: Number(yngste.period),
    yngsteKjerner: yngste.n_series ?? 0,
    trimmet,
    punkter: punkter.length,
    forsteAar: g.first_year,
  };
}
