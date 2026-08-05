"""Kartlegger GWIS' statistikk-API før en parser skrives.

Verten er avvist av nettverkspolicyen i utviklingsmiljøet, så strukturen kan
ikke ses derfra. Skriptet kjøres i GitHub Actions, der utgående trafikk er
åpen, og skriver strukturen til loggen.

Dette er et engangsverktøy for å slippe å skrive en parser mot en antatt
responsstruktur. Det slettes når k2_gwis.py er skrevet mot verifisert form.

Kjøres som modul fra repotoppen: ``python -m scripts.inspiser_gwis``
"""

import json
import re
import urllib.error
import urllib.request

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"

PORTAL = "https://gwis.jrc.ec.europa.eu/apps/gwis.statistics/seasonaltrend"

# Kandidater satt opp etter det portalen dokumenterer. Skriptet prøver alle og
# rapporterer hva som svarer, slik at vi slipper å gjette videre.
KANDIDATER = [
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/countries",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/estimates",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/estimates?country=NO",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/estimates?country=NO&year=2024",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/burnedareas",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/seasonal",
    "https://api2.effis.emergency.copernicus.eu/statistics/v2/seasonal/trend?country=NO",
]


def hent(url, maks=400_000):
    forespoersel = urllib.request.Request(url, headers={"User-Agent": BRUKERAGENT})
    with urllib.request.urlopen(forespoersel, timeout=60) as svar:
        return svar.status, svar.headers.get("content-type", ""), svar.read(maks)


def vis_struktur(verdi, innrykk=0, sti="", maks_dybde=4):
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
        vist = repr(verdi)
        print(f"{pre}{sti}: {type(verdi).__name__} = {vist[:80]}")


def finn_api_i_portalen():
    """Leter etter API-adresser i portalens egne skriptfiler."""
    print(f"\n### Leter etter API-adresser i {PORTAL}\n")
    try:
        _, _, kropp = hent(PORTAL)
    except Exception as e:
        print(f"  portalen svarte ikke: {type(e).__name__}: {e}")
        return

    html = kropp.decode("utf-8", errors="replace")
    skript = re.findall(r'src="([^"]+\.js[^"]*)"', html)
    print(f"  fant {len(skript)} skriptfiler")

    funnet = set()
    for sti in skript[:12]:
        url = sti if sti.startswith("http") else "https://gwis.jrc.ec.europa.eu" + sti
        try:
            _, _, innhold = hent(url, maks=3_000_000)
        except Exception:
            continue
        tekst = innhold.decode("utf-8", errors="replace")
        for treff in re.findall(r'https://[a-z0-9.\-]*(?:effis|gwis)[a-z0-9.\-/]*', tekst):
            funnet.add(treff)

    for adresse in sorted(funnet)[:40]:
        print(f"    {adresse}")
    if not funnet:
        print("    ingen adresser funnet i skriptfilene")


def main():
    print("=" * 72)
    print("GWIS — kartlegging av statistikk-API")
    print("=" * 72)

    for url in KANDIDATER:
        print(f"\n### {url}")
        try:
            status, ctype, kropp = hent(url)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} {e.reason}")
            continue
        except Exception as e:
            print(f"  {type(e).__name__}: {e}")
            continue

        print(f"  HTTP {status} | {ctype} | {len(kropp)} bytes")
        if "json" not in ctype:
            print(f"  første 300 tegn: {kropp[:300]!r}")
            continue
        try:
            data = json.loads(kropp)
        except json.JSONDecodeError as e:
            print(f"  ugyldig JSON: {e}")
            continue

        print("  STRUKTUR:")
        vis_struktur(data, innrykk=2)

        # Én komplett oppføring, slik at feltnavn og verdiformat kan leses av.
        forste = None
        if isinstance(data, list) and data:
            forste = data[0]
        elif isinstance(data, dict):
            for verdi in data.values():
                if isinstance(verdi, list) and verdi:
                    forste = verdi[0]
                    break
        if forste is not None:
            print("  KOMPLETT OPPFØRING:")
            print("   " + json.dumps(forste, ensure_ascii=False, indent=2)[:1500])

    finn_api_i_portalen()


if __name__ == "__main__":
    main()
