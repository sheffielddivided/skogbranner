"""K4 — EFFIS Rapid Damage Assessment: satellittkartlagt brent areal.

EFFIS kartlegger brente areal fra satellitt: MODIS fra 2003, VIIRS fra 2016 og
Sentinel-2 fra 2018. Det er disse tallene statistikkportalen viser, og de er
noe annet enn K3, som er tallene landene selv rapporterer inn. Se CLAUDE.md
§ 5.

Adressene er lest av portalens egen skriptfil på
``forest-fire.emergency.copernicus.eu``, som bygger dem av samme basis som
GWIS (K2), bare under ``/statistics/v2/effis/``.

To ting følger av hva produktet er, og skal ikke fjernes:

* Kartleggingen er en **hurtigvurdering** som revideres når bedre bilder
  foreligger, derfor ``f_product_level``.
* Fram til Sentinel-2 kom til i 2018 fanget den i praksis branner fra rundt
  30 hektar og oppover, derfor ``f_min_fire_size``.

Kilden oppgir hektar. Konverteringen til km² skjer i ``normalize.py``.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k4_effis``
"""

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K4"
SERIES_ID = "effis_rda_annual_burned_area"

# Satellittmålt, ikke rapportert. Se CLAUDE.md § 5 og § 6.
KVALITET = "measured"

API = "https://api2.effis.emergency.copernicus.eu"

# EFFIS samler alle landene sine under ett oppslag. Lista hentes fra kilden
# framfor å skrives her, slik at et land som kommer til i EFFIS-nettverket,
# kommer med av seg selv.
LAND_URL = f"{API}/statistics/utils/countriesbyaoi?aoi=effis"

# Årsserien per land: [{"year": 2006, "ba": 9216, "nf": 49}, …]
AAR_URL = f"{API}/statistics/v2/effis/estimatesbycountry?country={{land}}"

LANDING_URL = "https://forest-fire.emergency.copernicus.eu/apps/effis.statistics/estimates"
LICENSE_URL = "https://forest-fire.emergency.copernicus.eu/about-effis/data-license"
METODE_URL = (
    "https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/"
    "rapid-damage-assessment"
)

RAW_JSON = RAW_DIR / "k4_effis_rda.json"

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


def _hent_liste(url):
    """Henter en adresse som skal svare med en liste.

    Kilden svarer av og til null eller et objekt i stedet. Uten denne blir det
    en bar TypeError langt inne i en løkke, uten spor av hvilken adresse som
    sviktet. Her sier feilen hva som kom og hvorfra.
    """
    svar = _hent_json(url)
    if svar is None:
        return []
    if not isinstance(svar, list):
        raise ValueError(f"{url} svarte med {type(svar).__name__}, ikke en liste")
    return svar


def entity_kode(iso3):
    """Oversetter EFFIS' landkode til vår entity-kode."""
    return EFFIS_CODE_MAP.get(iso3, iso3)


def hent_landkoder():
    """Henter landkodene EFFIS fører.

    Samme land kan stå under flere områdekoder. Kodene samles derfor i et
    oppslag, ikke en liste.
    """
    koder = {}
    for oppforing in _hent_liste(LAND_URL):
        iso3 = (oppforing.get("iso3") or "").strip()
        if iso3:
            koder[iso3] = oppforing.get("name", "")

    if not koder:
        raise ValueError(f"ingen landkoder fra {LAND_URL}")
    return koder


