"""K2 — GWIS (JRC/Copernicus): årlig brent areal og antall branner.

GWIS har to roller (CLAUDE.md § 5). Denne modulen henter grunnlaget for begge,
men bare den første er tatt i bruk ennå:

* **Kryssjekk mot K1.** K1 er OWIDs bearbeiding av GWIS, så de to skal i
  utgangspunktet si det samme. Spriker de, er det fordi GWIS har oppdatert
  tallene etter at OWID tok sin kopi. Avviksrapporten er et arbeidsverktøy for
  redaktøren og publiseres ikke.
* **Ukesoppløsning til S3.** Endepunktet er kartlagt og virker, men brukes ikke
  ennå. Se ``UKE_URL``.

Adressene er lest av portalens egen skriptfil, ikke gjettet. Basisen er
``prefixUrl`` i appens http-oppsett, og hver sti settes sammen der.

Kilden oppgir hektar. Det er bekreftet mot K1: GWIS oppgir 510 for Norge i
2012, og K1 har 5,10 km² for samme entitet og år. Konverteringen til km² skjer
i ``normalize.py``.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k2_gwis``
"""

import hashlib
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K2"
SERIES_ID = "gwis_annual_burned_area"
UKE_SERIES_ID = "gwis_weekly_burned_area"

API = "https://api2.effis.emergency.copernicus.eu"

# Sonene kilden deler verden inn i, og landene i hver sone. Landlista hentes
# fra kilden framfor å skrives her, slik at et land som kommer til, kommer med
# av seg selv.
SONE_URL = f"{API}/statistics/utils/aoi?scope=gwis"
LAND_URL = f"{API}/statistics/utils/countriesbyaoi?aoi={{sone}}"

# Årsserien per land: [{"year": 2012, "ba": 510, "nf": 3}, …]
AAR_URL = f"{API}/statistics/v2/gwis/estimatesbycountry?country={{land}}"

# Ukesoppløsningen til S3. Kartlagt og bekreftet, men ikke tatt i bruk ennå.
UKE_URL = f"{API}/statistics/v2/gwis/weekly?country={{land}}&year={{aar}}"

LANDING_URL = "https://gwis.jrc.ec.europa.eu/apps/gwis.statistics/estimates"

RAW_JSON = RAW_DIR / "k2_gwis_estimates.json"
RAW_UKE_JSON = RAW_DIR / "k2_gwis_weekly.json"

# GWIS koder enkelte entiteter med egne X-koder. Her oversettes de til
# entity-kodene i data/geo/land_no.json.
GWIS_CODE_MAP = {
    "XKO": "XKX",  # Kosovo — vi beholder X-formen, se CLAUDE.md § 6
    "XAD": "NONISO_AKD",  # Akrotiri og Dhekelia
    "XNC": "NONISO_CYN",  # Nord-Kypros
}

# Kilden fører også oppføringer som ikke er geografiske entiteter vi har eller
# skal ha. De utelates med vilje, og står her framfor å bli fanget av en
# generell «hopp over det vi ikke kjenner igjen» — et land som kommer til hos
# GWIS skal fortsatt stoppe kjøringen, ikke forsvinne stille.
IKKE_ENTITETER = {
    "XCA": "Det kaspiske hav er et vannområde, ikke en entitet i landtabellen",
}

# Sonelista inneholder både verdensdeler og en verdenskode. Verdenskoden er
# ikke et land og har ingen landliste å slå opp.
SONETYPER_MED_LAND = frozenset({"continent", "macregion", "region"})

