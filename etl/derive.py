"""Maskinelle avledninger → data/processed/insights.json.

Enhver tallfestet påstand i brødteksten på siden kommer herfra (P3). Hver
avledning får en stabil id, som er verdien HTML bærer i sitt
``data-derivation``-attributt, slik at leseren kan spore tallet tilbake til
beregningen.

Hvilke avledninger som er tillatt, hva de betyr, og hvilke regler som gjelder
for grunnlaget — fullstendige år, trend innenfor én kilde og én ``quality``,
nullverdier, entiteter som alltid er null — står i CLAUDE.md § 7. Reglene
gjentas ikke her.

Filen leser de ferdige seriene under ``data/processed/`` og skriver dit. Den
kjører i ETL, ikke under bygging av siden, og resultatet committes som de
andre bearbeidede filene (P3, T3).

Kjøres som modul fra repotoppen: ``python -m etl.derive``
"""

import json
import math
import re
from collections import defaultdict

from etl import validate
from etl.schema import (
    ANOMALY_FACTOR_PCT,
    CONCENTRATION_TOP_N,
    GEO_WORLD_JSON,
    INSIGHTS_JSON,
    LAND_AREA_JSON,
    SEASON_BAND_PCT,
    TREND_ALPHA,
    TREND_MAX_ZERO_SHARE,
    TREND_MAX_ZERO_TAIL,
    TREND_MIN_YEARS,
    TREND_MIN_YEARS_AGGREGATE,
)

# Fotnotene avledningene leser. De er kildens egen merking av hva en verdi er,
# og avgjør hvilke observasjoner som kan inngå i et grunnlag (§ 7, § 9).
UFULLSTENDIG = "f_incomplete_year"
TVETYDIG_NULL = "f_zero_no_detection"
GLATTET = "f_smoothed"

# Nivåene som regnes som aggregater. En trend for dem har en egen grense for
# hvor kort serien kan være (§ 7).
AGGREGATNIVAA = frozenset({"world", "region"})

# Enheter en prosentvis avviks- eller andelsberegning er definert for. En
# z-score er en avstand i standardavvik, ikke en mengde, og «så mange prosent
# over normalen» ville vært et regnestykke på en skala uten nullpunkt.
FORHOLDSTALL_ENHETER = frozenset({"km2", "share", "count"})

# Enheter som lar seg summere til et totaltall, og dermed inngå i andel og
# konsentrasjon. En andel av landarealet summerer ikke til noe meningsfullt.
SUMMERBARE_ENHETER = frozenset({"km2", "count"})

DESIMALER_VERDI = 2
DESIMALER_ANDEL = 6
DESIMALER_PROSENT = 1
DESIMALER_P = 6


# --- Statistikk ------------------------------------------------------------
#
# Theil–Sen og Mann–Kendall er skrevet ut her fordi den månedlige kjøringen
# ikke har numeriske avhengigheter (se requirements.txt). Begge er kontrollert
# mot datasett med kjent fasit i etl/test_derive.py.


def theil_sen(punkter):
    """Theil–Sen-estimatoren: medianen av de parvise stigningstallene.

    ``punkter`` er (x, y). Returnerer stigning per x-enhet, eller None når det
    ikke finnes to punkter med ulik x.
    """
    stigninger = []
    for i in range(len(punkter)):
        xi, yi = punkter[i]
        for j in range(i + 1, len(punkter)):
            xj, yj = punkter[j]
            if xj != xi:
                stigninger.append((yj - yi) / (xj - xi))
    if not stigninger:
        return None
    return _median(stigninger)


def mann_kendall(punkter):
    """Mann–Kendall-testen, med korreksjon for bindinger.

    Returnerer (S, varians, Z, p). p er tosidig. Normaltilnærmingen holder
    ikke for korte serier — grensen står som TREND_MIN_YEARS i schema.py og
    håndheves av kalleren, ikke her.
    """
    verdier = [y for _, y in punkter]
    n = len(verdier)

    s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += _fortegn(verdier[j] - verdier[i])

    bindinger = defaultdict(int)
    for y in verdier:
        bindinger[y] += 1

    varians = n * (n - 1) * (2 * n + 5)
    for antall in bindinger.values():
        varians -= antall * (antall - 1) * (2 * antall + 5)
    varians /= 18

    if varians <= 0:
        return s, varians, 0.0, 1.0

    # Kontinuitetskorreksjonen trekker S ett steg mot null.
    if s > 0:
        z = (s - 1) / math.sqrt(varians)
    elif s < 0:
        z = (s + 1) / math.sqrt(varians)
    else:
        z = 0.0

    return s, varians, z, _tosidig_p(z)


