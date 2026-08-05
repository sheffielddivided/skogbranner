"""Normalisering til kanonisk form.

Tar råe kildefiler fra ``data/raw/`` slik ``etl/sources/`` leverte dem, og
skriver kanoniske serier til ``data/processed/``.

Dette er også det ene stedet i pipelinen der enheter konverteres. Kommer en
kilde i hektar eller acres, skjer omregningen her og bare her — verken
derive.py, byggetrinnet eller visningslaget rører en verdi.

Konverteringsfaktorene og de tillatte kodeverdiene importeres fra
``etl/schema.py``. Definer dem aldri på nytt her.

Se CLAUDE.md § 3 (T1) for enhetsregelen og § 6 for den kanoniske datamodellen.

Kjøres som modul fra repotoppen: ``python -m etl.normalize``
"""

import csv
import json
from collections import defaultdict

from etl.schema import (
    ACRE_TO_KM2,
    HA_TO_KM2,
    LAND_AREA_JSON,
    LAND_NO_JSON,
    PROCESSED_DIR,
    PROCESSED_FILE,
)
from etl.sources import k1_owid, k2_gwis, k3_effis, k4_effis, k5_nifc, k7_nbac

FELT = [
    "entity",
    "entity_name",
    "level",
    "period",
    "indicator",
    "value",
    "unit",
    "source_id",
    "series_id",
    "quality",
    "footnotes",
]

# Antall desimaler i km²-verdiene. Den groveste kilden oppgir hele hektar, så
# to desimaler holder på all informasjon i kilden (1 ha = 0,01 km²) uten å
# legge til flyttallsstøy.
DESIMALER = 2

INDIKATOR = "burned_area_km2"
ENHET = "km2"

INDIKATOR_ANTALL = "fire_count"
ENHET_ANTALL = "count"

INDIKATOR_ANDEL = "burned_area_share_land"
ENHET_ANDEL = "share"

# Andelen lagres som et tall mellom 0 og 1, og vises for leseren i prosent.
# Åtte desimaler holder på oppløsningen også for de minste andelene: et land
# der en brøkdel av en km² brant, får fortsatt en verdi som ikke runder til 0.
DESIMALER_ANDEL = 8


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def _observasjon(kode, land, aar, indikator, enhet, verdi, kilde, serie, kvalitet, fotnoter):
    """Setter sammen én kanonisk observasjon.

    Navnet og nivået hentes alltid fra land_no.json, som er fasit for hvilke
    entiteter som finnes og hva de heter (CLAUDE.md § 6).
    """
    return {
        "entity": kode,
        "entity_name": land[kode]["entity_name"],
        "level": land[kode]["level"],
        "period": str(aar),
        "indicator": indikator,
        "value": verdi,
        "unit": enhet,
        "source_id": kilde,
        "series_id": serie,
        "quality": kvalitet,
        "footnotes": fotnoter,
    }


def fra_k1(rader, info):
    """Gjør K1-rader om til kanoniske observasjoner.

    Kilden leverer hektar. Verdiene konverteres til km² her, og det er den
    konverterte verdien som finnes videre i pipelinen.
    """
    land = _land()

    # Data for nedlastingsåret er per definisjon ufullstendige.
    ufullstendig_aar = int(info["downloaded_at"][:4])

    # Gjelder hele serien: MODIS/VIIRS-overgangen og at de minste brannene
    # ikke fanges opp. Se data/_sources.json for kildens egen ordlyd.
    grunnfotnoter = ["f_sensor_break", "f_min_fire_size"]

    observasjoner = []
    ukjente = set()

    for rad in rader:
        raa = rad[k1_owid.VALUE_COLUMN]
        if raa == "":
            continue

        kode = k1_owid.entity_kode(rad)
        if kode is None or kode not in land:
            ukjente.add((rad["Entity"], rad["Code"]))
            continue

        aar = int(rad["Year"])
        verdi = round(float(raa) * HA_TO_KM2, DESIMALER)

        fotnoter = list(grunnfotnoter)
        if aar >= ufullstendig_aar:
            fotnoter.append("f_incomplete_year")

        # Kilden leverer et fullt rutenett og bruker 0 der den ikke har påvist
        # brent areal. Den skiller ikke mellom «ingenting brant» og «ingen
        # måling», så nullene merkes eksplisitt. Se CLAUDE.md § 9.
        if verdi == 0:
            fotnoter.append("f_zero_no_detection")

        observasjoner.append(
            _observasjon(
                kode,
                land,
                aar,
                INDIKATOR,
                ENHET,
                verdi,
                k1_owid.SOURCE_ID,
                k1_owid.SERIES_ID,
                "measured",
                fotnoter,
            )
        )

    if ukjente:
        raise ValueError(
            "Entiteter uten oppføring i data/geo/land_no.json: "
            + ", ".join(f"{navn} ({kode or 'ingen kode'})" for navn, kode in sorted(ukjente))
        )

    observasjoner.sort(key=lambda o: (o["entity"], o["period"]))
    return observasjoner


