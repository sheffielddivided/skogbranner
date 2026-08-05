"""Kartlegger GWIS' statistikk-API før en parser skrives.

Verten er avvist av nettverkspolicyen i utviklingsmiljøet, så responsene kan
ikke ses derfra. Skriptet kjøres i GitHub Actions, der utgående trafikk er
åpen, og skriver strukturen til loggen.

Dette er et engangsverktøy for å slippe å skrive en parser mot en antatt
responsstruktur. Det slettes når k2_gwis.py er skrevet mot verifisert form.

Kjøres som modul fra repotoppen: ``python -m scripts.inspiser_gwis``
"""

import json
import urllib.error
import urllib.request

BRUKERAGENT = "skogbranner-etl/1.0 (+https://github.com/sheffielddivided/skogbranner)"

# Runde tre. Portalens egen skriptfil (_nuxt/86508f3.js) viste både basisen og
# hvordan hver adresse settes sammen, så disse er lest av kilden og ikke gjettet:
#
#   prefixUrl              https://api2.effis.emergency.copernicus.eu
#   estimatesByCountryURL  /statistics/v2/gwis/estimatesbycountry?country=
#   estimatesOverviewURL   /statistics/v2/gwis/estimatesoverview?countries=&year=
#   seasonalTrendBANFURL   /statistics/v2/gwis/weekly?country=&year=
#   aoiURL                 statistics/utils/aoi?scope=
#   countriesByAOIURL      statistics/utils/countriesbyaoi?aoi=
#
# Det som gjenstår å få bekreftet er responsformene og hvilken enhet ``ba``
# har. Portalen viser ``area_ha`` ved siden av, så hektar er antakelsen —
# ``sjekk_enhet`` under prøver den mot ``ba_p``, som er samme tall i prosent.
API = "https://api2.effis.emergency.copernicus.eu"

KANDIDATER = [
    f"{API}/statistics/utils/aoi?scope=gwis",
    f"{API}/statistics/utils/countriesbyaoi?aoi=UN_EUR",
    f"{API}/statistics/v2/gwis/estimatesbycountry?country=NOR",
    f"{API}/statistics/v2/gwis/estimatesbycountry?country=USA",
    f"{API}/statistics/v2/gwis/estimatesoverview?countries=UN_EUR&year=2024",
    f"{API}/statistics/v2/gwis/weekly?country=NOR&year=2024",
]

# Adressene over uten skjema-prefikset, i tilfelle basisen skal være med.
KANDIDATER += [f"{API}/api/gwis/estimatesbycountry?country=NOR"]


def hent(url, maks=2_000_000):
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
        print(f"{pre}{sti}: {type(verdi).__name__} = {repr(verdi)[:80]}")


def sjekk_enhet(rader):
    """Avgjør om ``ba`` er hektar, ved å prøve den mot ``ba_p`` og ``area_ha``.

    ``ba_p`` er brent areal som andel av landarealet, i prosent. Er ``ba``
    hektar, skal ``ba / area_ha * 100`` treffe ``ba_p``. Er den km², bommer
    den med faktor 100. Dette avgjør hvilken konstant normalize.py skal bruke,
    og skal ikke gjettes.
    """
    print("  ENHETSPRØVE (ba mot ba_p og area_ha):")
    vist = 0
    for rad in rader:
        if not isinstance(rad, dict):
            continue
        ba, areal, andel = rad.get("ba"), rad.get("area_ha"), rad.get("ba_p")
        if not all(isinstance(v, (int, float)) for v in (ba, areal, andel)):
            continue
        if not areal or not andel:
            continue
        beregnet = ba / areal * 100
        print(
            f"    {rad.get('iso3')}: ba={ba} area_ha={areal} ba_p={andel} "
            f"→ ba/area_ha*100 = {beregnet:.4f} "
            f"(forhold til ba_p: {beregnet / andel:.4f})"
        )
        vist += 1
        if vist >= 5:
            break
    if not vist:
        print("    ingen rader hadde ba, area_ha og ba_p samtidig")


def main():
    print("=" * 72)
    print("GWIS — kartlegging av statistikk-API, runde tre")
    print("=" * 72)

    for url in KANDIDATER:
        print(f"\n### {url}")
        try:
            status, ctype, kropp = hent(url)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} {e.reason}")
            print(f"  kropp: {e.read(400)!r}")
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

        if isinstance(data, list) and data:
            print("  FØRSTE OPPFØRING:")
            print("   " + json.dumps(data[0], ensure_ascii=False, indent=2)[:1200])
            print("  SISTE OPPFØRING:")
            print("   " + json.dumps(data[-1], ensure_ascii=False, indent=2)[:1200])
            sjekk_enhet(data)

            # Kodene serien bruker for entiteter, som må slås mot land_no.json.
            koder = sorted(
                {r.get("iso3") or r.get("country") for r in data if isinstance(r, dict)}
                - {None}
            )
            if koder:
                print(f"  KODER ({len(koder)}): {koder[:80]}")


if __name__ == "__main__":
    main()
