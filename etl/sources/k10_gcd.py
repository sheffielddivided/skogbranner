"""K10 — Global Charcoal Database: kompositt-kurven.

Kjører ``k10_gcd.R``, som bygger kompositten med paleofire og skriver den til
CSV med én gang, og leser CSV-en tilbake. Ingen tolkning, ingen omregning —
kompositten er en z-score og har ingen enhet å regne om (CLAUDE.md § 6).

Kilden er et *proxy*: sedimentært kull er et indirekte spor etter brann, ikke
en måling av brent areal. Serien får alltid ``f_proxy`` og kan aldri tegnes i
samme figur som en km²-serie.

Pakkene
-------
``GCD`` ligger på CRAN. ``paleofire`` ble **trukket fra CRAN 10. januar 2023**
og finnes bare i arkivet. Den siste versjonen, 1.2.4 fra 2019, importerer
``rgdal``, som selv ble trukket i oktober 2023.

``rgdal`` brukes kun av ``pfGridding`` og ``pfToKml``, som vi ikke bruker — det
er ``NAMESPACE`` som krever pakken ved lasting. Installasjonssteget i
workflowen fjerner derfor rgdal fra ``NAMESPACE`` og ``DESCRIPTION`` og de to
filene som bruker den, før pakken installeres. Funksjonene kompositten bygges
av røres ikke. At pakken er lappet, står i ``data/_sources.json``, slik at det
ikke er skjult hvordan tallene ble til.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k10_gcd``
"""

import csv
import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K10"
SERIES_ID = "gcd_charcoal_composite"

R_SKRIPT = Path(__file__).resolve().parent / "k10_gcd.R"
RAW_K10_DIR = RAW_DIR / "k10"
RAW_CSV = RAW_K10_DIR / "gcd_kompositt.csv"

LANDING_URL = "https://cran.r-project.org/package=GCD"
PALEOFIRE_ARKIV_URL = (
    "https://cran.r-project.org/src/contrib/Archive/paleofire/paleofire_1.2.4.tar.gz"
)

# Siteringen paleofire selv oppgir, gjengitt ordrett (CLAUDE.md § 5).
SITERING = (
    "Blarquez, O., Vannière, B., Marlon, J.R., Daniau, A.-L., Power, M.J., "
    "Brewer, S. & Bartlein, P.J. (2014). paleofire: an R package to analyse "
    "sedimentary charcoal records from the Global Charcoal Database to "
    "reconstruct past biomass burning. Computers & Geosciences 72: 255–261."
)

# Kompositten er datert i kalenderår før 1950 (BP), som er standarden i
# paleoklimatologi. Datamodellen fører kalenderår, så alderen regnes om her.
# Det er en datering, ikke en enhet, og hører derfor hjemme i kildemodulen.
BP_NULLPUNKT = 1950


class Kildefeil(Exception):
    """Reises når kompositten ikke lot seg bygge."""


def _sha256(sti):
    sum_ = hashlib.sha256()
    with open(sti, "rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            sum_.update(blokk)
    return sum_.hexdigest()


def hent():
    """Kjører R-skriptet og leser kompositten det skrev.

    Returnerer (rader, info). Radene står slik R-skriptet skrev dem, med alder
    i år før 1950.
    """
    RAW_K10_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CSV.unlink(missing_ok=True)

    resultat = subprocess.run(
        ["Rscript", "--vanilla", str(R_SKRIPT), str(RAW_CSV)],
        capture_output=True,
        text=True,
    )
    print(resultat.stdout, end="")
    if resultat.returncode != 0:
        raise Kildefeil(
            "R-skriptet feilet med kode "
            f"{resultat.returncode}. Siste utdata:\n{resultat.stderr[-2000:]}"
        )
    if not RAW_CSV.exists():
        raise Kildefeil(
            f"R-skriptet gikk gjennom, men skrev ingen {RAW_CSV.name}. "
            "Kompositten finnes ikke, og ingenting publiseres."
        )

    with open(RAW_CSV, encoding="utf-8") as f:
        rader = list(csv.DictReader(f))
    if not rader:
        raise Kildefeil(f"{RAW_CSV.name} er tom")

    manglende = {"age_bp", "composite", "n_sites"} - set(rader[0])
    if manglende:
        raise Kildefeil(
            f"{RAW_CSV.name} mangler kolonnene {sorted(manglende)}. "
            f"Den har {sorted(rader[0])}."
        )

    info = {
        "source_id": SOURCE_ID,
        "series_id": SERIES_ID,
        "downloaded_at": date.today().isoformat(),
        "checksum": _sha256(RAW_CSV),
        "rader": len(rader),
    }
    return rader, info


def kalenderaar(age_bp):
    """Gjør alder i år før 1950 om til kalenderår.

    Negative kalenderår er år før vår tidsregning, slik ISO 8601 skriver dem
    med fortegn (CLAUDE.md § 6).
    """
    return BP_NULLPUNKT - int(round(float(age_bp)))


def skriv_metadata(info, processed_files):
    """Registrerer kilden i data/_sources.json."""
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "Global Charcoal Database — global kompositt av sedimentært kull",
        "publisher": "Global Paleofire Working Group, via R-pakkene GCD og "
        "paleofire",
        "url": LANDING_URL,
        "download_url": PALEOFIRE_ARKIV_URL,
        "license": "GPL (>= 2) for pakkene. Dataene i GCD er fritt "
        "tilgjengelige med kildeangivelse.",
        "license_url": "https://cran.r-project.org/web/licenses/GPL-2",
        "attribution": SITERING,
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": str(info["aar_forste"]),
        "coverage_end": str(info["aar_siste"]),
        "temporal_resolution": "binned",
        "quality": "reconstructed",
        "unit_source": "zscore",
        "downloaded_at": info["downloaded_at"],
        "source_last_updated": None,
        "checksum": info["checksum"],
        "package_versions": info.get("pakkeversjoner", {}),
        "series": [SERIES_ID],
        "processed_files": processed_files,
        "footnotes": info["footnotes"],
        "notes": "Kompositt bygget med paleofire: minimaks, Box-Cox og z-score "
        "mot en felles basisperiode, deretter lavpassfiltrert snitt med "
        "bootstrappet usikkerhet. Utvalget er alle stedene i databasen, ikke et "
        "redaksjonelt utvalg. paleofire ble trukket fra CRAN i 2023 og "
        "installeres fra arkivet, uten rgdal, som pakken bare bruker i "
        "funksjoner vi ikke kaller. Alderen er regnet om fra år før 1950 til "
        "kalenderår.",
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
        "rows": info["rows"] if info and "rows" in info else forrige.get("rows"),
        "checksum": info["checksum"] if info else forrige.get("checksum"),
        "message": melding,
    }
    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    rader, info = hent()
    print(f"K10: {info['rader']} rader i kompositten")
    return rader, info


if __name__ == "__main__":
    main()
