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
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from etl.schema import (
    GWIS_REQUEST_PAUSE_S,
    HA_TO_KM2,
    PROCESSED_DIR,
    PROCESSED_FILE,
    RAW_DIR,
    SOURCES_JSON,
    STATUS_JSON,
)

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

# GWIS' soner, oversatt til regionkodene i data/geo/land_no.json (§ 6).
# Kodene er lest av sonelista, ikke gjettet — se sonder_uker().
#
# Verdensdelene hos GWIS følger FNs inndeling, der Amerika er én verdensdel
# (UN_AME). Vi fører Nord- og Sør-Amerika hver for seg, og bruker derfor
# kildens makroregioner N_AME og S_AME for de to.
#
# Ukesserien publiseres på verdensdel og verden, ikke per land: landene ville
# gitt over 180 000 rader uten at noen figur viser dem, og S3 spør om når på
# året det brenner hvor — ikke om det enkelte landet.
GWIS_SONE_MAP = {
    "UN_AFR": "AFR",
    "UN_ASI": "ASI",
    "UN_EUR": "EUR",
    "UN_OCE": "OCE",
    "N_AME": "NAC",
    "S_AME": "SAM",
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

    Sonderingen svarer på tre spørsmål: hvilke soner kilden har, om
    year-parameteret faktisk velger år, og om sonekodene kan brukes der
    landkoden står — det siste avgjør om verdensdelene kan hentes ferdig
    aggregert eller må summeres av landene.
    """
    soner = _hent_liste(SONE_URL)
    print(f"soner: {len(soner)}")
    for sone in soner:
        print(f"  {sone.get('code')!r} type={sone.get('type')!r} navn={sone.get('name')!r}")

    def vis(nokkel, adresse):
        print(f"\n--- {nokkel}: {adresse}")
        try:
            svar = _hent_json(adresse)
        except Exception as e:  # noqa: BLE001 — sonderingen skal vise alt
            print(f"  feilet: {type(e).__name__}: {e}")
            return
        if not isinstance(svar, dict):
            print(f"  type: {type(svar).__name__} — uventet")
            return
        for felt, rader in svar.items():
            if not isinstance(rader, list):
                print(f"  {felt}: {rader!r}")
                continue
            print(f"  {felt}: {len(rader)} rader")
            if rader:
                print(f"    første: {json.dumps(rader[0], ensure_ascii=False)}")
                print(f"    siste:  {json.dumps(rader[-1], ensure_ascii=False)}")

    # Samme land, tre år. Svarer year-parameteret med ulike datoer, velger den
    # faktisk år; er datoene like, gjør den det ikke.
    for aarstall in (2019, 2023, 2026):
        vis(f"land {land}, år {aarstall}", UKE_URL.format(land=land, aar=aarstall))

    # Sonekodene fra lista over, ikke gjettede navn.
    for sone in ("UN_AFR", "WORLD"):
        vis(f"sone {sone}", UKE_URL.format(land=sone, aar=2023))

    return None


def soner_med_land():
    """Sonene vi fører som regioner, med landene kilden legger i hver.

    Inndelingen er kildens. Summeringen er vår — GWIS svarer ikke på sone i
    ukesendepunktet, se sonder_uker().
    """
    ut = {}
    for sone in _hent_liste(SONE_URL):
        kode = sone.get("code")
        if kode not in GWIS_SONE_MAP:
            continue
        land = _hent_liste(LAND_URL.format(sone=kode))
        # Kildens koder oversettes til våre med én gang, slik at
        # sammenligningen mot de hentede landene skjer i ett kodesett (§ 6).
        iso3 = sorted(
            {entity_kode((o.get("iso3") or "").strip()) for o in land} - {""}
        )
        if iso3:
            ut[GWIS_SONE_MAP[kode]] = iso3

    mangler = sorted(set(GWIS_SONE_MAP.values()) - set(ut))
    if mangler:
        raise ValueError(f"GWIS ga ingen landliste for sonene {mangler}")
    return ut


def _bufrede_aar():
    """Årene ukesserien allerede er publisert for, og radene deres.

    Et fullstendig år hentes ikke på nytt: verdiene ligger fast, og en månedlig
    kjøring skal ikke be kilden om fjorten år med uker den allerede har svart
    på. Den publiserte filen er hurtigbufferen — se CLAUDE.md § 5.

    Inneværende år er aldri bufret. Det er nettopp det året som endrer seg.
    """
    sti = PROCESSED_DIR / f"{PROCESSED_FILE[UKE_SERIES_ID]}.json"
    if not sti.exists():
        return {}

    with open(sti, encoding="utf-8") as f:
        publisert = json.load(f)

    inneverende = date.today().year
    per_aar = {}
    for o in publisert:
        if o.get("series_id") != UKE_SERIES_ID:
            continue
        aar = int(o["period"][:4])
        if aar >= inneverende:
            continue
        per_aar.setdefault(aar, []).append(o)
    return per_aar


def hent_uker(aar_fra, aar_til, land_koder=None, bufret=None):
    """Henter ukesserien per land, og summerer den til soner og verden.

    Returnerer (rader, info). Radene er (entity, år, uke, hektar), der entity
    er en regionkode eller WLD — landene selv publiseres ikke (§ 5).

    Hentingen er skånsom: én forespørsel per land og år, med pause mellom, og
    fullstendige år som allerede er publisert, hentes ikke på nytt.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    soner = soner_med_land()
    # Verdenstallet summeres av alle landene kilden fører, ikke bare av dem som
    # ligger i en av de seks sonene. Et land utenfor sonene skal telle globalt.
    koder = land_koder if land_koder is not None else sorted(hent_landkoder())
    bufret = _bufrede_aar() if bufret is None else bufret

    aarene = [a for a in range(aar_fra, aar_til + 1) if a not in bufret]
    per_land = {}
    uten_svar = []
    forespørsler = 0

    for aar in aarene:
        for iso3 in koder:
            if forespørsler:
                time.sleep(GWIS_REQUEST_PAUSE_S)
            forespørsler += 1
            try:
                svar = _hent_json(UKE_URL.format(land=iso3, aar=aar))
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                uten_svar.append(f"{iso3} {aar}: {type(e).__name__}")
                continue

            for rad in (svar or {}).get("banfweekly") or []:
                # None betyr at uken ikke er nådd ennå. Det er ingen måling, og
                # skal ikke bli en null (§ 6).
                if rad.get("area_ha") is None:
                    continue
                per_land[(entity_kode(iso3), aar, int(rad["week"]))] = float(
                    rad["area_ha"]
                )

    rader = _summer_til_soner(per_land, soner)
    for aar, gamle in sorted(bufret.items()):
        rader.extend(
            {
                "entity": o["entity"],
                "year": aar,
                "week": int(o["period"][6:]),
                "ba_ha": o["value"] / HA_TO_KM2,
                "bufret": True,
            }
            for o in gamle
        )

    rader.sort(key=lambda r: (r["entity"], r["year"], r["week"]))

    info = {
        "source_id": SOURCE_ID,
        "series_id": UKE_SERIES_ID,
        "downloaded_at": date.today().isoformat(),
        "rows": len(rader),
        "requests": forespørsler,
        "years_fetched": aarene,
        "years_cached": sorted(bufret),
        "countries": len(koder),
        "zones": {kode: len(land) for kode, land in sorted(soner.items())},
        "unanswered": uten_svar,
    }
    return rader, info


def _summer_til_soner(per_land, soner):
    """Summerer landenes uker til regionene og til verden.

    Verdenstallet summeres av landene, ikke av regionene: et land kan ligge i
    flere soner eller i ingen, og en sum av soner ville da telt det to ganger
    eller ikke i det hele tatt.
    """
    per_entitet = {}
    for (iso3, aar, uke), hektar in per_land.items():
        for region, land in soner.items():
            if iso3 in land:
                nokkel = (region, aar, uke)
                per_entitet[nokkel] = per_entitet.get(nokkel, 0.0) + hektar
        verden = ("WLD", aar, uke)
        per_entitet[verden] = per_entitet.get(verden, 0.0) + hektar

    return [
        {"entity": entitet, "year": aar, "week": uke, "ba_ha": hektar}
        for (entitet, aar, uke), hektar in per_entitet.items()
    ]


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


def skriv_uke_metadata(info):
    """Oppdaterer K2s oppføring med ukesserien.

    Kilden er den samme; det er oppløsningen som er ny. Oppføringen får derfor
    begge seriene og en temporal_resolution som sier at begge finnes, framfor
    en ny kildekode — en K-kode er én kilde, ikke ett endepunkt (§ 5).
    """
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    oppforing = sources["sources"].setdefault(SOURCE_ID, {})
    oppforing.update(
        {
            "name": "GWIS — Global Wildfire Information System",
            "temporal_resolution": "annual og weekly",
            "series": sorted({*oppforing.get("series", []), SERIES_ID, UKE_SERIES_ID}),
            "weekly": {
                "downloaded_at": info["downloaded_at"],
                "requests": info["requests"],
                "years_fetched": info["years_fetched"],
                "years_cached": info["years_cached"],
                "countries": info["countries"],
                "zones": info["zones"],
                "unanswered": len(info["unanswered"]),
            },
            "notes": "Brukes til å kryssjekke K1, som er Our World in Datas "
            "bearbeiding av det samme grunnlaget. Avviksrapporten er et "
            "arbeidsverktøy og publiseres ikke. Ukesserien er hentet per land "
            "og summert til verdensdel og verden — kilden svarer ikke på sone "
            "i ukesendepunktet. Fullstendige år hentes ikke på nytt.",
        }
    )

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
