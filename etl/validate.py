"""Validering før publisering.

Ikke implementert ennå. Denne filen beskriver kun ansvarsområdet.

Ansvar
------
Kjøres mellom ``normalize.py`` og ``derive.py``. Kontrollerer at de kanoniske
seriene i ``data/processed/`` er gyldige, og avviser dem før de når siden hvis
de ikke er det.

Feiler valideringen, beholdes forrige datasett, feilen logges i
``data/_status.json``, og siden viser en diskré merknad om at akkurat den
serien ikke er oppdatert.

Reglene som skal håndheves — tillatte kodeverdier, enheter per indikator,
kildekoder, fotnoter og kravene til hver figur — står i CLAUDE.md § 6
(kanonisk datamodell) og § 11 (sjekkliste). De gjentas ikke her.
"""
