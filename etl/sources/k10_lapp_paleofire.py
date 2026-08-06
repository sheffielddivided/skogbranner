"""Lapper paleofire slik at pakken kan installeres og lastes i dag.

paleofire 1.2.4 er fra 2019 og ble trukket fra CRAN i januar 2023. To ting
hindrer den i å kjøre på en moderne R:

1. ``NAMESPACE`` importerer ``rgdal``, som selv ble trukket i oktober 2023.
   Pakken bruker den bare i ``pfGridding`` og ``pfToKml``, som vi ikke kaller.
2. ``pfTransform`` avgjør om en av de rullende metodene er bedt om med en kjede
   av ``||``-sammenligninger. R 4.3 gjorde det til en feil å gi ``||`` en
   vektor, og ``method`` *er* en vektor når kompositten bygges med flere
   metoder.

Begge lappene er mekaniske og rører ikke beregningene kompositten bygges av.
Skriptet stopper hvis et av uttrykkene ikke finnes, slik at en annen versjon av
pakken ikke lappes blindt.

At pakken er lappet, står i ``data/_sources.json``. Se CLAUDE.md § 5 (K10).

Kjøres som modul fra repotoppen, med katalogen den utpakkede pakken ligger i:

    python -m etl.sources.k10_lapp_paleofire paleofire
"""

import sys
from pathlib import Path

# NAMESPACE-importen, slik den står i 1.2.4.
RGDAL_FRA = "GCD,rgdal,lattice,raster)"
RGDAL_TIL = "GCD,lattice,raster)"

DESCRIPTION_FRA = "Imports: locfit, raster, ggplot2, plyr, rgdal, lattice"
DESCRIPTION_TIL = "Imports: locfit, raster, ggplot2, plyr, lattice"

# Filene som er de eneste brukerne av rgdal.
RGDAL_FILER = ("R/pfGridding.R", "R/pfToKml.R")

# ||-kjeden i pfTransform, og det den åpenbart betyr.
VEKTOR_FRA = (
    '  if (method == "RunMean" || method == "RunMin" || method == "RunMed" '
    '|| method == "RunMax" ||\n      method == "RunQuantile") {'
)
VEKTOR_TIL = (
    '  if (any(method %in% c("RunMean", "RunMin", "RunMed", "RunMax", '
    '"RunQuantile"))) {'
)


class Lappefeil(Exception):
    """Reises når pakken ikke ser ut som den vi vet hvordan skal lappes."""


def _bytt(sti, fra, til, hva):
    tekst = sti.read_text(encoding="utf-8")
    if fra not in tekst:
        raise Lappefeil(
            f"{sti}: fant ikke {hva}. Pakken er en annen versjon enn den "
            "lappene er skrevet for, og skal ikke lappes blindt."
        )
    sti.write_text(tekst.replace(fra, til), encoding="utf-8")


def lapp(rot):
    rot = Path(rot)
    _bytt(rot / "NAMESPACE", RGDAL_FRA, RGDAL_TIL, "rgdal-importen i NAMESPACE")
    _bytt(
        rot / "DESCRIPTION",
        DESCRIPTION_FRA,
        DESCRIPTION_TIL,
        "rgdal i Imports i DESCRIPTION",
    )
    for navn in RGDAL_FILER:
        (rot / navn).unlink(missing_ok=True)
    _bytt(
        rot / "R" / "pfTransform.R",
        VEKTOR_FRA,
        VEKTOR_TIL,
        "||-kjeden over metodenavn",
    )

    igjen = []
    for navn in ("NAMESPACE", "DESCRIPTION"):
        if "rgdal" in (rot / navn).read_text(encoding="utf-8"):
            igjen.append(navn)
    if igjen:
        raise Lappefeil(f"rgdal står fortsatt i {', '.join(igjen)}")

    print(f"paleofire lappet: rgdal fjernet, ||-kjeden i pfTransform erstattet")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        raise SystemExit("Bruk: python -m etl.sources.k10_lapp_paleofire <katalog>")
    lapp(argv[0])


if __name__ == "__main__":
    main()
