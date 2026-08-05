"""Navnekilde — SSBs standard for landkoder alfa-3 (Klass 1219).

Henter standarden og bygger ``data/geo/land_no.json``: entity-kode → norsk
navn og nivå. Leverer navn, ikke tallverdier — se CLAUDE.md § 5.

Regionkodene og territoriene uten ISO-kode finnes ikke hos SSB og legges til
her. Redaksjonelle overstyringer leses fra
``data/geo/land_no_overrides.json``.

ADVARSEL: denne modulen er ikke kjørt mot det virkelige endepunktet ennå.
``data.ssb.no`` er avvist av egress-policyen i utviklingsmiljøet, så
``land_no.json`` inneholder foreløpig navn skrevet for hånd. Kjør modulen og
sammenlign før du stoler på den.

Kjøres som modul fra repotoppen: ``python -m etl.sources.ssb_klass``
"""

import json
import urllib.request

from etl.schema import GEO_DIR, LAND_NO_JSON

KLASS_ID = 1219
KLASS_URL = f"https://data.ssb.no/api/klass/v1/versions/{KLASS_ID}.json"
LANDING_URL = f"https://www.ssb.no/klass/klassifikasjoner/{KLASS_ID}"

OVERRIDES_JSON = GEO_DIR / "land_no_overrides.json"

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"

# Regioner og aggregater. Finnes ikke i SSBs landkodestandard.
# NAC, ikke NAM: NAM er ISO3 for Namibia. Se CLAUDE.md § 6.
REGIONER = {
    "WLD": ("Verden", "world"),
    "EUR": ("Europa", "region"),
    "EUR_XRU": ("Europa (uten Russland)", "region"),
    "EU27": ("EU (27 land)", "region"),
    "AFR": ("Afrika", "region"),
    "ASI": ("Asia", "region"),
    "NAC": ("Nord-Amerika", "region"),
    "SAM": ("Sør-Amerika", "region"),
    "OCE": ("Oseania", "region"),
}

# Territorier uten ISO 3166-kode. Se CLAUDE.md § 6 for navnerommet.
UTEN_ISO = {
    "XKX": "Kosovo",
    "NONISO_CYN": "Nord-Kypros",
    "NONISO_AKD": "Akrotiri og Dhekelia",
}


def hent():
    forespoersel = urllib.request.Request(
        KLASS_URL, headers={"User-Agent": BRUKERAGENT}
    )
    with urllib.request.urlopen(forespoersel, timeout=120) as svar:
        return json.loads(svar.read().decode("utf-8"))


def _overrides():
    with open(OVERRIDES_JSON, encoding="utf-8") as f:
        return json.load(f)["overrides"]


def bygg(klass):
    """Bygger entity-tabellen fra SSBs klassifikasjon."""
    overrides = _overrides()
    entities = {}

    for element in klass["classificationItems"]:
        kode = element["code"].strip().upper()
        navn = element["name"].strip()
        if len(kode) != 3 or not kode.isalpha():
            continue
        entities[kode] = {
            "entity_name": overrides.get(kode, {}).get("entity_name", navn),
            "level": "country",
            "iso3": True,
        }

    for kode, navn in UTEN_ISO.items():
        entities[kode] = {"entity_name": navn, "level": "country", "iso3": False}

    for kode, (navn, niva) in REGIONER.items():
        entities[kode] = {"entity_name": navn, "level": niva, "iso3": False}

    ubrukte = set(overrides) - set(entities)
    if ubrukte:
        raise ValueError(
            "Overstyringer for koder som ikke finnes i standarden: "
            + ", ".join(sorted(ubrukte))
        )

    return dict(sorted(entities.items()))


def skriv(entities):
    ut = {
        "_om": "Entity-kode → norsk navn og nivå. Delt mapping for alle kilder, "
        "slik at samme land får samme norske navn uansett hvilken kilde tallet "
        "kommer fra. Filen er også fasit for hvilke entity-koder som er gyldige. "
        "Generert av etl/sources/ssb_klass.py — rediger ikke for hånd.",
        "_skjema": "se CLAUDE.md § 6 og etl/schema.py",
        "_navnekilde": f"SSB, standard for landkoder alfa-3 (Klass {KLASS_ID}), "
        f"{LANDING_URL}. Redaksjonelle overstyringer i land_no_overrides.json.",
        "entities": entities,
    }
    with open(LAND_NO_JSON, "w", encoding="utf-8") as f:
        json.dump(ut, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    entities = bygg(hent())
    skriv(entities)
    print(f"ssb_klass: {len(entities)} entiteter → {LAND_NO_JSON.name}")


if __name__ == "__main__":
    main()
