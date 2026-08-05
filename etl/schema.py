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

UNIT = frozenset({"km2", "share", "zscore"})

# Hver indikator har nøyaktig én tillatt enhet.
INDICATOR_UNIT = {
    "burned_area_km2": "km2",
    "burned_area_share_land": "share",
    "charcoal_index": "zscore",
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

# Rutenettkilder fordeles til land med geometrien fra K6. En rute som bærer
# brent areal uten at noen landgeometri dekker den, kan ikke tilskrives et
# land. Overstiger den uattribuerte andelen denne terskelen, stopper
# kjøringen — se CLAUDE.md § 5.
GRID_MAX_UNATTRIBUTED_SHARE = 0.02

# Ytre grenser for et gyldig årstall. Nedre grense er satt under den eldste
# serien vi tar inn (K8 fra 1982, NBAC fra 1972). Øvre grense settes av
# nedlastingsåret og beregnes i validate.py.
YEAR_MIN = 1900


# --- Serier (CLAUDE.md § 6) ---

# series_id er stabile. En serie-id gjenbrukes aldri til en annen serie.
SERIES_ID = frozenset(
    {
        "owid_annual_area_burnt",
        "firecci_lt11_annual_burned_area",
    }
)


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

SOURCES_JSON = REPO_ROOT / "data" / "_sources.json"
STATUS_JSON = REPO_ROOT / "data" / "_status.json"
FOOTNOTES_JSON = REPO_ROOT / "data" / "_footnotes.json"
LAND_NO_JSON = GEO_DIR / "land_no.json"
