"""K6 — Natural Earth, admin-0: landgeometri.

Henter Natural Earths admin-0-lag (1:10 mill.) som shapefil, legger arkivet
uendret i ``data/raw/`` og leverer geometriene videre som GeoJSON-aktige
ordbøker. Ingen tolkning, ingen omregning — se ``etl/sources/README.md``.

Kilden leverer ikke branndata. Den brukes til å fordele rutenettkilder på land
og til landarealer, og tegnes ikke som egen serie (CLAUDE.md § 5 og § 8).

Kjøres som modul fra repotoppen: ``python -m etl.sources.k6_natural_earth``
"""

import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import date

from etl.schema import LAND_NO_JSON, RAW_DIR, SOURCES_JSON

SOURCE_ID = "K6"

SKALA = "10m"
# Kartenhetene, ikke landene. Admin-0-laget slår Fransk Guyana, Réunion,
# Svalbard og en del andre områder sammen med moderlandet, og da ville brent
# areal i Fransk Guyana blitt ført på Frankrike. Kartenhetene skiller dem, og
# dekker 250 av de 251 landene i data/geo/land_no.json.
LAG = f"ne_{SKALA}_admin_0_map_units"
LANDING_URL = "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/"

# Natural Earth ligger på to verter med samme innhold. Den andre brukes bare
# hvis den første ikke svarer.
LASTE_URLER = (
    f"https://naciscdn.org/naturalearth/{SKALA}/cultural/{LAG}.zip",
    f"https://naturalearth.s3.amazonaws.com/{SKALA}_cultural/{LAG}.zip",
)

RAW_ZIP = RAW_DIR / f"k6_{LAG}.zip"

# Feltene som bærer en landkode, i den rekkefølgen de prøves. ISO_A3 er «-99»
# for en del land der tilhørigheten er omstridt, og ISO_A3_EH gir da koden for
# den suverene staten. ADM0_A3 er Natural Earths egen kode, som alltid finnes.
KODEFELT = ("ISO_A3_EH", "ISO_A3", "ADM0_A3")

# Verdier Natural Earth bruker for «ingen kode».
MANGLER = frozenset({"-99", "-099", ""})

# Natural Earths koder som ikke er ISO 3166, oversatt til entity-kodene i
# data/geo/land_no.json. Oversettelsen skjer her i kildemodulen, aldri ved å ta
# kildens egen kode rått inn i datamodellen (CLAUDE.md § 6).
NE_KODE_MAP = {
    # Territorier vi fører som egne entiteter.
    "KOS": "XKX",  # Kosovo
    "CYN": "NONISO_CYN",  # Nord-Kypros
    "WSB": "NONISO_AKD",  # Akrotiri, den vestlige basen
    "ESB": "NONISO_AKD",  # Dhekelia, den østlige basen
    # Områder ISO 3166 fører under en annen kode enn Natural Earth.
    "SAH": "ESH",  # Vest-Sahara
    "SOL": "SOM",  # Somaliland, ikke egen ISO-kode
    "CNM": "CYP",  # FN-sonen på Kypros
    "USG": "CUB",  # Guantánamo-basen ligger på Cuba
    "KAB": "KAZ",  # Bajkonur, leid av Russland, men kasakhisk territorium
    "CLP": "FRA",  # Clipperton, fransk uten egen ISO-kode
    "BRI": "BRA",  # Brasiliansk øy i Uruguay-elva
    "ATC": "AUS",  # Ashmore- og Cartierøyene
    "CSI": "AUS",  # Korallhavsøyene
    "IOA": "AUS",  # De australske øyene i Indiahavet
}

# Områder uten anerkjent tilhørighet. De rasteriseres ikke, og arealet deres
# havner i den uattribuerte andelen kjøringen rapporterer. Å tilskrive dem et
# land ville vært en redaksjonell avgjørelse siden ikke tar (P1).
UTEN_TILHORIGHET = frozenset(
    {
        "KAS",  # Siachen-breen
        "SPI",  # Den sørlige patagoniske isbreen
        "BRT",  # Bir Tawil
        "PGA",  # Spratlyøyene
        "SCR",  # Scarborough-revet
        "BJN",  # Bajo Nuevo
        "SER",  # Serranilla
    }
)


BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


