"""K8 — FireCCILT11 (ESA Fire_cci), rutenettproduktet, hentet fra CEDA.

Henter de månedlige netCDF-filene fra CEDA-arkivet, legger dem uendret i
``data/raw/`` og leverer rutenettene videre slik de står i kilden. Ingen
tolkning, ingen omregning — kilden oppgir m², og konverteringen til km² skjer i
``normalize.py`` (CLAUDE.md § 3, T1).

Filene ligger åpent uten autentisering. Katalogen enumereres som JSON ved å
legge ``?json`` på stien hos data.ceda.ac.uk, og listen derfra gir både
nedlastingslenke, filstørrelse og md5-sum. Det er den listen som styrer hva som
lastes ned — arkivet speiles ikke rekursivt.

CEDA svarer med en HTML-side i stedet for filinnhold når tilgangen avvises
eller stien er feil. En nedlasting som «lykkes» kan derfor inneholde en
feilside. Hver fil kontrolleres derfor mot katalogens størrelse og md5-sum, og
mot at de første bytene faktisk er en netCDF-signatur, før den brukes.

Serien er avsluttet (1982–2018, uten 1994) og hentes kun av den manuelt
utløste workflowen for statiske kilder, aldri av den månedlige (CLAUDE.md § 5).

Kjøres som modul fra repotoppen: ``python -m etl.sources.k8_firecci``
"""

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K8"
SERIES_ID = "firecci_lt11_annual_burned_area"

KATALOG_BASE = (
    "https://data.ceda.ac.uk/neodc/esacci/fire/data/burned_area/"
    "AVHRR-LTDR/grid/v1.1"
)
ARKIV_BASE = (
    "https://dap.ceda.ac.uk/neodc/esacci/fire/data/burned_area/"
    "AVHRR-LTDR/grid/v1.1"
)
LANDING_URL = "https://catalogue.ceda.ac.uk/uuid/62866635ab074e07b93f17fbf87a2c1a"
DOI = "10.5285/62866635ab074e07b93f17fbf87a2c1a"
LISENS_URL = (
    "https://artefacts.ceda.ac.uk/licences/specific_licences/"
    "esacci_fire_terms_and_conditions.pdf"
)

# Siteringen kilden selv oppgir, gjengitt ordrett (CLAUDE.md § 5).
SITERING = (
    "Chuvieco, E.; Pettinari, M.L.; Otón, G. (2020): ESA Fire Climate Change "
    "Initiative (Fire_cci): AVHRR-LTDR Fire_cci Burned Area Grid product, "
    "version 1.1. Centre for Environmental Data Analysis, 28 December 2020. "
    "doi:10.5285/62866635ab074e07b93f17fbf87a2c1a."
)

RAW_K8_DIR = RAW_DIR / "k8"

# Kun årsmapper og månedsfiler. Katalogen inneholder også README-filer, en
# docs-mappe og en Compressed-mappe med zip-arkiver av de samme dataene.
AARSMAPPE = re.compile(r"^\d{4}$")
MAANEDSFIL = re.compile(r"^(\d{4})(\d{2})\d{2}-ESACCI-L4_FIRE-BA-AVHRR-LTDR-fv1\.1\.nc$")

# Variabelen med brent areal, og enheten kilden oppgir for den.
VARIABEL = "burned_area"
ENHET_KILDE = "m2"

# netCDF-4 er HDF5 under panseret. Klassisk netCDF starter med «CDF». En
# HTML-feilside gjør ingen av delene.
SIGNATURER = (b"\x89HDF\r\n\x1a\n", b"CDF\x01", b"CDF\x02")

FORSOK = 4
BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


class Nedlastingsfeil(Exception):
    """Reises når en nedlasting ikke ga netCDF-innhold."""


