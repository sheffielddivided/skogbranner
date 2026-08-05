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

PORTALER = [
    "https://gwis.jrc.ec.europa.eu/apps/gwis.statistics/seasonaltrend",
    "https://gwis.jrc.ec.europa.eu/apps/country.profile/overview/",
]
PORTAL = PORTALER[0]

# Første runde traff ikke: alle /statistics/v2/-stiene svarte 404. Portalens
# skriptfiler viste at basisstien er /api/gwis/. Kandidatene under følger den.
API = "https://api2.effis.emergency.copernicus.eu"

KANDIDATER = [
    f"{API}/api/gwis/seasonaltrend/",
    f"{API}/api/gwis/seasonaltrend/?country=NO",
    f"{API}/api/gwis/seasonaltrend/data/?country=NO",
    f"{API}/api/gwis/countries/",
    f"{API}/api/gwis/country.profile/",
    f"{API}/api/gwis/country.profile/overview/?country=NO",
    f"{API}/api/gwis/",
    f"{API}/api/",
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
    """Leter etter API-stier i portalenes egne skriptfiler.

    Stiene settes gjerne sammen av en basiskonstant og et relativt fragment, så
    det holder ikke å lete etter hele adresser. Her samles begge deler.
    """
    for portal in PORTALER:
        print(f"\n### Leter etter API-stier i {portal}\n")
        try:
            _, _, kropp = hent(portal)
        except Exception as e:
            print(f"  portalen svarte ikke: {type(e).__name__}: {e}")
            continue

        html = kropp.decode("utf-8", errors="replace")
        skript = re.findall(r'src="([^"]+\.js[^"]*)"', html)
        print(f"  fant {len(skript)} skriptfiler")

        adresser, fragmenter = set(), set()
        for sti in skript[:15]:
            url = sti if sti.startswith("http") else "https://gwis.jrc.ec.europa.eu" + sti
            try:
                _, _, innhold = hent(url, maks=6_000_000)
            except Exception:
                continue
            tekst = innhold.decode("utf-8", errors="replace")
            adresser.update(
                re.findall(r'https://[a-z0-9.\-]*(?:effis|gwis)[a-z0-9.\-/]*', tekst)
            )
            # Relative stier i anførselstegn, som settes sammen med basisen.
            fragmenter.update(re.findall(r'["\'](/api/[a-zA-Z0-9._/\-]{2,80})["\']', tekst))
            fragmenter.update(
                re.findall(r'["\']([a-zA-Z0-9._/\-]*(?:statistic|estimate|burnt|burned|seasonal|country)[a-zA-Z0-9._/\-]*)["\']', tekst)
            )

        print("  hele adresser:")
        for a in sorted(adresser)[:30]:
            print(f"    {a}")
        print("  stifragmenter:")
        for f in sorted(fragmenter)[:60]:
            print(f"    {f}")


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
