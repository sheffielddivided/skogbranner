"""K9 — GFED5, brent areal fra Zenodo.

Henter de månedlige rutenettfilene, legger arkivet uendret i ``data/raw/`` og
leverer rutenettene videre slik de står i kilden. Ingen tolkning, ingen
omregning — se ``etl/sources/README.md``.

Hvilket datasett dette er
-------------------------
GFED5 ligger i to Zenodo-utgivelser, og bare den ene har brent areal:

* ``10.5281/zenodo.7668424`` — *GFED5 Burned Area*, månedlige rutenett med
  laget ``Total`` i km². Det er denne modulen henter.
* ``10.5281/zenodo.16794692`` — GFED5.1, artikkelutgivelsen. Der inneholder
  ``GFED5.1_monthly.zip`` og ``GFED5.1_daily.zip`` **kun utslipp** av 40 gasser
  og aerosoler, som er utenfor scope (CLAUDE.md P8). Brent areal finnes bare i
  ``GFED5.1_ecosystem.zip``, som starter i 2002 og er 0,25° hele veien.

Brent areal-datasettet dekker 1997–2020 og har oppløsningsskiftet § 5
beskriver: 1° til og med 2000, 0,25° fra 2001. Det er derfor dette som gir
serien og fotnoten ``f_resolution_change``.

Kilden oppgir km² per rute per måned. Enheten står ikke som attributt i
filene, kun i datasettets readme, så modulen kan ikke lese den ut av filen og
kontrollere den slik K8 gjør.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k9_gfed5``
"""

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K9"
SERIES_ID = "gfed5_annual_burned_area"

ZENODO_ID = "7668424"
ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_ID}"
LANDING_URL = f"https://zenodo.org/records/{ZENODO_ID}"
DOI = "10.5281/zenodo.7668424"
ARKIVFIL = "BA.zip"

# Artikkelen som dokumenterer *brent areal*-produktet, som er det vi bruker.
# Utslippsartikkelen under dokumenterer et annet produkt i samme familie, og
# er ikke siteringen for disse tallene (CLAUDE.md § 5).
SITERING = (
    "Chen, Y., Hall, J., van Wees, D., Andela, N., Hantson, S., Giglio, L., "
    "van der Werf, G. R., Morton, D. C., and Randerson, J. T.: Multi-decadal "
    "trends and variability in burned area from the fifth version of the "
    "Global Fire Emissions Database (GFED5), Earth Syst. Sci. Data, 15, "
    "5227–5259, https://doi.org/10.5194/essd-15-5227-2023, 2023."
)
ARTIKKEL_DOI = "10.5194/essd-15-5227-2023"

# GFED5.1, utslippsutgivelsen. Føres som referanse fordi den dokumenterer
# familien datasettet hører til, med sin publiserte rettelse som eget felt,
# slik at det er sporbart hvilken versjon av den artikkelen som gjelder.
GFED51_ARTIKKEL = {
    "citation": (
        "van der Werf, G.R., Randerson, J.T., van Wees, D., Chen, Y., "
        "Giglio, L., Hall, J., Vernooij, R., Mu, M., Binte Shahid, S., "
        "Barsanti, K.C., Yokelson, R. & Morton, D.C. (2025). Landscape fire "
        "emissions from the 5th version of the Global Fire Emissions Database "
        "(GFED5). Scientific Data 12, 1870. "
        "https://doi.org/10.1038/s41597-025-06127-w"
    ),
    "doi": "10.1038/s41597-025-06127-w",
    "correction": {
        "type": "Publisher Correction",
        "citation": "Publisher Correction, Scientific Data 13, 44 (15. januar 2026)",
        "doi": "10.1038/s41597-026-06613-9",
    },
}

RAW_K9_DIR = RAW_DIR / "k9"
RAW_ZIP = RAW_K9_DIR / ARKIVFIL

# Månedsfilene heter BAYYYYMM.nc. Arkivet har også __MACOSX-rester.
MAANEDSFIL = re.compile(r"^BA(\d{4})(\d{2})\.nc$")

# Laget med samlet brent areal. De øvrige lagene deler det opp etter branntype
# og landdekke, og brukes ikke.
VARIABEL = "Total"

# Årene produsenten har publisert som en ferdig utgivelse. Kataloger utover
# dette holdes ute (CLAUDE.md § 5).
AAR_FORSTE = 1997
AAR_SISTE = 2020

# Året oppløsningen skifter. Til og med året før er rutenettet 1°.
AAR_FIN_OPPLOSNING = 2001

FORSOK = 4
BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


class Nedlastingsfeil(Exception):
    """Reises når nedlastingen ikke ga et brukbart arkiv."""


def _les_json(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=180) as svar:
        innhold_type = svar.headers.get("Content-Type", "")
        raa = svar.read()
    if "json" not in innhold_type.lower():
        raise Nedlastingsfeil(
            f"{url} svarte med {innhold_type!r} i stedet for JSON."
        )
    return json.loads(raa.decode("utf-8"))


