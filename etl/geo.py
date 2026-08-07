"""Forenklet kartgeometri → data/geo/verden.json.

Kartet på siden tegnes fra geometri som ligger i repoet, ikke fra en
flistjeneste (T2). Denne modulen lager den filen, av det samme
kartenhetslaget fra K6 som landarealene og rutenettfordelingen bruker — ellers
ville kartet vist andre grenser enn tallene er regnet på (§ 12).

Full oppløsning er unødvendig for et verdenskart og gjør både repoet og
byggetiden større. Geometrien forenkles derfor med Douglas–Peucker, med
terskler fra ``etl/schema.py``.

Jobben laster ned en shapefil og hører hjemme i GitHub Actions, ikke i en
utviklingssesjon (T4). Se ``.github/workflows/geo.yml``.

Kjøres som modul fra repotoppen: ``python -m etl.geo``
"""

import json

from etl.schema import (
    GEO_COORD_DECIMALS,
    GEO_DIR,
    GEO_EUROPE_JSON,
    GEO_EUROPE_SIMPLIFY_TOLERANCE_DEG,
    GEO_MIN_RING_POINTS,
    GEO_SIMPLIFY_TOLERANCE_DEG,
    GEO_WORLD_JSON,
    LAND_NO_JSON,
    PROCESSED_DIR,
)
from etl.sources import k6_natural_earth


def _avstand_til_linje(punkt, start, slutt):
    """Vinkelrett avstand fra punkt til linjen start–slutt, i grader."""
    (x, y), (x1, y1), (x2, y2) = punkt, start, slutt
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def forenkle(punkter, toleranse):
    """Douglas–Peucker. Beholder endepunktene og formen, fjerner mellomledd."""
    if len(punkter) < 3:
        return list(punkter)

    stakk = [(0, len(punkter) - 1)]
    behold = {0, len(punkter) - 1}
    while stakk:
        forst, sist = stakk.pop()
        if sist <= forst + 1:
            continue
        storst, storst_i = 0.0, forst
        for i in range(forst + 1, sist):
            d = _avstand_til_linje(punkter[i], punkter[forst], punkter[sist])
            if d > storst:
                storst, storst_i = d, i
        if storst > toleranse:
            behold.add(storst_i)
            stakk.append((forst, storst_i))
            stakk.append((storst_i, sist))

    return [punkter[i] for i in sorted(behold)]


def _rund(punkter):
    return [
        [round(x, GEO_COORD_DECIMALS), round(y, GEO_COORD_DECIMALS)]
        for x, y in punkter
    ]


def _ringer(geometri):
    """Ringene i en geometri, med posisjonen sin, så de kan settes tilbake."""
    type_ = geometri["type"]
    if type_ == "Polygon":
        return [((i,), ring) for i, ring in enumerate(geometri["coordinates"])]
    if type_ == "MultiPolygon":
        return [
            ((i, j), ring)
            for i, polygon in enumerate(geometri["coordinates"])
            for j, ring in enumerate(polygon)
        ]
    raise ValueError(f"uventet geometritype: {type_}")


def behold_punkter(geometrier, toleranse):
    """Punktene forenklingen skal beholde, bestemt på tvers av alle ringene.

    **Dette er det som holder nabolandene sammen.** Natural Earth deler
    koordinater eksakt mellom naboer: samme punkt ligger i begge landenes ring.
    Forenkles hver ring for seg, kan Douglas–Peucker beholde et punkt i det ene
    landet og forkaste det i det andre. Grensen river seg da fra hverandre, og
    kartet får en hvit stripe mellom to land som deler grense.

    Derfor avgjøres punktene én gang, felles: et punkt beholdes hvis **minst
    én** ring trenger det. Da får begge naboene nøyaktig samme punktrekke langs
    den delte grensen, og stripen kan ikke oppstå.

    Prisen er at en ring kan beholde et punkt dens egen form ikke trengte.
    Det er en billig pris for en grense som holder.
    """
    behold = set()
    for geometri in geometrier:
        for _, ring in _ringer(geometri):
            for punkt in forenkle(_rund(ring), toleranse):
                behold.add((punkt[0], punkt[1]))
    return behold


