"""K6 — Natural Earth, admin-0: kartgeometri og landarealer.

Kilden leverer ingen branndata. Den gir to ting:

* **Geometri** til kartene, som forenklet TopoJSON under ``data/geo/``. Alt
  tegnes fra filer i repoet — siden henter ingenting fra en flistjeneste (T2).
* **Landarealer**, som er nevneren i ``burned_area_share_land`` og grunnlaget
  for arealsammenligningen i § 7.

**Admin-0 har ikke noe arealfelt.** Arealene regnes derfor fra polygonene, ved
å reprojisere til en arealtro projeksjon og måle flaten. En arealtro
projeksjon bevarer areal eksakt, så resultatet er polygonenes faktiske areal —
med den unøyaktigheten som ligger i at Natural Earth er generalisert.

Tallene avviker derfor noe fra offisielle landarealer, og de er ikke ment å
erstatte dem. Poenget er at nevneren og arealsammenligningen bruker det samme
grunnlaget, slik at de er innbyrdes konsistente. Se CLAUDE.md § 7.

Både forenkling og projeksjon gjøres med mapshaper, som er en
byggeavhengighet. Den kjører i Node og sender ingenting til leseren (T2).

Kjøres som modul fra repotoppen: ``python -m etl.sources.k6_natural_earth``
"""

import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import date, datetime, timezone

from etl.schema import (
    GEO_DIR,
    LAND_AREA_JSON,
    LAND_NO_JSON,
    RAW_DIR,
    REPO_ROOT,
    SOURCES_JSON,
    STATUS_JSON,
)

SOURCE_ID = "K6"

LANDING_URL = "https://www.naturalearthdata.com/downloads/"
BASE_URL = "https://naciscdn.org/naturalearth"

# Målestokkene vi tar inn. 110m er nok til et verdenskart, 50m gir nok
# oppløsning til et europakart og til arealberegningen.
MAALESTOKKER = {
    "110m": {
        "url": f"{BASE_URL}/110m/cultural/ne_110m_admin_0_countries.zip",
        "shapefile": "ne_110m_admin_0_countries.shp",
        # Forenklingsgraden er valgt så kystlinjene holder seg gjenkjennelige
        # i den størrelsen kartet faktisk vises i.
        "simplify": "8%",
    },
    "50m": {
        "url": f"{BASE_URL}/50m/cultural/ne_50m_admin_0_countries.zip",
        "shapefile": "ne_50m_admin_0_countries.shp",
        "simplify": "5%",
    },
}

# Arealene regnes fra den mest detaljerte målestokken vi henter.
AREAL_MAALESTOKK = "50m"

# Arealtro sylinderprojeksjon. Den bevarer areal eksakt, så flaten i
# projeksjonen er polygonets faktiske areal.
AREALPROJEKSJON = "+proj=cea +lat_ts=0 +datum=WGS84"

# Natural Earths egne koder for entiteter uten tildelt ISO 3166-kode. For alle
# andre brukes ISO_A3_EH, som kilden fyller ut der ISO_A3 står tom.
NE_CODE_MAP = {
    "KOS": "XKX",  # Kosovo — vi beholder X-formen, se CLAUDE.md § 6
    "CYN": "NONISO_CYN",  # Nord-Kypros
}

# Entiteter Natural Earth fører, men som vi bevisst ikke har med. De er ikke en
# feil, og skal ikke stoppe kjøringen — men de føres opp i utdatafilen, slik at
# det er sporbart hva som er utelatt og hvorfor.
ISO3 = re.compile(r"^[A-Z]{3}$")

RAW_UNPACKED = RAW_DIR / "k6_natural_earth"

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


