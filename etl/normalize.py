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
    M2_TO_KM2,
    PROCESSED_DIR,
    PROCESSED_FILE,
)
from etl.sources import (
    k1_owid,
    k2_gwis,
    k3_effis,
    k4_effis,
    k5_nifc,
    k7_nbac,
    k8_firecci,
    k9_gfed5,
    k10_gcd,
)

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

# Antall desimaler i km²-verdiene. To desimaler er 1 hektar, som er finere enn
# noen av kildene måler, og holder derfor på all informasjon i dem uten å legge
# til flyttallsstøy.
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

    # Gjelder hele serien: MODIS/VIIRS-overgangen, at de minste brannene ikke
    # fanges opp, og at nivået avhenger av produktet. Se data/_sources.json for
    # kildens egen ordlyd.
    grunnfotnoter = ["f_sensor_break", "f_min_fire_size", "f_product_level"]

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


def fra_rutenett(
    per_entitet,
    verden,
    info,
    kilde,
    serie,
    kvalitet,
    faktor,
    grunnfotnoter,
    per_aar=None,
):
    """Gjør aggregerte rutenettsummer om til kanoniske observasjoner.

    Felles vei for rutenettkildene. ``per_entitet`` er {entity: {år: verdi}} og
    ``verden`` er {år: verdi}, begge i kildens egen enhet; ``faktor`` gjør dem
    om til km².

    ``per_aar(aar)`` gir (fotnoter, for_smaa, uobservert) for ett år. Alt som
    kan endre seg innenfor en serie — oppløsning, og dermed både terskelen for
    ``f_grid_resolution`` og hvilke entiteter rutenettet i det hele tatt
    treffer — avgjøres der, ikke én gang for hele serien.

    Verdenstallet summeres fra rutenettet og ikke fra landene, slik at cellene
    ingen landgeometri dekker, fortsatt teller globalt. Se ``etl/grid.py``.
    """
    land = _land()

    aar = sorted(verden)
    if not aar:
        raise ValueError(f"{kilde}: ingen år å normalisere")

    if per_aar is None:
        def per_aar(_):
            return [], set(), set()

    hull = [a for a in range(aar[0], aar[-1] + 1) if a not in verden]
    felles = list(grunnfotnoter)
    if hull:
        # Mangler et år helt i kilden, gjelder det hele serien: figuren skal
        # vise bruddet, ikke en 0 og ikke en beregnet mellomverdi (§ 9).
        felles.append("f_missing_year")

    # Koder kilden fører, men som ikke står i land_no.json. Er de null hele
    # veien, har kilden ingen tall for entiteten og den utelates. Kommer det en
    # verdi, skal koden tas inn — se CLAUDE.md § 5.
    ukjente = {
        kode: max(aarlig.values())
        for kode, aarlig in per_entitet.items()
        if kode not in land and any(v > 0 for v in aarlig.values())
    }
    if ukjente:
        raise ValueError(
            f"{kilde} har verdier for entiteter uten oppføring i "
            "data/geo/land_no.json: "
            + ", ".join(f"{k} ({v:.0f})" for k, v in sorted(ukjente.items()))
            + ". Se CLAUDE.md § 5 — koden må tas inn før tallene kan publiseres."
        )

    observasjoner = []
    utelatt = set()
    for a in aar:
        aars_fotnoter, for_smaa, uobservert = per_aar(a)
        fotnoter = felles + list(aars_fotnoter)

        # Rutenettet treffer ikke geometrien til disse entitetene dette året,
        # så summen er 0 fordi ingenting er målt. De utelates framfor å
        # publiseres som en målt null (CLAUDE.md § 9).
        med_verdi = {
            kode: per_entitet[kode][a]
            for kode in uobservert
            if per_entitet.get(kode, {}).get(a, 0.0) > 0
        }
        if med_verdi:
            raise ValueError(
                f"{kilde}: entiteter uten treff i rutenettet har likevel en "
                f"verdi i {a}: "
                + ", ".join(f"{k} ({v:.0f})" for k, v in sorted(med_verdi.items()))
                + ". Da er de observert, og regelen i § 9 gjelder ikke for dem."
            )
        utelatt |= set(uobservert) & set(land)

        for kode in sorted(per_entitet):
            if kode not in land or kode in uobservert or a not in per_entitet[kode]:
                continue
            egne = list(fotnoter)
            if kode in for_smaa:
                egne.append("f_grid_resolution")
            observasjoner.append(
                _rutenett_observasjon(
                    kode, a, per_entitet[kode][a], land, egne,
                    kilde, serie, kvalitet, faktor,
                )
            )
        observasjoner.append(
            _rutenett_observasjon(
                "WLD", a, verden[a], land, fotnoter,
                kilde, serie, kvalitet, faktor,
            )
        )

    info["aar_mangler"] = hull
    info["utelatte_entiteter"] = sorted(utelatt)
    # Land uten geometri i K6 kom aldri inn i masken, og mangler av en annen
    # grunn enn de uobserverte: rutenettet har ikke bommet på geometrien, det
    # finnes ingen geometri å bomme på. Regioner og verdenskoden holdes utenfor
    # — K6 leverer ikke geometri for dem, og verdenstallet kommer fra
    # rutenettet. Settet beregnes her, ved kjøring (§ 7, T5).
    med_geometri = info.get("med_geometri")
    info["uten_geometri"] = (
        sorted(
            kode
            for kode, oppslag in land.items()
            if oppslag["level"] == "country" and kode not in med_geometri
        )
        if med_geometri is not None
        else []
    )
    info["footnotes"] = sorted({f for o in observasjoner for f in o["footnotes"]})
    info["rows"] = len(observasjoner)

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