def katalog():
    """Slår opp Zenodo-oppføringen og returnerer metadata om arkivfilen."""
    post = _les_json(ZENODO_API)
    filer = {f["key"]: f for f in post["files"]}
    if ARKIVFIL not in filer:
        raise Nedlastingsfeil(
            f"Zenodo-oppføring {ZENODO_ID} har ingen fil {ARKIVFIL}. "
            f"Den har {sorted(filer)}."
        )
    fil = filer[ARKIVFIL]
    sjekksum = fil.get("checksum", "")
    return {
        "navn": ARKIVFIL,
        "url": fil["links"]["self"],
        "bytes": fil["size"],
        "md5": sjekksum.split(":", 1)[1] if sjekksum.startswith("md5:") else None,
        "downloaded_at": date.today().isoformat(),
        "zenodo_doi": post.get("doi", DOI),
        "license": (post["metadata"].get("license") or {}).get("id", "cc-by-4.0"),
        "publication_date": post["metadata"].get("publication_date"),
    }


def katalogsammendrag(oppf):
    """Omfanget av kilden, til rapportering før nedlasting."""
    aar = list(range(AAR_FORSTE, AAR_SISTE + 1))
    return {
        "filer": 1,
        "bytes": oppf["bytes"],
        "maanedsfiler": len(aar) * 12,
        "aar_forste": AAR_FORSTE,
        "aar_siste": AAR_SISTE,
        "aar_antall": len(aar),
        "aar_mangler": [],
        "aar_grov_opplosning": [a for a in aar if a < AAR_FIN_OPPLOSNING],
        "downloaded_at": oppf["downloaded_at"],
    }


def _md5(sti):
    sum_ = hashlib.md5()
    with open(sti, "rb") as f:
        for blokk in iter(lambda: f.read(1 << 20), b""):
            sum_.update(blokk)
    return sum_.hexdigest()


def _verifiser(sti, oppf):
    """Kontrollerer at filen er zip-arkivet Zenodo lovet, ikke en feilside."""
    faktisk = sti.stat().st_size
    if faktisk != oppf["bytes"]:
        raise Nedlastingsfeil(
            f"{oppf['navn']}: fikk {faktisk} byte, Zenodo oppgir {oppf['bytes']}. "
            "Nedlastingen er ufullstendig, eller svaret er ikke filen vi ba om."
        )
    with open(sti, "rb") as f:
        if f.read(2) != b"PK":
            raise Nedlastingsfeil(
                f"{oppf['navn']}: innholdet er ikke et zip-arkiv. En tjeneste "
                "som avviser forespørselen svarer gjerne med en HTML-side."
            )
    if oppf["md5"]:
        faktisk_md5 = _md5(sti)
        if faktisk_md5 != oppf["md5"]:
            raise Nedlastingsfeil(
                f"{oppf['navn']}: md5 {faktisk_md5} stemmer ikke med Zenodos "
                f"{oppf['md5']}"
            )


def hent(oppf):
    """Laster ned arkivet til data/raw/k9/ og verifiserer det."""
    RAW_K9_DIR.mkdir(parents=True, exist_ok=True)

    siste = None
    for forsok in range(FORSOK):
        try:
            forespoersel = urllib.request.Request(
                oppf["url"], headers={"User-Agent": BRUKERAGENT}
            )
            with urllib.request.urlopen(forespoersel, timeout=1800) as svar:
                innhold_type = svar.headers.get("Content-Type", "")
                if "html" in innhold_type.lower():
                    raise Nedlastingsfeil(
                        f"{oppf['navn']}: Zenodo svarte med {innhold_type!r} i "
                        "stedet for filinnhold."
                    )
                with open(RAW_ZIP, "wb") as f:
                    while blokk := svar.read(1 << 20):
                        f.write(blokk)
            _verifiser(RAW_ZIP, oppf)
            return RAW_ZIP
        except (urllib.error.URLError, TimeoutError, Nedlastingsfeil, OSError) as e:
            siste = e
            RAW_ZIP.unlink(missing_ok=True)
            if forsok < FORSOK - 1:
                time.sleep(2 ** (forsok + 1))

    raise Nedlastingsfeil(
        f"Ga opp {oppf['navn']} etter {FORSOK} forsøk: "
        f"{type(siste).__name__}: {siste}"
    )


