/**
 * Katalogen over de bearbeidede filene, til nedlastingslisten i S6.
 *
 * Radtall og serier leses av filene selv ved bygging, ikke skrevet for hånd —
 * en fil som vokser, oppdaterer sin egen linje (P3). Beskrivelsen av hva filen
 * inneholder er derimot redaksjonell tekst, og står her.
 *
 * Filnavnene er de samme som PROCESSED_FILE i etl/schema.py gir. De står her
 * fordi importen trenger en litteral sti, ikke fordi lista er en ny sannhet:
 * en fil som ikke finnes, gir byggefeil med én gang.
 */

import burnedArea from "../../data/processed/burned_area.json";
import shareLand from "../../data/processed/burned_area_share_land.json";
import firecci from "../../data/processed/burned_area_firecci_lt11.json";
import gfed5 from "../../data/processed/burned_area_gfed5.json";
import weekly from "../../data/processed/burned_area_weekly.json";
import charcoal from "../../data/processed/charcoal_composite_gcd.json";
import fireCount from "../../data/processed/fire_count.json";
import type { Observasjon } from "./data";

export interface Datafil {
  navn: string;
  innhold: string;
  rader: number;
  serier: string[];
  /** Én ekstra opplysning der filen trenger den. Ikke alle gjør det. */
  merknad?: string;
}

const FILER: { navn: string; innhold: string; rader: Observasjon[]; merknad?: string }[] = [
  {
    navn: "burned_area.csv",
    innhold: "Brent areal i km², fra alle kildene som fører det som landtall.",
    rader: burnedArea as Observasjon[],
  },
  {
    navn: "burned_area_share_land.csv",
    innhold:
      "Brent areal som andel av landets samlede landareal. Avledet av arealet, med landarealene fra Natural Earth som nevner.",
    rader: shareLand as Observasjon[],
  },
  {
    navn: "burned_area_firecci_lt11.csv",
    innhold: "FireCCILT11, det eldste globale satellittproduktet.",
    rader: firecci as Observasjon[],
  },
  {
    navn: "burned_area_gfed5.csv",
    innhold: "GFED5, som ser en større del av brannene enn de øvrige produktene.",
    rader: gfed5 as Observasjon[],
  },
  {
    navn: "burned_area_weekly.csv",
    innhold:
      "Brent areal per uke, summert til verdensdeler og verden. Landene bak summene publiseres ikke.",
    rader: weekly as Observasjon[],
  },
  {
    navn: "charcoal_composite_gcd.csv",
    innhold:
      "Kullkompositten fra innsjøsedimenter. Verdien er et enhetsløst tall, ikke et areal.",
    rader: charcoal as Observasjon[],
    merknad:
      "Filen inneholder alle punktene, også de som er utelatt fra figuren fordi grunnlaget tynnes ut mot vår egen tid. Antall sedimentkjerner bak hvert punkt står i n_series.",
  },
  {
    navn: "fire_count.csv",
    innhold: "Antall registrerte branner, fra de kildene som fører det.",
    rader: fireCount as Observasjon[],
    merknad:
      "Antall branner er et annet mål enn brent areal: mange små branner og én stor kan gi samme areal, men svært ulikt antall. Ingen figur på siden viser dette ennå.",
  },
];

/** Filene med radtall og serier, lest av filene selv. */
export function datafiler(): Datafil[] {
  return FILER.map((f) => ({
    navn: f.navn,
    innhold: f.innhold,
    merknad: f.merknad,
    rader: f.rader.length,
    serier: [...new Set(f.rader.map((o) => o.series_id))].sort(),
  }));
}