def _tosidig_p(z):
    """Tosidig p-verdi for Z i standard normalfordeling."""
    return math.erfc(abs(z) / math.sqrt(2))


def _fortegn(x):
    return (x > 0) - (x < 0)


def _prosent(x):
    """Prosent med én desimal — men små andeler beholder to gjeldende siffer.

    Norges andel av verdens brente areal er 0,0003 prosent. Rundet til én
    desimal blir den 0,0, og en setning som sier at et land står for null
    prosent, sier noe annet enn tallet gjør.
    """
    if x == 0:
        return 0.0
    if abs(x) >= 1:
        return round(x, DESIMALER_PROSENT)
    return round(x, -int(math.floor(math.log10(abs(x)))) + 1)


def persentil(verdier, p):
    """Persentil med lineær interpolasjon mellom ordningsverdiene.

    Samme konvensjon som numpy og R type 7: er persentilen mellom to
    observasjoner, veies de to nærmeste. Skrevet ut her fordi den månedlige
    kjøringen ikke har numeriske avhengigheter.
    """
    sortert = sorted(verdier)
    if not sortert:
        return None
    if len(sortert) == 1:
        return sortert[0]

    plass = (len(sortert) - 1) * p / 100
    under = math.floor(plass)
    over = math.ceil(plass)
    if under == over:
        return sortert[int(plass)]
    return sortert[under] + (sortert[over] - sortert[under]) * (plass - under)


def persentilplass(n, p):
    """Hvilke ordningsverdier en persentil hviler på, talt fra nærmeste ende.

    Med få år ligger en ytterpersentil mellom to enkeltår, og båndet er da
    ikke bredere enn de to årene tillater. Setningen som forklarer båndet for
    leseren, trenger å kunne si hvilke to — se CLAUDE.md § 7 og § 9.

    Rangene telles fra den enden persentilen ligger nærmest: 1 er den laveste
    for en lav persentil og den høyeste for en høy. Er persentilen midt i
    serien, telles den fra bunnen.
    """
    if n < 2:
        return {"ranks": [1], "interpolated": False, "from": "low"}

    plass = (n - 1) * p / 100
    under, over = math.floor(plass), math.ceil(plass)
    fra_bunn = p <= 50
    rang = lambda i: i + 1 if fra_bunn else n - i  # noqa: E731

    if under == over:
        return {
            "ranks": [rang(under)],
            "interpolated": False,
            "from": "low" if fra_bunn else "high",
        }
    return {
        "ranks": sorted((rang(under), rang(over))),
        "interpolated": True,
        "from": "low" if fra_bunn else "high",
    }


def _median(verdier):
    sortert = sorted(verdier)
    n = len(sortert)
    midt = n // 2
    if n % 2:
        return sortert[midt]
    return (sortert[midt - 1] + sortert[midt]) / 2


# --- Grunnlaget ------------------------------------------------------------


def _aarstall(periode):
    """Årstallet i en periode, eller None for finere oppløsning enn år."""
    resten = periode[1:] if periode.startswith("-") else periode
    if "-" in resten:
        return None
    return int(periode)


def grunnlag(observasjoner):
    """Ordner observasjonene som serier av fullstendige år.

    Inneværende år kjennes på f_incomplete_year, som normalize.py setter ut
    fra kildens nedlastingsdato. Grunnlaget leses dermed av dataene selv, ikke
    av hvilken dato maskinen tilfeldigvis har når jobben kjører (§ 7).
    """
    serier = {}
    for o in observasjoner:
        aar = _aarstall(o["period"])
        if aar is None:
            continue

        serie = serier.setdefault(
            o["series_id"],
            {
                "series_id": o["series_id"],
                "source_id": o["source_id"],
                "quality": o["quality"],
                "indicator": o["indicator"],
                "unit": o["unit"],
                "smoothed": False,
                "entities": defaultdict(dict),
                "names": {},
                "levels": {},
                "incomplete_years": set(),
            },
        )
        serie["names"][o["entity"]] = o["entity_name"]
        serie["levels"][o["entity"]] = o["level"]
        if GLATTET in o["footnotes"]:
            serie["smoothed"] = True

        if UFULLSTENDIG in o["footnotes"]:
            serie["incomplete_years"].add(aar)
            continue

        serie["entities"][o["entity"]][aar] = {
            "value": o["value"],
            "ambiguous_zero": TVETYDIG_NULL in o["footnotes"],
        }

    for serie in serier.values():
        serie["incomplete_years"] = sorted(serie["incomplete_years"])
        serie["always_zero"] = sorted(
            kode
            for kode, aar in serie["entities"].items()
            if aar and all(p["value"] == 0 for p in aar.values())
        )
        alle_aar = {a for aar in serie["entities"].values() for a in aar}
        serie["first_year"] = min(alle_aar) if alle_aar else None
        serie["last_complete_year"] = max(alle_aar) if alle_aar else None
    return serier


