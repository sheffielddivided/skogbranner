/**
 * Kontroll av utsnittet kartene tegnes i.
 *
 * Testen tegner et kart med utsnittet og måler hvor stor flaten faktisk ble.
 * Det er den eneste kontrollen som fanger feilen: en rute vridd feil vei gir
 * ingen feilmelding, bare et kart der alt er tegnet i samme punkt.
 */

import test from "node:test";
import assert from "node:assert/strict";
import * as Plot from "@observablehq/plot";
import { parseHTML } from "linkedom";
import { utsnittsflate, signertAreal } from "./kartutsnitt.ts";

const EFFIS = { vest: -26, sor: 11, ost: 62, nord: 72 };

const BREDDE = 760;
const HOYDE = 460;

/** Hvor stor flate utsnittets fire hjørner faktisk dekker, i piksler. */
function tegnetFlate(domain: unknown): { bredde: number; hoyde: number } {
  const { document } = parseHTML("<!doctype html><html><body></body></html>");
  const figur = Plot.plot({
    document: document as unknown as Document,
    width: BREDDE,
    height: HOYDE,
    margin: 0,
    projection: { type: "conic-conformal", domain } as never,
    marks: [
      Plot.geo(
        {
          type: "MultiPoint",
          coordinates: [
            [EFFIS.vest, EFFIS.sor],
            [EFFIS.ost, EFFIS.sor],
            [EFFIS.ost, EFFIS.nord],
            [EFFIS.vest, EFFIS.nord],
          ],
        },
        { r: 1 },
      ),
    ],
  });
  const d = (figur as unknown as Element).querySelector("path")?.getAttribute("d") ?? "";
  const punkter = [...d.matchAll(/M(-?[\d.]+),(-?[\d.]+)/g)].map((m) => [
    Number(m[1]),
    Number(m[2]),
  ]);
  if (punkter.length < 4) return { bredde: 0, hoyde: 0 };
  const x = punkter.map((p) => p[0]!);
  const y = punkter.map((p) => p[1]!);
  return {
    bredde: Math.max(...x) - Math.min(...x),
    hoyde: Math.max(...y) - Math.min(...y),
  };
}

test("utsnittet fyller flaten det tegnes på", () => {
  const { bredde, hoyde } = tegnetFlate(utsnittsflate(EFFIS));
  assert.ok(
    bredde > BREDDE / 2 && hoyde > HOYDE / 2,
    `hjørnene i utsnittet dekker bare ${bredde.toFixed(1)}×${hoyde.toFixed(1)} ` +
      `piksler av ${BREDDE}×${HOYDE} — projeksjonen har kollapset, og kartet ` +
      "blir en prikk",
  );
});

test("motsatt vikling er hele kloden utenom ruten, og kollapser kartet", () => {
  const vrengt = {
    type: "Polygon" as const,
    coordinates: [
      utsnittsflate(EFFIS).coordinates[0]!.slice().reverse() as [number, number][],
    ],
  };
  const { bredde, hoyde } = tegnetFlate(vrengt);
  assert.ok(bredde < 1 && hoyde < 1);
});

test("ruten vikles med klokken lest i lengde- og breddegrad", () => {
  assert.ok(signertAreal(utsnittsflate(EFFIS).coordinates[0]!) < 0);
});
