/**
 * S1, figur 2 — oversiktsfiguren (CLAUDE.md § 8).
 *
 * Globalt brent areal per år over hele den tilgjengelige perioden, bygget på
 * K8, K9 og K1. De tegnes som tre serier med synlige brudd, hver etter sin
 * egen quality-verdi (§ 6). Ingen sammenskjøting til én kurve, verken visuelt
 * eller i data.
 *
 * Hvilke fotnoter figuren viser, utledes av observasjonene, ikke av en liste
 * her (P6).
 */

import * as Plot from "@observablehq/plot";
import { serie, alleFotnoter, type Observasjon } from "../lib/data";
import { tilSvg } from "../lib/plot";
import { tall, aarstall } from "../lib/format";

const ENTITY = "WLD";

export const ID = "figur-globalt-brent-areal";

const FOTNOTE_UFULLSTENDIG = "f_incomplete_year";

/**
 * Seriene i figuren, i den rekkefølgen de starter.
 *
 * Navnet er kortformen leseren ser i tegnforklaringen og tabellen. Kildens
 * fulle navn, lenke og lisens kommer fra data/_sources.json og står i
 * kildelinjen under figuren (P5).
 *
 * Fargen bærer aldri informasjon alene: hver serie har også sin egen
 * punktform, og den foreløpige serien er i tillegg tegnet svakere (§ 9).
 */
const SERIER = [
  {
    seriesId: "firecci_lt11_annual_burned_area",
    navn: "FireCCILT11",
    farge: "var(--farge-serie-c)",
    form: "triangle" as const,
    merke: "beta",
  },
  {
    seriesId: "gfed5_annual_burned_area",
    navn: "GFED5",
    farge: "var(--farge-serie-b)",
    form: "square" as const,
    merke: "maalt-b",
  },
  {
    seriesId: "owid_annual_area_burnt",
    navn: "Our World in Data",
    farge: "var(--farge-serie)",
    form: "circle" as const,
    merke: "maalt",
  },
];

interface Punkt {
  aar: number;
  verdi: number | null;
  navn: string;
  ufullstendig: boolean;
}

