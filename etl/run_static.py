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
from collections import defaultdict

from etl import normalize, validate
from etl.schema import GRID_MAX_UNATTRIBUTED_SHARE, GRID_MIN_ENTITY_CELLS
from etl.sources import k6_natural_earth, k8_firecci

# Filnavnet under data/processed/ per kilde. Navnet følger serien, ikke
# kildekoden, slik at en lesbar nedlastingslenke peker på det figuren viser.
FILNAVN = {"k8": "burned_area_firecci_lt11"}


class Kjorefeil(Exception):
    """Reises når kjøringen ikke kan fullføres, og datasettet ikke skal røres."""


def _rydd():
    """Fjerner rådata. De committes aldri (CLAUDE.md T4)."""
    shutil.rmtree(k8_firecci.RAW_K8_DIR, ignore_errors=True)
    k6_natural_earth.RAW_ZIP.unlink(missing_ok=True)


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
                print(
                    f"K8: maske for {len(maske.koder)} entiteter. "
                    f"En rute er {maske.ruteareal_ekvator_km2:.0f} km² ved "
                    f"ekvator; {len(for_smaa)} entiteter har mindre landareal "
                    "enn det og får f_grid_resolution",
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
    info["for_smaa"] = sorted(for_smaa)
    info["checksum"] = hashlib.sha256(
        "".join(o["md5"] or o["navn"] for o in oppforinger).encode("utf-8")
    ).hexdigest()
    info["k6_checksum"] = k6_info["checksum"]

    observasjoner = normalize.fra_k8(
        {k: dict(v) for k, v in per_entitet.items()},
        dict(verden),
        info,
        for_smaa=for_smaa,
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
        f"observasjoner, {andel:.4%} uten landtilknytning",
        info,
    )

    print(f"normalize: {len(observasjoner)} observasjoner")
    print("validate:  OK")
    print(f"skrevet:   {sti_json.name}, {sti_csv.name}")
    return observasjoner


def _ikke_implementert(kode):
    def kjor(kun_katalog=False):
        raise SystemExit(
            f"{kode.upper()} er ikke implementert ennå. Se CLAUDE.md § 12."
        )

    return kjor


KILDER = {
    "k8": kjor_k8,
    "k9": _ikke_implementert("k9"),
    "k10": _ikke_implementert("k10"),
}


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
        if args.kilde == "k8" and not args.kun_katalog:
            k8_firecci.skriv_status("failed", f"{type(e).__name__}: {e}")
        raise
    finally:
        # Rådata skal aldri bli liggende, uansett hvordan kjøringen endte.
        _rydd()


if __name__ == "__main__":
    main()