def fra_k2(rader, info):
    """Gjør GWIS-rader om til kanoniske observasjoner.

    Kilden leverer hektar, som konverteres til km² her. Det er den samme
    målingen K1 bygger på, så fotnotene er de samme.

    Observasjonene skrives ikke til data/processed/ i denne omgangen. K2 tegnes
    ikke i noen figur i kryssjekkrollen (§ 5), og formen brukes for at
    kryssjekken skal sammenligne to sett i samme enhet — ikke for å publisere
    en serie ingen seksjon leser.
    """
    land = _land()
    ufullstendig_aar = int(info["downloaded_at"][:4])
    grunnfotnoter = ["f_sensor_break", "f_min_fire_size"]

    observasjoner = []
    ukjente = set()

    for rad in rader:
        # Oppføringer kilden fører som ikke er entiteter i landtabellen, er
        # utelatt med vilje og skal ikke stoppe kjøringen.
        if rad["iso3"] in k2_gwis.IKKE_ENTITETER:
            continue

        kode = k2_gwis.entity_kode(rad["iso3"])
        if kode not in land:
            ukjente.add((rad["name"], rad["iso3"]))
            continue

        aar = rad["year"]
        verdi = round(rad["ba_ha"] * HA_TO_KM2, DESIMALER)

        fotnoter = list(grunnfotnoter)
        if aar >= ufullstendig_aar:
            fotnoter.append("f_incomplete_year")
        # Samme grunnlag som K1: en 0 skiller ikke mellom «ingenting brant» og
        # «ingen måling». Se CLAUDE.md § 9.
        if verdi == 0:
            fotnoter.append("f_zero_no_detection")

        observasjoner.append(
            _observasjon(
                kode,
                land,
                aar,
                INDIKATOR,
                ENHET,
                verdi,
                k2_gwis.SOURCE_ID,
                k2_gwis.SERIES_ID,
                "measured",
                fotnoter,
            )
        )

    if ukjente:
        raise ValueError(
            "Entiteter uten oppføring i data/geo/land_no.json: "
            + ", ".join(f"{navn} ({kode})" for navn, kode in sorted(ukjente))
        )

    observasjoner.sort(key=lambda o: (o["entity"], o["period"]))
    return observasjoner


def fra_k3(areal, antall, info):
    """Gjør EFFIS' nasjonalt rapporterte landtotaler om til observasjoner.

    Kilden leverer hektar, som konverteres til km² her. Branntallet har ingen
    enhet å konvertere.

    Tallene er rapportert inn av landene selv, etter deres egne definisjoner,
    derfor f_reporting_basis. Serien begynner i 1980 med fem land, og flere
    kommer til utover i serien, derfor f_coverage_change.

    En tom celle i regnearket betyr at landet ikke rapporterte det året. Den
    er allerede utelatt i kildemodulen, og skal aldri bli en 0 her.
    """
    land = _land()
    ufullstendig_aar = int(info["downloaded_at"][:4])
    grunnfotnoter = ["f_reporting_basis", "f_coverage_change"]

    observasjoner = []
    ukjente = set()

    def legg_til(rader, indikator, enhet, serie, omregn):
        for rad in rader:
            kode = k3_effis.entity_kode(rad["code"])
            if kode not in land:
                ukjente.add((rad["code"], kode))
                continue

            aar = rad["year"]
            fotnoter = list(grunnfotnoter)
            if aar >= ufullstendig_aar:
                fotnoter.append("f_incomplete_year")

            observasjoner.append(
                _observasjon(
                    kode,
                    land,
                    aar,
                    indikator,
                    enhet,
                    omregn(rad["value"]),
                    k3_effis.SOURCE_ID,
                    serie,
                    k3_effis.KVALITET,
                    fotnoter,
                )
            )

    legg_til(
        areal,
        INDIKATOR,
        ENHET,
        k3_effis.SERIES_BURNED_AREA,
        lambda v: round(v * HA_TO_KM2, DESIMALER),
    )
    legg_til(
        antall,
        INDIKATOR_ANTALL,
        ENHET_ANTALL,
        k3_effis.SERIES_FIRE_COUNT,
        lambda v: int(round(v)),
    )

    if ukjente:
        raise ValueError(
            "Kolonner uten oppføring i data/geo/land_no.json: "
            + ", ".join(f"{kilde} → {vaar}" for kilde, vaar in sorted(ukjente))
        )

    observasjoner.sort(key=lambda o: (o["series_id"], o["entity"], o["period"]))
    return observasjoner