def _punkter(serie, kode):
    """Entitetens år, sortert, som (år, verdi)."""
    aar = serie["entities"][kode]
    return [(a, aar[a]["value"]) for a in sorted(aar)]


def _felles(serie, kode):
    """Feltene enhver avledning bærer, slik en setning kan si hva den viser."""
    return {
        "series_id": serie["series_id"],
        "source_id": serie["source_id"],
        "quality": serie["quality"],
        "indicator": serie["indicator"],
        "unit": serie["unit"],
        "entity": kode,
        "entity_name": serie["names"][kode],
        "level": serie["levels"][kode],
    }


# --- Avledningene (CLAUDE.md § 7) ------------------------------------------


def dekning(serie, kode):
    """Første og siste år med data, og hvilke år som mangler innimellom."""
    punkter = _punkter(serie, kode)
    if not punkter:
        return None
    aar = [a for a, _ in punkter]
    mangler = [a for a in range(aar[0], aar[-1] + 1) if a not in set(aar)]
    return dict(
        _felles(serie, kode),
        kind="coverage",
        first_year=aar[0],
        last_year=aar[-1],
        n_years=len(aar),
        missing_years=mangler,
        incomplete_years=serie["incomplete_years"],
    )


def felles_dekning(serier, kode):
    """Årene alle seriene for én entitet dekker.

    Flere serier kan måle det samme, hver over sin egen periode. Skal to av dem
    sammenlignes i et enkeltår, må året være et år begge faktisk dekker — og
    hvilket år det er, følger av dekningen, ikke av hva noen husker.

    Overlappet er første år noen serie starter, seneste av startene, mot siste
    år alle rekker. Serier uten rader for entiteten teller ikke med.

    Returnerer None når færre enn to serier dekker entiteten, eller når de
    ikke overlapper i det hele tatt.
    """
    dekkende = []
    for serie_id, serie in sorted(serier.items()):
        # «in» framfor oppslag: entities er en defaultdict, og et oppslag på en
        # entitet serien ikke har, ville opprettet den som tom.
        if kode not in serie["entities"]:
            continue
        punkter = _punkter(serie, kode)
        if punkter:
            dekkende.append((serie_id, punkter[0][0], punkter[-1][0]))

    if len(dekkende) < 2:
        return None

    forste = max(d[1] for d in dekkende)
    siste = min(d[2] for d in dekkende)
    if forste > siste:
        return None

    return {
        "kind": "coverage_overlap",
        "entity": kode,
        "series": [d[0] for d in dekkende],
        "n_series": len(dekkende),
        "first_year": forste,
        "last_year": siste,
        "n_years": siste - forste + 1,
    }


def rangering(serie, kode, aar):
    """«År X er nummer N av M år med data for enhet E.»

    Rangeringen er synkende: nummer 1 er den høyeste verdien. Like verdier får
    samme nummer.
    """
    punkter = dict(_punkter(serie, kode))
    if aar not in punkter:
        return None
    verdi = punkter[aar]
    hoyere = sum(1 for v in punkter.values() if v > verdi)
    like = sum(1 for v in punkter.values() if v == verdi)
    return dict(
        _felles(serie, kode),
        kind="rank",
        period=str(aar),
        value=verdi,
        ambiguous_zero=serie["entities"][kode][aar]["ambiguous_zero"],
        rank=hoyere + 1,
        of=len(punkter),
        tied=like - 1,
        first_year=min(punkter),
        last_year=max(punkter),
    )


