"""Maskinelle avledninger.

Ikke implementert ennå. Denne filen beskriver kun ansvarsområdet.

Ansvar
------
Leser kanoniske serier fra ``data/processed/`` og skriver
``data/processed/insights.json``.

Enhver tallfestet påstand i brødteksten på siden kommer herfra. Teksten på
siden er maler som fylles med disse verdiene ved byggetidspunkt. Ingen
håndskrevne tall i brødtekst — aldri (CLAUDE.md P3).

Beregningene skal være deterministiske: samme input gir samme output.

Tillatte avledninger
--------------------
* **Rangering** — «År X er nummer N av M år med data for enhet E»
* **Avvik fra normal** — verdi mot median for hele dekningsperioden, i prosent
* **Trend** — Theil–Sen-estimator med Mann–Kendall-test. Rapporteres med
  retning, størrelse per tiår og p-verdi. Ikke-signifikant trend rapporteres
  som «ingen statistisk signifikant trend».
* **Andel** — enhetens andel av globalt totaltall for gitt år
* **Konsentrasjon** — andel av totalt brent areal fra de N største brannene
  eller landene
* **Dekning** — første og siste år med data per enhet og serie

Ikke tillatt
------------
Årsaksforklaringer, sammenligning mot klimascenarier, prognoser, kvalitative
karakteristikker.

Ordet «rekord» kan kun brukes på siden der det er avledet her og eksplisitt
definert, for eksempel som «høyeste registrerte verdi i dekningsperioden».

Regler
------
* Inneværende år inngår aldri i trendberegninger.
* Hver avledning får en stabil id, slik at HTML kan bære et
  ``data-derivation``-attributt som peker tilbake til beregningen.
* Verdier er i km². Ingen konvertering her — den skjedde i normalize.py.
"""
