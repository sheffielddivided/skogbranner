# CLAUDE.md

Arbeidsinstruks for dette repoet. Les hele dokumentet før du gjør endringer.
Dokumentet er skrevet slik at en sesjon uten forhistorie skal kunne følge det
uten å gjette.

---

## 1. Hva dette prosjektet er

En redaksjonell datanettside om skogbranner, globalt og i Europa.

- Språk på siden og i koden: **norsk (bokmål)**. Kommentarer, variabelnavn i
  data, overskrifter, commit-meldinger — alt på norsk. Unntak: etablerte
  engelske faguttrykk i feltnavn der en oversettelse ville skapt tvetydighet
  (`burned_area_km2`, `entity`, `indicator`).
- Privat, ikke-kommersielt prosjekt. Ingen tilknytning til arbeidsgiver.
- Publiseres statisk på GitHub Pages under stien `/skogbranner/`.
- Alt bygges på forhånd. Nettleseren gjør ingen API-kall.

Siden er **ikke** en artikkel med et budskap. Den er et oppslagsverk som viser
hva målingene sier, hvor langt tilbake de går, og hvor de er usikre.

---

## 2. Bindende redaksjonelle prinsipper

Disse er ufravikelige. De gjelder all tekst, all kode og all kodegjennomgang.
Er du i tvil om en endring bryter et prinsipp, gjør den ikke — spør først.

### P1 — Ingen tese

Siden fremmer ikke et standpunkt og har ingen konklusjon. Den viser hva dataene
måler, hvor langt tilbake de går, og hvor de er usikre. Overskrifter beskriver
hva figuren viser, aldri hva det betyr.

- Tillatt: «Brent areal i Europa per år, 2012–2024»
- Ikke tillatt: «Europa brenner mer enn før»

### P2 — Data har forrang

Hver seksjon åpner med visualiseringen. Forklarende tekst ligger **under**
figuren, aldri foran den. Dette gjelder også i DOM-rekkefølgen, ikke bare
visuelt — en skjermleser skal møte figuren først.

### P3 — Ingen håndskrevne tall i brødtekst

Alle tallfestede påstander i brødteksten genereres maskinelt fra datasettet ved
byggetidspunkt, av `etl/derive.py`. **Aldri unntak.** Ikke «omtrent», ikke
«rundt», ikke «i overkant av». Skal et tall stå i teksten, kommer det fra en
mal som fylles fra `data/processed/insights.json`.

Praktisk konsekvens: brødtekst skrives som maler med plassholdere. Finnes ikke
avledningen, skal setningen ikke skrives — da må avledningen implementeres
først i `derive.py`.

Hver genererte setning skal bære et `data-derivation`-attributt i HTML som
peker til hvilken beregning verdien kommer fra, slik at leseren kan spore den.

### P4 — Nøytralt språk

Forbudte ord i brødtekst, overskrifter, figurtitler og bildetekster:

> paradoks, alarmerende, dramatisk, katastrofal, eksplosjon, krise, skremmende

Ordet **«rekord»** er kun tillatt der det er maskinelt avledet og eksplisitt
definert på siden (for eksempel: «høyeste registrerte verdi i dekningsperioden
2012–2024»). Aldri som løs karakteristikk.

Beskriv retning og størrelse. Ikke betydning.

### P5 — Full sporbarhet per figur

Hver figur har en synlig kildelinje som inneholder, som et minimum:

1. Kildens navn, som **lenke** til kilden
2. Dekningsperiode (første–siste år figuren faktisk viser)
3. Nedlastingsdato for dataene
4. Lenke til den CSV-filen figuren faktisk bruker — ikke til mappen, ikke til
   en «lignende» fil

Kildelinjen er ikke valgfri og skjules ikke bak et klikk.

### P6 — Forbehold som fotnoter per figur

Metodiske begrensninger vises som **nummererte fotnoter rett under den enkelte
figuren**. Ikke som en generell ansvarsfraskrivelse i sidefoten, ikke samlet på
en egen side. En leser som ser én figur skal se forbeholdene som gjelder akkurat
den.

Fotnotene samles *i tillegg* på «Om dataene»-seksjonen, men det erstatter ikke
plasseringen under figuren.

### P7 — Leseren er allmennheten

Ingen fagbakgrunn forutsettes. Fagbegreper forklares første gang de brukes, med
en kort forklaring i tekst, og gjentas i ordlisten. Gjelder blant annet:
brent areal, aktiv branndeteksjon, hotspot, brannsesong, satellittsensor,
persentilbånd, median.

Skriv korte setninger. Unngå passiv der aktiv er mulig.

### P8 — Utenfor scope