def avvik_fra_normal(serie, kode, aar):
    """Verdien mot medianen for hele dekningsperioden, i prosent."""
    punkter = dict(_punkter(serie, kode))
    if aar not in punkter:
        return None
    median = _median(list(punkter.values()))
    if median <= 0:
        return None
    verdi = punkter[aar]
    avvik = (verdi - median) / median * 100
    return dict(
        _felles(serie, kode),
        kind="anomaly",
        period=str(aar),
        value=verdi,
        ambiguous_zero=serie["entities"][kode][aar]["ambiguous_zero"],
        median=round(median, DESIMALER_VERDI),
        deviation_pct=_prosent(avvik),
        # Store avvik sier mer som multiplikator enn som prosent. Verdien er
        # den samme — det er formuleringen som skifter, se § 7.
        factor=round(verdi / median, 1),
        express_as="factor" if avvik >= ANOMALY_FACTOR_PCT else "percent",
        n_years=len(punkter),
        first_year=min(punkter),
        last_year=max(punkter),
    )


def trend(serie, kode):
    """Theil–Sen med Mann–Kendall, innenfor én serie — én kilde, én quality.

    Serier der nullverdiene gjør trenden meningsløs, får ingen. Hvilke det er,
    og hvorfor, står i § 7. Avledningen føres likevel, med ``computed: false``
    og en grunn, slik at siden kan si at trenden ikke er beregnet i stedet for
    å tie om den.
    """
    felles = dict(_felles(serie, kode), kind="trend", computed=False)
    punkter = _punkter(serie, kode)
    aar = serie["entities"][kode]

    if serie["smoothed"]:
        return dict(felles, reason="smoothed", n_years=len(punkter))

    # Aggregatene har sin egen grense. En trend for verden eller en region
    # leses som en oppsummering, og tåler ikke å hvile på et enkeltår (§ 7).
    min_aar = (
        TREND_MIN_YEARS_AGGREGATE
        if serie["levels"][kode] in AGGREGATNIVAA
        else TREND_MIN_YEARS
    )
    if len(punkter) < min_aar:
        return dict(
            felles,
            reason="too_few_years",
            n_years=len(punkter),
            min_years=min_aar,
        )

    tvetydige = [a for a in sorted(aar) if aar[a]["ambiguous_zero"]]
    andel_null = len(tvetydige) / len(punkter)
    if andel_null > TREND_MAX_ZERO_SHARE:
        return dict(
            felles,
            reason="zero_share",
            n_years=len(punkter),
            zero_share=round(andel_null, DESIMALER_ANDEL),
            max_zero_share=TREND_MAX_ZERO_SHARE,
        )

    hale = 0
    for a, _verdi in reversed(punkter):
        if aar[a]["ambiguous_zero"]:
            hale += 1
        else:
            break
    if hale > TREND_MAX_ZERO_TAIL:
        return dict(
            felles,
            reason="zero_tail",
            n_years=len(punkter),
            zero_tail=hale,
            max_zero_tail=TREND_MAX_ZERO_TAIL,
        )

    stigning = theil_sen(punkter)
    s, _varians, z, p = mann_kendall(punkter)
    signifikant = p < TREND_ALPHA

    if not signifikant or stigning == 0:
        retning = "none"
    elif stigning > 0:
        retning = "increasing"
    else:
        retning = "decreasing"

    return dict(
        _felles(serie, kode),
        kind="trend",
        computed=True,
        n_years=len(punkter),
        first_year=punkter[0][0],
        last_year=punkter[-1][0],
        slope_per_year=round(stigning, DESIMALER_VERDI),
        slope_per_decade=round(stigning * 10, DESIMALER_VERDI),
        s=s,
        z=round(z, 4),
        p_value=round(p, DESIMALER_P),
        alpha=TREND_ALPHA,
        significant=signifikant,
        direction=retning,
    )


def andel(serie, kode, aar, verdenstall):
    """Entitetens andel av det globale totaltallet for året."""
    punkter = dict(_punkter(serie, kode))
    if aar not in punkter or not verdenstall:
        return None
    verdi = punkter[aar]
    return dict(
        _felles(serie, kode),
        kind="share_of_world",
        period=str(aar),
        value=verdi,
        world_value=verdenstall,
        share=round(verdi / verdenstall, DESIMALER_ANDEL),
        share_pct=_prosent(verdi / verdenstall * 100),
    )


