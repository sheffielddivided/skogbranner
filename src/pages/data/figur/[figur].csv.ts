/**
 * Figurenes egne CSV-filer.
 *
 * Byggesteget skriver én CSV per figur, med nøyaktig de radene figuren tegner
 * — samme serier, samme entiteter, samme år (P5). Filene lages her og ikke av
 * et skript, slik at de får basisstien fra Astro og ikke kan komme i utakt med
 * figurene de hører til.
 *
 * De kanoniske filene under data/processed/ er noe annet. De bærer flere
 * serier og lenkes i sin helhet fra S6 (§ 8).
 */

import type { APIRoute } from "astro";
import { figurer } from "../../../figurer";
import { tilCsv } from "../../../lib/csv";

export function getStaticPaths() {
  return figurer.map((figur) => ({
    params: { figur: figur.id },
    props: { csv: tilCsv(figur.observasjoner) },
  }));
}

export const GET: APIRoute = ({ props }) =>
  new Response((props as { csv: string }).csv, {
    headers: { "content-type": "text/csv; charset=utf-8" },
  });
