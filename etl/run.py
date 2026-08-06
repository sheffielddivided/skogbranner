"""Kjører hele pipelinen: hent → normaliser → valider → publiser.

Rekkefølgen står i CLAUDE.md § 4.

**Én kilde som feiler, tar ikke ned de andre.** Hver kilde hentes for seg. Går
den i stykker, logges feilen i ``data/_status.json``, og kildens forrige
observasjoner leses tilbake fra ``data/processed/`` og blir stående. Uten det
ville en feilet kilde stille forsvunnet ut av datasettet neste gang en annen
kilde ble oppdatert — som er verre enn å vise gamle tall med en merknad om at
de er gamle.

Kjøres som modul fra repotoppen: ``python -m etl.run``
"""

import json
import traceback

from etl import derive, normalize, validate
from etl.schema import RAW_DIR, SOURCES_JSON
from etl.sources import (
    k1_owid,
    k2_gwis,
    k3_effis,
    k4_effis,
    k5_nifc,
    k6_natural_earth,
    k7_nbac,
)

# Avviksrapporten fra kryssjekken mellom K1 og K2. Den er et arbeidsverktøy for
# redaktøren og publiseres ikke, så den legges under data/raw/, som er
# gitignorert. Se CLAUDE.md § 5.
AVVIKSRAPPORT = RAW_DIR / "kryssjekk_k1_k2.md"


def _forrige(publisert, source_id):
    """Plukker ut en kildes forrige observasjoner fra det som lå der før."""
    return [o for o in publisert if o["source_id"] == source_id]


def hent_k1():
    rader, metadata, info = k1_owid.hent()
    observasjoner = normalize.fra_k1(rader, info)
    observasjoner += normalize.andel_av_landareal(
        observasjoner, "owid_annual_area_burnt_share_land"
    )
    k1_owid.skriv_metadata(metadata, info, [])
    return observasjoner, info


def hent_k3():
    areal, antall, info = k3_effis.hent()
    k3_effis.skriv_metadata(info, [])
    return normalize.fra_k3(areal, antall, info), info


def hent_k4():
    rader, info = k4_effis.hent()
    k4_effis.skriv_metadata(info, [])
    return normalize.fra_k4(rader, info), info


def hent_k5():
    rader, info = k5_nifc.hent()
    k5_nifc.skriv_metadata(info, [])
    return normalize.fra_k5(rader, info), info


def hent_k7():
    areal, branner, info = k7_nbac.hent()
    k7_nbac.skriv_metadata(info, [])
    return normalize.fra_k7(areal, branner, info), info


# Kildene som leverer observasjoner, i den rekkefølgen de kjøres. Listen står
# her og ikke i workflowen, slik at kildeoversikten ikke får en kopi til (T5).
KILDER = [
    (k1_owid, hent_k1),
    (k3_effis, hent_k3),
    (k4_effis, hent_k4),
    (k5_nifc, hent_k5),
    (k7_nbac, hent_k7),
]


def landarealer():
    """Kjører K6, som gir landarealene til andelsindikatoren.

    Kjøres først, fordi normalize.andel_av_landareal leser resultatet. Feiler
    den, beholdes forrige data/geo/land_area_km2.json, og andelene regnes mot
    den — gamle landarealer er langt bedre enn ingen.

    Samme geometri som rutenettkildene fordeles på, slik at nevneren og
    rasteriseringen er enige om hvor landegrensene går.
    """
    try:
        sti, info = k6_natural_earth.hent()
        geo, uten_kode = k6_natural_earth.geometrier(sti)
        arealer, utelatt = k6_natural_earth.landarealer(geo)
        k6_natural_earth.skriv_arealer(arealer, utelatt, info)
        k6_natural_earth.skriv_metadata(info)
        print(
            f"K6: {len(arealer)} entiteter med landareal, "
            f"{len(utelatt)} koder utenfor land_no.json, "
            f"{len(uten_kode)} områder uten kode"
        )
        return True
    except Exception as e:
        print(f"K6 FEILET: {type(e).__name__}: {e} — forrige landarealer beholdes")
        return False


