"""Kontroll av forenklingen i etl/geo.py.

Geometrien bygges bare i Actions, av en shapefil som ikke ligger i repoet
(T4). Testene her kjører derfor på små, håndlagde former der fasiten er
åpenbar, og kontrollerer det forenklingen har lov til å gjøre: fjerne punkter
som ikke bærer form, og aldri fjerne et hjørne.

Kjøres fra repotoppen: ``python -m unittest etl.test_geo``
"""

import unittest

from etl import geo
from etl.schema import (
    GEO_COORD_DECIMALS,
    GEO_MIN_RING_POINTS,
    GEO_SIMPLIFY_TOLERANCE_DEG,
)


class Forenkling(unittest.TestCase):
    def test_punkter_paa_en_rett_linje_forsvinner(self):
        linje = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        self.assertEqual(geo.forenkle(linje, 0.05), [(0, 0), (4, 0)])

    def test_hjoerner_beholdes(self):
        # En firkant med et unødvendig midtpunkt på hver kant. Hjørnene bærer
        # formen; midtpunktene gjør ikke.
        ring = [
            (0, 0), (0.5, 0), (1, 0), (1, 0.5),
            (1, 1), (0.5, 1), (0, 1), (0, 0.5), (0, 0),
        ]
        self.assertEqual(
            geo.forenkle(ring, 0.05), [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        )

    def test_utstikk_over_toleransen_beholdes(self):
        self.assertEqual(
            geo.forenkle([(0, 0), (0.5, 0.2), (1, 0)], 0.05),
            [(0, 0), (0.5, 0.2), (1, 0)],
        )

    def test_utstikk_under_toleransen_fjernes(self):
        self.assertEqual(
            geo.forenkle([(0, 0), (0.5, 0.01), (1, 0)], 0.05), [(0, 0), (1, 0)]
        )

    def test_ingenting_aa_forenkle(self):
        self.assertEqual(geo.forenkle([(0, 0), (1, 1)], 0.05), [(0, 0), (1, 1)])
        self.assertEqual(geo.forenkle([], 0.05), [])


class Geometri(unittest.TestCase):
    def kvadrat(self, storrelse):
        return [
            [
                [0, 0],
                [storrelse, 0],
                [storrelse, storrelse],
                [0, storrelse],
                [0, 0],
            ]
        ]

    def forenkle(self, geometri, toleranse=GEO_SIMPLIFY_TOLERANCE_DEG):
        """Samme to steg som bygget: punktene avgjøres først, så settes de inn.

        Punktutvalget er felles for alle ringene, fordi det er det som holder
        delte grenser sammen. Testene går derfor samme vei som bygget.
        """
        behold = geo.behold_punkter([geometri], toleranse)
        return geo.forenkle_geometri(geometri, behold)

    def test_polygon_beholder_formen_og_lukkes(self):
        ut = self.forenkle({"type": "Polygon", "coordinates": self.kvadrat(10)})
        ring = ut["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertGreaterEqual(len(ring), GEO_MIN_RING_POINTS)

    def test_en_flate_som_forsvinner_helt_tas_ut(self):
        # En ring som er mindre enn toleransen har ingen flate igjen å tegne.
        liten = {"type": "Polygon", "coordinates": self.kvadrat(0.001)}
        self.assertIsNone(self.forenkle(liten))

    def test_multipolygon_beholder_de_flatene_som_har_form(self):
        ut = self.forenkle(
            {
                "type": "MultiPolygon",
                "coordinates": [self.kvadrat(10), self.kvadrat(0.001)],
            }
        )
        self.assertEqual(len(ut["coordinates"]), 1)

    def test_koordinatene_rundes(self):
        ut = self.forenkle(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [0.123456789, 0],
                        [10.987654321, 0],
                        [10, 10.55555555],
                        [0.123456789, 0],
                    ]
                ],
            }
        )
        for x, y in ut["coordinates"][0]:
            self.assertEqual(x, round(x, GEO_COORD_DECIMALS))
            self.assertEqual(y, round(y, GEO_COORD_DECIMALS))

    def test_en_ring_som_har_vrengt_seg_tas_ut(self):
        """En splint som overlever som en nesten rett trekant, tegnes ikke.

        Grensesplinter i kartdataene forenkles til noen få punkter som ligger
        nesten på linje. Fortegnet på arealet er da tilfeldig, og en ring som
        har byttet fortegn dekker hele kloden i stedet for seg selv.
        """
        splint = [[0, 0], [2, 0.02], [4, 0], [2, 0.01], [0, 0]]
        self.assertLess(geo.signert_areal(splint), 0)

        # Fire punkter igjen, altså nok til å passere punkttellingen, men det
        # ene av de to som bar formen er borte, og ringen vikler seg motsatt.
        vrengt = geo._ring(splint, {(0, 0), (4, 0), (2, 0.01)})
        self.assertIsNone(vrengt)

    def test_en_ring_som_beholder_viklingen_blir_staaende(self):
        ring = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        behold = {(p[0], p[1]) for p in ring}
        ut = geo._ring(ring, behold)
        self.assertIsNotNone(ut)
        self.assertGreater(geo.signert_areal(ut) * geo.signert_areal(ring), 0)

    def test_signert_areal_skiller_de_to_retningene(self):
        med_klokken = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
        mot_klokken = list(reversed(med_klokken))
        self.assertLess(geo.signert_areal(med_klokken), 0)
        self.assertGreater(geo.signert_areal(mot_klokken), 0)

    def test_ukjent_geometritype_avvises(self):
        with self.assertRaises(ValueError):
            geo.forenkle_geometri({"type": "LineString", "coordinates": []}, set())


