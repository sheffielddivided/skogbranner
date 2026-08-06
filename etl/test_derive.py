"""Kontroll av avledningene i etl/derive.py.

Theil–Sen og Mann–Kendall er skrevet ut i repoet, og en implementasjon som
bare sammenlignes med seg selv er ikke kontrollert. Testene her bruker derfor
datasett der fasiten er kjent uten å kjøre koden:

* stigningstall som følger av at dataene ligger på en rett linje
* S og variansen regnet for hånd fra definisjonen, med tallene i kommentaren
* p-verdien kontrollert mot statistics.NormalDist, som er en annen
  implementasjon av normalfordelingen enn math.erfc i derive.py

I tillegg kontrolleres egenskaper som må holde uansett datasett: snur man
serien, snur S fortegn; legger man til en konstant, endres ingenting.

Kjøres fra repotoppen: ``python -m unittest etl.test_derive``
"""

import unittest
from statistics import NormalDist

from etl import derive
from etl.schema import TREND_MAX_ZERO_SHARE, TREND_MAX_ZERO_TAIL, TREND_MIN_YEARS


def _serie(verdier, **felt):
    """En serie i den formen avledningene leser, bygget fra år og verdier.

    ``verdier`` er {år: verdi} eller {år: (verdi, tvetydig_null)}.
    """
    entiteter = {}
    for aar, rad in verdier.items():
        verdi, tvetydig = rad if isinstance(rad, tuple) else (rad, False)
        entiteter[aar] = {"value": verdi, "ambiguous_zero": tvetydig}
    serie = {
        "series_id": "test_serie",
        "source_id": "K1",
        "quality": "measured",
        "indicator": "burned_area_km2",
        "unit": "km2",
        "smoothed": False,
        "entities": {"NOR": entiteter},
        "names": {"NOR": "Norge"},
        "levels": {"NOR": "country"},
        "incomplete_years": [],
        "always_zero": [],
        "first_year": min(verdier),
        "last_complete_year": max(verdier),
    }
    serie.update(felt)
    return serie


class TheilSen(unittest.TestCase):
    def test_rett_linje_gir_stigningstallet_eksakt(self):
        # y = 3x + 5. Hvert eneste parvise stigningstall er 3, og medianen òg.
        punkter = [(x, 3 * x + 5) for x in range(1, 11)]
        self.assertAlmostEqual(derive.theil_sen(punkter), 3.0)

    def test_fallende_linje(self):
        punkter = [(x, 100 - 2.5 * x) for x in range(2000, 2015)]
        self.assertAlmostEqual(derive.theil_sen(punkter), -2.5)

    def test_uendret_serie_gir_null(self):
        punkter = [(x, 7) for x in range(1, 9)]
        self.assertEqual(derive.theil_sen(punkter), 0)

    def test_taaler_en_grov_uteligger(self):
        # x = 1..7, y = 1..6 og så 100. Av de 21 parvise stigningstallene er de
        # 15 som ikke berører siste punkt lik 1, mens de 6 som gjør det er
        # 16,5 / 19,6 / 24,25 / 32 / 47,5 / 94. Medianen er det 11. tallet i
        # sortert rekkefølge, altså 1. Minste kvadraters metode ville gitt over
        # 10 for de samme punktene.
        punkter = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 100)]
        self.assertEqual(derive.theil_sen(punkter), 1)

    def test_median_av_partall_er_snittet_av_de_to_midterste(self):
        # Tre punkter gir tre stigningstall: 2, 4 og 3. Fire punkter under.
        punkter = [(0, 0), (1, 2), (2, 8), (3, 9)]
        # Stigningstall: 2, 4, 3, 6, 3,5, 1 → sortert 1, 2, 3, 3,5, 4, 6.
        self.assertAlmostEqual(derive.theil_sen(punkter), (3 + 3.5) / 2)

    def test_for_faa_punkter(self):
        self.assertIsNone(derive.theil_sen([(2020, 5)]))