def _hent(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=300) as svar:
        return svar.read()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _mapshaper(*argumenter):
    """Kjører mapshaper og reiser feil hvis den ikke finnes eller feiler.

    Foretrekker den innstallerte binærfilen framfor npx, slik at kjøringen
    ikke henter noe fra nettverket underveis.
    """
    lokal = REPO_ROOT / "node_modules" / ".bin" / "mapshaper"
    if lokal.exists():
        kommando = [str(lokal)]
    elif shutil.which("mapshaper"):
        kommando = ["mapshaper"]
    else:
        raise RuntimeError(
            "mapshaper mangler. Den er en byggeavhengighet — kjør «npm ci» først."
        )

    resultat = subprocess.run(
        kommando + list(argumenter),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if resultat.returncode != 0:
        raise RuntimeError(
            f"mapshaper feilet ({resultat.returncode}): {resultat.stderr.strip()}"
        )
    return resultat.stdout


def entity_kode(post):
    """Oversetter Natural Earths koder til vår entity-kode.

    ISO_A3_EH er kildens eget felt for «ISO-koden, også der ISO_A3 står tom».
    Der den er tom, er entiteten uten tildelt ISO-kode, og da slår vi opp i
    NE_CODE_MAP. Finnes den ikke der heller, har vi ingen kode for entiteten.
    """
    adm = (post.get("ADM0_A3") or "").strip()
    if adm in NE_CODE_MAP:
        return NE_CODE_MAP[adm]
    iso = (post.get("ISO_A3_EH") or "").strip()
    if ISO3.match(iso):
        return iso
    return None


def beregn_arealer(poster, land):
    """Summerer polygonarealene per entity-kode.

    Summeres, ikke settes: Natural Earth fører enkelte territorier som egne
    polygoner under samme ISO-kode som moderlandet. To polygoner med samme kode
    er da to deler av samme entitet, og arealet er summen av dem.

    Returnerer (arealer, utelatt).
    """
    arealer = {}
    utelatt = []

    for post in poster:
        areal = post.get("area_km2")
        if areal is None:
            continue
        kode = entity_kode(post)
        if kode is None or kode not in land:
            utelatt.append(
                {
                    "ne_code": (post.get("ADM0_A3") or "").strip(),
                    "name": post.get("NAME_EN", ""),
                    "area_km2": round(areal, 2),
                    "entity": kode,
                }
            )
            continue
        arealer[kode] = round(arealer.get(kode, 0.0) + areal, 2)

    utelatt.sort(key=lambda u: -u["area_km2"])
    return arealer, utelatt


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def hent():
    """Laster ned begge målestokkene, bygger geometri og regner arealer.

    Returnerer (arealer, utelatt, info).
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    RAW_UNPACKED.mkdir(parents=True, exist_ok=True)

    sjekksummer = {}
    geometrifiler = []

    for maalestokk, oppsett in MAALESTOKKER.items():
        zip_bytes = _hent(oppsett["url"])
        zip_sti = RAW_DIR / f"k6_ne_{maalestokk}_admin_0_countries.zip"
        zip_sti.write_bytes(zip_bytes)
        sjekksummer[maalestokk] = _sha256(zip_bytes)

        utpakket = RAW_UNPACKED / maalestokk
        with zipfile.ZipFile(zip_sti) as arkiv:
            arkiv.extractall(utpakket)

        shapefile = utpakket / oppsett["shapefile"]

        # Geometri til kartene. Kun entity-kodene følger med — navnene slås opp
        # i land_no.json ved tegning, så de ikke får en kopi til her.
        ut = GEO_DIR / f"world_{maalestokk}.topo.json"
        _mapshaper(
            str(shapefile),
            "-filter-fields",
            "ADM0_A3,ISO_A3_EH",
            "-simplify",
            oppsett["simplify"],
            "keep-shapes",
            "-clean",
            "-o",
            "format=topojson",
            str(ut),
        )
        geometrifiler.append(ut.name)

    # Arealene: reprojiser til arealtro projeksjon og les av flaten.
    oppsett = MAALESTOKKER[AREAL_MAALESTOKK]
    shapefile = RAW_UNPACKED / AREAL_MAALESTOKK / oppsett["shapefile"]
    attributter = RAW_DIR / "k6_natural_earth_areas.json"
    _mapshaper(
        str(shapefile),
        "-proj",
        AREALPROJEKSJON,
        "-each",
        "area_km2 = this.area / 1e6",
        "-filter-fields",
        "ADM0_A3,ISO_A3_EH,NAME_EN,area_km2",
        "-o",
        "format=json",
        str(attributter),
    )
    with open(attributter, encoding="utf-8") as f:
        poster = json.load(f)

    arealer, utelatt = beregn_arealer(poster, _land())

    info = {
        "source_id": SOURCE_ID,
        "downloaded_at": date.today().isoformat(),
        "checksum": sjekksummer[AREAL_MAALESTOKK],
        "checksums": sjekksummer,
        "rows": len(arealer),
        "geometry_files": geometrifiler,
        "excluded": len(utelatt),
    }
    return arealer, utelatt, info


def skriv_arealer(arealer, utelatt, info):
    """Skriver data/geo/land_area_km2.json."""
    data = {
        "schema_version": 1,
        "_om": "Landareal per entitet i km², regnet fra Natural Earth admin-0 "
        "ved reprojeksjon til en arealtro projeksjon. Admin-0 har ikke noe "
        "arealfelt. Tallene er nevneren i burned_area_share_land og grunnlaget "
        "for arealsammenligningen. Se CLAUDE.md § 5 og etl/sources/"
        "k6_natural_earth.py.",
        "source_id": SOURCE_ID,
        "scale": AREAL_MAALESTOKK,
        "projection": AREALPROJEKSJON,
        "downloaded_at": info["downloaded_at"],
        "_utelatt": "Entiteter Natural Earth fører, men som ikke står i "
        "land_no.json. De er utelatt med vilje og føres opp her for at det skal "
        "være sporbart hva som ikke er med.",
        "excluded": utelatt,
        "areas": dict(sorted(arealer.items())),
    }
    with open(LAND_AREA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return LAND_AREA_JSON


def skriv_metadata(info):
    """Registrerer kilden i data/_sources.json.

    K6 leverer ingen tallserie og står derfor ikke i kildekolonnen i § 8. Den
    føres likevel her, fordi geometrien og arealene er synlige for leseren og
    må kunne spores.
    """
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "Natural Earth — Admin 0, countries",
        "publisher": "Natural Earth",
        "url": LANDING_URL,
        "download_url": MAALESTOKKER[AREAL_MAALESTOKK]["url"],
        "license": "Public domain. Natural Earth setter ingen vilkår for bruk.",
        "license_url": "https://www.naturalearthdata.com/about/terms-of-use/",
        "attribution": "Made with Natural Earth.",
        "requires_agreement": False,
        "geography": "global",
        "temporal_resolution": None,
        "quality": None,
        "unit_source": None,
        "downloaded_at": info["downloaded_at"],
        "checksum": info["checksum"],
        "checksums": info["checksums"],
        "series": [],
        "processed_files": info["geometry_files"] + [LAND_AREA_JSON.name],
        "footnotes": [],
        "notes": "Leverer kartgeometri og landarealer, ikke branndata. "
        "Admin-0 har ikke noe arealfelt, så arealene er regnet fra polygonene "
        "ved reprojeksjon til en arealtro projeksjon. Fordi Natural Earth er "
        "generalisert, avviker de noe fra offisielle landarealer.",
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
    arealer, utelatt, info = hent()
    sti = skriv_arealer(arealer, utelatt, info)
    print(
        f"K6: {len(arealer)} entiteter med areal, {len(utelatt)} utelatt "
        f"→ {sti.name}, {', '.join(info['geometry_files'])}"
    )
    return arealer, utelatt, info


if __name__ == "__main__":
    main()
