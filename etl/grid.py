"""Fra rutenett til landnivå.

Rutenettkildene leverer brent areal per celle, ikke per land. Denne modulen
bygger en vektmaske fra admin-0-geometrien (K6) og summerer et rutenett til
entiteter.

Modulen er enhetsnøytral: den summerer verdiene slik de kommer inn, og vet
ikke om de står i m² eller km². All enhetskonvertering skjer i
``normalize.py`` (CLAUDE.md § 3, T1).

Slik fordeles en celle
----------------------
Hver celle deles i et finere delrutenett, og hver delrute tilskrives det landet
geometrien dekker. Cellens verdi fordeles så mellom landene i cellen etter hvor
stor andel av **landarealet** i cellen hvert av dem har. Havet får ingenting:
brent areal finnes bare på land, og en kystcelle skal ikke miste arealet sitt
fordi halve cellen er sjø.

En celle der ingen landgeometri når fram, kan ikke tilskrives et land. Verdien
går da til den uattribuerte andelen, som kjøringen rapporterer og
``etl.schema.GRID_MAX_UNATTRIBUTED_SHARE`` setter en øvre grense for. Verdien
forsvinner ikke: verdenstotalen summeres fra rutenettet selv, ikke fra landene.

Kjøres ikke direkte. Se ``etl/run_static.py``.
"""

import numpy as np

# Delruter per celle langs hver akse. 5 gir 0,05° for et 0,25°-rutenett, som er
# den oppløsningen FireCCILT11 selv er produsert i før den ble summert opp.
DELRUTER = 5

# Rutenettene er regelmessige. Toleransen fanger opp flyttallsstøy i
# koordinatene, ikke et faktisk ujevnt rutenett.
TOLERANSE = 1e-6


class Rutenettfeil(Exception):
    """Reises når rutenettet ikke er det maskeen ble bygget for."""


class Maske:
    """Vekter fra celle til entitet, bygget for ett bestemt rutenett.

    Maskeen er dyr å bygge og billig å bruke. Den bygges én gang og brukes på
    alle månedsfilene i serien.
    """

    def __init__(self, lat, lon, koder, rute, entitet, vekt, uten_land):
        self.lat = lat
        self.lon = lon
        self.koder = koder
        self._rute = rute
        self._entitet = entitet
        self._vekt = vekt
        self._uten_land = uten_land

    @property
    def form(self):
        return (self.lat.size, self.lon.size)

    def passer(self, lat, lon):
        """Sant hvis maskeen ble bygget for dette rutenettet."""
        return (
            lat.shape == self.lat.shape
            and lon.shape == self.lon.shape
            and np.allclose(lat, self.lat, atol=TOLERANSE)
            and np.allclose(lon, self.lon, atol=TOLERANSE)
        )

    def aggreger(self, verdier):
        """Summerer ett rutenett til entiteter.

        Returnerer (per_entitet, uattribuert, total), der ``per_entitet`` er en
        ordbok fra entity-kode til sum, ``uattribuert`` er den delen av
        rutenettet ingen landgeometri dekker, og ``total`` er summen av hele
        rutenettet. Enheten er den samme som verdiene kom inn med.
        """
        if verdier.shape != self.form:
            raise Rutenettfeil(
                f"rutenettet har formen {verdier.shape}, maskeen er bygget for "
                f"{self.form}"
            )
        flat = np.asarray(verdier, dtype="float64").ravel()
        bidrag = flat[self._rute] * self._vekt
        sum_per_entitet = np.bincount(
            self._entitet, weights=bidrag, minlength=len(self.koder)
        )
        per_entitet = {
            kode: float(sum_per_entitet[i]) for i, kode in enumerate(self.koder)
        }
        return per_entitet, float(flat[self._uten_land].sum()), float(flat.sum())


def _steg(akse, navn):
    diff = np.diff(akse)
    if diff.size == 0:
        raise Rutenettfeil(f"{navn} har bare ett punkt")
    if np.ptp(np.abs(diff)) > TOLERANSE:
        raise Rutenettfeil(f"{navn} er ikke regelmessig fordelt")
    return float(abs(diff[0]))


def bygg_maske(lat, lon, geometrier, delruter=DELRUTER):
    """Bygger vektmasken for et rutenett ut fra admin-0-geometrien.

    ``geometrier`` er en liste med (entity-kode, GeoJSON-geometri), slik
    ``etl.sources.k6_natural_earth.geometrier`` leverer den. Flere geometrier
    kan ha samme kode.
    """
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    lat = np.asarray(lat, dtype="float64")
    lon = np.asarray(lon, dtype="float64")
    dlat = _steg(lat, "lat")
    dlon = _steg(lon, "lon")
    nlat, nlon = lat.size, lon.size

    if not geometrier:
        raise Rutenettfeil("ingen geometrier å bygge maske av")

    # Koordinatene peker på cellenes midtpunkt.
    nord = float(lat.max()) + dlat / 2
    vest = float(lon.min()) - dlon / 2

    koder = sorted({kode for kode, _ in geometrier})
    nummer = {kode: i + 1 for i, kode in enumerate(koder)}  # 0 er «ingen land»

    transform = from_origin(vest, nord, dlon / delruter, dlat / delruter)
    indeks = rasterize(
        ((geometri, nummer[kode]) for kode, geometri in geometrier),
        out_shape=(nlat * delruter, nlon * delruter),
        transform=transform,
        fill=0,
        dtype="int32",
    )

    # Rasteret er tegnet med nord øverst og vest til venstre. Ligger aksene
    # motsatt vei i kilden, speiles rasteret, slik at rad i alltid hører til
    # lat[i]. Rekkefølgen av delruter inne i en celle betyr ingenting — de
    # telles.
    if lat[0] < lat[-1]:
        indeks = np.flipud(indeks)
    if lon[0] > lon[-1]:
        indeks = np.fliplr(indeks)

    flat = indeks.ravel()
    land = np.flatnonzero(flat)
    if land.size == 0:
        raise Rutenettfeil("ingen delruter traff land — geometri og rutenett spriker")

    entitet = flat[land].astype("int64") - 1
    kolonner = nlon * delruter
    rute = (land // kolonner // delruter) * nlon + (land % kolonner // delruter)

    # Én rad per (celle, entitet) med antall delruter, og antall landruter per
    # celle som nevner.
    nokkel = rute * len(koder) + entitet
    unike, antall = np.unique(nokkel, return_counts=True)
    rute_u = unike // len(koder)
    entitet_u = (unike % len(koder)).astype("int64")
    per_rute = np.bincount(rute_u, weights=antall, minlength=nlat * nlon)
    vekt = antall / per_rute[rute_u]

    return Maske(
        lat=lat,
        lon=lon,
        koder=koder,
        rute=rute_u,
        entitet=entitet_u,
        vekt=vekt,
        uten_land=per_rute == 0,
    )