class MannKendall(unittest.TestCase):
    def test_strengt_stigende_serie(self):
        # n = 10 uten bindinger: S = n(n-1)/2 = 45, og
        # Var(S) = n(n-1)(2n+5)/18 = 10·9·25/18 = 125.
        punkter = [(x, x) for x in range(1, 11)]
        s, varians, z, p = derive.mann_kendall(punkter)
        self.assertEqual(s, 45)
        self.assertAlmostEqual(varians, 125.0)
        self.assertAlmostEqual(z, 44 / 125**0.5)
        self.assertAlmostEqual(p, 2 * NormalDist().cdf(-abs(z)))
        self.assertLess(p, 0.001)

    def test_strengt_fallende_serie_speiler_den_stigende(self):
        stigende = [(x, x) for x in range(1, 11)]
        fallende = [(x, -x) for x in range(1, 11)]
        s_opp, var_opp, z_opp, p_opp = derive.mann_kendall(stigende)
        s_ned, var_ned, z_ned, p_ned = derive.mann_kendall(fallende)
        self.assertEqual(s_ned, -s_opp)
        self.assertAlmostEqual(var_ned, var_opp)
        self.assertAlmostEqual(z_ned, -z_opp)
        self.assertAlmostEqual(p_ned, p_opp)

    def test_bindinger_trekkes_fra_variansen(self):
        # y = 1, 1, 2, 2, 3. Av de ti parene er åtte stigende og to like:
        # S = 8. Uten bindinger ville Var = 5·4·15/18 = 16,667. To grupper med
        # to like verdier trekker fra 2·(2·1·9)/18 = 2, altså Var = 14,667.
        punkter = list(enumerate([1, 1, 2, 2, 3]))
        s, varians, z, p = derive.mann_kendall(punkter)
        self.assertEqual(s, 8)
        self.assertAlmostEqual(varians, 5 * 4 * 15 / 18 - 2)
        self.assertAlmostEqual(z, 7 / varians**0.5)
        self.assertAlmostEqual(p, 2 * NormalDist().cdf(-abs(z)))

    def test_konstant_serie_har_ingen_retning(self):
        punkter = [(x, 4) for x in range(1, 9)]
        s, varians, z, p = derive.mann_kendall(punkter)
        self.assertEqual(s, 0)
        self.assertEqual(z, 0.0)
        self.assertEqual(p, 1.0)

    def test_kjent_datasett_regnet_for_haand(self):
        # y = 5, 3, 8, 6, 9, 7, 12. Parene som stiger minus de som faller:
        # fra 5: -,+,+,+,+,+ = 4;  fra 3: +,+,+,+,+ = 5;  fra 8: -,+,-,+ = 0;
        # fra 6: +,+,+ = 3;  fra 9: -,+ = 0;  fra 7: + = 1.  S = 13.
        # n = 7 uten bindinger: Var = 7·6·19/18 = 44,333.
        punkter = list(enumerate([5, 3, 8, 6, 9, 7, 12]))
        s, varians, z, p = derive.mann_kendall(punkter)
        self.assertEqual(s, 13)
        self.assertAlmostEqual(varians, 7 * 6 * 19 / 18)
        self.assertAlmostEqual(z, 12 / varians**0.5)
        self.assertAlmostEqual(p, 2 * NormalDist().cdf(-abs(z)))

    def test_uavhengig_av_naar_serien_starter_og_hvilken_enhet_den_har(self):
        grunn = [5, 3, 8, 6, 9, 7, 12]
        a = derive.mann_kendall(list(enumerate(grunn)))
        b = derive.mann_kendall([(1900 + x, y * 100) for x, y in enumerate(grunn)])
        self.assertEqual(a[0], b[0])
        self.assertAlmostEqual(a[3], b[3])

    def test_p_er_tosidig(self):
        # Z = 1,96 skal gi p nær 0,05 — den tosidige grensen alle kjenner.
        self.assertAlmostEqual(derive._tosidig_p(1.959964), 0.05, places=6)
        self.assertAlmostEqual(derive._tosidig_p(0.0), 1.0)