def _rutenett_observasjon(kode, aar, raa, land, fotnoter, kilde, serie, kvalitet, faktor):
    verdi = round(raa * faktor, DESIMALER)

    # Kilden har ikke påvist brent areal, men skiller ikke mellom «ingenting
    # brant» og «ingen måling». Nullene merkes derfor eksplisitt, på samme måte
    # som for K1. Merkingen er også det trendreglene i § 7 kjenner nullene sine
    # på — se CLAUDE.md § 9.
    if verdi == 0:
        fotnoter = fotnoter + ["f_zero_no_detection"]

    return {
        "entity": kode,
        "entity_name": land[kode]["entity_name"],
        "level": land[kode]["level"],
        "period": str(aar),
        "indicator": INDIKATOR,
        "value": verdi,
        "unit": ENHET,
        "source_id": kilde,
        "series_id": serie,
        "quality": kvalitet,
        "footnotes": list(fotnoter),
    }


def fra_k8(per_entitet, verden, info, for_smaa=(), uobservert=(), med_geometri=None):
    """K8 — FireCCILT11. Ett rutenett for hele serien, m² inn.

    Produsenten merker selv datasettet som foreløpig, og AVHRR-serien går over
    flere satellitter.
    """
    if med_geometri is not None:
        info["med_geometri"] = set(med_geometri)
    return fra_rutenett(
        per_entitet,
        verden,
        info,
        kilde=k8_firecci.SOURCE_ID,
        serie=k8_firecci.SERIES_ID,
        kvalitet="beta",
        faktor=M2_TO_KM2,
        grunnfotnoter=["f_beta_product", "f_sensor_break", "f_product_level"],
        per_aar=lambda _: ([], set(for_smaa), set(uobservert)),
    )


def fra_k9(per_entitet, verden, info, per_aar, med_geometri=None):
    """K9 — GFED5. Kilden oppgir km², så faktoren er 1.

    Oppløsningen skifter innenfor serien, og ``per_aar`` gir derfor både
    fotnoter og terskelsett per år.
    """
    if med_geometri is not None:
        info["med_geometri"] = set(med_geometri)
    return fra_rutenett(
        per_entitet,
        verden,
        info,
        kilde=k9_gfed5.SOURCE_ID,
        serie=k9_gfed5.SERIES_ID,
        kvalitet="measured",
        faktor=1.0,
        grunnfotnoter=["f_product_level"],
        per_aar=per_aar,
    )