Følgende skal **ikke** inn på siden, uansett hvor fristende:

- Utslipp (CO₂, partikler, karbon)
- Klimadrivere og værforklaringer
- Klimaattribusjon
- Egen Norden-seksjon (Norge og nabolandene inngår som ordinære land uten
  særbehandling)
- Sanntidsdata og live-kart

Sanntid er ute av scope. Det betyr også: ingen proxy-tjeneste, ingen API-nøkler,
ingen Cloudflare Worker, ingen FIRMS-integrasjon i klienten.

---

## 3. Tekniske rammer

### T1 — km² er primærenhet

**Hele grensesnittet bruker km².** Aksetitler, tabeller, tooltips, nedlastbare
CSV-filer under `data/processed/`, avledede tall — alt i km².

All enhetskonvertering skjer i `etl/normalize.py`. Aldri i visningslaget, aldri
i JavaScript, aldri i en malfil. Kommer en kilde med hektar eller acres,
konverteres den én gang under normalisering, og den konverterte verdien er den
eneste som finnes videre i pipelinen.

Referanse: 1 km² = 100 ha. 1 acre = 0,00404686 km².

Feltnavn bærer enheten: `burned_area_km2`. Et felt uten enhet i navnet er en
feil.

### T2 — Ingen eksterne avhengigheter i klienten

Den publiserte siden laster **ingenting** fra et annet domene:

- Ingen CDN-er
- Ingen kartflis-tjenester (OSM, Carto, Mapbox, Maptiler — ingen)
- Ingen webfonter fra tredjepart
- Ingen sporing, ingen analyse, ingen cookies, ingen samtykkebanner
- Ingen `fetch()` mot eksterne verter

Kart tegnes fra geometri som ligger i repoet under `data/geo/` (forenklet
GeoJSON eller TopoJSON), som SVG eller canvas. Trenger vi et bibliotek,
vendorer vi det inn i `src/` med lisensfil. Byggeverktøy og
utviklingsavhengigheter er greit — det er *det som sendes til leseren* som skal
være avhengighetsfritt.

### T3 — Alt bygges statisk

Ingen server, ingen kjøretidslogikk, ingen API-kall fra nettleseren. Data er
ferdige filer i repoet når siden bygges. Bygget skal være deterministisk: samme
input gir samme output.

Basisstien er `/skogbranner/`. Alle interne lenker og ressursstier må tåle det —
bruk relative stier eller en konfigurerbar base, aldri hardkodet `/`.

### T4 — Tunge jobber kjører ALDRI i sandkassen

Nedlasting av datasett og prosessering av dem skjer **kun i GitHub Actions**.

I en Claude Code-sesjon:

- Last ned maks **én fil** eller **ett år** for å teste et format
- Ikke kjør fullt ETL-løp
- Ikke last ned shapefiler, NetCDF-arkiver eller rutenettsdata i full størrelse
- Ikke commit noe til `data/raw/` — den er gitignorert med vilje

Er du usikker på om en jobb er «tung»: hvis den tar mer enn noen sekunder eller
laster mer enn noen få MB, er den tung. Legg den i en workflow i stedet.

---

## 4. Mappestruktur

```
etl/
  sources/          Én modul per kilde. Kun henting + råformat-parsing.
  normalize.py      Kanonisk form. All enhetskonvertering skjer her.
  derive.py         Maskinelle avledninger → data/processed/insights.json
  validate.py       Kontrollerer at output er gyldig før publisering
data/
  raw/              Uendrede kildefiler. GITIGNORERT. Aldri committet.
  processed/        Kanoniske serier siden faktisk leser. Committes.
  geo/              Forenklet geometri for kart. Committes.
  _sources.json     Kildemetadata: lisens, lenke, dekning, nedlastingsdato
  _status.json      Siste kjørestatus per kilde, for degradert visning
src/                Nettsidens kildekode
public/             Statiske ressurser som kopieres uendret
.github/workflows/  ETL-kjøring og deploy
```

**Dataflyt:** `sources/` henter → `normalize.py` kanoniserer og konverterer til
km² → `validate.py` avviser ugyldig output → `derive.py` beregner avledninger →
`data/processed/` committes → siden bygges.

Feiler en kilde, beholdes forrige datasett, feilen logges i `data/_status.json`,
og siden viser en diskré merknad om at akkurat den serien ikke er oppdatert
siden dato X. Siden skal aldri gå i stykker av at en kilde er nede.

---

## 5. Kanonisk datamodell

Alle kilder normaliseres til langformat før publisering:

```json
{
  "entity": "NOR",
  "entity_name": "Norge",
  "level": "country",
  "period": "2024",
  "indicator": "burned_area_km2",
  "value": 9.71,
  "unit": "km2",
  "source_id": "K1",
  "series_id": "owid_arlig_brent_areal",
  "quality": "measured",
  "footnotes": ["f_sensor_break", "f_min_fire_size"]
}
```

- `level`: `country` | `region` | `world`
- `period`: ISO 8601 — `YYYY`, `YYYY-MM` eller `YYYY-Www`
- `quality`: `measured` | `reported` | `reconstructed`

**`quality` styrer visuell fremstilling:** målte serier tegnes med heltrukket
linje, rapporterte med stiplet, rekonstruerte med eget bånd og separat akse.
Serier med ulikt kvalitetsflagg slås **aldri** sammen til én kurve uten synlig
markering av bruddet.

**Ulike startår skjules ikke.** Hver figur viser dekningsperioden eksplisitt.
Land uten data for et gitt år vises som «ingen data», aldri som null.

**Inneværende år** markeres alltid visuelt som ufullstendig og inngår aldri i
trendberegninger.

---

## 6. Tillatte maskinelle avledninger

`derive.py` produserer kun disse. Alt annet krever at prinsippene diskuteres på
nytt.

| Avledning | Definisjon |
|---|---|
| Rangering | «År X er nummer N av M år med data for enhet E» |
| Avvik fra normal | Verdi mot median for hele dekningsperioden, i prosent |
| Trend | Theil–Sen-estimator med Mann–Kendall-test. Rapporteres med retning, størrelse per tiår og p-verdi. Ikke-signifikant trend rapporteres som «ingen statistisk signifikant trend» |
| Andel | Enhetens andel av globalt totaltall for gitt år |
| Konsentrasjon | Andel av totalt brent areal fra de N største brannene eller landene |
| Dekning | Første og siste år med data per enhet og serie |

**Ikke tillatt:** årsaksforklaringer, sammenligning mot klimascenarier,
prognoser, kvalitative karakteristikker.

---

## 7. Krav til hver figur

- Tittel som beskriver hva som vises, ikke hva det betyr
- Enhet oppgitt i aksen — km²
- Kildelinje under figuren (se P5)
- Nummererte fotnoter direkte under figuren (se P6)
- Tastaturnavigerbar, med tabellvisning som alternativ til grafikken
- Eget mobiloppsett, ikke nedskalert skrivebordsfigur
- WCAG 2.1 AA: kontrast, `prefers-reduced-motion`, fargeskalaer som fungerer
  ved fargeblindhet
- Tekst og tabeller skal være lesbare uten JavaScript

**Gjenbrukbare fotnoter:**

- `f_sensor_break` — overgang mellom satellittsensorer kan gi brudd i serien
- `f_min_fire_size` — systemet fanger i praksis ikke opp de minste brannene
- `f_incomplete_year` — inneværende år er ufullstendig
- `f_reporting_basis` — nasjonalt rapporterte tall følger andre definisjoner
  enn satellittmålte
- `f_coverage_change` — antall rapporterende land eller områder har endret seg
  over tid

---

## 8. Lisens

- Kode: MIT (se `LICENSE`)
- Sidens tekst: CC BY 4.0
- Bearbeidede data: videreformidles under den strengeste av kildelisensene, med
  kildeangivelse per serie i `data/_sources.json`

Sidefoten skal inneholde en samlet attribusjonsblokk. En kilde som krever
sluttbrukeravtale tas ikke inn før avtalen er avklart og notert i
`data/_sources.json`.

---

## 9. Sjekkliste før du committer

- [ ] Ingen håndskrevne tall i brødtekst (P3)
- [ ] Ingen forbudte ord (P4)
- [ ] Figuren står før teksten, også i DOM (P2)
- [ ] Kildelinje med lenke, dekning, nedlastingsdato og CSV-lenke (P5)
- [ ] Fotnoter under figuren (P6)
- [ ] Nye fagbegreper forklart første gang (P7)
- [ ] Ingenting fra scope-listen har sneket seg inn (P8)
- [ ] Alle verdier i km², konvertert i `normalize.py` (T1)
- [ ] Ingen eksterne forespørsler fra klienten (T2)
- [ ] Ingen tunge nedlastinger kjørt lokalt (T4)
- [ ] `data/raw/` er ikke committet

---

## 10. Status

Prosjektet er i oppstartsfasen. Kun mappestruktur, konfigurasjon og dette
dokumentet finnes. ETL-koden er **ikke** skrevet ennå — `etl/*.py` inneholder
kun beskrivelser av ansvarsområde. Skriv den ikke uten at det er bedt om det.
