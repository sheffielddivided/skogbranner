"""K3 — EFFIS: årlige landtotaler for brent areal.

Dekker Europa, Midtøsten og Nord-Afrika. Tallene kommer fra EFFIS' egen
statistikkportal, som bygger adressene av samme basis som GWIS (K2), bare
under ``/statistics/v2/effis/``. Adressene er lest av portalens skriptfil.

**Hva tallene er.** De kommer fra EFFIS' Rapid Damage Assessment, som kartlegger
brente areal fra satellitt — MODIS fra 2003, Sentinel-2 fra 2018 og VIIRS fra
2016. De er altså EFFIS' egen kartlegging, ikke tall det enkelte land har
rapportert inn. De nasjonalt innrapporterte tallene ligger i European Fire
Database, som krever en egen dataforespørsel, og som derfor ikke er tatt inn
(CLAUDE.md § 10).

Kilden oppgir hektar. Konverteringen til km² skjer i ``normalize.py``.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k3_effis``
"""

import hashlib
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K3"
SERIES_ID = "effis_annual_country_totals"

# CLAUDE.md § 5 fastsetter reported for K3, og den er bindende. Verdien står
# her og ikke spredt utover, slik at den kan endres ett sted.
#
# MERK, til avklaring: § 5 beskriver K3 som «Nasjonalt rapporterte totaler».
# Endepunktet portalen bruker leverer Rapid Damage Assessment, altså EFFIS' egen
# satellittkartlegging. Geografien i § 5 stemmer eksakt med dette endepunktet, så
# det er kilden som er ment — men beskrivelsen og dermed quality passer ikke på
# tallene. Fotnoten f_reporting_basis er derfor ikke satt: den sier at tallene
# er nasjonalt rapporterte og følger andre definisjoner enn satellittmålte, og
# det ville vært en påstand om dataene som ikke stemmer.
KVALITET = "reported"

API = "https://api2.effis.emergency.copernicus.eu"

# EFFIS samler alle landene sine under ett oppslag. Lista hentes fra kilden
# framfor å skrives her, slik at et land som kommer til i EFFIS-nettverket,
# kommer med av seg selv.
LAND_URL = f"{API}/statistics/utils/countriesbyaoi?aoi=effis"

# Årsserien per land: [{"year": 2006, "ba": 9216, "nf": 49}, …]
AAR_URL = f"{API}/statistics/v2/effis/estimatesbycountry?country={{land}}"

LANDING_URL = "https://forest-fire.emergency.copernicus.eu/apps/effis.statistics/estimates"
LICENSE_URL = "https://forest-fire.emergency.copernicus.eu/about-effis/data-license"

RAW_JSON = RAW_DIR / "k3_effis_estimates.json"

# EFFIS bruker XKO for Kosovo. Vi bruker XKX — se CLAUDE.md § 6.
EFFIS_CODE_MAP = {
    "XKO": "XKX",
}

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


def _hent_json(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=120) as svar:
        return json.loads(svar.read().decode("utf-8"))


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def entity_kode(iso3):
    """Oversetter EFFIS' landkode til vår entity-kode."""
    return EFFIS_CODE_MAP.get(iso3, iso3)


def hent_landkoder():
    """Henter landkodene EFFIS fører.

    Samme land kan stå under flere områdekoder. Kodene samles derfor i et
    oppslag, ikke en liste.
    """
    koder = {}
    for oppforing in _hent_json(LAND_URL):
        iso3 = (oppforing.get("iso3") or "").strip()
        if iso3:
            koder[iso3] = oppforing.get("name", "")

    if not koder:
        raise ValueError(f"ingen landkoder fra {LAND_URL}")
    return koder


def hent():
    """Henter årsserien for hvert land EFFIS fører.

    Returnerer (rader, info). Radene bærer hektar slik de står i kilden.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    koder = hent_landkoder()

    rader = []
    uten_svar = []
    for iso3 in sorted(koder):
        try:
            serie = _hent_json(AAR_URL.format(land=iso3))
        except urllib.error.HTTPError as e:
            uten_svar.append(f"{iso3}: HTTP {e.code}")
            continue
        for punkt in serie:
            if punkt.get("ba") is None:
                continue
            rader.append(
                {
                    "iso3": iso3,
                    "name": koder[iso3],
                    "year": int(punkt["year"]),
                    "ba_ha": float(punkt["ba"]),
                    "fires": punkt.get("nf"),
                }
            )

    if not rader:
        raise ValueError("EFFIS ga ingen årsrader")

    rader.sort(key=lambda r: (r["iso3"], r["year"]))

    raa = json.dumps(rader, ensure_ascii=False, sort_keys=True).encode("utf-8")
    RAW_JSON.write_bytes(raa)

    aar = [r["year"] for r in rader]
    info = {
        "source_id": SOURCE_ID,
        "series_id": SERIES_ID,
        "downloaded_at": date.today().isoformat(),
        "checksum": _sha256(raa),
        "rows": len(rader),
        "countries": len(koder),
        "coverage_start": min(aar),
        "coverage_end": max(aar),
        "unanswered": uten_svar,
    }
    return rader, info


def skriv_metadata(info, processed_files):
    """Registrerer kilden i data/_sources.json.

    EFFIS har egen datalisens som må gjengis. Lenken til lisensteksten står i
    ``license_url`` og refereres i attribusjonsblokken — se CLAUDE.md § 5.
    """
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "EFFIS — European Forest Fire Information System, landtotaler",
        "publisher": "Joint Research Centre, Europakommisjonen, under Copernicus",
        "url": LANDING_URL,
        "download_url": AAR_URL.format(land="ITA"),
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0). "
        "Copyright (C) European Union, 1995–2025. Kommisjonens gjenbrukspolitikk "
        "følger kommisjonsbeslutningen av 12. desember 2011 om gjenbruk av "
        "kommisjonsdokumenter.",
        "license_url": LICENSE_URL,
        "attribution": "European Forest Fire Information System (EFFIS), "
        "Copernicus Emergency Management Service, Joint Research Centre.",
        "requires_agreement": False,
        "geography": "Europa, Midtøsten og Nord-Afrika",
        "coverage_start": str(info["coverage_start"]),
        "coverage_end": str(info["coverage_end"]),
        "temporal_resolution": "annual",
        "quality": KVALITET,
        "unit_source": "hectares",
        "downloaded_at": info["downloaded_at"],
        "checksum": info["checksum"],
        "series": [SERIES_ID],
        "processed_files": processed_files,
        "footnotes": ["f_sensor_break", "f_min_fire_size", "f_coverage_change"],
        "notes": "Tallene kommer fra EFFIS' Rapid Damage Assessment, som "
        "kartlegger brent areal fra satellitt: MODIS fra 2003, VIIRS fra 2016 "
        "og Sentinel-2 fra 2018. Fram til 2018 fanget kartleggingen i praksis "
        "branner fra rundt 30 hektar og oppover; med Sentinel-2 kommer også "
        "mindre branner med. Antallet land i EFFIS-nettverket har økt over tid, "
        "så hvor langt tilbake serien går, varierer mellom land.",
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
    rader, info = hent()
    print(
        f"K3: {info['rows']} årsrader for {info['countries']} land, "
        f"{info['coverage_start']}–{info['coverage_end']}"
    )
    if info["unanswered"]:
        print(f"K3: uten svar: {', '.join(info['unanswered'])}")
    return rader, info


if __name__ == "__main__":
    main()
