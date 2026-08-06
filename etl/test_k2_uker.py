"""Kontroll av summeringen av GWIS' ukesserie til soner og verden.

Hentingen krever nett og kjøres bare i Actions (T4). Summeringen gjør ikke,
og er der feilene ville blitt dyre: et land i feil sone, eller et land som
telles to ganger i verdenstallet.

Kjøres fra repotoppen: ``python -m unittest etl.test_k2_uker``
"""

import unittest

from etl.sources import k2_gwis


class Summering(unittest.TestCase):
    def setUp(self):
        self.soner = {"EUR": ["NOR", "SWE"], "NAC": ["USA"]}

    def test_landene_summeres_til_sin_sone(self):
        rader = k2_gwis._summer_til_soner(
            {("NOR", 2024, 1): 100.0, ("SWE", 2024, 1): 50.0}, self.soner
        )
        eur = [r for r in rader if r["entity"] == "EUR"]
        self.assertEqual(len(eur), 1)
        self.assertEqual(eur[0]["ba_ha"], 150.0)

    def test_verden_summeres_av_landene_ikke_av_sonene(self):
        # USA ligger i NAC, Norge i EUR. Verden er summen av landene.
        rader = k2_gwis._summer_til_soner(
            {("NOR", 2024, 1): 100.0, ("USA", 2024, 1): 700.0}, self.soner
        )
        verden = [r for r in rader if r["entity"] == "WLD"]
        self.assertEqual(verden[0]["ba_ha"], 800.0)

    def test_et_land_utenfor_sonene_teller_likevel_globalt(self):
        # Et land kilden fører uten å legge i en sone, skal ikke forsvinne ut
        # av verdenstallet.
        rader = k2_gwis._summer_til_soner({("ATA", 2024, 1): 9.0}, self.soner)
        self.assertEqual([r["entity"] for r in rader], ["WLD"])
        self.assertEqual(rader[0]["ba_ha"], 9.0)

    def test_et_land_i_to_soner_telles_en_gang_globalt(self):
        soner = {"EUR": ["RUS"], "ASI": ["RUS"]}
        rader = k2_gwis._summer_til_soner({("RUS", 2024, 1): 10.0}, soner)
        per = {r["entity"]: r["ba_ha"] for r in rader}
        self.assertEqual(per["EUR"], 10.0)
        self.assertEqual(per["ASI"], 10.0)
        self.assertEqual(per["WLD"], 10.0)

    def test_ukene_holdes_fra_hverandre(self):
        rader = k2_gwis._summer_til_soner(
            {("NOR", 2024, 1): 1.0, ("NOR", 2024, 2): 2.0}, self.soner
        )
        eur = {r["week"]: r["ba_ha"] for r in rader if r["entity"] == "EUR"}
        self.assertEqual(eur, {1: 1.0, 2: 2.0})


if __name__ == "__main__":
    unittest.main()
