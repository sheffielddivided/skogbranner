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
import type { Observasjon } from "../lib/data";

export interface FigurData {
  id: string;
  csvFil: string;
  observasjoner: Observasjon[];
}

export const figurer: FigurData[] = [
  overskriftstall(),
  globaltBrentAreal(),
  kartBrentAreal(),
  rangering(),
  sesongprofil(),
  kumulativUke(),
];

export {
  overskriftstall,
  globaltBrentAreal,
  kartBrentAreal,
  rangering,
  sesongprofil,
  kumulativUke,
};