class Nedlastingsfeil(Exception):
    """Reises når nedlastingen ikke ga et brukbart arkiv."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def hent():
    """Laster ned admin-0-arkivet til data/raw/ og returnerer (sti, info).

    Verifiserer at svaret faktisk er et zip-arkiv med en shapefil i, ikke en
    feilside.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    feil = []
    for url in LASTE_URLER:
        try:
            forespoersel = urllib.request.Request(
                url, headers={"User-Agent": BRUKERAGENT}
            )
            with urllib.request.urlopen(forespoersel, timeout=300) as svar:
                innhold_type = svar.headers.get("Content-Type", "")
                data = svar.read()
        except (urllib.error.URLError, TimeoutError) as e:
            feil.append(f"{url}: {type(e).__name__}: {e}")
            continue

        if "html" in innhold_type.lower() or not data.startswith(b"PK"):
            feil.append(
                f"{url}: svaret er ikke et zip-arkiv "
                f"(Content-Type {innhold_type!r}, {len(data)} byte)"
            )
            continue

        RAW_ZIP.write_bytes(data)
        with zipfile.ZipFile(RAW_ZIP) as arkiv:
            if not any(n.lower().endswith(".shp") for n in arkiv.namelist()):
                RAW_ZIP.unlink()
                feil.append(f"{url}: arkivet inneholder ingen .shp-fil")
                continue

        return RAW_ZIP, {
            "source_id": SOURCE_ID,
            "download_url": url,
            "downloaded_at": date.today().isoformat(),
            "checksum": _sha256(data),
            "bytes": len(data),
        }

    raise Nedlastingsfeil(
        "Fikk ikke lastet ned Natural Earth admin-0. Forsøk:\n  "
        + "\n  ".join(feil)
    )


def entity_kode(felt):
    """Oversetter Natural Earths kodefelt til vår entity-kode.

    Returnerer None for områder uten anerkjent tilhørighet.
    """
    for navn in KODEFELT:
        kode = str(felt.get(navn, "")).strip().upper()
        if kode in MANGLER:
            continue
        if kode in NE_KODE_MAP:
            return NE_KODE_MAP[kode]
        if kode in UTEN_TILHORIGHET:
            return None
        return kode
    return None


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def geometrier(sti=None):
    """Leser admin-0-laget og returnerer (geometrier, utelatt).

    ``geometrier`` er en liste med (entity-kode, GeoJSON-geometri). Koder som
    ikke står i data/geo/land_no.json tas med likevel — den som aggregerer
    avgjør hva som skal skje med dem, slik at et land som dukker opp i en kilde
    ikke forsvinner stille (CLAUDE.md § 5).

    ``utelatt`` er navnene på de områdene som ikke fikk en kode, til logging.
    """
    import shapefile  # pyshp. Installeres av workflowen, ikke av den månedlige.

    sti = sti or RAW_ZIP
    with zipfile.ZipFile(sti) as arkiv:
        deler = {}
        for navn in arkiv.namelist():
            for ending in ("shp", "dbf", "shx"):
                if navn.lower().endswith("." + ending):
                    deler[ending] = navn
        if len(deler) < 3:
            raise Nedlastingsfeil(
                f"{sti.name} mangler shapefil-deler, fant {sorted(deler)}"
            )
        biter = {e: io.BytesIO(arkiv.read(n)) for e, n in deler.items()}

    leser = shapefile.Reader(shp=biter["shp"], dbf=biter["dbf"], shx=biter["shx"])
    feltnavn = [f[0] for f in leser.fields[1:]]

    ut = []
    utelatt = []
    for post in leser.iterShapeRecords():
        felt = dict(zip(feltnavn, post.record))
        kode = entity_kode(felt)
        geometri = post.shape.__geo_interface__
        if not geometri.get("coordinates"):
            continue
        if kode is None:
            utelatt.append(str(felt.get("NAME") or felt.get("ADMIN") or "uten navn"))
            continue
        ut.append((kode, geometri))

    leser.close()
    return ut, utelatt


def skriv_metadata(info):
    """Registrerer kilden i data/_sources.json."""
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": f"Natural Earth — admin-0, kartenheter ({SKALA}, 1:10 mill.)",
        "publisher": "Natural Earth",
        "url": LANDING_URL,
        "download_url": info["download_url"],
        "license": "Public domain",
        "license_url": "https://www.naturalearthdata.com/about/terms-of-use/",
        "attribution": "Made with Natural Earth. Free vector and raster map "
        "data @ naturalearthdata.com.",
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": "",
        "coverage_end": "",
        "temporal_resolution": "",
        "quality": "",
        "unit_source": "",
        "downloaded_at": info["downloaded_at"],
        "source_last_updated": None,
        "checksum": info["checksum"],
        "series": [],
        "processed_files": [],
        "footnotes": [],
        "notes": "Geometri for kart, og grunnlaget for å fordele "
        "rutenettkilder på land. Leverer ingen tallverdier og står derfor ikke "
        "i kildekolonnen for noen seksjon.",
    }
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    sti, info = hent()
    geo, utelatt = geometrier(sti)
    land = _land()
    ukjente = sorted({k for k, _ in geo if k not in land})
    print(f"K6: {len(geo)} geometrier, {info['bytes']} byte")
    print(f"K6: uten kode: {len(utelatt)}")
    if ukjente:
        print(f"K6: koder utenfor land_no.json: {', '.join(ukjente)}")
    return geo, info


if __name__ == "__main__":
    main()
