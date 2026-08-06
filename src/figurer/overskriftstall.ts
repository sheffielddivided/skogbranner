/**
 * S1, figur 1 — overskriftstallet (CLAUDE.md § 8).
 *
 * Globalt brent areal for siste fullstendige år, med arealsammenligningen som
 * gir leseren en fysisk referanse. Begge tall er maskinelt avledet, og hver
 * setning bærer id-en til avledningen den kommer fra (P3).
 *
 * Ingenting her velges redaksjonelt: verken året, tallet eller
 * sammenligningslandet.
 */

import { avledning, grunnlag, serie, type Observasjon } from "../lib/data";

const SERIES_ID = "owid_annual_area_burnt";
const ENTITY = "WLD";

export const ID = "figur-overskriftstall";

export interface Overskriftstall {
  id: string;
  tittel: string;
  /** Året tallet gjelder — siste fullstendige år, aldri inneværende (§ 7). */
  aar: number;
  verdi: number;
  enhet: string;
  sammenligning: {
    land: string;
    areal: number;
    avvikProsent: number;
  };
  /** Verdien av data-derivation på setningene som bærer tallene (P3). */
  avledningId: string;
  kildeIder: string[];
  dekning: Record<string, { fra: number; til: number }>;
  fotnoter: string[];
  observasjoner: Observasjon[];
  csvFil: string;
}

export function overskriftstall(): Overskriftstall {
  const aar = grunnlag(SERIES_ID).last_complete_year;
  const id = `area_comparison.${SERIES_ID}.${aar}`;
  const a = avledning(id);

  const observasjon = serie(SERIES_ID, ENTITY).find(
    (o) => o.period === String(aar),
  );
  if (!observasjon) {
    throw new Error(
      `Fant ingen observasjon for ${ENTITY} i ${aar}, som avledningen ${id} bygger på.`,
    );
  }

  return {
    id: ID,
    tittel: `Globalt brent areal i ${aar}`,
    aar,
    verdi: a.value as number,
    enhet: a.unit as string,
    sammenligning: {
      land: a.comparison_entity_name as string,
      areal: a.comparison_area_km2 as number,
      avvikProsent: a.deviation_pct as number,
    },
    avledningId: id,
    kildeIder: [observasjon.source_id],
    dekning: { [observasjon.source_id]: { fra: aar, til: aar } },
    fotnoter: observasjon.footnotes,
    observasjoner: [observasjon],
    csvFil: `${ID}.csv`,
  };
}