def konsentrasjon(serie, aar, verdenstall):
    """Andelen av totalen som de N største entitetene står for.

    Nevneren er seriens eget verdenstall der det finnes. For rutenettkildene
    er det summert fra rutenettet og bærer også areal som ikke lot seg
    tilskrive et land (§ 5), så summen av landene er ikke det samme tallet.
    Hvilken nevner som er brukt, står i ``denominator_kind``.
    """
    land = [
        (kode, aar_verdier[aar]["value"])
        for kode, aar_verdier in serie["entities"].items()
        if aar in aar_verdier and serie["levels"][kode] == "country"
    ]
    # Med like mange entiteter som N står de største for hele totalen, og
    # konsentrasjonen sier ingenting. K5 og K7 har ett land hver.
    if len(land) <= CONCENTRATION_TOP_N:
        return None

    land.sort(key=lambda rad: (-rad[1], rad[0]))
    storste = land[:CONCENTRATION_TOP_N]
    sum_land = sum(v for _, v in land)
    nevner = verdenstall if verdenstall else sum_land
    if not nevner:
        return None

    sum_storste = sum(v for _, v in storste)
    return {
        "kind": "concentration",
        "series_id": serie["series_id"],
        "source_id": serie["source_id"],
        "quality": serie["quality"],
        "indicator": serie["indicator"],
        "unit": serie["unit"],
        "period": str(aar),
        "top_n": len(storste),
        "n_entities": len(land),
        "denominator": round(nevner, DESIMALER_VERDI),
        "denominator_kind": "world_row" if verdenstall else "country_sum",
        "top_value": round(sum_storste, DESIMALER_VERDI),
        "share": round(sum_storste / nevner, DESIMALER_ANDEL),
        "share_pct": _prosent(sum_storste / nevner * 100),
        "entities": [
            {"entity": kode, "entity_name": serie["names"][kode], "value": verdi}
            for kode, verdi in storste
        ],
    }


def arealsammenligning(verdi, landarealer, navn):
    """Landet hvis landareal ligger nærmest en arealverdi i km².

    Valget er maskinelt: minst absolutt avvik. Avviket i prosent følger med,
    slik at leseren ser hvor god tilnærmingen er (§ 7).
    """
    if verdi is None or verdi <= 0 or not landarealer:
        return None
    kode, areal = min(
        landarealer.items(), key=lambda rad: (abs(rad[1] - verdi), rad[0])
    )
    return {
        "kind": "area_comparison",
        "value": round(verdi, DESIMALER_VERDI),
        "unit": "km2",
        "comparison_entity": kode,
        "comparison_entity_name": navn.get(kode, kode),
        "comparison_area_km2": areal,
        "deviation_pct": _prosent((verdi - areal) / areal * 100),
    }


def kartdekning(serie, aar, flater, landarealer, navn):
    """Hvor mange av entitetene med tall som har en egen flate på kartet.

    Forenklingen av kartgeometrien tar bort de minste landene: etter den har de
    ingen flate igjen å tegne (§ 12). De har fortsatt tall i tabellen, og
    figuren skal kunne si hvor mange det gjelder uten å ramse dem opp.

    Illustrasjonen viser hvor grensen faktisk går: det minste landet som ennå
    har en flate, mot det største som ikke har det. Grensen følger form like
    mye som areal, så de to er ikke sortert etter hverandre — og det er nettopp
    derfor begge oppgis.
    """
    med_verdi = sorted(
        kode
        for kode, aar_verdier in serie["entities"].items()
        if serie["levels"][kode] == "country" and aar in aar_verdier
    )
    if not med_verdi:
        return None

    med = [kode for kode in med_verdi if kode in flater]
    uten = [kode for kode in med_verdi if kode not in flater]

    def ytterpunkt(koder, velg):
        kandidater = {k: landarealer[k] for k in koder if k in landarealer}
        if not kandidater:
            return None
        kode = velg(kandidater.items(), key=lambda rad: (rad[1], rad[0]))[0]
        return {
            "entity": kode,
            "entity_name": navn.get(kode, kode),
            "land_area_km2": kandidater[kode],
        }

    return {
        "kind": "map_area_coverage",
        "geometry": GEO_WORLD_JSON.name,
        "period": str(aar),
        "entities_with_value": len(med_verdi),
        "entities_with_area": len(med),
        "entities_without_area": len(uten),
        "smallest_with_area": ytterpunkt(med, min),
        "largest_without_area": ytterpunkt(uten, max),
    }



# --- Sesong (CLAUDE.md § 7) ---------------------------------------------
#
# Ukesseriene håndteres for seg. De årlige avledningene regner på år, og en
# uke er ikke et år — men dekning og sesong er definert for begge.

UKEPERIODE = re.compile(r"^(\d{4})-W(\d{2})$")