class Grunnlag(unittest.TestCase):
    def test_ufullstendig_aar_holdes_utenfor(self):
        observasjoner = [
            _observasjon(2024, 10.0),
            _observasjon(2025, 12.0),
            _observasjon(2026, 1.0, ["f_incomplete_year"]),
        ]
        serier = derive.grunnlag(observasjoner)
        serie = serier["test_serie"]
        self.assertEqual(sorted(serie["entities"]["NOR"]), [2024, 2025])
        self.assertEqual(serie["incomplete_years"], [2026])
        self.assertEqual(serie["last_complete_year"], 2025)

    def test_alltid_null_avgjoeres_av_fullstendige_aar(self):
        # Grenada-tilfellet fra § 7: en verdi i inneværende år gjør ikke
        # entiteten rangerbar, for det året inngår ikke i grunnlaget.
        observasjoner = [
            _observasjon(2024, 0.0),
            _observasjon(2025, 0.0),
            _observasjon(2026, 3.0, ["f_incomplete_year"]),
        ]
        serie = derive.grunnlag(observasjoner)["test_serie"]
        self.assertEqual(serie["always_zero"], ["NOR"])

    def test_perioder_finere_enn_aar_hoppes_over(self):
        observasjoner = [_observasjon(2025, 4.0), _observasjon("2025-W03", 1.0)]
        serie = derive.grunnlag(observasjoner)["test_serie"]
        self.assertEqual(sorted(serie["entities"]["NOR"]), [2025])

    def test_aar_foer_aar_null_leses_med_fortegn(self):
        self.assertEqual(derive._aarstall("-6050"), -6050)
        self.assertEqual(derive._aarstall("2024"), 2024)
        self.assertIsNone(derive._aarstall("2024-03"))


def _observasjon(periode, verdi, fotnoter=None):
    return {
        "entity": "NOR",
        "entity_name": "Norge",
        "level": "country",
        "period": str(periode),
        "indicator": "burned_area_km2",
        "value": verdi,
        "unit": "km2",
        "source_id": "K1",
        "series_id": "test_serie",
        "quality": "measured",
        "footnotes": fotnoter or [],
    }


class TrendReglene(unittest.TestCase):
    def test_serie_med_for_faa_aar_faar_ingen_trend(self):
        serie = _serie({2000 + i: i for i in range(TREND_MIN_YEARS - 1)})
        t = derive.trend(serie, "NOR")
        self.assertFalse(t["computed"])
        self.assertEqual(t["reason"], "too_few_years")

    def test_for_mange_tvetydige_nuller(self):
        # Halvparten av årene er nuller kilden ikke kan skille fra manglende
        # måling. Over TREND_MAX_ZERO_SHARE beregnes ingen trend.
        verdier = {}
        for i in range(12):
            verdier[2000 + i] = (0.0, True) if i % 2 else (float(i), False)
        serie = _serie(verdier)
        self.assertGreater(6 / 12, TREND_MAX_ZERO_SHARE)
        t = derive.trend(serie, "NOR")
        self.assertFalse(t["computed"])
        self.assertEqual(t["reason"], "zero_share")

    def test_hale_av_nuller_stopper_trenden(self):
        # Qatar-tilfellet fra § 7: deteksjoner som stopper, ikke branner som
        # avtar. Andelen nuller er innenfor, men de ligger alle til slutt.
        verdier = {2000 + i: (float(10 - i), False) for i in range(9)}
        for i in range(3):
            verdier[2009 + i] = (0.0, True)
        serie = _serie(verdier)
        self.assertLessEqual(3 / 12, TREND_MAX_ZERO_SHARE)
        self.assertGreater(3, TREND_MAX_ZERO_TAIL)
        t = derive.trend(serie, "NOR")
        self.assertFalse(t["computed"])
        self.assertEqual(t["reason"], "zero_tail")

    def test_nuller_uten_fotnote_stopper_ikke_trenden(self):
        # En målt null fra en kilde som skiller null fra manglende måling, er
        # en observasjon som alle andre.
        verdier = {2000 + i: (float(10 - i), False) for i in range(9)}
        for i in range(3):
            verdier[2009 + i] = (0.0, False)
        t = derive.trend(_serie(verdier), "NOR")
        self.assertTrue(t["computed"])
        self.assertEqual(t["direction"], "decreasing")

    def test_glattet_serie_faar_ingen_trend(self):
        serie = _serie({i: float(i) for i in range(40)}, smoothed=True)
        t = derive.trend(serie, "NOR")
        self.assertFalse(t["computed"])
        self.assertEqual(t["reason"], "smoothed")

    def test_stigende_serie_rapporteres_med_retning_og_stigning_per_tiaar(self):
        serie = _serie({2000 + i: 100.0 + 2 * i for i in range(15)})
        t = derive.trend(serie, "NOR")
        self.assertTrue(t["computed"])
        self.assertEqual(t["direction"], "increasing")
        self.assertAlmostEqual(t["slope_per_year"], 2.0)
        self.assertAlmostEqual(t["slope_per_decade"], 20.0)
        self.assertTrue(t["significant"])

    def test_serie_uten_signifikant_trend_rapporteres_som_ingen(self):
        verdier = [5, 3, 8, 4, 6, 3, 7, 4, 6, 5, 4, 6]
        t = derive.trend(_serie({2000 + i: float(v) for i, v in enumerate(verdier)}), "NOR")
        self.assertTrue(t["computed"])
        self.assertGreater(t["p_value"], t["alpha"])
        self.assertFalse(t["significant"])
        self.assertEqual(t["direction"], "none")


