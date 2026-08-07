/**
 * Kontroll av formateringen.
 *
 * Årstall er den ene som kan bite: perioden bærer fortegn for K10, som rekker
 * ned før år null (CLAUDE.md § 6). Et utsnitt på fire tegn ville gjort
 * «-6050» til −605 uten å feile noe sted.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { aarstall, aarstallTekst } from "./format.ts";

test("aarstall leser år av en periode", () => {
  assert.equal(aarstall("2026"), 2026);
  assert.equal(aarstall("2026-W31"), 2026);
  assert.equal(aarstall("2026-08"), 2026);
});

test("aarstall tar fortegnet med", () => {
  assert.equal(aarstall("-6050"), -6050);
  assert.equal(aarstall("-0500"), -500);
});

test("aarstallTekst skriver år før år null som fvt", () => {
  assert.equal(aarstallTekst(-6050), "6050 fvt");
  assert.equal(aarstallTekst(-500), "500 fvt");
});

test("aarstallTekst lar år etter år null stå som tall", () => {
  assert.equal(aarstallTekst(1990), "1990");
  assert.equal(aarstallTekst(0), "0");
});
