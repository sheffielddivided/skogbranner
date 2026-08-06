"""Enumerasjonene i kode.

Dette er den maskinlesbare halvdelen av T5: hver enumerasjon finnes som prosa
i CLAUDE.md for mennesket, og som konstant her for maskinen. Ingen tredje kopi
— alle andre moduler importerer herfra og definerer aldri egne lister.

Endres en verdi her, endres prosaen i CLAUDE.md i samme commit.

Filen inneholder kun konstanter. Ingen logikk, ingen validering — den hører
hjemme i validate.py.

Se CLAUDE.md § 3 (T5), § 5 og § 6.
"""

# --- Kodeverdier i den kanoniske datamodellen (CLAUDE.md § 6) ---

QUALITY = frozenset({"measured", "reported", "beta", "reconstructed"})

LEVEL = frozenset({"country", "region", "world"})

UNIT = frozenset({"km2", "share", "zscore", "count"})

# Hver indikator har nøyaktig én tillatt enhet.
INDICATOR_UNIT = {
    "burned_area_km2": "km2",
    "burned_area_share_land": "share",
    "charcoal_index": "zscore",
    "fire_count": "count",
}

INDICATOR = frozenset(INDICATOR_UNIT)


# --- Kildekoder (CLAUDE.md § 5) ---

SOURCE = frozenset(
    {"K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10"}
)

# Kilder som ikke skal inn i den månedlige ETL-kjøringen.
STATIC_SOURCES = frozenset({"K8", "K9", "K10"})

# Kilder med sitering som må gjengis ordrett. Selve siteringsteksten står i
# data/_sources.json, som er der den hentes fra ved bygging.
SOURCES_REQUIRING_CITATION = frozenset({"K7", "K8", "K9", "K10"})


# --- Fotnotekoder (CLAUDE.md § 9) ---

FOOTNOTE = frozenset(
    {
        "f_sensor_break",
        "f_min_fire_size",
        "f_incomplete_year",
        "f_reporting_basis",
        "f_coverage_change",
        "f_beta_product",
        "f_missing_year",
        "f_proxy",
        "f_resolution_change",
        "f_zero_no_detection",
        "f_record_start",
        "f_incomplete_inventory",
        "f_product_level",
        "f_grid_resolution",
        "f_smoothed",
        "f_thinning_record",
    }
)


# --- Konverteringsfaktorer til km² (CLAUDE.md § 3, T1) ---

HA_TO_KM2 = 0.01
ACRE_TO_KM2 = 0.00404686
M2_TO_KM2 = 1e-6


# --- Terskler (CLAUDE.md § 5) ---

# Relativt avvik mellom K1 og K2 for samme enhet og år som utløser en
# oppføring i avviksrapporten.
CROSSCHECK_THRESHOLD = 0.05

# Nullverdier merket f_zero_no_detection er tvetydige og kan gi en trend som
# måler at deteksjonene stoppet. Terskler for når trend ikke beregnes — se
# CLAUDE.md § 7.
#
# Andel nuller i serien. Over denne andelen beregnes ingen trend.
TREND_MAX_ZERO_SHARE = 0.33
#
# Lengste tillatte sammenhengende rekke nuller sist i serien. Er halen lengre,
# beregnes ingen trend.
TREND_MAX_ZERO_TAIL = 2

# Færreste år en serie må ha før en trend beregnes. Mann–Kendall-testen bruker
# en normaltilnærming som ikke holder for korte serier — se CLAUDE.md § 7.
TREND_MIN_YEARS = 10

# Signifikansnivå for Mann–Kendall. Over denne p-verdien rapporteres trenden
# som «ingen statistisk signifikant trend» (CLAUDE.md § 7).
TREND_ALPHA = 0.05

# Antall entiteter konsentrasjonen regnes over: andelen av totalen som de N
# største står for (CLAUDE.md § 7).
CONCENTRATION_TOP_N = 10

# Rutenettkilder fordeles til land med geometrien fra K6. En rute som bærer
# brent areal uten at noen landgeometri dekker den, kan ikke tilskrives et
# land. Overstiger den uattribuerte andelen denne terskelen, stopper
# kjøringen — se CLAUDE.md § 5.
GRID_MAX_UNATTRIBUTED_SHARE = 0.02