def fra_k4(rader, info):
    """Gjør EFFIS' satellittkartlegging om til kanoniske observasjoner.

    Kilden leverer hektar, som konverteres til km² her.

    Fotnotene følger av hva produktet er: sensorene har skiftet (MODIS, VIIRS,
    Sentinel-2), de minste brannene kom først med fra 2018, antallet land har
    økt over tid, og kartleggingen er en hurtigvurdering som revideres når
    bedre bilder foreligger.

    f_reporting_basis settes aldri her. Tallene er ikke rapportert av noen.
    """
    land = _land()
    ufullstendig_aar = int(info["downloaded_at"][:4])
    grunnfotnoter = [
        "f_sensor_break",
        "f_min_fire_size",
        "f_coverage_change",
        "f_product_level",
    ]

    observasjoner = []
    ukjente = set()

    for rad in rader:
        kode = k4_effis.entity_kode(rad["iso3"])
        if kode not in land:
            ukjente.add((rad["name"], rad["iso3"]))
            continue

        aar = rad["year"]
        verdi = round(rad["ba_ha"] * HA_TO_KM2, DESIMALER)

        fotnoter = list(grunnfotnoter)
        if aar >= ufullstendig_aar:
            fotnoter.append("f_incomplete_year")
        if verdi == 0:
            fotnoter.append("f_zero_no_detection")

        observasjoner.append(
            _observasjon(
                kode,
                land,
                aar,
                INDIKATOR,
                ENHET,
                verdi,
                k4_effis.SOURCE_ID,
                k4_effis.SERIES_ID,
                k4_effis.KVALITET,
                fotnoter,
            )
        )

    if ukjente:
        raise ValueError(
            "Entiteter uten oppføring i data/geo/land_no.json: "
            + ", ".join(f"{navn} ({kode})" for navn, kode in sorted(ukjente))
        )

    observasjoner.sort(key=lambda o: (o["entity"], o["period"]))
    return observasjoner


def fra_k5(rader, info):
    """Gjør NIFC-rader om til kanoniske observasjoner.

    Kilden leverer acres og antall branner. Acres konverteres til km² her.

    Kilden er nasjonalt rapportert og følger amerikanske definisjoner, og den
    starter i 1983 fordi de føderale brannmyndighetene ikke førte offisielle
    tall etter dagens rapporteringsprosesser før det. Begge deler gjelder hele
    serien.
    """
    land = _land()
    ufullstendig_aar = int(info["downloaded_at"][:4])
    grunnfotnoter = ["f_reporting_basis", "f_record_start"]

    observasjoner = []
    for rad in rader:
        aar = rad["year"]
        fotnoter = list(grunnfotnoter)
        if aar >= ufullstendig_aar:
            fotnoter.append("f_incomplete_year")
        # Kilden merker 2004 med at delstatsarealer for North Carolina mangler.
        if rad["marked"]:
            fotnoter.append("f_incomplete_inventory")

        observasjoner.append(
            _observasjon(
                k5_nifc.ENTITY,
                land,
                aar,
                INDIKATOR,
                ENHET,
                round(rad["acres"] * ACRE_TO_KM2, DESIMALER),
                k5_nifc.SOURCE_ID,
                k5_nifc.SERIES_BURNED_AREA,
                "reported",
                fotnoter,
            )
        )
        observasjoner.append(
            _observasjon(
                k5_nifc.ENTITY,
                land,
                aar,
                INDIKATOR_ANTALL,
                ENHET_ANTALL,
                rad["fires"],
                k5_nifc.SOURCE_ID,
                k5_nifc.SERIES_FIRE_COUNT,
                "reported",
                list(fotnoter),
            )
        )

    observasjoner.sort(key=lambda o: (o["series_id"], o["period"]))
    return observasjoner


