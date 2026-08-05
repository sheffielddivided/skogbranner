"""Kartlegger kildeformater som ikke kan ses fra utviklingsmiljøet.

To grunner til at en kilde havner her:

* **Verten er blokkert.** Nettverkspolicyen i utviklingsmiljøet avviser
  ``api2.effis.emergency.copernicus.eu`` med 403 på CONNECT, så K2 og K3 kan
  ikke prøves derfra.
* **Filen er for tung.** NBAC-aggregatet til K7 er på flere megabyte, og skal
  ikke lastes ned i en utviklingssesjon (CLAUDE.md T4).

Skriptet kjøres i GitHub Actions, der begge deler er greit, og skriver det den
finner til loggen.

Engangsverktøy. Både dette skriptet og ``.github/workflows/inspiser.yml``
slettes før grenen slås sammen med main.

Kjøres som modul fra repotoppen: ``python -m scripts.inspiser_kilder``
"""

import json
import urllib.error
import urllib.request

from etl.sources import k2_gwis, k7_nbac

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"

API = "https://api2.effis.emergency.copernicus.eu"

# K3 EFFIS. Adressene er lest av portalens skriptfil på
# forest-fire.emergency.copernicus.eu, som bygger dem av samme basis som GWIS.
# Det som gjenstår er responsformen og hvilken enhet ba har.
EFFIS_KANDIDATER = [
    f"{API}/statistics/utils/aoi?scope=effis",
    f"{API}/statistics/utils/countriesbyaoi?aoi=effis",
    f"{API}/statistics/v2/effis/estimatesbycountry?country=ITA",
    f"{API}/statistics/v2/effis/estimatesbycountry?country=NOR",
]


def hent(url, maks=2_000_000):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=60) as svar:
        return svar.status, svar.headers.get("content-type", ""), svar.read(maks)


def vis_struktur(verdi, innrykk=0, sti="", maks_dybde=3):
    """Skriver ut formen på et JSON-tre uten å gjengi hele innholdet."""
    pre = "  " * innrykk
    if isinstance(verdi, dict):
        print(f"{pre}{sti or '.'}: objekt med {len(verdi)} nøkler")
        if innrykk < maks_dybde:
            for nokkel, under in list(verdi.items())[:15]:
                vis_struktur(under, innrykk + 1, nokkel, maks_dybde)
    elif isinstance(verdi, list):
        print(f"{pre}{sti}: liste med {len(verdi)} elementer")
        if verdi and innrykk < maks_dybde:
            vis_struktur(verdi[0], innrykk + 1, f"{sti}[0]", maks_dybde)
    else:
        print(f"{pre}{sti}: {type(verdi).__name__} = {repr(verdi)[:80]}")


def effis():
    print("=" * 72)
    print("K3 EFFIS — responsform")
    print("=" * 72)

    for url in EFFIS_KANDIDATER:
        print(f"\n### {url}")
        try:
            status, ctype, kropp = hent(url)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} {e.reason}: {e.read(300)!r}")
            continue
        except Exception as e:
            print(f"  {type(e).__name__}: {e}")
            continue

        print(f"  HTTP {status} | {ctype} | {len(kropp)} bytes")
        if "json" not in ctype:
            print(f"  første 300 tegn: {kropp[:300]!r}")
            continue

        data = json.loads(kropp)
        print("  STRUKTUR:")
        vis_struktur(data, innrykk=2)
        if isinstance(data, list) and data:
            print("  FØRSTE:", json.dumps(data[0], ensure_ascii=False)[:400])
            print("  SISTE: ", json.dumps(data[-1], ensure_ascii=False)[:400])
            koder = sorted({r.get("iso3") for r in data if isinstance(r, dict)} - {None})
            if koder:
                print(f"  KODER ({len(koder)}): {koder}")


def gwis():
    """Prøver K2-modulen mot det virkelige API-et.

    Verifiserer at hele hentingen virker, ikke bare at ett endepunkt svarer.
    """
    print()
    print("=" * 72)
    print("K2 GWIS — full henting via etl.sources.k2_gwis")
    print("=" * 72)
    rader, info = k2_gwis.hent()
    print(f"  {info['rows']} årsrader for {info['countries']} land")
    print(f"  dekning {info['coverage_start']}–{info['coverage_end']}")
    print(f"  uten svar: {info['unanswered'] or 'ingen'}")
    print(f"  første: {rader[0]}")
    print(f"  siste:  {rader[-1]}")

    # Kodene må kunne slås mot land_no.json. Her vises de rå, slik at et avvik
    # kan fanges før normalize.py reiser feil på dem.
    koder = sorted({r["iso3"] for r in rader})
    print(f"  KODER ({len(koder)}): {koder}")


def nbac():
    """Prøver K7s NBAC-parser mot den virkelige filen.

    Filen er for tung til å lastes ned i en utviklingssesjon (T4), så arket og
    kolonnen er ikke prøvd der. Her leses den, og radene skrives ut.
    """
    print()
    print("=" * 72)
    print("K7 NBAC — parser mot virkelig fil")
    print("=" * 72)
    areal, branner, info = k7_nbac.hent()
    print(f"  fil: {info['nbac_file']} (utgitt {info['nbac_release']})")
    print(f"  areal: {len(areal)} årsrader, {areal[0]} … {areal[-1]}")
    print(f"  branntall: {len(branner)} årsrader, {branner[0]} … {branner[-1]}")


def main():
    for steg in (effis, gwis, nbac):
        try:
            steg()
        except Exception as e:
            print(f"\n!! {steg.__name__} feilet: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