def _les_json(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=180) as svar:
        innhold_type = svar.headers.get("Content-Type", "")
        raa = svar.read()
    if "html" in innhold_type.lower():
        raise Nedlastingsfeil(
            f"{url} svarte med HTML ({innhold_type!r}) i stedet for katalog-JSON. "
            "CEDA gjør det når stien er feil eller tilgangen avvises."
        )
    try:
        return json.loads(raa.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise Nedlastingsfeil(f"{url} ga ikke gyldig JSON: {e}") from None


def katalog():
    """Enumererer arkivet og returnerer månedsfilene, sortert på periode.

    Hver oppføring har ``aar``, ``maaned``, ``navn``, ``url``, ``bytes`` og
    ``md5``, slik katalogen oppgir dem.
    """
    rot = _les_json(KATALOG_BASE + "/?json")["items"]
    aarsmapper = sorted(
        e["name"] for e in rot if e.get("type") == "dir" and AARSMAPPE.match(e["name"])
    )
    if not aarsmapper:
        raise Nedlastingsfeil(f"Fant ingen årsmapper under {KATALOG_BASE}")

    oppforinger = []
    for aar in aarsmapper:
        for e in _les_json(f"{KATALOG_BASE}/{aar}/?json")["items"]:
            if e.get("type") != "file":
                continue
            treff = MAANEDSFIL.match(e["name"])
            if not treff:
                continue
            if treff.group(1) != aar:
                raise Nedlastingsfeil(
                    f"Filen {e['name']} ligger i årsmappen {aar}, men gjelder "
                    f"{treff.group(1)}"
                )
            oppforinger.append(
                {
                    "aar": int(treff.group(1)),
                    "maaned": int(treff.group(2)),
                    "navn": e["name"],
                    "url": e.get("download") or (ARKIV_BASE + f"/{aar}/{e['name']}"),
                    "bytes": e["size"],
                    "md5": e.get("md5"),
                }
            )

    oppforinger.sort(key=lambda o: (o["aar"], o["maaned"]))
    return oppforinger


def _md5(sti):
    sum_ = hashlib.md5()
    with open(sti, "rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            sum_.update(blokk)
    return sum_.hexdigest()


def _verifiser(sti, oppf):
    """Kontrollerer at filen er netCDF og hel, ikke en feilside eller et brudd."""
    faktisk = sti.stat().st_size
    if faktisk != oppf["bytes"]:
        raise Nedlastingsfeil(
            f"{oppf['navn']}: fikk {faktisk} byte, katalogen oppgir "
            f"{oppf['bytes']}. Nedlastingen er ufullstendig eller svaret er "
            "ikke filen vi ba om."
        )

    with open(sti, "rb") as f:
        start = f.read(8)
    if not any(start.startswith(s) for s in SIGNATURER):
        raise Nedlastingsfeil(
            f"{oppf['navn']}: innholdet er ikke netCDF (starter med {start!r}). "
            "CEDA svarer med en HTML-side når tilgangen avvises."
        )

    if oppf["md5"]:
        faktisk_md5 = _md5(sti)
        if faktisk_md5 != oppf["md5"]:
            raise Nedlastingsfeil(
                f"{oppf['navn']}: md5 {faktisk_md5} stemmer ikke med "
                f"katalogens {oppf['md5']}"
            )


def hent_fil(oppf):
    """Laster ned én månedsfil til data/raw/k8/ og verifiserer den.

    Returnerer stien. Kalleren sletter filen etter aggregering — rådata
    committes aldri (CLAUDE.md T4).
    """
    RAW_K8_DIR.mkdir(parents=True, exist_ok=True)
    sti = RAW_K8_DIR / oppf["navn"]

    siste = None
    for forsok in range(FORSOK):
        try:
            forespoersel = urllib.request.Request(
                oppf["url"], headers={"User-Agent": BRUKERAGENT}
            )
            with urllib.request.urlopen(forespoersel, timeout=600) as svar:
                innhold_type = svar.headers.get("Content-Type", "")
                if "html" in innhold_type.lower():
                    raise Nedlastingsfeil(
                        f"{oppf['navn']}: CEDA svarte med {innhold_type!r} i "
                        "stedet for filinnhold. Tilgangen ble avvist."
                    )
                with open(sti, "wb") as f:
                    while blokk := svar.read(1 << 20):
                        f.write(blokk)
            _verifiser(sti, oppf)
            return sti
        except (urllib.error.URLError, TimeoutError, Nedlastingsfeil, OSError) as e:
            siste = e
            sti.unlink(missing_ok=True)
            if forsok < FORSOK - 1:
                time.sleep(2 ** (forsok + 1))

    raise Nedlastingsfeil(
        f"Ga opp {oppf['navn']} etter {FORSOK} forsøk: {type(siste).__name__}: {siste}"
    )


def les_rutenett(sti):
    """Leser brent areal fra én månedsfil.

    Returnerer (lat, lon, verdier) der verdiene står i kildens egen enhet, m².
    """
    import netCDF4  # Installeres av workflowen, ikke av den månedlige kjøringen.
    import numpy as np

    with netCDF4.Dataset(sti) as nc:
        if VARIABEL not in nc.variables:
            raise Nedlastingsfeil(
                f"{sti.name}: fant ingen variabel {VARIABEL!r}. Filen har "
                f"{sorted(nc.variables)}."
            )
        variabel = nc.variables[VARIABEL]
        enhet = getattr(variabel, "units", None)
        if enhet != ENHET_KILDE:
            raise Nedlastingsfeil(
                f"{sti.name}: {VARIABEL} oppgir enheten {enhet!r}, ikke "
                f"{ENHET_KILDE!r}. Omregningen i normalize.py forutsetter "
                f"{ENHET_KILDE}."
            )
        lat = np.asarray(nc.variables["lat"][:], dtype="float64")
        lon = np.asarray(nc.variables["lon"][:], dtype="float64")
        verdier = np.ma.filled(variabel[:], 0.0).astype("float64")

    # Tidsdimensjonen har lengde 1 i månedsfilene. Er den lengre, er filen noe
    # annet enn en månedsfil, og en sum over den ville blandet perioder.
    if verdier.ndim == 3:
        if verdier.shape[0] != 1:
            raise Nedlastingsfeil(
                f"{sti.name}: filen har {verdier.shape[0]} tidssteg, ventet ett. "
                "Én månedsfil per periode er forutsetningen for årssummene."
            )
        verdier = verdier[0]
    if verdier.shape != (lat.size, lon.size):
        raise Nedlastingsfeil(
            f"{sti.name}: {VARIABEL} har formen {verdier.shape}, ventet "
            f"{(lat.size, lon.size)}"
        )
    verdier = np.nan_to_num(verdier, nan=0.0, posinf=0.0, neginf=0.0)
    verdier[verdier < 0] = 0.0
    return lat, lon, verdier


def skriv_metadata(info, processed_files):
    """Registrerer kilden i data/_sources.json."""
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "ESA Fire_cci — AVHRR-LTDR Burned Area Grid product v1.1 "
        "(FireCCILT11)",
        "publisher": "University of Alcalá for ESA Fire_cci, distribuert av "
        "Centre for Environmental Data Analysis (CEDA)",
        "url": LANDING_URL,
        "download_url": KATALOG_BASE,
        "license": "ESA CCI Data Policy: free and open access. Bruken er "
        "dekket av Fire_cci terms and conditions.",
        "license_url": LISENS_URL,
        "attribution": SITERING,
        "doi": DOI,
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": str(info["aar_forste"]),
        "coverage_end": str(info["aar_siste"]),
        "missing_years": [str(a) for a in info["aar_mangler"]],
        "temporal_resolution": "monthly",
        "quality": "beta",
        "unit_source": ENHET_KILDE,
        "spatial_resolution": "0.25 degrees",
        "downloaded_at": info["downloaded_at"],
        "source_last_updated": info.get("source_last_updated"),
        "checksum": info["checksum"],
        "series": [SERIES_ID],
        "processed_files": processed_files,
        "footnotes": info["footnotes"],
        "notes": "Månedlige rutenett på 0,25° summert til årlige landtotaler "
        "med admin-0-geometrien fra K6. Rutenettfilene lastes ned i GitHub "
        "Actions og slettes etter aggregering. Andelen brent areal uten "
        f"landtilknytning i denne kjøringen: {info['uattribuert_andel']:.4%}. "
        f"{len(info['utelatte_entiteter'])} entiteter er utelatt fordi "
        "rutenettet ikke treffer geometrien deres.",
        "excluded_entities": info["utelatte_entiteter"],
    }
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        f.write("\n")


def skriv_status(status, melding, info=None):
    """Skriver kjørestatus til data/_status.json.

    Den uattribuerte andelen føres som eget felt, ikke bare som tekst i
    meldingen. Den sier hvor mye brent areal som faller utenfor all
    landgeometri, og skal kunne følges fra kjøring til kjøring.
    """
    with open(STATUS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    naa = datetime.now(timezone.utc).isoformat(timespec="seconds")
    forrige = data["sources"].get(SOURCE_ID, {})

    def felt(fra_info, i_status, avrund=None):
        """Verdien fra denne kjøringen, ellers den forrige kjøring satte."""
        if info and fra_info in info:
            verdi = info[fra_info]
            return round(verdi, avrund) if avrund is not None else verdi
        return forrige.get(i_status)

    data["last_run"] = naa
    data["sources"][SOURCE_ID] = {
        "status": status,
        "last_attempt": naa,
        "last_success": naa if status == "ok" else forrige.get("last_success"),
        "rows": felt("rows", "rows"),
        "checksum": felt("checksum", "checksum"),
        "unattributed_share": felt("uattribuert_andel", "unattributed_share", 6),
        "unattributed_km2": felt("uattribuert_km2", "unattributed_km2", 2),
        "message": melding,
    }
    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def katalogsammendrag(oppforinger):
    """Antall filer, samlet størrelse og hvilke år katalogen dekker."""
    aar = sorted({o["aar"] for o in oppforinger})
    hull = [a for a in range(aar[0], aar[-1] + 1) if a not in aar] if aar else []
    return {
        "filer": len(oppforinger),
        "bytes": sum(o["bytes"] for o in oppforinger),
        "aar_forste": aar[0] if aar else None,
        "aar_siste": aar[-1] if aar else None,
        "aar_antall": len(aar),
        "aar_mangler": hull,
        "downloaded_at": date.today().isoformat(),
    }


def main():
    oppforinger = katalog()
    sammendrag = katalogsammendrag(oppforinger)
    print(
        f"K8: {sammendrag['filer']} månedsfiler, "
        f"{sammendrag['bytes'] / 2**30:.2f} GiB, "
        f"{sammendrag['aar_forste']}–{sammendrag['aar_siste']} "
        f"({sammendrag['aar_antall']} år)"
    )
    if sammendrag["aar_mangler"]:
        print(f"K8: år som mangler i kilden: {sammendrag['aar_mangler']}")
    return oppforinger, sammendrag


if __name__ == "__main__":
    main()