if __name__ == "__main__":
    unittest.main()


class DelteGrenser(unittest.TestCase):
    """Forenklingen skal ikke rive naboland fra hverandre.

    Natural Earth deler koordinater eksakt mellom naboer. Forenkles hver ring
    for seg, kan Douglas–Peucker beholde et punkt i det ene landet og forkaste
    det i det andre — og da får kartet en hvit stripe langs grensen.
    """

    def naboer(self):
        """To ruter som deler en grense med en liten bulk på midten.

        Bulken er akkurat stor nok til at den ene ringen kan finne den verdt å
        beholde og den andre ikke, hvis de forenkles hver for seg.
        """
        grense = [[5, 0], [5, 3], [5.04, 5], [5, 7], [5, 10]]
        vest = [[0, 0]] + grense + [[0, 10], [0, 0]]
        # Øst leser den samme grensen andre veien, slik kartdata gjør. Ringen
        # går derfor rundt den andre veien også — ellers krysser den seg selv.
        ost = [[10, 0], [10, 10]] + list(reversed(grense)) + [[10, 0]]
        return (
            {"type": "Polygon", "coordinates": [vest]},
            {"type": "Polygon", "coordinates": [ost]},
        )

    def grensepunkter(self, ring):
        return [tuple(p) for p in ring if p[0] >= 5 - 1e-9 and p[0] <= 5.05]

    def test_delt_grense_far_samme_punkter_i_begge_land(self):
        vest, ost = self.naboer()
        behold = geo.behold_punkter([vest, ost], 0.05)

        ut_vest = geo.forenkle_geometri(vest, behold)
        ut_ost = geo.forenkle_geometri(ost, behold)

        langs_vest = set(self.grensepunkter(ut_vest["coordinates"][0]))
        langs_ost = set(self.grensepunkter(ut_ost["coordinates"][0]))
        self.assertEqual(
            langs_vest,
            langs_ost,
            "delt grense har ulike punkter i de to landene — kartet får en "
            "hvit stripe mellom dem",
        )

    def test_douglas_peucker_kan_avgjore_samme_punkt_ulikt(self):
        """Kontrollen som gir testen over verdi.

        Samme punkt, to omgivelser: i den ene ligger det langt fra linjen
        mellom naboene og beholdes, i den andre nesten på den og forkastes.
        Det er slik en delt grense river seg når hver ring forenkles for seg.
        """
        felles = [5, 0.06]
        med_bulk = geo.forenkle([[0, 0], felles, [10, 0]], 0.05)
        uten_bulk = geo.forenkle([[0, 0], felles, [10, 0.12]], 0.05)

        self.assertIn(felles, med_bulk)
        self.assertNotIn(felles, uten_bulk)

    def test_utvalget_er_unionen_av_ringenes_egne(self):
        """Et punkt én ring trenger, beholdes for alle ringene som har det."""
        a = {"type": "Polygon", "coordinates": [[[0, 0], [5, 0.06], [10, 0], [0, 0]]]}
        b = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [5, 0.06], [10, 0.12], [0, 0]]],
        }
        alene = geo.behold_punkter([b], 0.05)
        sammen = geo.behold_punkter([a, b], 0.05)

        self.assertNotIn((5, 0.06), alene)
        self.assertIn((5, 0.06), sammen)

