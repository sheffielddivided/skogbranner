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

from etl.schema import HA_TO_KM2, LAND_NO_JSON, M2_TO_KM2, PROCESSED_DIR
from etl.sources import k1_owid, k8_firecci, k9_gfed5, k10_gcd

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


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


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
            {
                "entity": kode,
                "entity_name": land[kode]["entity_name"],
                "level": land[kode]["level"],
                "period": str(aar),
                "indicator": INDIKATOR,
                "value": verdi,
                "unit": ENHET,
                "source_id": k1_owid.SOURCE_ID,
                "series_id": k1_owid.SERIES_ID,
                "quality": "measured",
                "footnotes": fotnoter,
            }
        )

    if ukjente:
        raise ValueError(
            "Entiteter uten oppføring i data/geo/land_no.json: "
            + ", ".join(f"{navn} ({kode or 'ingen kode'})" for navn, kode in sorted(ukjente))
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
    fotnoter = ["f_proxy"]

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
            }
        )

    if not observasjoner:
        raise ValueError("K10: kompositten ga ingen brukbare verdier")

    aar = [int(o["period"]) for o in observasjoner]
    info["aar_forste"] = min(aar)
    info["aar_siste"] = max(aar)
    info["footnotes"] = fotnoter
    info["rows"] = len(observasjoner)

    observasjoner.sort(key=lambda o: int(o["period"]))
    return observasjoner


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


def main():
    rader, metadata, info = k1_owid.hent()
    observasjoner = fra_k1(rader, info)
    sti_json, sti_csv = skriv(observasjoner, "burned_area")
    print(f"normalize: {len(observasjoner)} observasjoner → {sti_json.name}, {sti_csv.name}")
    return observasjoner, metadata, info


if __name__ == "__main__":
    main()