def maanedsfiler(sti=None):
    """Månedsfilene i arkivet, sortert på periode.

    Returnerer en liste med (år, måned, navn i arkivet).
    """
    sti = sti or RAW_ZIP
    ut = []
    with zipfile.ZipFile(sti) as arkiv:
        for navn in arkiv.namelist():
            if navn.startswith("__MACOSX"):
                continue
            treff = MAANEDSFIL.match(navn.rsplit("/", 1)[-1])
            if not treff:
                continue
            aar, maaned = int(treff.group(1)), int(treff.group(2))
            # Kataloger utenfor den publiserte utgivelsen holdes ute (§ 5).
            if not (AAR_FORSTE <= aar <= AAR_SISTE):
                continue
            ut.append((aar, maaned, navn))
    ut.sort()
    return ut


def les_rutenett(arkiv, navn):
    """Leser brent areal fra én månedsfil i arkivet.

    Returnerer (lat, lon, verdier) i kildens egen enhet, km² per rute.
    """
    import netCDF4
    import numpy as np

    raa = arkiv.read(navn)
    with netCDF4.Dataset("i_minnet_" + navn.rsplit("/", 1)[-1], memory=raa) as nc:
        if VARIABEL not in nc.variables:
            raise Nedlastingsfeil(
                f"{navn}: fant ingen variabel {VARIABEL!r}. Filen har "
                f"{sorted(nc.variables)}."
            )
        lat = np.asarray(nc.variables["lat"][:], dtype="float64")
        lon = np.asarray(nc.variables["lon"][:], dtype="float64")
        verdier = np.ma.filled(nc.variables[VARIABEL][:], 0.0).astype("float64")

    if verdier.ndim == 3:
        if verdier.shape[0] != 1:
            raise Nedlastingsfeil(
                f"{navn}: filen har {verdier.shape[0]} tidssteg, ventet ett."
            )
        verdier = verdier[0]
    if verdier.shape != (lat.size, lon.size):
        raise Nedlastingsfeil(
            f"{navn}: {VARIABEL} har formen {verdier.shape}, ventet "
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
        "name": "GFED5 — Global Fire Emissions Database version 5, brent areal",
        "publisher": "Chen, Y. m.fl., University of California, Irvine, "
        "distribuert av Zenodo",
        "url": LANDING_URL,
        "download_url": info["url"],
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": SITERING,
        "doi": ARTIKKEL_DOI,
        "dataset_doi": info["zenodo_doi"],
        "related_publication": GFED51_ARTIKKEL,
        "requires_agreement": False,
        "geography": "global",
        "coverage_start": str(info["aar_forste"]),
        "coverage_end": str(info["aar_siste"]),
        "temporal_resolution": "monthly",
        "quality": "measured",
        "unit_source": "km2",
        "spatial_resolution": "1 degree 1997–2000, 0.25 degrees 2001–",
        "downloaded_at": info["downloaded_at"],
        "source_last_updated": info.get("publication_date"),
        "checksum": info["checksum"],
        "series": [SERIES_ID],
        "processed_files": processed_files,
        "footnotes": info["footnotes"],
        "excluded_unobserved": info["utelatte_entiteter"],
        "excluded_no_geometry": info["uten_geometri"],
        "resolutions": info["per_opplosning"],
        "notes": "Månedlige rutenett summert til årlige landtotaler med "
        "admin-0-geometrien fra K6. Rutenettet er 1° til og med 2000 og 0,25° "
        "fra 2001, og terskler og fotnoter regnes mot den oppløsningen som "
        "gjelder for det enkelte året. Arkivet lastes ned i GitHub Actions og "
        "slettes etter aggregering. Andelen brent areal uten landtilknytning i "
        f"denne kjøringen: {info['uattribuert_andel']:.4%}.",
    }
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        f.write("\n")


def skriv_status(status, melding, info=None):
    """Skriver kjørestatus til data/_status.json.

    Den uattribuerte andelen føres som eget felt, slik at den kan følges fra
    kjøring til kjøring — se CLAUDE.md § 5.
    """
    with open(STATUS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    naa = datetime.now(timezone.utc).isoformat(timespec="seconds")
    forrige = data["sources"].get(SOURCE_ID, {})

    def felt(fra_info, i_status, avrund=None):
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
        # Serien har to oppløsninger, og andelen henger sammen med
        # rutestørrelsen. Samletallet alene skjuler den forskjellen.
        "unattributed_by_resolution": (
            {
                navn: {
                    "unattributed_share": d["unattributed_share"],
                    "unattributed_km2": d["unattributed_km2"],
                    "years": d["years"],
                }
                for navn, d in info["per_opplosning"].items()
            }
            if info and "per_opplosning" in info
            else forrige.get("unattributed_by_resolution")
        ),
        "message": melding,
    }
    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    oppf = katalog()
    sammendrag = katalogsammendrag(oppf)
    print(
        f"K9: {oppf['navn']}, {oppf['bytes'] / 2**30:.2f} GiB, "
        f"{sammendrag['maanedsfiler']} månedsfiler, "
        f"{sammendrag['aar_forste']}–{sammendrag['aar_siste']}"
    )
    return oppf, sammendrag


if __name__ == "__main__":
    main()