# En entitet som dekker mindre enn dette antallet ruter av kildens eget
# rutenett, er liten i forhold til oppløsningen og får f_grid_resolution.
# Oppgitt i ruter, ikke km², fordi en rutes areal følger oppløsningen — se
# CLAUDE.md § 9.
GRID_MIN_ENTITY_CELLS = 1.0

# En kompositt av mange kilder tynnes ut mot slutten når kildene slutter til
# ulik tid. Visningen avgrenses der halen faller under denne andelen av det
# tetteste punktet — se CLAUDE.md § 9. Andel, ikke antall og ikke årstall, slik
# at grensen følger datasettet.
COMPOSITE_MIN_SERIES_SHARE = 0.5

# Ytre grenser for et gyldig årstall. Øvre grense settes av nedlastingsåret og
# beregnes i validate.py.
#
# Nedre grense må rekke ned til proxyen: K10 er sedimentært kull gjennom
# holocen, og en periode kan derfor være et år før vår tidsregning, skrevet med
# fortegn. Måleseriene starter alle etter 1900 — grensen her er ikke en påstand
# om at de gjør noe annet.
YEAR_MIN = -12000


# --- Serier (CLAUDE.md § 6) ---

# series_id er stabile. En serie-id gjenbrukes aldri til en annen serie.
#
# Én serie bærer én indikator. Avledede indikatorer får derfor egen serie-id,
# slik at dekningsperiode og trend regnes per indikator og ikke blandes.
#
# Verdien er filnavnet serien skrives til under data/processed/, uten
# etternavn. Filnavnene er en enumerasjon og bor bare her — ingen annen modul
# skriver et filnavn selv (CLAUDE.md § 4).
#
# Flere serier kan dele fil. De statiske kildene har hver sin, fordi hver av
# dem er én serie, mens de månedlige seriene med samme indikator ligger sammen.
# Arealfilen het burned_area før fire_count kom til, og beholder navnet — en
# omdøping ville brutt lenkene som allerede er publisert.
#
# None betyr at serien ikke publiseres. K2 hentes bare for kryssjekken mot K1,
# og observasjonene dens når aldri data/processed/ (§ 5).
PROCESSED_FILE = {
    "owid_annual_area_burnt": "burned_area",  # K1
    # avledet av K1, nevner fra K6
    "owid_annual_area_burnt_share_land": "burned_area_share_land",
    "gwis_annual_burned_area": None,  # K2, kun kryssjekk
    "effis_annual_country_totals": "burned_area",  # K3, rapportert areal
    "effis_annual_country_fire_count": "fire_count",  # K3, rapportert antall
    "effis_rda_annual_burned_area": "burned_area",  # K4, satellittkartlegging
    "nifc_annual_burned_area": "burned_area",  # K5
    "nifc_annual_fire_count": "fire_count",  # K5
    "nbac_annual_burned_area": "burned_area",  # K7
    "cnfdb_annual_fire_count": "fire_count",  # K7
    "firecci_lt11_annual_burned_area": "burned_area_firecci_lt11",  # K8
    "gfed5_annual_burned_area": "burned_area_gfed5",  # K9
    "gcd_charcoal_composite": "charcoal_composite_gcd",  # K10
}

SERIES_ID = frozenset(PROCESSED_FILE)


# --- Stier ---
#
# Ligger her for at ingen annen modul skal skrive stiene på nytt. Alle er
# absolutte og utledet fra repotoppen, slik at pipelinen gir samme resultat
# uansett arbeidskatalog.

from pathlib import Path as _Path

REPO_ROOT = _Path(__file__).resolve().parent.parent

RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
GEO_DIR = REPO_ROOT / "data" / "geo"

LAND_AREA_JSON = GEO_DIR / "land_area_km2.json"

INSIGHTS_JSON = PROCESSED_DIR / "insights.json"

SOURCES_JSON = REPO_ROOT / "data" / "_sources.json"
STATUS_JSON = REPO_ROOT / "data" / "_status.json"
FOOTNOTES_JSON = REPO_ROOT / "data" / "_footnotes.json"
LAND_NO_JSON = GEO_DIR / "land_no.json"
