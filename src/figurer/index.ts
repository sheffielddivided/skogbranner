/**
 * Figurene på siden, samlet ett sted.
 *
 * Både siden og endepunktet som skriver figurenes CSV-filer leser denne
 * listen, slik at en figur ikke kan bli tegnet uten at nedlastingslenken
 * finnes — eller motsatt (P5).
 */

import { overskriftstall } from "./overskriftstall";
import { globaltBrentAreal } from "./globaltBrentAreal";
import { kartBrentAreal } from "./kartBrentAreal";
import { rangering } from "./rangering";
import { sesongprofil } from "./sesongprofil";
import { kumulativUke } from "./kumulativUke";
import { kartEuropa } from "./kartEuropa";
import { landsammenligning } from "./landsammenligning";
import { rangeringEuropa } from "./rangeringEuropa";
import { globaleSerier } from "./globaleSerier";
import { nasjonaleSerier } from "./nasjonaleSerier";
import { kullindeks } from "./kullindeks";
import type { Observasjon } from "../lib/data";
import { kontrollerKvalitetsbrudd } from "../lib/figurkontroll";

export interface FigurData {
  id: string;
  csvFil: string;
  observasjoner: Observasjon[];
  tegnforklaring?: { merke: string; tekst: string }[];
  /** Kvalitet → teksten som forklarer hvordan den er skilt ut (§ 6). */
  kvalitetsforklaring?: Record<string, string>;
}

export const figurer: FigurData[] = [
  overskriftstall(),
  globaltBrentAreal(),
  kartBrentAreal(),
  rangering(),
  sesongprofil(),
  kumulativUke(),
  kartEuropa(),
  landsammenligning(),
  rangeringEuropa(),
  globaleSerier(),
  nasjonaleSerier(),
  kullindeks(),
];

// Ingen figur skal tegne flere quality-verdier uten at bruddet er markert
// (§ 6). Kontrollen kjører her, når listen bygges, slik at et brudd stopper
// bygget i stedet for å bli publisert.
kontrollerKvalitetsbrudd(figurer);

export {
  overskriftstall,
  globaltBrentAreal,
  kartBrentAreal,
  rangering,
  sesongprofil,
  kumulativUke,
  kartEuropa,
  landsammenligning,
  rangeringEuropa,
  globaleSerier,
  nasjonaleSerier,
  kullindeks,
};