def ukegrunnlag(observasjoner):
    """Ordner ukesobservasjonene per serie, entitet, år og uke.

    Samme regel som for årsseriene: inneværende år kjennes på
    f_incomplete_year og holdes utenfor grunnlaget for median og persentiler,
    men føres for seg slik at figuren kan tegne det (§ 7).
    """
    serier = {}
    for o in observasjoner:
        treff = UKEPERIODE.match(o["period"])
        if not treff:
            continue

        serie = serier.setdefault(
            o["series_id"],
            {
                "series_id": o["series_id"],
                "source_id": o["source_id"],
                "quality": o["quality"],
                "indicator": o["indicator"],
                "unit": o["unit"],
                "entities": defaultdict(lambda: defaultdict(dict)),
                "names": {},
                "levels": {},
                "incomplete_years": set(),
            },
        )
        serie["names"][o["entity"]] = o["entity_name"]
        serie["levels"][o["entity"]] = o["level"]

        aar, uke = int(treff.group(1)), int(treff.group(2))
        if UFULLSTENDIG in o["footnotes"]:
            serie["incomplete_years"].add(aar)
        serie["entities"][o["entity"]][aar][uke] = o["value"]

    for serie in serier.values():
        serie["incomplete_years"] = sorted(serie["incomplete_years"])
    return serier


def _kumulativ(uker):
    """Kumulativ sum uke for uke, fra uke 1 til den siste uken med måling."""
    ut = {}
    sum_ = 0.0
    for uke in range(1, max(uker) + 1 if uker else 1):
        if uke in uker:
            sum_ += uker[uke]
            ut[uke] = round(sum_, DESIMALER_VERDI)
    return ut


def ukesdekning(serie, kode):
    """Dekningen for en ukesserie: år, uker og hvilke år som er ufullstendige."""
    aarene = serie["entities"][kode]
    if not aarene:
        return None
    hele = [a for a in sorted(aarene) if a not in serie["incomplete_years"]]
    return dict(
        _felles(serie, kode),
        kind="coverage",
        first_year=min(aarene),
        last_year=max(aarene),
        n_years=len(aarene),
        complete_years=hele,
        n_complete_years=len(hele),
        incomplete_years=serie["incomplete_years"],
        n_weeks=sum(len(uker) for uker in aarene.values()),
    )


def sesongprofil(serie, kode):
    """Median brent areal per uke, over de fullstendige årene.

    Dette er sesongprofilen: når på året det brenner, uke for uke. Medianen
    brukes framfor gjennomsnittet fordi ett år som stikker ut ikke skal flytte
    hele kurven.
    """
    aarene = {
        aar: uker
        for aar, uker in serie["entities"][kode].items()
        if aar not in serie["incomplete_years"]
    }
    if not aarene:
        return None

    per_uke = defaultdict(list)
    for uker in aarene.values():
        for uke, verdi in uker.items():
            per_uke[uke].append(verdi)

    return dict(
        _felles(serie, kode),
        kind="season_week",
        basis_years=sorted(aarene),
        n_years=len(aarene),
        weeks=[
            {
                "week": uke,
                "median": round(_median(per_uke[uke]), DESIMALER_VERDI),
                "n_years": len(per_uke[uke]),
            }
            for uke in sorted(per_uke)
        ],
    )


def sesongband(serie, kode):
    """Kumulativ median og persentilbånd per uke, over fullstendige år.

    Båndet dekker SEASON_BAND_PCT — se CLAUDE.md § 7. Inneværende år føres for
    seg, med sin egen kumulative kurve, og inngår ikke i båndet.
    """
    alle = serie["entities"][kode]
    hele = {
        aar: _kumulativ(uker)
        for aar, uker in alle.items()
        if aar not in serie["incomplete_years"]
    }
    if not hele:
        return None

    lav, hoy = SEASON_BAND_PCT
    per_uke = defaultdict(list)
    for kurve in hele.values():
        for uke, verdi in kurve.items():
            per_uke[uke].append(verdi)

    ufullstendig = None
    for aar in serie["incomplete_years"]:
        if aar in alle:
            kurve = _kumulativ(alle[aar])
            ufullstendig = {
                "year": aar,
                "last_week": max(kurve) if kurve else None,
                "weeks": [
                    {"week": uke, "value": verdi} for uke, verdi in sorted(kurve.items())
                ],
            }

    return dict(
        _felles(serie, kode),
        kind="season_band",
        basis_years=sorted(hele),
        n_years=len(hele),
        band_pct=list(SEASON_BAND_PCT),
        # Hva kantene hviler på. Med få år er de interpolert mellom to
        # enkeltår, og båndet er ikke fastere enn det.
        band_edges={
            "low": persentilplass(len(hele), lav),
            "high": persentilplass(len(hele), hoy),
        },
        weeks=[
            {
                "week": uke,
                "median": round(_median(per_uke[uke]), DESIMALER_VERDI),
                "low": round(persentil(per_uke[uke], lav), DESIMALER_VERDI),
                "high": round(persentil(per_uke[uke], hoy), DESIMALER_VERDI),
                "n_years": len(per_uke[uke]),
            }
            for uke in sorted(per_uke)
        ],
        incomplete_year=ufullstendig,
    )


