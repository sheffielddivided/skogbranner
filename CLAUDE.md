# CLAUDE.md

Arbeidsinstruks for dette repoet. Les hele dokumentet før du gjør endringer.
Dokumentet er skrevet slik at en sesjon uten forhistorie skal kunne følge det
uten å gjette.

---

## 1. Hva dette prosjektet er

En redaksjonell datanettside om skogbranner, globalt og i Europa.

- **Alt leseren ser er norsk (bokmål).** Overskrifter, brødtekst, figurtitler,
  aksetitler, tooltips, ordliste, fotnoter. Det samme gjelder kommentarer i
  koden, dokumentasjon og commit-meldinger.
- **Identifikatorer i datamodell og kode er engelske.** Feltnavn, kodeverdier
  og verdier av `series_id` skrives på engelsk: `entity`, `indicator`,
  `burned_area_km2`, `measured`, `owid_annual_area_burnt`. Ikke bland
  språkene inne i en identifikator.

  Skillet er: teknisk lag på engelsk, presentasjonslag på norsk.
  Oversettelsen fra kodeverdi til lesbar norsk tekst skjer i visningslaget,
  aldri ved å døpe om selve identifikatoren.
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

## 5. Kildeoversikt

Kildekodene er stabile. De brukes som `source_id` i den kanoniske datamodellen
og som nøkkel i `data/_sources.json`. En kode gjenbrukes aldri til en annen
kilde.

| Kode | Kilde | Geografi | Dekning | `quality` | Merknad |
|---|---|---|---|---|---|
| K1 | Our World in Data | Global | 2012– | `measured` | CC BY 4.0 |
| K2 | GWIS (JRC/Copernicus) | Global | 2012– | `measured` | Kryssjekk mot K1 |
| K3 | EFFIS, landtotaler | Europa, Midtøsten, Nord-Afrika | — | `reported` | Nasjonalt rapporterte totaler |
| K4 | EFFIS, Burnt Areas | Europa | — | `reported` | Grunnlag for brannstørrelsesfordeling |
| K5 | NIFC | USA | 1983– | `reported` | Lang nasjonal serie |
| K6 | Natural Earth, admin-0 | Global | — | — | Geometri og landarealer. Public domain |
| K7 | CNFDB / NBAC | Canada | — | `reported` | Krever sluttbrukeravtale — akseptert |
| K8 | FireCCILT11 (ESA Fire_cci) | Global | 1982–2018, uten 1994 | `beta` | Statisk |
| K9 | GFED5 | Global | 1997–2022 | `beta` | Statisk |
| K10 | Global Charcoal Database | Global | — | `reconstructed` | Proxy. Statisk |

### Statiske kilder

K8, K9 og K10 er **statiske**. De skal aldri inn i den månedlige ETL-kjøringen.
Datasettene er avsluttede utgivelser, ikke løpende serier — å hente dem på nytt
hver måned gir ingen nye data og bare unødig last. De hentes én gang, ved en
manuelt utløst workflow, og oppdateres kun hvis produsenten faktisk publiserer
en ny versjon.

### Avgrensninger per kilde

- **K6 Natural Earth** leverer ikke branndata. Den brukes til kartgeometri og
  til landarealer, som er nevneren i `burned_area_share_land`.
- **K9 GFED5** brukes kun for årene **1997–2022**. Produsentens beta-år fra
  2023 og framover holdes ute.
- **K10 Global Charcoal Database** er et *proxy*: sedimentært kull som
  indirekte spor etter brann, ikke en måling av brent areal. Alltid
  `f_proxy`.

### Påkrevd sitering for K7

CNFDB krever at følgende sitering gjengis **ordrett** på siden. Teksten skal
ikke oversettes, forkortes eller omskrives:

> Canadian Forest Service. 2021. Canadian National Fire Database – Agency Fire
> Data. Natural Resources Canada, Canadian Forest Service, Northern Forestry
> Centre, Edmonton, Alberta. https://cwfis.cfs.nrcan.gc.ca/ha/nfdb