def fra_k10(rader, info):
    """K10 — kompositten av sedimentært kull.

    Verdien er en z-score uten enhet, og skal aldri regnes om eller tegnes i
    samme figur som et areal (CLAUDE.md § 6). Serien er global og har ingen
    landnivå.
    """
    land = _land()

    # Kurven er både et indirekte mål og et glidende gjennomsnitt. Vindusbredden
    # står i fotnoteteksten, fordi den avgjør hvordan kurven skal leses.
    fotnoter = ["f_proxy", "f_smoothed", "f_thinning_record"]

    observasjoner = []
    for rad in rader:
        if rad["composite"] in ("", "NA", "NaN"):
            continue
        aar = k10_gcd.kalenderaar(rad["age_bp"])
        observasjoner.append(
            {
                "entity": "WLD",
                "entity_name": land["WLD"]["entity_name"],
                "level": land["WLD"]["level"],
                "period": str(aar),
                "indicator": "charcoal_index",
                "value": round(float(rad["composite"]), 4),
                "unit": "zscore",
                "source_id": k10_gcd.SOURCE_ID,
                "series_id": k10_gcd.SERIES_ID,
                "quality": "reconstructed",
                "footnotes": list(fotnoter),
                # Hvor mange kullserier som bidrar i punktet. Tallet avgjør
                # hvor langt tilbake kurven kan vises, og må kunne leses uten
                # å kjøre kilden på nytt (CLAUDE.md § 6).
                "n_series": int(float(rad["n_sites"])),
            }
        )

    if not observasjoner:
        raise ValueError("K10: kompositten ga ingen brukbare verdier")

    # En kompositt der alle punktene er like, er ikke en kurve. Den passerer
    # validate.py, som ser på kodeverdier og ikke på om tallene betyr noe, og
    # ville blitt publisert som om den var et resultat.
    if len({o["value"] for o in observasjoner}) < 2:
        raise ValueError(
            f"K10: alle {len(observasjoner)} punktene har samme verdi "
            f"({observasjoner[0]['value']}). Kompositten er flat, og det er "
            "ikke et resultat — se etter en kolonne av feil lengde i "
            "R-utdataene."
        )

    aar = [int(o["period"]) for o in observasjoner]
    serier = [o["n_series"] for o in observasjoner]
    info["aar_forste"] = min(aar)
    info["aar_siste"] = max(aar)
    info["n_series_min"] = min(serier)
    info["n_series_max"] = max(serier)
    info["footnotes"] = fotnoter
    info["rows"] = len(observasjoner)

    observasjoner.sort(key=lambda o: int(o["period"]))
    return observasjoner


def _kolonner(observasjoner):
    """FELT, pluss de valgfrie feltene observasjonene faktisk har.

    Et valgfritt felt skal bare gi en kolonne i de filene som bruker det, ikke
    en tom kolonne i alle de andre.
    """
    ekstra = sorted({k for o in observasjoner for k in o} - set(FELT))
    return FELT + ekstra


def skriv(observasjoner, navn):
    """Skriver observasjonene som JSON og CSV under data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sti_json = PROCESSED_DIR / f"{navn}.json"
    sti_csv = PROCESSED_DIR / f"{navn}.csv"

    with open(sti_json, "w", encoding="utf-8") as f:
        json.dump(observasjoner, f, ensure_ascii=False, indent=1)
        f.write("\n")

    with open(sti_csv, "w", encoding="utf-8", newline="") as f:
        skriver = csv.DictWriter(f, fieldnames=_kolonner(observasjoner))
        skriver.writeheader()
        for o in observasjoner:
            rad = dict(o)
            rad["footnotes"] = ";".join(o["footnotes"])
            skriver.writerow(rad)

    return sti_json, sti_csv


def skriv_per_fil(observasjoner):
    """Skriver observasjonene til filene serien deres hører hjemme i.

    Hvilken fil en serie havner i, står i schema.PROCESSED_FILE — flere serier
    kan dele fil. Observasjonene sorteres innenfor hver fil, slik at samme
    input alltid gir samme fil (T3).

    Returnerer filnavnene per series_id.
    """
    per_fil = defaultdict(list)
    for o in observasjoner:
        per_fil[_filnavn(o["series_id"])].append(o)

    navn_per_serie = {}
    for navn, gruppe in sorted(per_fil.items()):
        gruppe.sort(key=lambda o: (o["series_id"], o["entity"], o["period"]))
        sti_json, sti_csv = skriv(gruppe, navn)
        for o in gruppe:
            navn_per_serie[o["series_id"]] = [sti_json.name, sti_csv.name]
    return navn_per_serie


def _filnavn(series_id):
    """Filnavnet serien skrives til, fra schema.PROCESSED_FILE."""
    navn = PROCESSED_FILE[series_id]
    if navn is None:
        raise KeyError(
            f"serien {series_id!r} har ingen fil i PROCESSED_FILE og skal ikke "
            "publiseres"
        )
    return navn


def main():
    rader, metadata, info = k1_owid.hent()
    observasjoner = fra_k1(rader, info)
    filer = skriv_per_fil(observasjoner)
    print(f"normalize: {len(observasjoner)} observasjoner → {filer}")
    return observasjoner, metadata, info


if __name__ == "__main__":
    main()
