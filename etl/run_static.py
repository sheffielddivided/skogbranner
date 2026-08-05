"""Kjører de statiske kildene: hent → aggreger → normaliser → valider → publiser.

Egen inngang, ikke et flagg til ``etl/run.py``. De statiske kildene er
avsluttede utgivelser som ikke skal hentes på nytt hver måned, og skillet er
lagt i strukturen slik at den månedlige kjøringen ikke kan dra dem med seg
(CLAUDE.md § 5).

Jobben laster ned rutenettfiler i gigabyte-klassen og hører derfor hjemme i
GitHub Actions, ikke i en utviklingssesjon (T4). Se
``.github/workflows/etl-statisk.yml``. Hver fil slettes så snart den er
aggregert, og rådata committes aldri.

Kjøres som modul fra repotoppen:

    python -m etl.run_static --kilde k8
    python -m etl.run_static --kilde k8 --kun-katalog
"""

import argparse
import hashlib
import shutil
import time
import zipfile
from collections import defaultdict

from etl import normalize, validate
from etl.schema import GRID_MAX_UNATTRIBUTED_SHARE, GRID_MIN_ENTITY_CELLS
from etl.sources import k6_natural_earth, k8_firecci, k9_gfed5, k10_gcd

# Filnavnet under data/processed/ per kilde. Navnet følger serien, ikke
# kildekoden, slik at en lesbar nedlastingslenke peker på det figuren viser.
FILNAVN = {
    "k8": "burned_area_firecci_lt11",
    "k9": "burned_area_gfed5",
    "k10": "charcoal_composite_gcd",
}


class Kjorefeil(Exception):
    """Reises når kjøringen ikke kan fullføres, og datasettet ikke skal røres."""


def _rydd():
    """Fjerner rådata. De committes aldri (CLAUDE.md T4)."""
    shutil.rmtree(k8_firecci.RAW_K8_DIR, ignore_errors=True)
    shutil.rmtree(k9_gfed5.RAW_K9_DIR, ignore_errors=True)
    shutil.rmtree(k10_gcd.RAW_K10_DIR, ignore_errors=True)
    k6_natural_earth.RAW_ZIP.unlink(missing_ok=True)


def _geometri():
    """Henter K6 og skriver ut hva den dekker."""
    _, k6_info = k6_natural_earth.hent()
    geometrier, uten_kode = k6_natural_earth.geometrier()
    print(
        f"K6: {len(geometrier)} geometrier. "
        f"{len(uten_kode)} områder uten anerkjent tilhørighet holdes utenfor"
        + (f": {', '.join(sorted(uten_kode))}" if uten_kode else "")
    )
    return geometrier, k6_info


def _kontroller_uattribuert(andel, kilde):
    print(f"{kilde}: uten landtilknytning: {andel:.4%} av samlet brent areal")
    if andel > GRID_MAX_UNATTRIBUTED_SHARE:
        raise Kjorefeil(
            f"{kilde}: {andel:.2%} av arealet lot seg ikke tilskrive et land, "
            f"over grensen på {GRID_MAX_UNATTRIBUTED_SHARE:.2%} "
            "(GRID_MAX_UNATTRIBUTED_SHARE i etl/schema.py). Geometri og "
            "rutenett spriker — kontroller K6-nedlastingen før tallene brukes."
        )


def _skriv_ut_katalog(sammendrag):
    print(
        f"K8: {sammendrag['filer']} månedsfiler, "
        f"{sammendrag['bytes'] / 2**30:.2f} GiB "
        f"({sammendrag['bytes']} byte)"
    )
    print(
        f"K8: {sammendrag['aar_forste']}–{sammendrag['aar_siste']}, "
        f"{sammendrag['aar_antall']} år med data"
    )
    if sammendrag["aar_mangler"]:
        print(
            "K8: år uten filer i kilden: "
            + ", ".join(str(a) for a in sammendrag["aar_mangler"])
        )


