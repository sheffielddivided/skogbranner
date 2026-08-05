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
SOURCES_REQUIRING_CITATION = frozenset({"K7", "K9", "K10"})


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
    }
)


# --- Konverteringsfaktorer til km² (CLAUDE.md § 3, T1) ---

HA_TO_KM2 = 0.01
ACRE_TO_KM2 = 0.00404686


# --- Terskler (CLAUDE.md § 5) ---

# Relativt avvik mellom K1 og K2 for samme enhet og år som utløser en
# oppføring i avviksrapporten.
KRYSSJEKK_TERSKEL = 0.05