# --- Sammenstilling --------------------------------------------------------


def _landarealer():
    with open(LAND_AREA_JSON, encoding="utf-8") as f:
        return json.load(f)["areas"]


def _kartflater():
    """Entitetene kartgeometrien har en flate for, slik den ligger nå (§ 12)."""
    with open(GEO_WORLD_JSON, encoding="utf-8") as f:
        return {flate["id"] for flate in json.load(f)["features"]}


def _verdenstall(serie, aar):
    """Seriens eget verdenstall for året, der serien har en verdensrad."""
    for kode, aar_verdier in serie["entities"].items():
        if serie["levels"][kode] == "world" and aar in aar_verdier:
            return aar_verdier[aar]["value"]
    return None


def avled(observasjoner):
    """Bygger alle avledningene, med id som nøkkel."""
    serier = grunnlag(observasjoner)
    landarealer = _landarealer()
    kartflater = _kartflater()
    navn = {}
    for serie in serier.values():
        navn.update(serie["names"])

    avledninger = {}
    sammendrag = {
        "series": len(serier),
        "trend": {"computed": 0, "skipped": defaultdict(int)},
        "coverage": 0,
        "rank": 0,
        "anomaly": 0,
        "share_of_world": 0,
        "concentration": 0,
        "coverage_overlap": 0,
        "area_comparison": 0,
        "map_area_coverage": 0,
        "always_zero_entities": 0,
    }

    # Årene flere serier for samme indikator dekker samtidig. Et enkeltår som
    # sammenligner to produkter, må være et år begge faktisk måler, og hvilket
    # år det er, følger av dekningen (§ 7).
    per_indikator = defaultdict(dict)
    for serie_id, serie in serier.items():
        per_indikator[serie["indicator"]][serie_id] = serie

    for indikator, gruppe in sorted(per_indikator.items()):
        entiteter = sorted({k for s in gruppe.values() for k in s["entities"]})
        for kode in entiteter:
            overlapp = felles_dekning(gruppe, kode)
            if overlapp:
                overlapp["indicator"] = indikator
                overlapp["entity_name"] = navn.get(kode, kode)
                avledninger[f"coverage_overlap.{indikator}.{kode}"] = overlapp
                sammendrag["coverage_overlap"] += 1

    for serie_id, serie in sorted(serier.items()):
        siste = serie["last_complete_year"]
        alltid_null = set(serie["always_zero"])
        sammendrag["always_zero_entities"] += len(alltid_null)
        forholdstall = serie["unit"] in FORHOLDSTALL_ENHETER
        summerbar = serie["unit"] in SUMMERBARE_ENHETER

        for kode in sorted(serie["entities"]):
            avledninger[f"coverage.{serie_id}.{kode}"] = dekning(serie, kode)
            sammendrag["coverage"] += 1

            t = trend(serie, kode)
            avledninger[f"trend.{serie_id}.{kode}"] = t
            if t["computed"]:
                sammendrag["trend"]["computed"] += 1
            else:
                sammendrag["trend"]["skipped"][t["reason"]] += 1

            # Rangering og avvik fra normal utelater entiteter uten en eneste
            # påvist brann i et fullstendig år (§ 7).
            if kode in alltid_null or not forholdstall:
                continue

            # Per entitet regnes siste fullstendige år, som er året brødteksten
            # snakker om. Verdensraden får hele serien, slik at en setning også
            # kan vise til et enkeltår lenger tilbake.
            aarene = (
                sorted(serie["entities"][kode])
                if serie["levels"][kode] == "world"
                else [siste]
            )

            for aar in aarene:
                r = rangering(serie, kode, aar)
                if r:
                    avledninger[f"rank.{serie_id}.{kode}.{aar}"] = r
                    sammendrag["rank"] += 1
                a = avvik_fra_normal(serie, kode, aar)
                if a:
                    avledninger[f"anomaly.{serie_id}.{kode}.{aar}"] = a
                    sammendrag["anomaly"] += 1
                if summerbar and serie["levels"][kode] != "world":
                    s = andel(serie, kode, aar, _verdenstall(serie, aar))
                    if s:
                        avledninger[f"share.{serie_id}.{kode}.{aar}"] = s
                        sammendrag["share_of_world"] += 1

        if summerbar:
            for aar in sorted({a for v in serie["entities"].values() for a in v}):
                k = konsentrasjon(serie, aar, _verdenstall(serie, aar))
                if k:
                    avledninger[f"concentration.{serie_id}.{aar}"] = k
                    sammendrag["concentration"] += 1

        if serie["unit"] == "km2" and siste is not None:
            s = arealsammenligning(_verdenstall(serie, siste), landarealer, navn)
            if s:
                avledninger[f"area_comparison.{serie_id}.{siste}"] = dict(
                    s,
                    series_id=serie_id,
                    source_id=serie["source_id"],
                    period=str(siste),
                )
                sammendrag["area_comparison"] += 1

        if siste is not None:
            d = kartdekning(serie, siste, kartflater, landarealer, navn)
            if d:
                avledninger[f"map_area_coverage.{serie_id}.{siste}"] = dict(
                    d,
                    series_id=serie_id,
                    source_id=serie["source_id"],
                    quality=serie["quality"],
                    indicator=serie["indicator"],
                )
                sammendrag["map_area_coverage"] += 1

    # Ukesseriene: dekning, sesongprofil og sesongbånd (§ 7).
    for serie_id, serie in sorted(ukegrunnlag(observasjoner).items()):
        for kode in sorted(serie["entities"]):
            for navn, avledning_ in (
                ("coverage", ukesdekning(serie, kode)),
                ("season_week", sesongprofil(serie, kode)),
                ("season_band", sesongband(serie, kode)),
            ):
                if avledning_:
                    avledninger[f"{navn}.{serie_id}.{kode}"] = avledning_
                    sammendrag[navn] = sammendrag.get(navn, 0) + 1

    sammendrag["trend"]["skipped"] = dict(
        sorted(sammendrag["trend"]["skipped"].items())
    )
    sammendrag["derivations"] = len(avledninger)
    return serier, avledninger, sammendrag


