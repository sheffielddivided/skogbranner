# Skogbranner

Redaksjonell datanettside om skogbranner, globalt og i Europa. På norsk.

Siden viser hva målingene sier, hvor langt tilbake de går, og hvor de er
usikre. Den fremmer ikke et standpunkt og trekker ingen konklusjon.

Publiseres statisk på GitHub Pages under `/skogbranner/`.

## Prinsipper

- **Ingen tese.** Ingen standpunkt, ingen konklusjon.
- **Data har forrang.** Hver seksjon åpner med figuren. Teksten står under.
- **Ingen håndskrevne tall.** Alle tallfestede påstander i brødteksten
  genereres maskinelt fra datasettet, i ETL.
- **Nøytralt språk.** Retning og størrelse beskrives, ikke betydning.
- **Full sporbarhet.** Hver figur oppgir kilde med lenke, dekningsperiode,
  nedlastingsdato og lenke til CSV-filen figuren faktisk bruker.
- **Forbehold per figur.** Metodiske begrensninger står som nummererte
  fotnoter under den enkelte figuren.
- **Skrevet for allmennheten.** Fagbegreper forklares første gang de brukes.

Primærenhet i hele grensesnittet er **km²**. All enhetskonvertering skjer i
`etl/normalize.py`.

Den publiserte siden laster ingenting fra andre domener: ingen CDN, ingen
kartflis-tjenester, ingen sporing, ingen cookies. Alt bygges statisk, og
nettleseren gjør ingen API-kall.

Utenfor scope: utslipp, klimadrivere, klimaattribusjon, egen Norden-seksjon og
sanntidsdata.

De bindende reglene i sin helhet står i [CLAUDE.md](CLAUDE.md).

## Struktur

```
etl/sources/          Én modul per datakilde
etl/normalize.py      Kanonisk form, all enhetskonvertering
etl/derive.py         Maskinelle avledninger
etl/validate.py       Validering før publisering
data/raw/             Uendrede kildefiler (gitignorert)
data/processed/       Kanoniske serier siden leser
data/geo/             Forenklet geometri for kart
data/_sources.json    Kildemetadata
data/_status.json     Siste kjørestatus per kilde
data/_footnotes.json  Fotnotekode → norsk tekst
src/figurer/          Én modul per figur: graf, tabell og fotnoter
src/komponenter/      Figur, innholdsnavigasjon, sidefot
src/lib/              Datalesing, formatering, Plot-til-SVG
public/               Statiske ressurser
.github/workflows/    ETL-kjøring og deploy
```

## Bygging

```
npm install
npm run build      # → dist/
npm run dev
```

Grafene tegnes med Observable Plot, men **i Node under bygging**, ikke i
nettleseren. Det som legges ut er ferdig SVG, så leseren laster verken
grafbibliotek eller annen JavaScript, og figurene vises også med skript slått
av.

Byggeavhengighetene — Astro (MIT), Observable Plot (ISC), linkedom (ISC) —
sendes derfor aldri til leseren. Fullstendige lisenstekster ligger under
`node_modules/` etter `npm install`.

ETL-en kjøres som moduler fra repotoppen:

```
python -m etl.run
python -m etl.validate
```

## Status

ETL er i drift for K1. Nettsiden har skjelett med seks seksjoner, og S1 viser
globalt brent areal per år. S2–S6 er ikke laget ennå.

## Lisens

- **Kode:** MIT — se [LICENSE](LICENSE).
- **Sidens tekst:** CC BY 4.0.
- **Bearbeidede data:** videreformidles under den strengeste av
  kildelisensene. Lisens, opphav og dekningsperiode per kilde er oppgitt i
  [`data/_sources.json`](data/_sources.json), og gjengis i sidefoten.

Dette er et privat, ikke-kommersielt prosjekt uten tilknytning til noen
arbeidsgiver eller organisasjon.
