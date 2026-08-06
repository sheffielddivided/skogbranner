"""K6 — Natural Earth, admin-0: landgeometri og landarealer.

Henter Natural Earths admin-0-lag (1:10 mill.) som shapefil, legger arkivet
uendret i ``data/raw/`` og leverer geometriene videre som GeoJSON-aktige
ordbøker. Ingen tolkning, ingen omregning — se ``etl/sources/README.md``.

Kilden leverer ikke branndata. Den gir to ting, og tegnes ikke som egen serie
(CLAUDE.md § 5 og § 8):

* **Geometri**, som rutenettkildene fordeles på land med, og som kartene
  tegnes fra.
* **Landarealer**, som er nevneren i ``burned_area_share_land`` og grunnlaget
  for arealsammenligningen i § 7.

**Admin-0 har ikke noe arealfelt.** Arealene regnes derfor fra polygonene, med
den samme geometrien rutenettkildene fordeles på. Da er nevneren og
rasteriseringen enige om hvor landegrensene går.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k6_natural_earth``
"""

import hashlib
import io
import json
import math
import urllib.error
import urllib.request
import zipfile
from datetime import date

from etl.schema import LAND_AREA_JSON, LAND_NO_JSON, RAW_DIR, SOURCES_JSON

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


# Jordas autaliske radius i km: radien i den kula som har samme overflate som
# WGS84-ellipsoiden. Den gjør at arealene stemmer i sum, ikke bare lokalt.
AUTALISK_RADIUS_KM = 6371.0072


def _ringareal(ring):
    """Arealet av én lukket ring på kula, i km². Fortegnet følger omløpet.

    Bruker formelen for sfærisk polygonareal. Fortegnet skiller ytterkant fra
    hull, slik at et land med innsjøhull ikke får hullet regnet med.
    """
    if len(ring) < 4:
        return 0.0

    sum_ = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:]):
        sum_ += math.radians(lon2 - lon1) * (
            math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return sum_ * AUTALISK_RADIUS_KM**2 / 2.0


def _geometriareal(geometri):
    """Arealet av en GeoJSON-geometri i km².

    Første ring i et polygon er ytterkanten, resten er hull. Hullene kommer med
    motsatt fortegn av ytterkanten, så summen trekker dem fra av seg selv.
    """
    type_ = geometri.get("type")
    koordinater = geometri.get("coordinates") or []

    if type_ == "Polygon":
        polygoner = [koordinater]
    elif type_ == "MultiPolygon":
        polygoner = koordinater
    else:
        return 0.0

    total = 0.0
    for polygon in polygoner:
        if not polygon:
            continue
        ytre = abs(_ringareal(polygon[0]))
        hull = sum(abs(_ringareal(r)) for r in polygon[1:])
        total += ytre - hull
    return total


def landarealer(geo, land=None):
    """Summerer polygonarealene per entity-kode.

    Summeres, ikke settes: et land består gjerne av flere polygoner, og
    kartenhetene deler dessuten enkelte land i flere poster. Arealet er summen
    av delene.

    Returnerer (arealer, utelatt). ``utelatt`` er koder kilden fører som ikke
    står i land_no.json — de er ikke en feil her, men føres opp slik at det er
    sporbart hva som ikke er med.
    """
    land = land if land is not None else _land()

    arealer = {}
    utelatt = {}
    for kode, geometri in geo:
        areal = _geometriareal(geometri)
        if areal <= 0:
            continue
        if kode in land:
            arealer[kode] = arealer.get(kode, 0.0) + areal
        else:
            utelatt[kode] = round(utelatt.get(kode, 0.0) + areal, 2)

    arealer = {k: round(v, 2) for k, v in sorted(arealer.items())}
    return arealer, dict(sorted(utelatt.items()))


def skriv_arealer(arealer, utelatt, info):
    """Skriver data/geo/land_area_km2.json."""
    data = {
        "schema_version": 1,
        "_om": "Landareal per entitet i km², regnet fra Natural Earths "
        "admin-0-kartenheter. Admin-0 har ikke noe arealfelt, så arealene er "
        "regnet fra polygonene med formelen for sfærisk polygonareal. Tallene "
        "er nevneren i burned_area_share_land og grunnlaget for "
        "arealsammenligningen. Se CLAUDE.md § 5 og etl/sources/"
        "k6_natural_earth.py.",
        "source_id": SOURCE_ID,
        "layer": LAG,
        "downloaded_at": info["downloaded_at"],
        "_utelatt": "Koder Natural Earth fører, men som ikke står i "
        "land_no.json. De er utelatt med vilje og føres opp her for at det "
        "skal være sporbart hva som ikke er med.",
        "excluded": utelatt,
        "areas": arealer,
    }
    LAND_AREA_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(LAND_AREA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return LAND_AREA_JSON


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

    arealer, uten_oppforing = landarealer(geo, land)
    skriv_arealer(arealer, uten_oppforing, info)
    print(
        f"K6: landareal for {len(arealer)} entiteter → {LAND_AREA_JSON.name}"
        + (f", {len(uten_oppforing)} utelatt" if uten_oppforing else "")
    )
    return geo, info


if __name__ == "__main__":
    main()