def _kontroller_katalog(oppforinger):
    """Avviser en katalog med ufullstendige år før noe lastes ned."""
    maaneder = defaultdict(set)
    for o in oppforinger:
        maaneder[o["aar"]].add(o["maaned"])

    mangler = {a: sorted(set(range(1, 13)) - m) for a, m in maaneder.items()}
    mangler = {a: m for a, m in mangler.items() if m}
    if mangler:
        raise Kjorefeil(
            "K8: katalogen har år uten alle tolv månedsfiler: "
            + "; ".join(f"{a} mangler {m}" for a, m in sorted(mangler.items()))
            + ". Et halvt år kan ikke summeres til en årstotal."
        )


def kjor_k8(kun_katalog=False):
    oppforinger = k8_firecci.katalog()
    sammendrag = k8_firecci.katalogsammendrag(oppforinger)
    _skriv_ut_katalog(sammendrag)
    _kontroller_katalog(oppforinger)

    if kun_katalog:
        print("K8: --kun-katalog, ingenting lastes ned.")
        return None

    # Importeres først her, slik at --kun-katalog kan kjøres uten at
    # rasteriseringsavhengighetene er installert.
    from etl import grid

    print("K6: henter admin-0-geometrien …", flush=True)
    _, k6_info = k6_natural_earth.hent()
    geometrier, uten_kode = k6_natural_earth.geometrier()
    print(
        f"K6: {len(geometrier)} geometrier. "
        f"{len(uten_kode)} områder uten anerkjent tilhørighet holdes utenfor"
        + (f": {', '.join(sorted(uten_kode))}" if uten_kode else "")
    )

    maske = None
    for_smaa = set()
    uobservert = set()
    per_entitet = defaultdict(lambda: defaultdict(float))
    verden = defaultdict(float)
    uattribuert = defaultdict(float)
    start = time.monotonic()

    for nr, oppf in enumerate(oppforinger, start=1):
        sti = k8_firecci.hent_fil(oppf)
        try:
            lat, lon, verdier = k8_firecci.les_rutenett(sti)

            # Den første filen er både verifikasjon av at nedlastingen gir data
            # og grunnlaget for maskeen. Slår noe feil, skjer det her og ikke
            # etter 6,7 GiB.
            if maske is None:
                print(
                    f"K8: første fil åpnet, rutenett {lat.size}×{lon.size}. "
                    "Bygger maske …",
                    flush=True,
                )
                maske = grid.bygg_maske(lat, lon, geometrier)
                for_smaa = maske.for_smaa_entiteter(GRID_MIN_ENTITY_CELLS)
                uobservert = maske.uobserverte_entiteter()
                print(
                    f"K8: maske for {len(maske.koder)} entiteter. "
                    f"En rute er {maske.ruteareal_ekvator_km2:.0f} km² ved "
                    f"ekvator; {len(for_smaa)} entiteter har mindre landareal "
                    "enn det og får f_grid_resolution",
                    flush=True,
                )
                if uobservert:
                    print(
                        f"K8: {len(uobservert)} entiteter treffes ikke av "
                        "delrutenettet og utelates: "
                        + ", ".join(sorted(uobservert)),
                        flush=True,
                    )
            elif not maske.passer(lat, lon):
                raise Kjorefeil(
                    f"{oppf['navn']}: rutenettet er et annet enn i den første "
                    "filen. Maskeen gjelder ikke, og summene ville blitt feil."
                )

            sum_entitet, sum_uten_land, sum_total = maske.aggreger(verdier)
        finally:
            sti.unlink(missing_ok=True)

        for kode, verdi in sum_entitet.items():
            per_entitet[kode][oppf["aar"]] += verdi
        verden[oppf["aar"]] += sum_total
        uattribuert[oppf["aar"]] += sum_uten_land

        gaatt = time.monotonic() - start
        print(
            f"K8: {nr}/{len(oppforinger)} {oppf['navn']} "
            f"({sum_total * 1e-6:,.0f} km², {gaatt:.0f} s)",
            flush=True,
        )

    _rydd()

    total = sum(verden.values())
    uten_land = sum(uattribuert.values())
    andel = uten_land / total if total else 0.0
    print(f"K8: uten landtilknytning: {andel:.4%} av samlet brent areal")
    if andel > GRID_MAX_UNATTRIBUTED_SHARE:
        raise Kjorefeil(
            f"K8: {andel:.2%} av arealet lot seg ikke tilskrive et land, over "
            f"grensen på {GRID_MAX_UNATTRIBUTED_SHARE:.2%} "
            "(GRID_MAX_UNATTRIBUTED_SHARE i etl/schema.py). Geometri og "
            "rutenett spriker — kontroller K6-nedlastingen før tallene brukes."
        )

    info = dict(sammendrag)
    info["uattribuert_andel"] = andel
    info["uattribuert_km2"] = uten_land * 1e-6
    info["checksum"] = hashlib.sha256(
        "".join(o["md5"] or o["navn"] for o in oppforinger).encode("utf-8")
    ).hexdigest()
    info["k6_checksum"] = k6_info["checksum"]

    observasjoner = normalize.fra_k8(
        {k: dict(v) for k, v in per_entitet.items()},
        dict(verden),
        info,
        for_smaa=for_smaa,
        uobservert=uobservert,
        med_geometri=set(maske.koder),
    )

    feil = validate.valider(observasjoner)
    if feil:
        for melding in feil:
            print("FEIL:", melding)
        k8_firecci.skriv_status(
            "failed", f"{len(feil)} valideringsfeil, ingenting publisert", info
        )
        raise validate.Valideringsfeil(f"{len(feil)} feil — ingenting publisert")

    sti_json, sti_csv = normalize.skriv(observasjoner, FILNAVN["k8"])
    k6_natural_earth.skriv_metadata(k6_info)
    k8_firecci.skriv_metadata(info, [sti_json.name, sti_csv.name])
    k8_firecci.skriv_status(
        "ok",
        f"{sammendrag['filer']} månedsfiler aggregert til {info['rows']} "
        f"observasjoner, {andel:.4%} uten landtilknytning, "
        f"{len(info['utelatte_entiteter'])} entiteter uten treff i rutenettet "
        "utelatt",
        info,
    )

    if info["uten_geometri"]:
        print(
            f"K8: {len(info['uten_geometri'])} land mangler geometri i K6 og "
            "får ingen rader: " + ", ".join(info["uten_geometri"])
        )
    print(f"normalize: {len(observasjoner)} observasjoner")
    print("validate:  OK")
    print(f"skrevet:   {sti_json.name}, {sti_csv.name}")
    return observasjoner


