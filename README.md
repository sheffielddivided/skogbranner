# Skogbranner

Redaksjonell datanettside om skogbranner, globalt og i Europa. På norsk.

Siden viser hva målingene sier, hvor langt tilbake de går, og hvor de er
usikre. Den fremmer ikke et standpunkt og trekker ingen konklusjon.

Publiseres statisk på GitHub Pages under `/skogbranner/`.

## Prinsipper

- **Ingen tese.** Ingen standpunkt, ingen konklusjon.
- **Data har forrang.** Hver seksjon åpner med figuren. Teksten står under.
- **Ingen håndskrevne tall.** Alle tallfestede påstander i brødteksten
  genereres maskinelt fra datasettet ved byggetidspunkt.
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
src/                  Nettsidens kildekode
public/               Statiske ressurser
.github/workflows/    ETL-kjøring og deploy
```

## Status

Oppstartsfase. Kun struktur og dokumentasjon. ETL og nettside er ikke
implementert.

## Lisens

- **Kode:** MIT — se [LICENSE](LICENSE).
- **Sidens tekst:** CC BY 4.0.
- **Bearbeidede data:** videreformidles under den strengeste av
  kildelisensene. Lisens, opphav og dekningsperiode per kilde er oppgitt i
  [`data/_sources.json`](data/_sources.json), og gjengis i sidefoten.

Dette er et privat, ikke-kommersielt prosjekt uten tilknytning til noen
arbeidsgiver eller organisasjon.