Sluttbrukeravtalen er akseptert. Siteringen skal stå både i kildelinjen under
figurer som bruker K7, og i attribusjonsblokken i sidefoten.

---

## 6. Kanonisk datamodell

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
  "series_id": "owid_annual_area_burnt",
  "quality": "measured",
  "footnotes": ["f_sensor_break", "f_min_fire_size"]
}
```

- `level`: `country` | `region` | `world`
- `period`: ISO 8601 — `YYYY`, `YYYY-MM` eller `YYYY-Www`
- `quality`: `measured` | `reported` | `beta` | `reconstructed`

### Indikatorer

| `indicator` | Enhet | Kilde | Merknad |
|---|---|---|---|
| `burned_area_km2` | km² | K1–K5, K7–K9 | Brent areal |
| `burned_area_share_land` | andel (0–1) | avledet, nevner fra K6 | Brent areal som andel av landareal. Gjør små og store land sammenlignbare |
| `charcoal_index` | enhetsløs | K10 | Z-score |

`charcoal_index` er en **z-score**: hvor mange standardavvik en verdi ligger
over eller under gjennomsnittet for serien. Den har ingen enhet og kan ikke
sammenlignes med et areal.

Derfor: `charcoal_index` får **alltid egen akse** og skal **aldri** tegnes i
samme figur som en km²-serie. Å legge dem oppå hverandre antyder en
sammenlignbarhet som ikke finnes. Vil du vise dem sammen, bruk to figurer
under hverandre med felles tidsakse.

`burned_area_share_land` beregnes i `normalize.py` med landareal fra K6 som
nevner. Andelen vises for leseren i prosent, men lagres som andel.

### `quality` styrer visuell fremstilling

| Verdi | Betydning | Tegnes som |
|---|---|---|
| `measured` | Satellittmålt | Heltrukket linje |
| `reported` | Nasjonalt rapportert, egne definisjoner | Stiplet linje |
| `beta` | Foreløpig datasett, merket som sådan av produsenten | Heltrukket linje med redusert opasitet |
| `reconstructed` | Rekonstruert eller proxy | Eget bånd, separat akse |

`beta` betyr at **produsenten selv** har merket datasettet som foreløpig. Det
er ikke vår vurdering av datakvaliteten. Serier med `beta` skal alltid ha
`f_beta_product`, og den reduserte opasiteten skal forklares i figurens
tegnforklaring — en leser skal ikke måtte gjette hva den blekere linjen betyr.

Serier med ulik `quality` slås **aldri** sammen til én kurve uten synlig
markering av bruddet.

**Ulike startår skjules ikke.** Hver figur viser dekningsperioden eksplisitt.
Land uten data for et gitt år vises som «ingen data», aldri som null.

**Inneværende år** markeres alltid visuelt som ufullstendig og inngår aldri i
trendberegninger.

---

## 7. Tillatte maskinelle avledninger

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
| Arealsammenligning | Landet hvis landareal ligger nærmest en gitt arealverdi, valgt maskinelt fra Natural Earth-arealene (K6) |

**Arealsammenligning** gir leseren en fysisk referanse for et tall i km², som
ellers er vanskelig å forestille seg. Sammenligningslandet velges maskinelt
som det med minst absolutt avvik i landareal — ingen redaksjonelt valgte
eksempler, ingen «omtrent på størrelse med». Avviket i prosent oppgis sammen
med sammenligningen, slik at leseren ser hvor god tilnærmingen er.

### Trend: aldri på tvers av kilde eller kvalitet

Trendberegninger kjøres **kun innenfor én kilde og én `quality`-verdi**. Aldri
på en serie som er skjøtt sammen av flere kilder, og aldri på tvers av ulike
`quality`-verdier.

Grunnen er at et skifte av kilde eller målemetode gir et nivåbrudd i serien.
En regresjon over et slikt brudd måler skiftet i metode, ikke en endring i
verden, og gir en trend som ser reell ut uten å være det. Trenger to serier å
vises sammen, tegnes de som to serier med synlig brudd, med hver sin trend
eller ingen.

**Ikke tillatt:** årsaksforklaringer, sammenligning mot klimascenarier,
prognoser, kvalitative karakteristikker.

---

## 8. Sidestruktur

Én lang side med sticky innholdsnavigasjon. Seks seksjoner, i denne
rekkefølgen. Hver seksjon åpner med figuren (P2).

| # | Seksjon | Viser | Kilder |
|---|---|---|---|
| S1 | Hvor mye brenner det på jorden | Globalt brent areal per år | K1, K2 |
| S2 | Hvor på kloden | Geografisk fordeling: kart og rangering av land | K1, K6 |
| S3 | Året gjennom | Sesongvariasjon innenfor året — kumulativ kurve mot median og persentilbånd | K2 |
| S4 | Europa | Land- og regionnivå, brent areal og andel av landareal, sorterbar tabell, brannstørrelsesfordeling | K3, K4, K6 |
| S5 | Den lange linjen | De seriene som går lengst tilbake, vist hver for seg | K5, K7, K8, K9, K10 |
| S6 | Om dataene | Kildeoversikt, definisjoner, ordliste, alle fotnoter samlet, nedlastingslenker til alle bearbeidede CSV-filer, lenke til repoet | alle |

**Overskriftene er beskrivende, ikke tolkende.** «Hvor mye brenner det på
jorden» stiller et spørsmål dataene kan svare på. Den svarer ikke på om det er
mye eller lite — det er en vurdering siden ikke gjør (P1).

**S5 er den seksjonen som lettest bryter reglene.** Seriene der har ulik kilde,
ulik `quality`, ulike startår og ulike definisjoner. De skal vises **hver for
seg**, med tydelig markering av at de ikke er direkte sammenlignbare, og aldri
skjøtes til én lang kurve. `charcoal_index` (K10) står i egen figur med egen
akse. Trender beregnes per serie, innenfor én kilde og én `quality`.

Norge og de nordiske landene inngår i S4 som ordinære land, uten
særbehandling og uten egen seksjon (P8).

---

## 9. Krav til hver figur

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
- `f_beta_product` — produsenten merker datasettet som foreløpig
- `f_missing_year` — enkeltår mangler helt i kilden
- `f_proxy` — indirekte mål, ikke en måling av brent areal

`f_missing_year` gjelder blant annet 1994 i K8. Et manglende år vises som
brudd i kurven, aldri som 0 og aldri som interpolert verdi.

---

## 10. Lisens

- Kode: MIT (se `LICENSE`)
- Sidens tekst: CC BY 4.0
- Bearbeidede data: videreformidles under den strengeste av kildelisensene, med
  kildeangivelse per serie i `data/_sources.json`

Sidefoten skal inneholde en samlet attribusjonsblokk. En kilde som krever
sluttbrukeravtale tas ikke inn før avtalen er avklart og notert i
`data/_sources.json`.

---

## 11. Sjekkliste før du committer

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
- [ ] **Ingen figur blander `quality`-verdier uten synlig brudd.**
      `validate.py` skal feile hvis det skjer — dette er en maskinell
      kontroll, ikke en vurdering som overlates til den som skriver figuren
- [ ] Trender er beregnet innenfor én kilde og én `quality`
- [ ] `charcoal_index` står ikke i samme figur som en km²-serie
- [ ] Siteringen for K7 gjengis ordrett der K7 brukes
- [ ] Identifikatorer er engelske, alt leseren ser er norsk

---

## 12. Status

Prosjektet er i oppstartsfasen. Kun mappestruktur, konfigurasjon og dette
dokumentet finnes. ETL-koden er **ikke** skrevet ennå — `etl/*.py` inneholder
kun beskrivelser av ansvarsområde. Skriv den ikke uten at det er bedt om det.
