"""K5 — NIFC: årlige branntall og brent areal for USA.

Tallene ligger som en HTML-tabell i selve statistikksiden. Det finnes ingen
CSV eller XLS bak den, så siden lastes ned uendret til ``data/raw/`` og
tabellen parses derfra.

Kilden oppgir acres. Konverteringen til km² skjer i ``normalize.py``.

Kjøres som modul fra repotoppen: ``python -m etl.sources.k5_nifc``
"""

import hashlib
import json
import re
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser

from etl.schema import RAW_DIR, SOURCES_JSON, STATUS_JSON

SOURCE_ID = "K5"
SERIES_BURNED_AREA = "nifc_annual_burned_area"
SERIES_FIRE_COUNT = "nifc_annual_fire_count"

LANDING_URL = "https://www.nifc.gov/fire-information/statistics/wildfires"

RAW_HTML = RAW_DIR / "k5_nifc_wildfires.html"

# NIFC fører kun USA som helhet.
ENTITY = "USA"

# Overskriften i tabellen vi er ute etter. Siden har flere tabeller over tid,
# så tabellen velges på overskrift og ikke på rekkefølge.
TABELLOVERSKRIFT = "Total Wildland Fires and Acres"

# Kolonneoverskriftene, som brukes til å finne hvor dataradene begynner.
KOLONNER = ["Year", "Fires", "Acres"]

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"


class _Tabelluttrekk(HTMLParser):
    """Plukker ut cellene i hver tabell på siden.

    Bevisst enkel: den bryr seg bare om ``table``, ``tr`` og ``td``/``th``, og
    samler ren tekst per celle. Ingen tolkning av tallene — den hører hjemme i
    ``_les_tabell``.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabeller = []
        self._tabell = None
        self._rad = None
        self._celle = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._tabell = []
        elif tag == "tr" and self._tabell is not None:
            self._rad = []
        elif tag in ("td", "th") and self._rad is not None:
            self._celle = []

    def handle_endtag(self, tag):
        if tag == "table" and self._tabell is not None:
            self.tabeller.append(self._tabell)
            self._tabell = None
        elif tag == "tr" and self._rad is not None:
            self._tabell.append(self._rad)
            self._rad = None
        elif tag in ("td", "th") and self._celle is not None:
            self._rad.append(re.sub(r"\s+", " ", "".join(self._celle)).strip())
            self._celle = None

    def handle_data(self, data):
        if self._celle is not None:
            self._celle.append(data)


def _tall(tekst):
    """Leser et tall med tusenskille-komma, og sier fra om det er merket.

    Kilden setter en stjerne foran verdier med et forbehold — for 2004 mangler
    delstatsarealer for North Carolina. Stjernen returneres som et eget flagg,
    slik at ``normalize.py`` kan feste en fotnote på akkurat den observasjonen
    i stedet for på hele serien.
    """
    merket = "*" in tekst
    reint = tekst.replace("*", "").replace(",", "").strip()
    return int(reint), merket


def _les_tabell(html):
    """Finner tabellen med årstall, branntall og acres, og leser radene.

    Returnerer (rader, dekning), der dekning er perioden slik overskriften
    oppgir den.
    """
    uttrekk = _Tabelluttrekk()
    uttrekk.feed(html)

    for tabell in uttrekk.tabeller:
        flat = " ".join(celle for rad in tabell for celle in rad)
        if TABELLOVERSKRIFT not in flat:
            continue

        # Overskriften bærer dekningsperioden: «… Acres (1983-2025)».
        dekning = None
        for rad in tabell:
            for celle in rad:
                treff = re.search(rf"{TABELLOVERSKRIFT}\s*\((\d{{4}})-(\d{{4}})\)", celle)
                if treff:
                    dekning = (int(treff.group(1)), int(treff.group(2)))

        # Dataradene begynner etter kolonneoverskriftene.
        start = None
        for i, rad in enumerate(tabell):
            if [celle.strip() for celle in rad[:3]] == KOLONNER:
                start = i + 1
                break
        if start is None:
            raise ValueError(
                f"fant ikke kolonneoverskriftene {KOLONNER} i NIFC-tabellen"
            )

        rader = []
        for rad in tabell[start:]:
            if len(rad) < 3 or not re.fullmatch(r"\*?\d{4}", rad[0].strip()):
                # Fotnoteraden nederst har én celle over hele bredden.
                continue
            aar, _ = _tall(rad[0])
            branner, branner_merket = _tall(rad[1])
            acres, acres_merket = _tall(rad[2])
            rader.append(
                {
                    "year": aar,
                    "fires": branner,
                    "acres": acres,
                    "marked": branner_merket or acres_merket,
                }
            )

        if not rader:
            raise ValueError("NIFC-tabellen ga ingen datarader")

        rader.sort(key=lambda r: r["year"])
        if dekning is None:
            dekning = (rader[0]["year"], rader[-1]["year"])
        return rader, dekning

    raise ValueError(
        f"fant ingen tabell med overskriften {TABELLOVERSKRIFT!r} på {LANDING_URL}"
    )


def _hent(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=120) as svar:
        return svar.read()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def hent():
    """Laster ned statistikksiden, skriver den til data/raw/ og leser tabellen.

    Returnerer (rader, info). Radene bærer acres og branntall slik de står i
    kilden — ingen omregning her.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    html_bytes = _hent(LANDING_URL)
    RAW_HTML.write_bytes(html_bytes)

    rader, dekning = _les_tabell(html_bytes.decode("utf-8", errors="replace"))

    info = {
        "source_id": SOURCE_ID,
        "series_id": [SERIES_BURNED_AREA, SERIES_FIRE_COUNT],
        "downloaded_at": date.today().isoformat(),
        "checksum": _sha256(html_bytes),
        "rows": len(rader),
        "coverage_start": dekning[0],
        "coverage_end": dekning[1],
    }
    return rader, info


