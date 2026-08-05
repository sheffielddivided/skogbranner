"""Navnekilde — SSBs standard for landkoder alfa-3 (Klass 552).

Henter standarden og bygger ``data/geo/land_no.json``: entity-kode → norsk
navn og nivå. Leverer navn, ikke tallverdier — se CLAUDE.md § 5.

Kjøres som modul fra repotoppen: ``python -m etl.sources.ssb_klass``
"""

import json
import urllib.request

from etl.schema import GEO_DIR, LAND_NO_JSON

# Klass 552 er «Standard for landkoder (alfa-3)». Klassifikasjonen har mange
# versjoner, én per gang standarden er revidert. Versjonen som gjelder nå,
# slås opp ved kjøring i stedet for å skrives inn her, slik at en revisjon hos
# SSB kommer med uten at noen må redigere en id.
KLASS_ID = 552
KLASS_URL = f"https://data.ssb.no/api/klass/v1/classifications/{KLASS_ID}.json"
LANDING_URL = f"https://www.ssb.no/klass/klassifikasjoner/{KLASS_ID}"

OVERRIDES_JSON = GEO_DIR / "land_no_overrides.json"

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"

# --- Det SSB ikke dekker ---
#
# SSB fører land og territorier. Aggregater gjør den ikke, og et par av
# territoriene vi trenger står ikke i ISO 3166 i det hele tatt. De tre gruppene
# under finnes derfor ikke i standarden og navngis her. Det er ikke et unntak
# fra regelen om at navn skal komme fra SSB (CLAUDE.md § 5) — det finnes ingen
# SSB-form å hente for en kode SSB ikke har.

# Regioner og aggregater. Kodene er fastsatt i CLAUDE.md § 6.
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

# Territorier uten ISO 3166-kode, som heller ikke står hos SSB.
UTEN_ISO = {
    "NONISO_CYN": "Nord-Kypros",
    "NONISO_AKD": "Akrotiri og Dhekelia",
}

# Koder vi fører selv. Merkes iso3: false, se CLAUDE.md § 6.
EGNE_KODER = frozenset(REGIONER) | frozenset(UTEN_ISO) | {"XKX"}

# --- Avvik mellom SSBs kodebruk og vår ---

# SSB fører Kosovo som XXK. Vi bruker XKX (CLAUDE.md § 6), så oppføringen leses
# under SSBs kode og lagres under vår. Navnet kommer dermed fra SSB, som for
# alle andre land.
KODE_ALIAS = {"XXK": "XKX"}

# Oppføringer i standarden som ikke er geografiske entiteter. De hører hjemme i
# et skjema for personstatistikk, ikke i en entity-tabell.
IKKE_ENTITET = frozenset(
    {
        "XUK",  # Uoppgitt
        "XXX",  # Statsløs
    }
)

# Entiteter i standarden som ingen kilde vi bruker rapporterer. Holdes ute så
# tabellen bare inneholder entiteter det finnes tall for. Kommer en kilde med
# tall for en av dem, avviser validate.py observasjonen — da fjernes koden her.
UTEN_DATA = frozenset(
    {
        "ATA",  # Antarktis
    }
)


def hent():
    """Henter klassifikasjonen og versjonen som gjelder nå."""
    klassifikasjon = _hent_json(KLASS_URL)
    versjon = _gjeldende_versjon(klassifikasjon["versions"])
    return _hent_json(versjon["_links"]["self"]["href"] + ".json")


def _hent_json(url):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=120) as svar:
        return json.loads(svar.read().decode("utf-8"))


def _gjeldende_versjon(versjoner):
    """Versjonen uten sluttdato. Eldre versjoner har validTo satt."""
    gjeldende = [v for v in versjoner if not v.get("validTo")]
    if len(gjeldende) != 1:
        raise ValueError(
            f"Fant {len(gjeldende)} gjeldende versjoner av Klass {KLASS_ID}, "
            "forventet nøyaktig én"
        )
    return gjeldende[0]


def _overrides():
    with open(OVERRIDES_JSON, encoding="utf-8") as f:
        return json.load(f)["overrides"]


def bygg(versjon):
    """Bygger entity-tabellen fra en versjon av SSBs klassifikasjon."""
    overrides = _overrides()
    entities = {}

    for element in versjon["classificationItems"]:
        kode = element["code"].strip().upper()
        if kode in IKKE_ENTITET or kode in UTEN_DATA:
            continue
        kode = KODE_ALIAS.get(kode, kode)
        entities[kode] = _entitet(kode, element["name"].strip(), "country", overrides)

    for kode, navn in UTEN_ISO.items():
        entities[kode] = _entitet(kode, navn, "country", overrides)

    for kode, (navn, niva) in REGIONER.items():
        entities[kode] = _entitet(kode, navn, niva, overrides)

    ubrukte = set(overrides) - set(entities)
    if ubrukte:
        raise ValueError(
            "Overstyringer for koder som ikke finnes i standarden: "
            + ", ".join(sorted(ubrukte))
        )

    return dict(sorted(entities.items()))


def _entitet(kode, navn, niva, overrides):
    return {
        "entity_name": overrides.get(kode, {}).get("entity_name", navn),
        "level": niva,
        "iso3": kode not in EGNE_KODER,
    }


def skriv(entities, versjon):
    ut = {
        "_om": "Entity-kode → norsk navn og nivå. Delt mapping for alle kilder, "
        "slik at samme land får samme norske navn uansett hvilken kilde tallet "
        "kommer fra. Filen er også fasit for hvilke entity-koder som er gyldige. "
        "Generert av etl/sources/ssb_klass.py — rediger ikke for hånd.",
        "_skjema": "se CLAUDE.md § 6 og etl/schema.py",
        "_navnekilde": f"SSB, standard for landkoder alfa-3 (Klass {KLASS_ID}), "
        f"{LANDING_URL}. Versjon: {versjon['name']}, gyldig fra "
        f"{versjon['validFrom']}. Regionkoder, verdenskoden og koder utenfor "
        "ISO 3166 dekkes ikke av standarden og navngis i ssb_klass.py. "
        "Redaksjonelle overstyringer i land_no_overrides.json.",
        "entities": entities,
    }
    with open(LAND_NO_JSON, "w", encoding="utf-8") as f:
        json.dump(ut, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    versjon = hent()
    entities = bygg(versjon)
    skriv(entities, versjon)
    print(
        f"ssb_klass: {versjon['name']} → {len(entities)} entiteter "
        f"→ {LAND_NO_JSON.name}"
    )


if __name__ == "__main__":
    main()
