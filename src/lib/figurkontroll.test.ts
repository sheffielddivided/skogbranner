/**
 * Kontroll av byggekontrollen (CLAUDE.md § 6).
 *
 * Regelen står i to lag: validate.py ser dataene, denne ser figurene. Testene
 * under dekker det validate.py ikke kan se — at flere kvaliteter i én figur
 * krever en markering leseren faktisk møter.
 */

import test from "node:test";
import assert from "node:assert/strict";
import {
  kontrollerKvalitetsbrudd,
  kvaliteter,
  Figurfeil,
} from "./figurkontroll.ts";

const maalt = { quality: "measured" };
const beta = { quality: "beta" };
const rapportert = { quality: "reported" };

test("én kvalitet krever ingen markering", () => {
  kontrollerKvalitetsbrudd([
    { id: "figur-en", observasjoner: [maalt, maalt] },
  ]);
});

test("flere kvaliteter uten erklæring stopper bygget", () => {
  assert.throws(
    () =>
      kontrollerKvalitetsbrudd([
        { id: "figur-to", observasjoner: [maalt, beta] },
      ]),
    Figurfeil,
  );
});

test("erklæring som mangler én av kvalitetene stopper bygget", () => {
  assert.throws(
    () =>
      kontrollerKvalitetsbrudd([
        {
          id: "figur-tre",
          observasjoner: [maalt, beta],
          tegnforklaring: [{ merke: "maalt", tekst: "Satellittmålt." }],
          kvalitetsforklaring: { measured: "Satellittmålt." },
        },
      ]),
    /mangler kvalitetsforklaring for beta/,
  );
});

test("erklæring som ikke står i tegnforklaringen stopper bygget", () => {
  // Dette er kjernen: en markering som bare finnes i koden, når ikke leseren.
  assert.throws(
    () =>
      kontrollerKvalitetsbrudd([
        {
          id: "figur-fire",
          observasjoner: [maalt, beta],
          tegnforklaring: [{ merke: "maalt", tekst: "Satellittmålt." }],
          kvalitetsforklaring: {
            measured: "Satellittmålt.",
            beta: "Tegnet svakere fordi produsenten merker den som foreløpig.",
          },
        },
      ]),
    /står ikke i figurens tegnforklaring/,
  );
});

test("markert brudd går igjennom", () => {
  kontrollerKvalitetsbrudd([
    {
      id: "figur-fem",
      observasjoner: [maalt, rapportert],
      tegnforklaring: [
        { merke: "maalt", tekst: "Satellittkartlagt av EFFIS, 2006–2025." },
        { merke: "rapportert", tekst: "Rapportert av landet selv, 1980–2024." },
      ],
      kvalitetsforklaring: {
        measured: "Satellittkartlagt av EFFIS",
        reported: "Rapportert av landet selv",
      },
    },
  ]);
});

test("kvaliteter leses av observasjonene, ikke av erklæringen", () => {
  assert.deepEqual(
    kvaliteter({ id: "f", observasjoner: [beta, maalt, maalt, rapportert] }),
    ["beta", "measured", "reported"],
  );
});