# GWIS' verdensdeler, oversatt til regionkodene i data/geo/land_no.json (§ 6).
# Ukesserien publiseres på verdensdel og verden, ikke per land: landene ville
# gitt 180 000 rader uten at noen figur viser dem, og S3 spør om når på året
# det brenner hvor — ikke om det enkelte landet.
#
# Sonekoden hos GWIS er nøkkelen, vår regionkode er verdien. En sone vi ikke
# kjenner igjen, stopper kjøringen framfor å forsvinne stille.
GWIS_SONE_MAP = {
    "AFRICA": "AFR",
    "ASIA": "ASI",
    "EUROPE": "EUR",
    "NORTH_AMERICA": "NAC",
    "SOUTH_AMERICA": "SAM",
    "OCEANIA": "OCE",
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
    """Oversetter GWIS' landkode til vår entity-kode."""
    return GWIS_CODE_MAP.get(iso3, iso3)


def hent_landkoder():
    """Henter alle landkoder kilden fører, via sonene.

    Samme land kan ligge i flere soner. Kodene samles derfor i et sett.
    """
    soner = _hent_liste(SONE_URL)

    koder = {}
    for sone in soner:
        if sone.get("type") not in SONETYPER_MED_LAND:
            continue
        try:
            land = _hent_liste(LAND_URL.format(sone=sone["code"]))
        except urllib.error.HTTPError as e:
            # En sone uten landliste skal ikke stoppe de andre.
            if e.code == 404:
                continue
            raise
        for oppforing in land:
            iso3 = (oppforing.get("iso3") or "").strip()
            if iso3:
                koder[iso3] = oppforing.get("name", "")

    if not koder:
        raise ValueError(f"ingen landkoder fra {SONE_URL}")
    return koder


def hent():
    """Henter årsserien for hvert land kilden fører.

    Returnerer (rader, info). Radene bærer hektar slik de står i kilden —
    ingen omregning her.
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
        raise ValueError("GWIS ga ingen årsrader")

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


def sonder_uker(land="NOR", aar=None):
    """Skriver ut hva ukesendepunktet faktisk svarer med.

    Formatet er ikke dokumentert noe sted, og verten er ikke nåbar fra en
    utviklingssesjon. Uten denne måtte parseren skrives på gjetning. Kjøres i
    Actions, se .github/workflows/etl.yml.

    Sonderingen henter tre ting: sonelista med koder og typer, ukesserien for
    ett land, og den samme adressen med en sonekode i stedet for et land — det
    siste avgjør om verdensdelene kan hentes ferdig aggregert fra kilden, eller
    om de må summeres av landene.
    """
    aar = aar or date.today().year - 1

    soner = _hent_liste(SONE_URL)
    print(f"soner: {len(soner)}")
    for sone in soner:
        print(f"  {sone.get('code')!r} type={sone.get('type')!r} navn={sone.get('name')!r}")

    for nokkel, adresse in (
        (f"land {land}", UKE_URL.format(land=land, aar=aar)),
        ("sone AFRICA", UKE_URL.format(land="AFRICA", aar=aar)),
    ):
        print(f"\n--- {nokkel}: {adresse}")
        try:
            svar = _hent_json(adresse)
        except Exception as e:  # noqa: BLE001 — sonderingen skal vise alt
            print(f"  feilet: {type(e).__name__}: {e}")
            continue
        print(f"  type: {type(svar).__name__}")
        if isinstance(svar, list):
            print(f"  lengde: {len(svar)}")
            for rad in svar[:3]:
                print(f"  rad: {json.dumps(rad, ensure_ascii=False)}")
        else:
            print(f"  innhold: {json.dumps(svar, ensure_ascii=False)[:600]}")

    return None


def skriv_metadata(info):
    """Registrerer kilden i data/_sources.json.

    K2 tegnes ikke i noen figur i kryssjekkrollen, og står derfor ikke i
    kildekolonnen i § 8 for S1. Den føres likevel her, fordi kilden er hentet
    og fordi ukesoppløsningen skal brukes i S3.
    """
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "GWIS — Global Wildfire Information System, årlige estimater",
        "publisher": "Joint Research Centre, Europakommisjonen, under Copernicus",
        "url": LANDING_URL,
        "download_url": AAR_URL.format(land="NOR"),
        "license": "Copernicus-data. Fri bruk med kildeangivelse.",
        "license_url": "https://www.copernicus.eu/en/access-data/copyright-and-licences",
        "attribution": "Global Wildfire Information System (GWIS), Copernicus "
        "Emergency Management Service, Joint Research Centre.",
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": str(info["coverage_start"]),
        "coverage_end": str(info["coverage_end"]),
        "temporal_resolution": "annual",
        "quality": "measured",
        "unit_source": "hectares",
        "downloaded_at": info["downloaded_at"],
        "checksum": info["checksum"],
        "series": [SERIES_ID],
        "processed_files": [],
        "footnotes": ["f_sensor_break", "f_min_fire_size"],
        "notes": "Brukes til å kryssjekke K1, som er Our World in Datas "
        "bearbeiding av det samme grunnlaget. Avviksrapporten er et "
        "arbeidsverktøy og publiseres ikke. Ukesoppløsningen fra samme kilde "
        "skal brukes i seksjonen om sesongvariasjon.",
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


def main(argv=None):
    import sys

    if (argv or sys.argv[1:])[:1] == ["--uke-prove"]:
        return sonder_uker()
    return _main_aar()


def _main_aar():
    rader, info = hent()
    print(
        f"K2: {info['rows']} årsrader for {info['countries']} land, "
        f"{info['coverage_start']}–{info['coverage_end']}"
    )
    if info["unanswered"]:
        print(f"K2: uten svar: {', '.join(info['unanswered'])}")
    return rader, info


if __name__ == "__main__":
    main()