class Avledninger(unittest.TestCase):
    def setUp(self):
        self.serie = _serie({2020: 10.0, 2021: 30.0, 2022: 20.0, 2023: 40.0})

    def test_rangering_teller_synkende(self):
        r = derive.rangering(self.serie, "NOR", 2023)
        self.assertEqual((r["rank"], r["of"]), (1, 4))
        self.assertEqual(derive.rangering(self.serie, "NOR", 2020)["rank"], 4)
        self.assertEqual(derive.rangering(self.serie, "NOR", 2021)["rank"], 2)

    def test_like_verdier_deler_plass(self):
        serie = _serie({2020: 5.0, 2021: 5.0, 2022: 1.0})
        r = derive.rangering(serie, "NOR", 2020)
        self.assertEqual((r["rank"], r["tied"]), (1, 1))
        self.assertEqual(derive.rangering(serie, "NOR", 2022)["rank"], 3)

    def test_avvik_maales_mot_medianen(self):
        # Medianen av 10, 20, 30, 40 er 25. 40 ligger 60 prosent over.
        a = derive.avvik_fra_normal(self.serie, "NOR", 2023)
        self.assertEqual(a["median"], 25.0)
        self.assertAlmostEqual(a["deviation_pct"], 60.0)

    def test_avvik_beregnes_ikke_naar_medianen_er_null(self):
        serie = _serie({2020: 0.0, 2021: 0.0, 2022: 8.0})
        self.assertIsNone(derive.avvik_fra_normal(serie, "NOR", 2022))

    def test_dekning_viser_hull_i_serien(self):
        serie = _serie({2020: 1.0, 2021: 2.0, 2023: 3.0})
        d = derive.dekning(serie, "NOR")
        self.assertEqual((d["first_year"], d["last_year"]), (2020, 2023))
        self.assertEqual(d["n_years"], 3)
        self.assertEqual(d["missing_years"], [2022])

    def test_andel_av_verdenstallet(self):
        a = derive.andel(self.serie, "NOR", 2023, 200.0)
        self.assertAlmostEqual(a["share"], 0.2)
        self.assertAlmostEqual(a["share_pct"], 20.0)

    def _konsentrasjonsserie(self, antall_land):
        """En serie med N land der land nummer i har verdien N - i."""
        serie = _serie({2023: 1.0})
        serie["entities"] = {
            f"L{i:02d}": {2023: {"value": float(antall_land - i), "ambiguous_zero": False}}
            for i in range(antall_land)
        }
        serie["entities"]["WLD"] = {2023: {"value": 1000.0, "ambiguous_zero": False}}
        serie["names"] = {k: k for k in serie["entities"]}
        serie["levels"] = {k: "country" for k in serie["entities"]}
        serie["levels"]["WLD"] = "world"
        return serie

    def test_konsentrasjon_bruker_verdensraden_naar_den_finnes(self):
        # 20 land med verdiene 20 … 1. De ti største er 20 + … + 11 = 155,
        # summen av alle er 210, og verdensraden er 1000.
        serie = self._konsentrasjonsserie(20)
        k = derive.konsentrasjon(serie, 2023, 1000.0)
        self.assertEqual(k["denominator_kind"], "world_row")
        self.assertEqual(k["top_value"], 155.0)
        self.assertAlmostEqual(k["share_pct"], 15.5)

        uten_verden = derive.konsentrasjon(serie, 2023, None)
        self.assertEqual(uten_verden["denominator_kind"], "country_sum")
        self.assertAlmostEqual(uten_verden["share_pct"], 155 / 210 * 100, places=1)

    def test_konsentrasjon_beregnes_ikke_for_faa_entiteter(self):
        # Med ti land eller færre er «de ti største» alle sammen.
        self.assertIsNone(derive.konsentrasjon(self._konsentrasjonsserie(10), 2023, None))
        self.assertIsNotNone(derive.konsentrasjon(self._konsentrasjonsserie(11), 2023, None))

    def test_smaa_andeler_rundes_ikke_bort(self):
        # Norges andel av verdens brente areal er om lag 0,0003 prosent. Én
        # desimal ville gjort den til null.
        a = derive.andel(self.serie, "NOR", 2023, 12_000_000.0)
        self.assertGreater(a["share_pct"], 0)
        self.assertEqual(derive._prosent(0.0003333), 0.00033)
        self.assertEqual(derive._prosent(0.00126), 0.0013)
        self.assertEqual(derive._prosent(64.87), 64.9)
        self.assertEqual(derive._prosent(0), 0.0)

    def test_tvetydig_null_merkes_i_rangering_og_avvik(self):
        serie = _serie({2020: 10.0, 2021: 6.0, 2022: (0.0, True)})
        self.assertTrue(derive.rangering(serie, "NOR", 2022)["ambiguous_zero"])
        self.assertFalse(derive.rangering(serie, "NOR", 2020)["ambiguous_zero"])
        self.assertTrue(derive.avvik_fra_normal(serie, "NOR", 2022)["ambiguous_zero"])

    def test_arealsammenligning_velger_naermeste_land(self):
        arealer = {"ISL": 100000.0, "NOR": 320000.0, "SWE": 410000.0}
        navn = {"ISL": "Island", "NOR": "Norge", "SWE": "Sverige"}
        s = derive.arealsammenligning(330000.0, arealer, navn)
        self.assertEqual(s["comparison_entity"], "NOR")
        self.assertAlmostEqual(s["deviation_pct"], 3.1, places=1)

    def test_arealsammenligning_uten_gyldig_verdi(self):
        self.assertIsNone(derive.arealsammenligning(0, {"NOR": 1.0}, {}))
        self.assertIsNone(derive.arealsammenligning(None, {"NOR": 1.0}, {}))


