# etl/sources/

Én modul per datakilde. Hvilke kilder som finnes, står i CLAUDE.md § 5 —
listen gjentas ikke her.

## Ansvar

En kildemodul gjør **kun** to ting:

1. Henter kildens filer og legger dem uendret i `data/raw/`
2. Parser råformatet til rader, uten å tolke eller omregne

Den skal ikke konvertere enheter, ikke fylle hull, ikke slå sammen serier og
ikke beregne noe. Alt slikt hører hjemme i `normalize.py`.

I tillegg registrerer modulen kilden i `data/_sources.json` og skriver
kjørestatus til `data/_status.json`, også når hentingen feiler.

## Regler

Kildekoder, hvilke kilder som er statiske, hvilke som krever ordrett sitering,
og hva som gjelder for kjøring i sandkasse kontra GitHub Actions: se
CLAUDE.md § 5 og § 3 (T4).

Kodeverdier importeres fra `etl/schema.py`.