def kjor_k9(kun_katalog=False):
    oppf = k9_gfed5.katalog()
    sammendrag = k9_gfed5.katalogsammendrag(oppf)
    print(
        f"K9: {oppf['navn']}, {oppf['bytes'] / 2**30:.2f} GiB "
        f"({oppf['bytes']} byte), {sammendrag['maanedsfiler']} månedsfiler"
    )
    print(
        f"K9: {sammendrag['aar_forste']}–{sammendrag['aar_siste']}, "
        f"{sammendrag['aar_antall']} år. Grov oppløsning: "
        f"{sammendrag['aar_grov_opplosning'][0]}–"
        f"{sammendrag['aar_grov_opplosning'][-1]}"
    )
    if kun_katalog:
        print("K9: --kun-katalog, ingenting lastes ned.")
        return None

    from etl import grid

    geometrier, k6_info = _geometri()
    sti = k9_gfed5.hent(oppf)
    filer = k9_gfed5.maanedsfiler(sti)

    maaneder = defaultdict(set)
    for aar, maaned, _ in filer:
        maaneder[aar].add(maaned)
    mangler = {a: sorted(set(range(1, 13)) - m) for a, m in maaneder.items()}
    mangler = {a: m for a, m in mangler.items() if m}
    if mangler:
        raise Kjorefeil(
            "K9: arkivet har år uten alle tolv månedsfiler: "
            + "; ".join(f"{a} mangler {m}" for a, m in sorted(mangler.items()))
        )

    masker = {}
    maske_for_aar = {}
    per_entitet = defaultdict(lambda: defaultdict(float))
    verden = defaultdict(float)
    uattribuert = defaultdict(float)
    start = time.monotonic()

    with zipfile.ZipFile(sti) as arkiv:
        for nr, (aar, maaned, navn) in enumerate(filer, start=1):
            lat, lon, verdier = k9_gfed5.les_rutenett(arkiv, navn)
            form = (lat.size, lon.size)

            # Oppløsningen skifter innenfor serien, så det trengs én maske per
            # rutenett. Terskler og fotnoter regnes mot den maskeen året
            # faktisk ble aggregert med.
            if form not in masker:
                print(
                    f"K9: nytt rutenett {form[0]}×{form[1]} i {aar}. "
                    "Bygger maske …",
                    flush=True,
                )
                masker[form] = grid.bygg_maske(lat, lon, geometrier)
                print(
                    f"K9: rute {masker[form].ruteareal_ekvator_km2:.0f} km² ved "
                    "ekvator",
                    flush=True,
                )
            maske = masker[form]
            if not maske.passer(lat, lon):
                raise Kjorefeil(
                    f"{navn}: rutenettet har samme form som en tidligere maske, "
                    "men andre koordinater. Summene ville blitt feil."
                )
            maske_for_aar[aar] = form

            sum_entitet, sum_uten_land, sum_total = maske.aggreger(verdier)
            for kode, verdi in sum_entitet.items():
                per_entitet[kode][aar] += verdi
            verden[aar] += sum_total
            uattribuert[aar] += sum_uten_land

            if maaned == 12:
                print(
                    f"K9: {nr}/{len(filer)} {aar} ferdig "
                    f"({verden[aar]:,.0f} km², {time.monotonic() - start:.0f} s)",
                    flush=True,
                )

    _rydd()

    total = sum(verden.values())
    andel = sum(uattribuert.values()) / total if total else 0.0
    _kontroller_uattribuert(andel, "K9")

    # Hvilke år som er grovt oppløst, følger av maskene kjøringen faktisk
    # bygget, ikke av et årstall i koden.
    finest = min(m.ruteareal_ekvator_km2 for m in masker.values())
    grove = {
        aar
        for aar, form in maske_for_aar.items()
        if masker[form].ruteareal_ekvator_km2 > finest
    }
    if grove:
        print(
            f"K9: {len(grove)} år med grovere rutenett får f_resolution_change: "
            f"{min(grove)}–{max(grove)}"
        )

    smaa_per_maske = {
        form: m.for_smaa_entiteter(GRID_MIN_ENTITY_CELLS) for form, m in masker.items()
    }
    uobs_per_maske = {form: m.uobserverte_entiteter() for form, m in masker.items()}
    for form in masker:
        print(
            f"K9: rutenett {form[0]}×{form[1]}: "
            f"{len(smaa_per_maske[form] - uobs_per_maske[form])} entiteter med "
            f"f_grid_resolution, {len(uobs_per_maske[form])} uten treff"
        )

    def per_aar(aar):
        form = maske_for_aar[aar]
        return (
            ["f_resolution_change"] if aar in grove else [],
            smaa_per_maske[form],
            uobs_per_maske[form],
        )

    info = dict(sammendrag)
    info.update(
        {
            "url": oppf["url"],
            "zenodo_doi": oppf["zenodo_doi"],
            "publication_date": oppf.get("publication_date"),
            "checksum": oppf["md5"] or "",
            "k6_checksum": k6_info["checksum"],
            "uattribuert_andel": andel,
            "uattribuert_km2": sum(uattribuert.values()),
        }
    )

    alle_koder = {k for m in masker.values() for k in m.koder}
    observasjoner = normalize.fra_k9(
        {k: dict(v) for k, v in per_entitet.items()},
        dict(verden),
        info,
        per_aar,
        med_geometri=alle_koder,
    )

    feil = validate.valider(observasjoner)
    if feil:
        for melding in feil:
            print("FEIL:", melding)
        k9_gfed5.skriv_status(
            "failed", f"{len(feil)} valideringsfeil, ingenting publisert", info
        )
        raise validate.Valideringsfeil(f"{len(feil)} feil — ingenting publisert")

    sti_json, sti_csv = normalize.skriv(observasjoner, FILNAVN["k9"])
    k6_natural_earth.skriv_metadata(k6_info)
    k9_gfed5.skriv_metadata(info, [sti_json.name, sti_csv.name])
    k9_gfed5.skriv_status(
        "ok",
        f"{len(filer)} månedsfiler aggregert til {info['rows']} observasjoner, "
        f"{andel:.4%} uten landtilknytning",
        info,
    )
    print(f"normalize: {len(observasjoner)} observasjoner")
    print("validate:  OK")
    print(f"skrevet:   {sti_json.name}, {sti_csv.name}")
    return observasjoner