export function globaltBrentAreal() {
  const seriene = SERIER.map((oppsett) => {
    const observasjoner = serie(oppsett.seriesId, ENTITY);
    if (observasjoner.length === 0) {
      throw new Error(
        `Ingen observasjoner for ${ENTITY} i serien ${oppsett.seriesId}. Figuren kan ikke bygges.`,
      );
    }
    const punkter: Punkt[] = observasjoner.map((o) => ({
      aar: aarstall(o.period),
      verdi: o.value,
      navn: oppsett.navn,
      ufullstendig: o.footnotes.includes(FOTNOTE_UFULLSTENDIG),
    }));

    // Et år som mangler helt i kilden, tegnes som brudd i linjen — aldri som
    // null og aldri interpolert (§ 9). Et hull i punktene gir bruddet.
    const fra = punkter[0]!.aar;
    const til = punkter[punkter.length - 1]!.aar;
    const kjente = new Map(punkter.map((p) => [p.aar, p]));
    const medHull: Punkt[] = [];
    for (let aar = fra; aar <= til; aar++) {
      medHull.push(
        kjente.get(aar) ?? {
          aar,
          verdi: null,
          navn: oppsett.navn,
          ufullstendig: false,
        },
      );
    }

    return {
      ...oppsett,
      observasjoner,
      kvalitet: observasjoner[0]!.quality,
      kildeId: observasjoner[0]!.source_id,
      punkter: medHull,
      dekning: { fra, til },
    };
  });

  const alleObservasjoner = seriene.flatMap((s) => s.observasjoner);
  const dekning = {
    fra: Math.min(...seriene.map((s) => s.dekning.fra)),
    til: Math.max(...seriene.map((s) => s.dekning.til)),
  };

  const brukte = new Set(alleObservasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));
  const nummer = new Map(fotnoter.map((kode, i) => [kode, i + 1]));

  const marks = [
    Plot.ruleY([0], { stroke: "var(--farge-akse)" }),
    ...seriene.flatMap((s) => {
      // beta betyr at produsenten selv har merket datasettet som foreløpig.
      // Det vises som redusert opasitet, forklart i tegnforklaringen (§ 6).
      const opasitet = s.kvalitet === "beta" ? 0.55 : 1;
      const hele = s.punkter.filter((p) => !p.ufullstendig);
      const ufullstendige = s.punkter.filter((p) => p.ufullstendig);
      const sisteHele = hele.filter((p) => p.verdi !== null).at(-1);

      return [
        Plot.line(hele, {
          x: "aar",
          y: "verdi",
          stroke: s.farge,
          strokeWidth: 2,
          strokeOpacity: opasitet,
        }),
        Plot.dot(
          hele.filter((p) => p.verdi !== null),
          {
            x: "aar",
            y: "verdi",
            fill: s.farge,
            fillOpacity: opasitet,
            symbol: s.form,
            r: 3,
            title: (d: Punkt) => `${s.navn}, ${d.aar}: ${tall(d.verdi!)} km²`,
          },
        ),
        // Inneværende år vises, men skilles fra de hele årene: stiplet strek
        // fram til punktet, og et åpent merke (§ 6).
        ...(ufullstendige.length > 0 && sisteHele
          ? [
              Plot.line([sisteHele, ...ufullstendige], {
                x: "aar",
                y: "verdi",
                stroke: s.farge,
                strokeWidth: 2,
                strokeOpacity: opasitet,
                strokeDasharray: "4,3",
              }),
              Plot.dot(ufullstendige, {
                x: "aar",
                y: "verdi",
                stroke: s.farge,
                strokeOpacity: opasitet,
                fill: "var(--farge-flate)",
                symbol: s.form,
                r: 4,
                title: (d: Punkt) =>
                  `${s.navn}, ${d.aar}: ${tall(d.verdi!)} km², året er ikke omme`,
              }),
            ]
          : []),
      ];
    }),
  ];

  const yAkse = {
    label: "Brent areal (km²)",
    labelAnchor: "top" as const,
    labelArrow: "none" as const,
    grid: true,
    tickFormat: (d: number) => tall(d),
  };

  const svg = tilSvg(ID, {
    width: 760,
    height: 440,
    marginLeft: 96,
    marginBottom: 48,
    marginTop: 16,
    style: { background: "transparent", fontSize: "13px" },
    x: { label: "År", tickFormat: (d: number) => String(d), labelOffset: 40 },
    y: { ...yAkse, labelOffset: 90 },
    marks,
  });

  // Eget oppsett for smal skjerm, ikke den samme figuren skalert ned (§ 9).
  // Enheten er den samme — km² er primærenheten uansett skjermbredde (T1).
  const svgMobil = tilSvg(`${ID}-mobil`, {
    width: 360,
    height: 400,
    marginLeft: 82,
    marginBottom: 56,
    marginTop: 26,
    style: { background: "transparent", fontSize: "12px" },
    x: {
      label: "År",
      tickFormat: (d: number) => String(d),
      ticks: 5,
      tickRotate: -45,
      labelOffset: 48,
    },
    y: { ...yAkse, ticks: 4, labelOffset: 76 },
    marks,
  });

  const aarene: number[] = [];
  for (let aar = dekning.fra; aar <= dekning.til; aar++) aarene.push(aar);

  const verdiPerSerie = seriene.map(
    (s) =>
      new Map(
        s.observasjoner.map((o) => [aarstall(o.period), o] as [number, Observasjon]),
      ),
  );

  const tabell = {
    beskrivelse: `Globalt brent areal per år i km², ${dekning.fra}–${dekning.til}. Hver serie er ett produkt, og «ingen data» betyr at serien ikke dekker året. Tallene er de samme som i grafen over.`,
    kolonner: ["År", ...seriene.map((s) => `${s.navn} (km²)`), "Forbehold"],
    rader: aarene.map((aar) => {
      const rader = verdiPerSerie.map((per) => per.get(aar));
      const koder = new Set(rader.flatMap((o) => o?.footnotes ?? []));
      return [
        String(aar),
        ...rader.map((o) => (o ? tall(o.value) : "ingen data")),
        [...koder]
          .map((kode) => nummer.get(kode))
          .filter((n): n is number => n !== undefined)
          .sort((a, b) => a - b)
          .join(", "),
      ];
    }),
  };

  const tegnforklaring = [
    ...seriene.map((s) => ({
      merke: s.merke,
      tekst:
        s.kvalitet === "beta"
          ? `${s.navn}, ${s.dekning.fra}–${s.dekning.til}. Tegnet svakere fordi produsenten selv har merket datasettet som foreløpig.`
          : `${s.navn}, ${s.dekning.fra}–${s.dekning.til}. Satellittmålt.`,
    })),
    {
      merke: "ufullstendig-punkt",
      tekst:
        "Åpent merke og stiplet strek: året er ikke omme. Punktet viser bare det som er registrert så langt, og kan ikke sammenlignes med et helt år.",
    },
  ];

  return {
    id: ID,
    tittel: `Globalt brent areal per år, ${dekning.fra}–${dekning.til}`,
    svg,
    svgMobil,
    grafBeskrivelse:
      `Linjediagram som viser globalt brent areal i kvadratkilometer per år fra ${dekning.fra} til ${dekning.til}. ` +
      `Tre serier tegnes hver for seg, uten å skjøtes sammen: ` +
      seriene
        .map((s) => `${s.navn} ${s.dekning.fra}–${s.dekning.til}`)
        .join(", ") +
      ". Tallene står i tabellen under grafen.",
    kildeIder: seriene.map((s) => s.kildeId),
    dekning,
    dekningPerKilde: Object.fromEntries(
      seriene.map((s) => [s.kildeId, s.dekning]),
    ),
    fotnoter,
    tegnforklaring,
    // Figuren tegner både beta og measured. Bruddet er markert med opasitet og
    // punktform, og markeringen står i tegnforklaringen (§ 6).
    kvalitetsforklaring: {
      beta: "Tegnet svakere fordi produsenten selv har merket datasettet som foreløpig.",
      measured: "Satellittmålt.",
    },
    tabell,
    observasjoner: alleObservasjoner,
    csvFil: `${ID}.csv`,
  };
}
