"""Maskinelle avledninger.

Ikke implementert ennå. Denne filen beskriver kun ansvarsområdet.

Ansvar
------
Leser kanoniske serier fra ``data/processed/`` og skriver
``data/processed/insights.json``.

Enhver tallfestet påstand i brødteksten på siden kommer herfra. Beregningene
skal være deterministiske: samme input gir samme output. Hver avledning får en
stabil id, slik at HTML kan bære et ``data-derivation``-attributt som peker
tilbake til beregningen.

Hvilke avledninger som er tillatt, og hvilke som ikke er det, står i
CLAUDE.md § 7. Listen gjentas ikke her.
"""
