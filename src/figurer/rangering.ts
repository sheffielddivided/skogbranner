/**
 * S2, figur 4 — rangeringstabellen (CLAUDE.md § 8).
 *
 * Hvert land med brent areal i km², andel av landarealet og andel av verdens
 * brente areal, for siste fullstendige år.
 *
 * Rekkefølgen er synkende etter brent areal. Land uten data står med «ingen
 * data» og sorteres sist uansett retning — en måling som mangler er ikke en
 * lav verdi (§ 6).
 */

import {
  serie,
  serieAar,
  grunnlag,
  avledning,
  alleFotnoter,
  type Observasjon,
} from "../lib/data";

const AREAL_SERIE = "owid_annual_area_burnt";
const ANDEL_SERIE = "owid_annual_area_burnt_share_land";

export const ID = "figur-rangering-land";

export interface Rad {
  entity: string;
  entity_name: string;
  /** null betyr at kilden ikke fører entiteten dette året — ingen data. */
  areal: number | null;
  andelLand: number | null;
  andelVerden: number | null;
  fotnoter: string[];
}

export function rangering() {
  const aar = grunnlag(AREAL_SERIE).last_complete_year;
  const periode = String(aar);

  const areal = serieAar(AREAL_SERIE, periode, "country");
  const andel = new Map(
    serieAar(ANDEL_SERIE, periode, "country").map((o) => [o.entity, o]),
  );

  const verden = serie(AREAL_SERIE, "WLD").find((o) => o.period === periode);
  if (!verden) {
    throw new Error(
      `Fant ingen verdensrad for ${periode}. Andelen av verdens brente areal kan ikke regnes.`,
    );
  }

  const rader: Rad[] = areal
    .map((o) => ({
      entity: o.entity,
      entity_name: o.entity_name,
      areal: o.value,
      andelLand: andel.get(o.entity)?.value ?? null,
      andelVerden: o.value / verden.value,
      fotnoter: o.footnotes,
    }))
    .sort((a, b) => (b.areal ?? -1) - (a.areal ?? -1) || a.entity.localeCompare(b.entity));

  const observasjoner = [
    ...areal,
    ...areal.map((o) => andel.get(o.entity)).filter((o): o is Observasjon => !!o),
  ];

  const brukte = new Set(observasjoner.flatMap((o) => o.footnotes));
  const fotnoter = alleFotnoter()
    .map(([kode]) => kode)
    .filter((kode) => brukte.has(kode));

  return {
    id: ID,
    aar,
    fotnoter,
    tittel: `Land etter brent areal, ${aar}`,
    rader,
    kildeIder: [verden.source_id],
    dekningPerKilde: { [verden.source_id]: { fra: aar, til: aar } },
    observasjoner,
    csvFil: `${ID}.csv`,
    konsentrasjon: avledning(`concentration.${AREAL_SERIE}.${aar}`),
  };
}