class HeleDatasettet(unittest.TestCase):
    """Kontroller som må holde for avledningene slik de faktisk publiseres."""

    @classmethod
    def setUpClass(cls):
        from etl import validate

        cls.serier, cls.avledninger, cls.sammendrag = derive.avled(
            validate.les_publiserte()
        )

    def test_ingen_avledning_bruker_et_ufullstendig_aar(self):
        ufullstendige = {
            (s_id, aar)
            for s_id, s in self.serier.items()
            for aar in s["incomplete_years"]
        }
        self.assertTrue(ufullstendige, "datasettet har ingen ufullstendige år å teste")
        for nokkel, a in self.avledninger.items():
            if "period" in a and "series_id" in a:
                self.assertNotIn(
                    (a["series_id"], int(a["period"])), ufullstendige, nokkel
                )
            if a.get("kind") in {"coverage", "trend"} and a.get("last_year"):
                self.assertNotIn(
                    (a["series_id"], a["last_year"]), ufullstendige, nokkel
                )

    def test_entiteter_som_alltid_er_null_rangeres_ikke(self):
        alltid_null = {
            (s_id, kode) for s_id, s in self.serier.items() for kode in s["always_zero"]
        }
        self.assertTrue(alltid_null, "datasettet har ingen alltid-null-entiteter")
        for nokkel, a in self.avledninger.items():
            if a.get("kind") in {"rank", "anomaly"}:
                self.assertNotIn((a["series_id"], a["entity"]), alltid_null, nokkel)

    def test_trend_kjoeres_aldri_paa_tvers_av_kilde_eller_kvalitet(self):
        # En trend hører til én series_id, og en series_id har én kilde og én
        # quality — det er validate.py sin kontroll. Her kontrolleres at
        # avledningen ikke har funnet på å slå sammen noe.
        for nokkel, a in self.avledninger.items():
            if a.get("kind") == "trend":
                serie = self.serier[a["series_id"]]
                self.assertEqual(a["source_id"], serie["source_id"], nokkel)
                self.assertEqual(a["quality"], serie["quality"], nokkel)

    def test_z_score_serien_faar_verken_avvik_eller_andel(self):
        for nokkel, a in self.avledninger.items():
            if a.get("unit") == "zscore":
                self.assertIn(a["kind"], {"coverage", "trend"}, nokkel)

    def test_nokler_er_stabile_og_entydige(self):
        for nokkel, a in self.avledninger.items():
            self.assertTrue(nokkel.startswith(a["kind"].split("_")[0]), nokkel)
            self.assertNotIn(" ", nokkel)


if __name__ == "__main__":
    unittest.main()