def kjor_k10(kun_katalog=False):
    print(
        "K10: R-pakkene GCD (CRAN) og paleofire (CRAN-arkivet, 3,5 MB). "
        "Ingen datanedlasting — kullserien ligger i GCD-pakken."
    )
    if kun_katalog:
        print("K10: --kun-katalog, ingenting kjøres.")
        return None

    rader, info = k10_gcd.hent()
    print(f"K10: {info['rader']} rader i kompositten")

    observasjoner = normalize.fra_k10(rader, info)
    feil = validate.valider(observasjoner)
    if feil:
        for melding in feil:
            print("FEIL:", melding)
        k10_gcd.skriv_status(
            "failed", f"{len(feil)} valideringsfeil, ingenting publisert", info
        )
        raise validate.Valideringsfeil(f"{len(feil)} feil — ingenting publisert")

    sti_json, sti_csv = normalize.skriv(observasjoner, FILNAVN["k10"])
    k10_gcd.skriv_metadata(info, [sti_json.name, sti_csv.name])
    k10_gcd.skriv_status(
        "ok",
        f"kompositt med {info['rows']} punkter, "
        f"{info['aar_forste']}–{info['aar_siste']}",
        info,
    )
    _rydd()

    print(f"normalize: {len(observasjoner)} observasjoner")
    print("validate:  OK")
    print(f"skrevet:   {sti_json.name}, {sti_csv.name}")
    return observasjoner



KILDER = {"k8": kjor_k8, "k9": kjor_k9, "k10": kjor_k10}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Henter og aggregerer en statisk kilde."
    )
    parser.add_argument("--kilde", required=True, choices=sorted(KILDER))
    parser.add_argument(
        "--kun-katalog",
        action="store_true",
        help="Rapporter omfanget av kilden uten å laste ned noe.",
    )
    args = parser.parse_args(argv)

    kjor = KILDER[args.kilde]
    try:
        return kjor(kun_katalog=args.kun_katalog)
    except Exception as e:
        # Feiler kjøringen, beholdes forrige datasett og feilen logges, slik at
        # siden kan vise at serien ikke er oppdatert siden dato X (§ 4).
        statusskriver = {
            "k8": k8_firecci.skriv_status,
            "k9": k9_gfed5.skriv_status,
            "k10": k10_gcd.skriv_status,
        }
        if not args.kun_katalog:
            statusskriver[args.kilde]("failed", f"{type(e).__name__}: {e}")
        raise
    finally:
        # Rådata skal aldri bli liggende, uansett hvordan kjøringen endte.
        _rydd()


if __name__ == "__main__":
    main()
