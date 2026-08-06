/**
 * Kontroll av figurens egen CSV (P5).
 *
 * Filen skal inneholde nøyaktig de radene figuren tegner, i den rekkefølgen
 * figuren tegner dem, med de samme kolonnene som de kanoniske filene.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { tilCsv } from "./csv.ts";
import type { Observasjon } from "./data.ts";

const rad = (over: Partial<Observasjon> = {}): Observasjon => ({
  entity: "WLD",
  entity_name: "Verden",
  level: "world",
  period: "2025",
  indicator: "burned_area_km2",
  value: 2653676,
  unit: "km2",
  source_id: "K1",
  series_id: "owid_annual_area_burnt",
  quality: "measured",
  footnotes: ["f_sensor_break", "f_min_fire_size"],
  ...over,
});

test("kolonnene er de samme som i de kanoniske filene", () => {
  const [hode] = tilCsv([rad()]).split("\n");
  assert.equal(
    hode,
    "entity,entity_name,level,period,indicator,value,unit,source_id,series_id,quality,footnotes",
  );
});

test("fotnoter skilles med semikolon, ikke komma", () => {
  const linjer = tilCsv([rad()]).trim().split("\n");
  assert.equal(linjer.length, 2);
  assert.ok(linjer[1]!.endsWith("f_sensor_break;f_min_fire_size"));
  assert.equal(linjer[1]!.split(",").length, 11);
});

test("radene beholder rekkefølgen figuren tegner dem i", () => {
  const csv = tilCsv([
    rad({ period: "2024", value: 1 }),
    rad({ period: "2025", value: 2 }),
  ]);
  const perioder = csv
    .trim()
    .split("\n")
    .slice(1)
    .map((linje) => linje.split(",")[3]);
  assert.deepEqual(perioder, ["2024", "2025"]);
});

test("et navn med komma i seg bryter ikke kolonnene", () => {
  const csv = tilCsv([rad({ entity_name: "Kongo, Den demokratiske republikken" })]);
  const linje = csv.trim().split("\n")[1]!;
  assert.ok(linje.includes('"Kongo, Den demokratiske republikken"'));
});
