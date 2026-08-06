/**
 * S4, figur 11 — den sorterbare tabellen for EFFIS-området (CLAUDE.md § 8).
 *
 * Hvert land med brent areal i km² og som andel av landarealet, for siste
 * fullstendige år. Kilden er K4, EFFIS' egen satellittkartlegging.
 *
 * Ingen andel av verdens brente areal: K4 dekker et område, ikke kloden, og en
 * andel av en sum som ikke finnes, ville vært et tall uten nevner. Kolonnen
 * faller derfor bort her.
 *
 * Rekkefølgen er synkende etter brent areal. Land uten data står med «ingen
 * data» og sorteres sist uansett retning — en måling som mangler er ikke en
 * lav verdi (§ 6).
 */

import {
  serieAar,
  grunnlag,
  alleFotnoter,
  type Observasjon,
} from "../lib/data";
import type { Rad } from "./rangering";

const AREAL_SERIE = "effis_rda_annual_burned_area";
const ANDEL_SERIE = "effis_rda_annual_burned_area_share_land";

export const ID = "figur-rangering-europa";

export function rangeringEuropa() {
  const aar = grunnlag(AREAL_SERIE).last_complete_year;
  const periode = String(aar);

  const areal = serieAar(AREAL_SERIE, periode, "country");
  const andel = serieAar(ANDEL_SERIE, periode, "country");
  const andelPer = new Map(andel.map((o) => [o.entity, o.value]));

  const rader: Rad[] = [...areal]
    .sort((a, b) => b.value - a.value || a.entity.localeCompare(b.entity))
    .map((o) => ({
      entity: o.entity,
      entity_name: o.entity_name,
      areal: o.value,
      andelLand: andelPer.get(o.entity) ?? null,
      fotnoter: o.footnotes,
    }));

  const observasjoner: Observasjon[] = [...areal, ...andel];
  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  return {
    id: ID,
    tittel: `Brent areal per land, ${aar}`,
    aar,
    rader,
    kildeIder: ["K4"],
    dekningPerKilde: { K4: { fra: aar, til: aar } },
    fotnoter,
    observasjoner,
    csvFil: `${ID}.csv`,
  };
}