def _ring(ring, behold):
    """Én ring med bare de punktene som skal beholdes.

    En ring som faller under GEO_MIN_RING_POINTS punkter, har ingen flate igjen
    å tegne. Da utelates den heller enn å bli en strek.
    """
    rundet = _rund(ring)
    igjen = [p for p in rundet if (p[0], p[1]) in behold]
    if igjen and igjen[0] != igjen[-1]:
        igjen.append(igjen[0])
    if len(igjen) < GEO_MIN_RING_POINTS:
        return None
    return igjen


def forenkle_geometri(geometri, behold):
    """Forenkler en GeoJSON-geometri mot et felles punktutvalg.

    Returnerer None hvis alt forsvant.
    """
    type_ = geometri["type"]
    if type_ == "Polygon":
        ringer = [r for r in (_ring(ring, behold) for ring in geometri["coordinates"]) if r]
        return {"type": "Polygon", "coordinates": ringer} if ringer else None

    if type_ == "MultiPolygon":
        flater = []
        for polygon in geometri["coordinates"]:
            ringer = [r for r in (_ring(ring, behold) for ring in polygon) if r]
            if ringer:
                flater.append(ringer)
        return {"type": "MultiPolygon", "coordinates": flater} if flater else None

    raise ValueError(f"uventet geometritype: {type_}")


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def effis_land():
    """Entitetene EFFIS' egen kartlegging fører, lest av det ferdige datasettet.

    Europa-kartet i S4 skal vise nøyaktig de landene serien dekker, verken
    flere eller færre. Settet leses derfor av serien selv og skrives ikke som
    en liste her — et land som kommer til i EFFIS-nettverket, skal komme med
    uten at noen husker å redigere en liste (§ 7, T5).
    """
    with open(PROCESSED_DIR / "burned_area.json", encoding="utf-8") as f:
        observasjoner = json.load(f)
    return {
        o["entity"]
        for o in observasjoner
        if o["series_id"] == "effis_rda_annual_burned_area"
    }


def bygg(sti=None, toleranse=GEO_SIMPLIFY_TOLERANCE_DEG, entiteter=None):
    """Leser K6-laget og returnerer (features, sammendrag).

    Flere kartenheter kan dele entity-kode. De samles til én flate per kode,
    slik at kartet har nøyaktig én form per entitet — den samme entiteten som
    tallene er ført på.

    ``entiteter`` avgrenser utvalget til et kart som ikke viser hele verden.
    Da regnes manglende geometri mot det utvalget, ikke mot alle entitetene i
    land_no.json.
    """
    geometrier, utelatt = k6_natural_earth.geometrier(sti)
    land = _land()  # fasit for hvilke entiteter som finnes (§ 6)

    valgte = [
        (kode, geometri)
        for kode, geometri in geometrier
        if entiteter is None or kode in entiteter
    ]

    # Punktene avgjøres først, på tvers av alle ringene, slik at delte grenser
    # beholder samme punktrekke i begge landene. Se behold_punkter().
    behold = behold_punkter([g for _, g in valgte], toleranse)

    per_kode = {}
    for kode, geometri in valgte:
        forenklet = forenkle_geometri(geometri, behold)
        if forenklet is None:
            continue
        flater = (
            [forenklet["coordinates"]]
            if forenklet["type"] == "Polygon"
            else forenklet["coordinates"]
        )
        per_kode.setdefault(kode, []).extend(flater)

    # Navnet står ikke her. Det bor i land_no.json, som er fasit for hva en
    # entitet heter (§ 6), og en kopi i geometrifilen ville divergert fra den.
    ukjente = sorted(k for k in per_kode if k not in land)
    features = [
        {
            "type": "Feature",
            "id": kode,
            "properties": {"entity": kode},
            "geometry": {"type": "MultiPolygon", "coordinates": per_kode[kode]},
        }
        for kode in sorted(per_kode)
    ]

    sammendrag = {
        "entities": len(features),
        "rings": sum(len(f) for flater in per_kode.values() for f in flater),
        "points": sum(
            len(ring)
            for flater in per_kode.values()
            for polygon in flater
            for ring in polygon
        ),
        "unknown_entities": ukjente,
        "without_code": utelatt if entiteter is None else [],
        "missing_geometry": sorted(
            k for k in (entiteter if entiteter is not None else land) if k not in per_kode
        ),
    }
    return features, sammendrag


