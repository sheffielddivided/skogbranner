/**
 * Tester at avgrensningen av kompositten trimmer halen og ikke filtrerer.
 *
 * Kjøres med `npm test`. Node kjører TypeScript direkte, så testen trenger
 * ingen avhengigheter — og `visning.ts` importerer ingen data, slik at den kan
 * kjøres uten Astro.
 *
 * Regelen står i CLAUDE.md § 9.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { visningsgrense, visningspunkter, type Punkt } from "./visning.ts";

const ANDEL = 0.5;

/**
 * Formen på den virkelige kompositten: en lang, tynn eldste ende, en tett
 * midte, og en hale som faller brått. Tallene er K10s egne størrelsesordener.
 */
function kompositt(): Punkt[] {
  const punkter: Punkt[] = [];
  // Eldste ende: lavt, men stabilt — 31–39 % av det tetteste.
  for (let aar = -6050; aar < -2000; aar += 20) {
    punkter.push({ period: String(aar), n_series: 110 + (aar % 7) + 20 });
  }
  // Midten stiger mot det tetteste punktet.
  for (let aar = -2000; aar <= 1950; aar += 20) {
    punkter.push({ period: String(aar), n_series: 200 + Math.round((aar + 2000) / 25) });
  }
  // Halen faller: 69 %, 69 %, 28 %.
  punkter.push({ period: "1970", n_series: 248 });
  punkter.push({ period: "1990", n_series: 248 });
  punkter.push({ period: "2010", n_series: 99 });
  return punkter;
}

test("halen trimmes ved den yngste enden", () => {
  const vist = visningspunkter(kompositt(), ANDEL);
  assert.equal(visningsgrense(kompositt(), ANDEL), "1990");
  assert.equal(vist.at(-1)!.period, "1990");
  assert.ok(
    !vist.some((p) => p.period === "2010"),
    "punktet under terskelen ytterst i halen skal ikke vises",
  );
});

test("regelen er ikke et filter: det eldste punktet i visningen ligger UNDER terskelen", () => {
  const punkter = kompositt();
  const vist = visningspunkter(punkter, ANDEL);
  const grense = ANDEL * Math.max(...punkter.map((p) => p.n_series!));
  const eldste = vist[0];

  // Kjernen i asymmetrien. Gjøres regelen om til et filter, blir det eldste
  // viste punktet nødvendigvis større enn eller lik terskelen, og denne
  // påstanden faller. Se CLAUDE.md § 9.
  assert.ok(
    eldste.n_series! < grense,
    `det eldste viste punktet har ${eldste.n_series} serier, som er over ` +
      `terskelen på ${grense}. Da er regelen blitt et filter, og den lange ` +
      `linjen proxyen finnes for, er kuttet.`,
  );
});

test("den eldste enden beholdes i sin helhet", () => {
  const punkter = kompositt();
  const vist = visningspunkter(punkter, ANDEL);
  const eldsteIData = Math.min(...punkter.map((p) => Number(p.period)));

  assert.equal(Number(vist[0].period), eldsteIData);

  // Flertallet av punktene under terskelen ligger i den eldste enden. Et
  // filter ville strøket dem alle.
  const grense = ANDEL * Math.max(...punkter.map((p) => p.n_series!));
  const underTerskel = punkter.filter((p) => p.n_series! < grense);
  const beholdteUnderTerskel = vist.filter((p) => p.n_series! < grense);
  assert.ok(underTerskel.length > 10, "fikstur uten tynn eldste ende tester ingenting");
  assert.equal(beholdteUnderTerskel.length, underTerskel.length - 1);
});

test("utfallet er stabilt for terskler mellom 30 og 67 prosent", () => {
  // Verdien er ikke stemt for å gi et bestemt svar. Endres den innenfor
  // båndet, skal grensen ligge i ro.
  for (const andel of [0.3, 0.4, 0.5, 0.6, 0.667]) {
    assert.equal(visningsgrense(kompositt(), andel), "1990", `andel ${andel}`);
  }
});

test("punkter uten n_series holdes utenfor", () => {
  assert.equal(visningsgrense([{ period: "2000" }], ANDEL), null);
  assert.deepEqual(visningspunkter([], ANDEL), []);
});
