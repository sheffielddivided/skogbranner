"""Validering før publisering.

Kjøres mellom ``normalize.py`` og ``derive.py``. Kontrollerer at de kanoniske
seriene i ``data/processed/`` er gyldige, og avviser dem før de når siden hvis
de ikke er det.

Feiler valideringen, beholdes forrige datasett, feilen logges i
``data/_status.json``, og siden viser en diskré merknad om at akkurat den
serien ikke er oppdatert.

Reglene som skal håndheves — tillatte kodeverdier, enheter per indikator,
kildekoder, fotnoter og kravene til hver figur — står i CLAUDE.md § 6
(kanonisk datamodell) og § 11 (sjekkliste). De gjentas ikke her.

Kjøres som modul fra repotoppen: ``python -m etl.validate``
"""

import json
import re
from collections import Counter, defaultdict
from datetime import date

from etl import schema

ISO3 = re.compile(r"^[A-Z]{3}$")


class Valideringsfeil(Exception):
    """Reises når datasettet ikke kan publiseres."""


def _land():
    with open(schema.LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def valider_fotnotetekster():
    """Kontrollerer at hver fotnotekode har én norsk tekst, og ingen flere.

    Uten denne kan en ny kode tas i bruk i dataene uten at leseren får se hva
    den betyr, eller en tekst bli stående etter at koden er fjernet.
    """
    with open(schema.FOOTNOTES_JSON, encoding="utf-8") as f:
        tekster = json.load(f)["footnotes"]

    feil = []
    for kode in sorted(schema.FOOTNOTE - set(tekster)):
        feil.append(f"fotnoten {kode!r} mangler tekst i _footnotes.json")
    for kode in sorted(set(tekster) - schema.FOOTNOTE):
        feil.append(f"_footnotes.json har teksten {kode!r}, som ikke er en gyldig fotnote")
    for kode, tekst in sorted(tekster.items()):
        if not tekst.strip():
            feil.append(f"fotnoten {kode!r} har tom tekst")
    return feil


def valider(observasjoner):
    """Kontrollerer et sett kanoniske observasjoner.

    Returnerer en liste med feilmeldinger. Tom liste betyr at datasettet kan
    publiseres.
    """
    land = _land()
    aar_maks = date.today().year
    feil = valider_fotnotetekster()

    def meld(tekst):
        if len(feil) < 25:
            feil.append(tekst)

    sett = Counter()
    kvalitet_per_serie = defaultdict(set)

    for i, o in enumerate(observasjoner):
        hvor = f"rad {i} ({o.get('entity')} {o.get('period')})"

        # Kodeverdier mot enumerasjonene i schema.py
        if o["indicator"] not in schema.INDICATOR:
            meld(f"{hvor}: ukjent indicator {o['indicator']!r}")
        elif o["unit"] != schema.INDICATOR_UNIT[o["indicator"]]:
            meld(
                f"{hvor}: {o['indicator']} skal ha unit "
                f"{schema.INDICATOR_UNIT[o['indicator']]!r}, ikke {o['unit']!r}"
            )
        if o["quality"] not in schema.QUALITY:
            meld(f"{hvor}: ukjent quality {o['quality']!r}")
        if o["level"] not in schema.LEVEL:
            meld(f"{hvor}: ukjent level {o['level']!r}")
        if o["source_id"] not in schema.SOURCE:
            meld(f"{hvor}: ukjent source_id {o['source_id']!r}")
        if o["series_id"] not in schema.SERIES_ID:
            meld(f"{hvor}: ukjent series_id {o['series_id']!r}")
        for fotnote in o["footnotes"]:
            if fotnote not in schema.FOOTNOTE:
                meld(f"{hvor}: ukjent fotnote {fotnote!r}")

        # Ingen negative verdier
        if o["value"] is None:
            meld(f"{hvor}: verdien mangler — bruk «ingen data», ikke null")
        elif o["value"] < 0:
            meld(f"{hvor}: negativ verdi ({o['value']})")
        # En andel lagres mellom 0 og 1. Er den større, er nevneren feil —
        # typisk et landareal fra en annen entitet enn telleren.
        elif o["unit"] == "share" and o["value"] > 1:
            meld(f"{hvor}: andel over 1 ({o['value']})")

        # Entity-koder: land_no.json er fasit. Landkoder skal være ISO3, med
        # unntak av territoriene som er merket iso3: false.
        oppslag = land.get(o["entity"])
        if oppslag is None:
            meld(f"{hvor}: entity {o['entity']!r} finnes ikke i land_no.json")
        else:
            if oppslag["level"] != o["level"]:
                meld(
                    f"{hvor}: level {o['level']!r} stemmer ikke med "
                    f"land_no.json ({oppslag['level']!r})"
                )
            if oppslag["entity_name"] != o["entity_name"]:
                meld(f"{hvor}: entity_name stemmer ikke med land_no.json")
            if oppslag["iso3"] and not ISO3.match(o["entity"]):
                meld(f"{hvor}: {o['entity']!r} er merket iso3, men er ikke en ISO3-kode")

        # Årstall innenfor rimelig intervall
        aar = int(o["period"][:4])
        if not (schema.YEAR_MIN <= aar <= aar_maks):
            meld(f"{hvor}: årstall {aar} utenfor {schema.YEAR_MIN}–{aar_maks}")

        sett[(o["entity"], o["period"], o["indicator"], o["source_id"])] += 1
        kvalitet_per_serie[o["series_id"]].add(o["quality"])

    # Ingen duplikater
    for nokkel, antall in sett.items():
        if antall > 1:
            meld(f"duplikat: {nokkel} forekommer {antall} ganger")

    # Én quality per serie (CLAUDE.md § 6)
    for serie, kvaliteter in kvalitet_per_serie.items():
        if len(kvaliteter) > 1:
            meld(f"serien {serie!r} blander quality: {sorted(kvaliteter)}")

    return feil


def les_publiserte():
    """Leser alle kanoniske filer som finnes under data/processed/.

    Filnavnene står i schema.PROCESSED_FILE. En indikator uten fil ennå er
    ikke en feil — den er bare ikke tatt inn.
    """
    observasjoner = []
    for navn in sorted(set(schema.PROCESSED_FILE.values())):
        sti = schema.PROCESSED_DIR / f"{navn}.json"
        if not sti.exists():
            continue
        with open(sti, encoding="utf-8") as f:
            observasjoner.extend(json.load(f))
    return observasjoner


def main():
    observasjoner = les_publiserte()
    if not observasjoner:
        raise Valideringsfeil("ingen kanoniske filer under data/processed/")

    feil = valider(observasjoner)
    if feil:
        for f_ in feil:
            print("FEIL:", f_)
        raise Valideringsfeil(f"{len(feil)} feil i data/processed/")

    print(f"validate: {len(observasjoner)} observasjoner OK")
    return observasjoner


if __name__ == "__main__":
    main()
