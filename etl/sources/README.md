# etl/sources/

Én modul per datakilde. Ingen kildemoduler er skrevet ennå.

## Ansvar

En kildemodul gjør **kun** to ting:

1. Henter kildens filer og legger dem uendret i `data/raw/`
2. Parser råformatet til rader, uten å tolke eller omregne

Den skal ikke konvertere enheter, ikke fylle hull, ikke slå sammen serier og
ikke beregne noe. Alt slikt hører hjemme i `normalize.py`.

## Krav per modul

- Registrerer kilden i `data/_sources.json` med lisens, lenke,
  dekningsperiode, nedlastingsdato og SHA-256 av råfilen
- Skriver kjørestatus til `data/_status.json`, også ved feil
- Feiler kontrollert: en kilde som er nede skal aldri stoppe de andre eller
  ødelegge siden
- Oppgir hvilken enhet kilden leverer i, slik at `normalize.py` kan konvertere
  til km²
- Kilder som krever registrering eller sluttbrukeravtale merkes med
  `requires_agreement` og tas ikke i bruk før avtalen er avklart

## Kjøring

Nedlasting og prosessering kjører **kun i GitHub Actions**. I en lokal sesjon
eller sandkasse: hent maks én fil eller ett år for å undersøke formatet. Aldri
fullt løp, aldri store arkiver. `data/raw/` er gitignorert med vilje.