def skriv_metadata(info, processed_files):
    """Registrerer kilden i data/_sources.json."""
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    sources["sources"][SOURCE_ID] = {
        "source_id": SOURCE_ID,
        "name": "NIFC — Total Wildland Fires and Acres",
        "publisher": "National Interagency Fire Center, med tall fra National "
        "Interagency Coordination Center",
        "url": LANDING_URL,
        "download_url": LANDING_URL,
        "license": "Offentlig eiendom. Verk av USAs føderale myndigheter er "
        "ikke opphavsrettsbeskyttet.",
        "license_url": "https://www.doi.gov/disclaimer",
        "attribution": "National Interagency Coordination Center, via National "
        "Interagency Fire Center.",
        "requires_agreement": False,
        "geography": "USA",
        "coverage_start": str(info["coverage_start"]),
        "coverage_end": str(info["coverage_end"]),
        "temporal_resolution": "annual",
        "quality": "reported",
        "unit_source": "acres",
        "downloaded_at": info["downloaded_at"],
        "checksum": info["checksum"],
        "series": [SERIES_BURNED_AREA, SERIES_FIRE_COUNT],
        "processed_files": processed_files,
        "footnotes": ["f_reporting_basis", "f_record_start"],
        "notes": "Tallene er nasjonalt rapporterte og følger amerikanske "
        "definisjoner av hva som telles som en branntilfelle. Kilden oppgir at "
        "de føderale brannmyndighetene ikke førte offisielle branndata etter "
        "dagens rapporteringsprosesser før 1983, og at det derfor ikke finnes "
        "offisielle tall for tidligere år.",
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
        f"K5: {info['rows']} rader {info['coverage_start']}–{info['coverage_end']}, "
        f"sha256 {info['checksum'][:16]}…"
    )
    return rader, info


if __name__ == "__main__":
    main()
