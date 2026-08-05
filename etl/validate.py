"""Validering før publisering.

Ikke implementert ennå. Denne filen beskriver kun ansvarsområdet.

Ansvar
------
Kjøres mellom ``normalize.py`` og ``derive.py``. Avviser ugyldig output før den
når siden. Feiler valideringen, beholdes forrige datasett, feilen logges i
``data/_status.json``, og siden viser en diskré merknad om at akkurat den
serien ikke er oppdatert.

Kontroller
----------
* Alle verdifelt er i km² og har enhet i navnet (``*_km2``).
* ``period`` er gyldig ISO 8601: YYYY, YYYY-MM eller YYYY-Www.
* ``entity`` er gyldig ISO3-kode eller kjent regionkode.
* ``level`` er country | region | world.
* ``quality`` er measured | reported | reconstructed.
* Manglende observasjoner er «ingen data», ikke 0.
* Ingen negative arealverdier.
* Hver ``source_id`` finnes i ``data/_sources.json`` med lisens, lenke,
  dekningsperiode og nedlastingsdato — kildelinjen under figurene kan ikke
  bygges uten.
* Hver ``series_id`` peker på en fil under ``data/processed/`` som faktisk
  finnes, slik at figurenes CSV-lenker ikke blir døde.
* Alle refererte fotnote-id-er er definert.
* Dekningsperioden i metadataene stemmer med dataene.
* Store avvik fra forrige kjøring flagges i stedet for å publiseres stille.
"""
