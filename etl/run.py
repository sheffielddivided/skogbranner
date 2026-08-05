"""Kjører hele pipelinen: hent → normaliser → valider → publiser.

Rekkefølgen står i CLAUDE.md § 4. Feiler en kilde eller valideringen, beholdes
forrige datasett i ``data/processed/`` og feilen logges i ``data/_status.json``.

Kjøres som modul fra repotoppen: ``python -m etl.run``
"""

from etl import normalize, validate
from etl.sources import k1_owid


def main():
    try:
        rader, metadata, info = k1_owid.hent()
        print(f"K1: {info['rows']} rader hentet, sha256 {info['checksum'][:16]}…")

        observasjoner = normalize.fra_k1(rader, info)
        feil = validate.valider(observasjoner)
        if feil:
            for melding in feil:
                print("FEIL:", melding)
            k1_owid.skriv_status(
                "failed", f"{len(feil)} valideringsfeil, forrige datasett beholdt", info
            )
            raise validate.Valideringsfeil(f"{len(feil)} feil — ingenting publisert")

        sti_json, sti_csv = normalize.skriv(observasjoner, "burned_area")
        k1_owid.skriv_metadata(
            metadata, info, [sti_json.name, sti_csv.name]
        )
        k1_owid.skriv_status("ok", "hentet og publisert", info)

        print(f"normalize: {len(observasjoner)} observasjoner")
        print(f"validate:  OK")
        print(f"skrevet:   {sti_json.name}, {sti_csv.name}")
        return observasjoner

    except Exception as e:
        if not isinstance(e, validate.Valideringsfeil):
            k1_owid.skriv_status("failed", f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