def fra_k7(areal, branner, info):
    """Gjør NBAC- og CNFDB-rader om til kanoniske observasjoner.

    NBAC oppgir justerte hektar, som konverteres til km² her. Antall branner
    kommer fra CNFDBs punktdata og har ingen enhet å konvertere.

    De to seriene har hver sin dekningsperiode: NBAC starter i 1972, CNFDBs
    punktdata tidligere. De skjøtes ikke sammen — hver serie beholder sin egen.
    """
    land = _land()
    ufullstendig_aar = int(info["downloaded_at"][:4])
    # Kilden opplyser selv at databasen verken er komplett eller feilfri, og at
    # kvaliteten varierer mellom rapporterende byråer og mellom år.
    grunnfotnoter = ["f_reporting_basis", "f_incomplete_inventory"]

    def fotnoter_for(aar):
        fotnoter = list(grunnfotnoter)
        if aar >= ufullstendig_aar:
            fotnoter.append("f_incomplete_year")
        return fotnoter

    observasjoner = []
    for rad in areal:
        observasjoner.append(
            _observasjon(
                k7_nbac.ENTITY,
                land,
                rad["year"],
                INDIKATOR,
                ENHET,
                round(rad["adjusted_ha"] * HA_TO_KM2, DESIMALER),
                k7_nbac.SOURCE_ID,
                k7_nbac.SERIES_BURNED_AREA,
                "reported",
                fotnoter_for(rad["year"]),
            )
        )
    for rad in branner:
        observasjoner.append(
            _observasjon(
                k7_nbac.ENTITY,
                land,
                rad["year"],
                INDIKATOR_ANTALL,
                ENHET_ANTALL,
                rad["fires"],
                k7_nbac.SOURCE_ID,
                k7_nbac.SERIES_FIRE_COUNT,
                "reported",
                fotnoter_for(rad["year"]),
            )
        )

    observasjoner.sort(key=lambda o: (o["series_id"], o["period"]))
    return observasjoner


def _landarealer():
    with open(LAND_AREA_JSON, encoding="utf-8") as f:
        return json.load(f)["areas"]


def andel_av_landareal(observasjoner, serie_id):
    """Beregner brent areal som andel av landareal, med nevner fra K6.

    Gjør små og store land sammenlignbare. Andelen får egen serie-id, slik at
    dekning og trend regnes per indikator og ikke blandes med arealet.

    Kilden er den samme som telleren — K6 leverer bare nevneren, og står derfor
    ikke i kildekolonnen i § 8.

    Entiteter uten landareal hos K6 får ingen andel. Det gjelder blant annet
    regionene og verden, som er aggregater uten polygon, og de territoriene
    Natural Earth fører sammen med moderlandet. En manglende nevner skal gi
    «ingen data», aldri en beregnet verdi.
    """
    arealer = _landarealer()

    observasjoner_andel = []
    for o in observasjoner:
        if o["indicator"] != INDIKATOR:
            continue
        areal = arealer.get(o["entity"])
        if not areal:
            continue
        observasjoner_andel.append(
            dict(
                o,
                indicator=INDIKATOR_ANDEL,
                unit=ENHET_ANDEL,
                value=round(o["value"] / areal, DESIMALER_ANDEL),
                series_id=serie_id,
                footnotes=list(o["footnotes"]),
            )
        )

    observasjoner_andel.sort(key=lambda o: (o["entity"], o["period"]))
    return observasjoner_andel


def skriv(observasjoner, navn):
    """Skriver observasjonene som JSON og CSV under data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sti_json = PROCESSED_DIR / f"{navn}.json"
    sti_csv = PROCESSED_DIR / f"{navn}.csv"

    with open(sti_json, "w", encoding="utf-8") as f:
        json.dump(observasjoner, f, ensure_ascii=False, indent=1)
        f.write("\n")

    with open(sti_csv, "w", encoding="utf-8", newline="") as f:
        skriver = csv.DictWriter(f, fieldnames=FELT)
        skriver.writeheader()
        for o in observasjoner:
            rad = dict(o)
            rad["footnotes"] = ";".join(o["footnotes"])
            skriver.writerow(rad)

    return sti_json, sti_csv


def skriv_per_indikator(observasjoner):
    """Skriver én fil per indikator, og returnerer filnavnene per indikator.

    Filnavnene står i schema.PROCESSED_FILE. Observasjonene sorteres innenfor
    hver fil, slik at samme input alltid gir samme fil (T3).
    """
    filer = {}
    per_indikator = defaultdict(list)
    for o in observasjoner:
        per_indikator[o["indicator"]].append(o)

    for indikator, gruppe in sorted(per_indikator.items()):
        gruppe.sort(key=lambda o: (o["series_id"], o["entity"], o["period"]))
        sti_json, sti_csv = skriv(gruppe, PROCESSED_FILE[indikator])
        filer[indikator] = [sti_json.name, sti_csv.name]
    return filer


def main():
    rader, metadata, info = k1_owid.hent()
    observasjoner = fra_k1(rader, info)
    filer = skriv_per_indikator(observasjoner)
    print(f"normalize: {len(observasjoner)} observasjoner → {filer}")
    return observasjoner, metadata, info


if __name__ == "__main__":
    main()
