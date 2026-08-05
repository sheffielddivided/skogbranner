"""K1 — Our World in Data: årlig brent areal.

Henter CSV og tilhørende metadata, legger dem uendret i ``data/raw/``, og
returnerer rådataene. Ingen tolkning, ingen omregning — se
``etl/sources/README.md``.

Kilden leverer hektar. Konverteringen til km² skjer i ``normalize.py``.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k1_owid``
"""

import csv
import hashlib
import io
import json
import urllib.request
from datetime import date, timezone, datetime

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K1"
SERIES_ID = "owid_annual_area_burnt"

SLUG = "annual-area-burnt-by-wildfires"
CSV_URL = f"https://ourworldindata.org/grapher/{SLUG}.csv"
METADATA_URL = f"https://ourworldindata.org/grapher/{SLUG}.metadata.json"
LANDING_URL = f"https://ourworldindata.org/grapher/{SLUG}"

RAW_CSV = RAW_DIR / "k1_owid_annual_area_burnt.csv"
RAW_METADATA = RAW_DIR / "k1_owid_annual_area_burnt.metadata.json"

# OWID koder aggregater og enkelte territorier med egne OWID_-koder. Her
# oversettes de til entity-kodene i data/geo/land_no.json. Merk NAC for
# Nord-Amerika: NAM er opptatt av Namibia.
OWID_CODE_MAP = {
    "OWID_WRL": "WLD",
    "OWID_EUR": "EUR",
    "OWID_EU27": "EU27",
    "OWID_AFR": "AFR",
    "OWID_ASI": "ASI",
    "OWID_NAM": "NAC",
    "OWID_SAM": "SAM",
    "OWID_OCE": "OCE",
    "OWID_KOS": "XKX",
    "OWID_CYN": "NONISO_CYN",
    "OWID_AKD": "NONISO_AKD",
}

# Entiteter OWID leverer helt uten kode, nøklet på entitetsnavn.
UNCODED_ENTITY_MAP = {
    "Europe (excl. Russia)": "EUR_XRU",
}

VALUE_COLUMN = "Annual area burnt by wildfires"


# OWID avviser forespørsler uten User-Agent med 403.
BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


def _hent(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=120) as svar:
        return svar.read()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def hent():
    """Laster ned CSV og metadata, skriver dem til data/raw/ og returnerer dem.

    Returnerer (rader, metadata, info) der rader er en liste av dict-er slik
    de står i kilden, med hektarverdiene urørt.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    csv_bytes = _hent(CSV_URL)
    metadata_bytes = _hent(METADATA_URL)

    RAW_CSV.write_bytes(csv_bytes)
    RAW_METADATA.write_bytes(metadata_bytes)

    metadata = json.loads(metadata_bytes.decode("utf-8"))
    rader = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))

    info = {
        "source_id": SOURCE_ID,
        "series_id": SERIES_ID,
        "downloaded_at": date.today().isoformat(),
        "checksum": _sha256(csv_bytes),
        "metadata_checksum": _sha256(metadata_bytes),
        "rows": len(rader),
    }
    return rader, metadata, info


def entity_kode(rad):
    """Oversetter OWIDs Code-felt til vår entity-kode."""
    kode = rad["Code"]
    if kode in OWID_CODE_MAP:
        return OWID_CODE_MAP[kode]
    if kode:
        return kode
    return UNCODED_ENTITY_MAP.get(rad["Entity"])


def skriv_metadata(metadata, info, processed_files):
    """Registrerer kilden i data/_sources.json."""
    kolonne = metadata["columns"][VALUE_COLUMN]
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "Our World in Data — Annual area burnt by wildfires",
        "publisher": "Our World in Data, med data fra Global Wildfire "
        "Information System (GWIS)",
        "url": LANDING_URL,
        "download_url": CSV_URL,
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": kolonne.get("citationLong", ""),
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": kolonne["timespan"].split("-")[0],
        "coverage_end": kolonne["timespan"].split("-")[1],
        "temporal_resolution": "annual",
        "quality": "measured",
        "unit_source": kolonne.get("unit", "hectares"),
        "downloaded_at": info["downloaded_at"],
        "source_last_updated": kolonne.get("lastUpdated"),
        "checksum": info["checksum"],
        "series": [SERIES_ID],
        "processed_files": processed_files,
        "footnotes": ["f_sensor_break", "f_min_fire_size"],
        "notes": kolonne.get("descriptionShort", ""),
    }
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        f.write("\n")


def skriv_status(status, melding, info=None):
    """Skriver kjørestatus til data/_status.json."""
    with open(STATUS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    naa = datetime.now(timezone.utc).isoformat(timespec="seconds")
    forrige = data["sources"].get(SOURCE_ID, {})
    data["last_run"] = naa
    data["sources"][SOURCE_ID] = {
        "status": status,
        "last_attempt": naa,
        "last_success": naa if status == "ok" else forrige.get("last_success"),
        "rows": info["rows"] if info else forrige.get("rows"),
        "checksum": info["checksum"] if info else forrige.get("checksum"),
        "message": melding,
    }
    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    rader, metadata, info = hent()
    print(f"K1: {info['rows']} rader, sha256 {info['checksum'][:16]}…")
    return rader, metadata, info


if __name__ == "__main__":
    main()