def hent():
    """Henter årsserien for hvert land EFFIS kartlegger.

    Returnerer (rader, info). Radene bærer hektar slik de står i kilden.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    koder = hent_landkoder()

    rader = []
    uten_svar = []
    for iso3 in sorted(koder):
        try:
            serie = _hent_liste(AAR_URL.format(land=iso3))
        except urllib.error.HTTPError as e:
            uten_svar.append(f"{iso3}: HTTP {e.code}")
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            uten_svar.append(f"{iso3}: {type(e).__name__}")
            continue

        # Kilden svarer av og til null for et land i stedet for en tom liste.
        # Det er «ingen data», ikke en grunn til å stoppe hele hentingen.
        if not serie:
            uten_svar.append(f"{iso3}: tomt svar")
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
        raise ValueError("EFFIS RDA ga ingen årsrader")

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
    """Registrerer kilden i data/_sources.json."""
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "EFFIS — Rapid Damage Assessment, satellittkartlagt brent areal",
        "publisher": "Joint Research Centre, Europakommisjonen, under Copernicus",
        "url": LANDING_URL,
        "download_url": AAR_URL.format(land="ITA"),
        "method_url": METODE_URL,
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
        "footnotes": [
            "f_sensor_break",
            "f_min_fire_size",
            "f_coverage_change",
            "f_product_level",
        ],
        "notes": "EFFIS kartlegger brente areal fra satellitt: MODIS fra 2003, "
        "VIIRS fra 2016 og Sentinel-2 fra 2018. Fram til 2018 fanget "
        "kartleggingen i praksis branner fra rundt 30 hektar og oppover; med "
        "Sentinel-2 kommer også mindre branner med. Kartleggingen gjøres mens "
        "sesongen pågår og revideres når bedre bilder foreligger. Dette er en "
        "annen kilde enn K3, som er tallene landene selv rapporterer inn.",
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




# Brannstørrelsesfordelingen S4 skal vise, krever areal per brann og ikke bare
# landtotalen. Hvor de tallene ligger, er ikke dokumentert, og verten er ikke
# nåbar fra en utviklingssesjon. Sonderingen kjøres i Actions og skriver ut hva
# adressene faktisk svarer med, slik at en parser kan skrives mot noe kjent.
# Se .github/workflows/etl.yml.
KART_WFS = "https://maps.effis.emergency.copernicus.eu/gwis"


def sonder_branner():
    """Skriver ut hva EFFIS svarer med på areal per brann.

    Henter ingenting inn i datasettet og skriver ingen filer.

    Første runde ga 502 fra karttjenesten og 404 fra tre gjettede API-adresser.
    Denne runden slutter å gjette: den ber først om API-ets egen beskrivelse,
    og bruker WFS-parameternavnene som hører til hver versjon — 2.0.0 vil ha
    ``typeNames``, 1.1.0 vil ha ``typename``. Feil navn gir en tjenestefeil som
    ser ut som om laget ikke finnes.
    """

    def hent(navn, url, tegn=1500, tid=300):
        print(f"\n=== {navn}\n{url}")
        try:
            forespoersel = urllib.request.Request(
                url, headers={"User-Agent": BRUKERAGENT}
            )
            with urllib.request.urlopen(forespoersel, timeout=tid) as svar:
                kropp = svar.read().decode("utf-8", "replace")
            print(f"  status: {svar.status}, {len(kropp)} tegn")
            return kropp
        except Exception as e:  # noqa: BLE001 — sonderingen skal vise alt
            print(f"  FEIL: {type(e).__name__}: {e}")
            return None

    def vis(navn, url, tegn=1500, tid=300):
        kropp = hent(navn, url, tegn, tid)
        if kropp:
            print("  " + kropp[:tegn].replace("\n", "\n  "))

    # 1. Har API-et en beskrivelse av seg selv? Da slipper vi å gjette adresser.
    for sti in ("openapi.json", "docs", "statistics/openapi.json"):
        kropp = hent(f"API {sti}", f"{API}/{sti}", tid=60)
        if kropp and sti.endswith(".json"):
            try:
                spek = json.loads(kropp)
                for vei in sorted(spek.get("paths", {})):
                    print(f"    {vei}")
                continue
            except json.JSONDecodeError:
                pass
        if kropp:
            print("  " + kropp[:800].replace("\n", "\n  "))

    # 2. Lagnavnene i karttjenesten. Bare navnene, ikke hele dokumentet.
    kropp = hent(
        "WFS GetCapabilities",
        f"{KART_WFS}?service=WFS&version=1.1.0&request=GetCapabilities",
        tid=300,
    )
    if kropp:
        navn = re.findall(r"<(?:wfs:)?Name>([^<]+)</(?:wfs:)?Name>", kropp)
        print(f"  lag: {len(navn)}")
        for n in navn[:60]:
            print(f"    {n}")

    # 3. Noen få rader. Parameternavnet følger versjonen — se docstringen.
    for lag in ("ms:modis.ba.poly", "modis.ba.poly"):
        vis(
            f"WFS 1.1.0 {lag}",
            f"{KART_WFS}?service=WFS&version=1.1.0&request=GetFeature"
            f"&typename={lag}&maxFeatures=2&outputFormat=json",
            2000,
        )
        vis(
            f"WFS 2.0.0 {lag}",
            f"{KART_WFS}?service=WFS&version=2.0.0&request=GetFeature"
            f"&typeNames={lag}&count=2&outputFormat=json",
            2000,
        )

    return None


def main(argv=None):
    import sys

    if (argv or sys.argv[1:])[:1] == ["--brann-prove"]:
        return sonder_branner()
    rader, info = hent()
    print(
        f"K4: {info['rows']} årsrader for {info['countries']} land, "
        f"{info['coverage_start']}–{info['coverage_end']}"
    )
    if info["unanswered"]:
        print(f"K4: uten svar: {', '.join(info['unanswered'])}")
    return rader, info


if __name__ == "__main__":
    main()
