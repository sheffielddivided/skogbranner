"""Kontroll av forenklingen i etl/geo.py.

Geometrien bygges bare i Actions, av en shapefil som ikke ligger i repoet
(T4). Testene her kjører derfor på små, håndlagde former der fasiten er
åpenbar, og kontrollerer det forenklingen har lov til å gjøre: fjerne punkter
som ikke bærer form, og aldri fjerne et hjørne.

Kjøres fra repotoppen: ``python -m unittest etl.test_geo``
"""

import unittest

from etl import geo
from etl.schema import GEO_COORD_DECIMALS, GEO_MIN_RING_POINTS


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

    def test_polygon_beholder_formen_og_lukkes(self):
        ut = geo.forenkle_geometri({"type": "Polygon", "coordinates": self.kvadrat(10)})
        ring = ut["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertGreaterEqual(len(ring), GEO_MIN_RING_POINTS)

    def test_en_flate_som_forsvinner_helt_tas_ut(self):
        # En ring som er mindre enn toleransen har ingen flate igjen å tegne.
        liten = {"type": "Polygon", "coordinates": self.kvadrat(0.001)}
        self.assertIsNone(geo.forenkle_geometri(liten))

    def test_multipolygon_beholder_de_flatene_som_har_form(self):
        ut = geo.forenkle_geometri(
            {
                "type": "MultiPolygon",
                "coordinates": [self.kvadrat(10), self.kvadrat(0.001)],
            }
        )
        self.assertEqual(len(ut["coordinates"]), 1)

    def test_koordinatene_rundes(self):
        ut = geo.forenkle_geometri(
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

    def test_ukjent_geometritype_avvises(self):
        with self.assertRaises(ValueError):
            geo.forenkle_geometri({"type": "LineString", "coordinates": []})


if __name__ == "__main__":
    unittest.main()