def skriv(features, sammendrag, sti=GEO_WORLD_JSON, toleranse=GEO_SIMPLIFY_TOLERANCE_DEG, om=None):
    innhold = {
        "_om": om
        or (
            "Forenklet kartgeometri for verdenskartet, bygget fra "
            "kartenhetslaget i K6 — det samme laget landarealene og "
            "rutenettfordelingen bruker. Se CLAUDE.md § 12 og etl/geo.py."
        ),
        "_skjema": "GeoJSON FeatureCollection. id og properties.entity er entity-koden.",
        "source_id": k6_natural_earth.SOURCE_ID,
        "layer": k6_natural_earth.LAG,
        "simplify_tolerance_deg": toleranse,
        "coord_decimals": GEO_COORD_DECIMALS,
        "summary": sammendrag,
        "type": "FeatureCollection",
        "features": features,
    }
    with open(sti, "w", encoding="utf-8") as f:
        json.dump(innhold, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return sti


def _rapporter(sammendrag, sti, hva):
    print(
        f"geo: {sammendrag['entities']} entiteter, "
        f"{sammendrag['points']} punkter → {sti.name} "
        f"({sti.stat().st_size / 1024:.0f} KiB)"
    )
    if sammendrag["missing_geometry"]:
        print(
            f"geo: {len(sammendrag['missing_geometry'])} {hva} har ingen "
            "geometri: " + ", ".join(sammendrag["missing_geometry"])
        )


def kandidater(toleranser, sti=None):
    """Skriver verdenskartet ved flere terskler, til sammenligning.

    Forenklingen skal velges av hvordan kartet ser ut, ikke av et tall. Da
    trengs det noe å se på. Filene er midlertidige og skal ikke bli liggende.
    """
    for toleranse in toleranser:
        features, sammendrag = bygg(sti, toleranse=toleranse)
        navn = f"kandidat-{str(toleranse).replace('.', '_')}.json"
        sti_ut = skriv(
            features,
            sammendrag,
            GEO_DIR / navn,
            toleranse,
            f"Midlertidig kandidat ved toleranse {toleranse}°, til å velge "
            "forenkling av. Skal ikke publiseres.",
        )
        print(
            f"kandidat {toleranse}°: {sammendrag['points']} punkter, "
            f"{sammendrag['entities']} entiteter, "
            f"{len(sammendrag['missing_geometry'])} uten flate → "
            f"{sti_ut.name} ({sti_ut.stat().st_size / 1024:.0f} KiB)"
        )


def main():
    """Bygger begge kartfilene av samme nedlasting.

    Verdenskartet og Europa-kartet tegner ulikt store områder på samme flate,
    så én piksel dekker ulikt mange grader og forenklingen er ikke den samme.
    Tersklene står i schema.py.
    """
    import sys

    k6_natural_earth.hent()

    argv = sys.argv[1:]
    if argv and argv[0] == "--kandidater":
        return kandidater([float(x) for x in argv[1].split(",")])

    features, sammendrag = bygg()
    sti = skriv(features, sammendrag)
    _rapporter(sammendrag, sti, "entiteter i land_no.json")

    land = effis_land()
    features, sammendrag = bygg(
        toleranse=GEO_EUROPE_SIMPLIFY_TOLERANCE_DEG, entiteter=land
    )
    sti_europa = skriv(
        features,
        sammendrag,
        GEO_EUROPE_JSON,
        GEO_EUROPE_SIMPLIFY_TOLERANCE_DEG,
        "Forenklet kartgeometri for Europa-kartet i S4, bygget fra samme "
        "K6-lag som verdenskartet, men med finere toleranse. Utvalget er "
        "entitetene EFFIS' egen kartlegging fører. Se CLAUDE.md § 12.",
    )
    _rapporter(sammendrag, sti_europa, "EFFIS-entiteter")

    return sti


if __name__ == "__main__":
    main()
