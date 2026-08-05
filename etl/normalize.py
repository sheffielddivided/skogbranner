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
from etl.sources import k1_owid, k8_firecci

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


def fra_k8(per_entitet, verden, info, for_smaa=(), uobservert=()):
    """Gjør aggregerte K8-summer om til kanoniske observasjoner.

    ``per_entitet`` er {entity-kode: {år: m²}} slik ``etl/grid.py`` summerte
    rutenettet, og ``verden`` er {år: m²} summert fra rutenettet selv. Kilden
    leverer m², og konverteringen til km² skjer her.

    ``for_smaa`` er entitetene som er små i forhold til rutenettets oppløsning.
    De får ``f_grid_resolution``.

    ``uobservert`` er entitetene rutenettet ikke treffer i det hele tatt. De
    utelates — se CLAUDE.md § 9.

    Verdenstallet summeres fra rutenettet og ikke fra landene, slik at de
    cellene ingen landgeometri dekker, fortsatt teller globalt. Se
    ``etl/grid.py``.
    """
    land = _land()

    aar = sorted(verden)
    if not aar:
        raise ValueError("K8: ingen år å normalisere")

    # Serien er avsluttet, så fotnotene følger av dataene og ikke av datoen i
    # dag. Mangler et år helt i kilden, gjelder det hele serien: figuren skal
    # vise bruddet, ikke en 0 og ikke en beregnet mellomverdi (CLAUDE.md § 9).
    fotnoter = ["f_beta_product", "f_sensor_break"]
    hull = [a for a in range(aar[0], aar[-1] + 1) if a not in verden]
    if hull:
        fotnoter.append("f_missing_year")

    # Koder kilden fører, men som ikke står i land_no.json. Er de null hele
    # veien, har kilden ingen tall for entiteten og den utelates. Kommer det en
    # verdi, skal koden tas inn — se CLAUDE.md § 5.
    ukjente = {}
    for kode, aarlig in per_entitet.items():
        if kode not in land and any(v > 0 for v in aarlig.values()):
            ukjente[kode] = max(aarlig.values())
    if ukjente:
        raise ValueError(
            "K8 har verdier for entiteter uten oppføring i "
            "data/geo/land_no.json: "
            + ", ".join(f"{k} ({v:.0f} m²)" for k, v in sorted(ukjente.items()))
            + ". Se CLAUDE.md § 5 — koden må tas inn før tallene kan publiseres."
        )

    # Rutenettet treffer ikke geometrien til disse entitetene, så summen deres
    # er 0 fordi ingenting er målt, ikke fordi ingenting brant. De utelates
    # framfor å publiseres som en målt null (CLAUDE.md § 9).
    med_verdi = {
        kode: maks
        for kode in uobservert
        if (maks := max(per_entitet.get(kode, {0: 0.0}).values())) > 0
    }
    if med_verdi:
        raise ValueError(
            "K8: entiteter uten treff i rutenettet har likevel en verdi: "
            + ", ".join(f"{k} ({v:.0f} m²)" for k, v in sorted(med_verdi.items()))
            + ". Da er de observert, og regelen i § 9 gjelder ikke for dem."
        )

    observasjoner = []
    for kode in sorted(per_entitet):
        if kode not in land or kode in uobservert:
            continue
        # Entiteten er mindre enn én rute, så tallet er en andel av ruter den
        # deler med naboland eller hav. Gjelder alle årene for entiteten.
        egne = list(fotnoter)
        if kode in for_smaa:
            egne.append("f_grid_resolution")
        for a in sorted(per_entitet[kode]):
            observasjoner.append(
                _k8_observasjon(kode, a, per_entitet[kode][a], land, egne)
            )

    for a in aar:
        observasjoner.append(_k8_observasjon("WLD", a, verden[a], land, fotnoter))

    info["aar_mangler"] = hull
    info["utelatte_entiteter"] = sorted(set(uobservert) & set(land))
    info["footnotes"] = sorted({f for o in observasjoner for f in o["footnotes"]})
    info["rows"] = len(observasjoner)

    observasjoner.sort(key=lambda o: (o["entity"], o["period"]))
    return observasjoner


def _k8_observasjon(kode, aar, m2, land, fotnoter):
    verdi = round(m2 * M2_TO_KM2, DESIMALER)

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
        "source_id": k8_firecci.SOURCE_ID,
        "series_id": k8_firecci.SERIES_ID,
        "quality": "beta",
        "footnotes": list(fotnoter),
    }


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