def kryssjekk_k1_k2(k1_observasjoner):
    """Kryssjekker K1 mot K2 og skriver avviksrapporten.

    Feiler K2, er det ikke en grunn til å stoppe publiseringen. Kryssjekken er
    en kontroll av K1, ikke en kilde siden viser.
    """
    try:
        rader, info = k2_gwis.hent()
        k2_observasjoner = normalize.fra_k2(rader, info)
        avvik, sammenlignet = validate.kryssjekk(k1_observasjoner, k2_observasjoner)

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        AVVIKSRAPPORT.write_text(
            validate.avviksrapport(avvik, sammenlignet), encoding="utf-8"
        )

        k2_gwis.skriv_metadata(info)
        k2_gwis.skriv_status(
            "ok", f"{len(avvik)} avvik av {sammenlignet} sammenlignede", info
        )
        print(
            f"K2: kryssjekket {sammenlignet} observasjoner mot K1, "
            f"{len(avvik)} over terskelen → {AVVIKSRAPPORT.name}"
        )
    except Exception as e:
        k2_gwis.skriv_status("failed", f"{type(e).__name__}: {e}")
        print(f"K2 FEILET: {type(e).__name__}: {e} — kryssjekken er ikke kjørt")


def main():
    landarealer()

    # Leses før noe skrives, slik at en kilde som feiler kan få tilbake sine
    # egne rader fra forrige kjøring.
    publisert = validate.les_publiserte()

    observasjoner = []
    feilede = []

    for modul, hent in KILDER:
        try:
            nye, info = hent()
            modul.skriv_status("ok", "hentet og normalisert", info)
            observasjoner += nye
            print(f"{modul.SOURCE_ID}: {len(nye)} observasjoner")
        except Exception as e:
            beholdt = _forrige(publisert, modul.SOURCE_ID)
            modul.skriv_status(
                "failed",
                f"{type(e).__name__}: {e} — {len(beholdt)} observasjoner beholdt",
            )
            observasjoner += beholdt
            feilede.append(modul.SOURCE_ID)
            print(
                f"{modul.SOURCE_ID} FEILET: {type(e).__name__}: {e} — "
                f"{len(beholdt)} observasjoner beholdt fra forrige kjøring"
            )
            # Statusmeldingen sier hva som gikk galt, men ikke hvor. Uten
            # sporet må feilen gjettes fra utsiden, og en kjøring tar minutter.
            traceback.print_exc()

    feil = validate.valider(observasjoner)
    if feil:
        for melding in feil:
            print("FEIL:", melding)
        raise validate.Valideringsfeil(f"{len(feil)} feil — ingenting publisert")

    filer = normalize.skriv_per_fil(observasjoner)
    _oppdater_filliste(filer)

    kryssjekk_k1_k2([o for o in observasjoner if o["source_id"] == k1_owid.SOURCE_ID])

    # Avledningene regnes til slutt, av de ferdige filene, og committes som
    # dem (§ 4). Brødteksten på siden henter tallene sine herfra (P3).
    derive.main()

    print(f"validate: {len(observasjoner)} observasjoner OK")
    for serie, navn in sorted(filer.items()):
        print(f"skrevet:   {serie} → {', '.join(navn)}")

    if feilede:
        raise RuntimeError(
            "kilder som feilet: " + ", ".join(feilede) + " — forrige data beholdt"
        )
    return observasjoner


def _oppdater_filliste(filer):
    """Fører opp hvilke filer hver kilde havnet i, i data/_sources.json.

    Gjøres til slutt, fordi en kilde ikke vet hvilke filer den deler med de
    andre før alle er normalisert. Kildelinjen under en figur skal peke på den
    filen figuren faktisk bruker (P5).
    """
    with open(SOURCES_JSON, encoding="utf-8") as f:
        sources = json.load(f)

    per_kilde = {}
    for o in validate.les_publiserte():
        per_kilde.setdefault(o["source_id"], set()).update(filer.get(o["series_id"], []))

    for source_id, navn in per_kilde.items():
        if source_id in sources["sources"]:
            sources["sources"][source_id]["processed_files"] = sorted(navn)

    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
