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
    GEO_MIN_RING_POINTS,
    GEO_SIMPLIFY_TOLERANCE_DEG,
    GEO_WORLD_JSON,
    LAND_NO_JSON,
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


def _ring(ring):
    """Én forenklet ring, eller None hvis den ikke lenger er en flate.

    En ring som faller under GEO_MIN_RING_POINTS punkter, har ingen flate igjen
    å tegne. Da utelates den heller enn å bli en strek.
    """
    forenklet = _rund(forenkle(list(ring), GEO_SIMPLIFY_TOLERANCE_DEG))
    if forenklet and forenklet[0] != forenklet[-1]:
        forenklet.append(forenklet[0])
    if len(forenklet) < GEO_MIN_RING_POINTS:
        return None
    return forenklet


def forenkle_geometri(geometri):
    """Forenkler en GeoJSON-geometri. Returnerer None hvis alt forsvant."""
    type_ = geometri["type"]
    if type_ == "Polygon":
        ringer = [r for r in (_ring(ring) for ring in geometri["coordinates"]) if r]
        return {"type": "Polygon", "coordinates": ringer} if ringer else None

    if type_ == "MultiPolygon":
        flater = []
        for polygon in geometri["coordinates"]:
            ringer = [r for r in (_ring(ring) for ring in polygon) if r]
            if ringer:
                flater.append(ringer)
        return {"type": "MultiPolygon", "coordinates": flater} if flater else None

    raise ValueError(f"uventet geometritype: {type_}")


def _land():
    with open(LAND_NO_JSON, encoding="utf-8") as f:
        return json.load(f)["entities"]


def bygg(sti=None):
    """Leser K6-laget og returnerer (features, sammendrag).

    Flere kartenheter kan dele entity-kode. De samles til én flate per kode,
    slik at kartet har nøyaktig én form per entitet — den samme entiteten som
    tallene er ført på.
    """
    geometrier, utelatt = k6_natural_earth.geometrier(sti)
    land = _land()  # fasit for hvilke entiteter som finnes (§ 6)

    per_kode = {}
    for kode, geometri in geometrier:
        forenklet = forenkle_geometri(geometri)
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
        "without_code": utelatt,
        "missing_geometry": sorted(k for k in land if k not in per_kode),
    }
    return features, sammendrag


def skriv(features, sammendrag):
    innhold = {
        "_om": (
            "Forenklet kartgeometri for verdenskartet, bygget fra "
            "kartenhetslaget i K6 — det samme laget landarealene og "
            "rutenettfordelingen bruker. Se CLAUDE.md § 12 og etl/geo.py."
        ),
        "_skjema": "GeoJSON FeatureCollection. id og properties.entity er entity-koden.",
        "source_id": k6_natural_earth.SOURCE_ID,
        "layer": k6_natural_earth.LAG,
        "simplify_tolerance_deg": GEO_SIMPLIFY_TOLERANCE_DEG,
        "coord_decimals": GEO_COORD_DECIMALS,
        "summary": sammendrag,
        "type": "FeatureCollection",
        "features": features,
    }
    with open(GEO_WORLD_JSON, "w", encoding="utf-8") as f:
        json.dump(innhold, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return GEO_WORLD_JSON


def main():
    k6_natural_earth.hent()
    features, sammendrag = bygg()
    sti = skriv(features, sammendrag)
    print(
        f"geo: {sammendrag['entities']} entiteter, "
        f"{sammendrag['points']} punkter → {sti.name} "
        f"({sti.stat().st_size / 1024:.0f} KiB)"
    )
    if sammendrag["missing_geometry"]:
        print(
            f"geo: {len(sammendrag['missing_geometry'])} entiteter i land_no.json "
            "har ingen geometri: " + ", ".join(sammendrag["missing_geometry"])
        )
    return sti


if __name__ == "__main__":
    main()
