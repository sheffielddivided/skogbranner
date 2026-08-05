"""Normalisering til kanonisk form.

Ikke implementert ennå. Denne filen beskriver kun ansvarsområdet.

Ansvar
------
Tar råe kildefiler fra ``data/raw/`` slik ``etl/sources/`` leverte dem, og
skriver kanoniske serier til ``data/processed/``.

Kanonisk rad (langformat)::

    entity, entity_name, level, period, indicator, value, unit,
    source_id, series_id, quality, footnotes

* ``level``   — country | region | world
* ``period``  — ISO 8601: YYYY, YYYY-MM eller YYYY-Www
* ``quality`` — measured | reported | reconstructed

Enhet
-----
**All enhetskonvertering skjer her, og ingen andre steder.** Verken derive.py,
byggetrinnet, JavaScript eller en malfil skal konvertere en verdi.

Primærenhet i hele prosjektet er km². Kilder som leverer hektar eller acres
konverteres én gang her, og kun den konverterte verdien finnes videre i
pipelinen.

    1 km2 = 100 ha
    1 km2 = 247.10538 acres  (1 acre = 0.00404686 km2)

Feltnavn bærer enheten: ``burned_area_km2``. Et verdifelt uten enhet i navnet
er en feil.

Regler
------
* Manglende observasjoner skrives som «ingen data», aldri som 0.
* Serier med ulikt ``quality`` slås aldri sammen til én serie.
* Inneværende år merkes som ufullstendig.
* Kjøres kun i GitHub Actions, aldri som fullt løp lokalt.
"""