def _seriegrunnlag(serier):
    """Grunnlaget hver serie er regnet over, slik en setning kan oppgi det."""
    return {
        serie_id: {
            "source_id": serie["source_id"],
            "quality": serie["quality"],
            "indicator": serie["indicator"],
            "unit": serie["unit"],
            "first_year": serie["first_year"],
            "last_complete_year": serie["last_complete_year"],
            "incomplete_years": serie["incomplete_years"],
            "n_entities": len(serie["entities"]),
            "always_zero_entities": serie["always_zero"],
        }
        for serie_id, serie in sorted(serier.items())
    }


def skriv(serier, avledninger, sammendrag):
    """Skriver insights.json. Nøklene er sortert, slik at samme input gir
    samme fil (T3)."""
    innhold = {
        "_om": (
            "Maskinelle avledninger. Alle tallfestede påstander i brødteksten "
            "fylles herfra (CLAUDE.md P3). Nøkkelen under «derivations» er "
            "verdien HTML bærer i data-derivation-attributtet."
        ),
        "_skjema": "se CLAUDE.md § 7 og etl/derive.py",
        "series": _seriegrunnlag(serier),
        "summary": sammendrag,
        "derivations": dict(sorted(avledninger.items())),
    }
    with open(INSIGHTS_JSON, "w", encoding="utf-8") as f:
        json.dump(innhold, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return INSIGHTS_JSON


def main():
    observasjoner = validate.les_publiserte()
    if not observasjoner:
        raise RuntimeError("ingen kanoniske filer under data/processed/")

    serier, avledninger, sammendrag = avled(observasjoner)
    sti = skriv(serier, avledninger, sammendrag)

    print(f"derive: {len(avledninger)} avledninger → {sti.name}")
    print(
        f"derive: trend beregnet for {sammendrag['trend']['computed']} entiteter, "
        f"ikke beregnet for {sum(sammendrag['trend']['skipped'].values())}"
    )
    for grunn, antall in sammendrag["trend"]["skipped"].items():
        print(f"derive:   {grunn}: {antall}")
    return avledninger


if __name__ == "__main__":
    main()
