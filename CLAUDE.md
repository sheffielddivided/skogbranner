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

### T5 — CLAUDE.md er eneste sannhetskilde

Skill mellom **regler** og **enumerasjoner**. De to håndteres ulikt.

#### Regler

Prosa med begrunnelse og skjønn: hvorfor trender ikke krysser kildegrenser,
hva som gjør en overskrift tolkende, når et brudd skal være synlig.

Regler skrives **kun i CLAUDE.md**. Kodefiler, docstrings og kommentarer skal
**referere**, aldri gjenfortelle. Duplisert regelverk divergerer — én kopi
oppdateres, den andre blir stående, og da er det uklart hva som gjelder.

Trenger en fil å forklare seg, skriv `se CLAUDE.md § X` i stedet for å kopiere
regelen. En docstring skal si hva filen har ansvar for, ikke gjengi resonnementet
bak regelen den følger.

#### Enumerasjoner

Maskinlesbare lister koden må validere mot: gyldige `quality`-verdier,
`indicator`-navn, `unit`-verdier, kildekoder, fotnotekoder,
konverteringsfaktorer.

Disse defineres **ett sted i kode**: `etl/schema.py`. CLAUDE.md dokumenterer
dem i prosa, men `schema.py` er det maskinen leser.

At en konstant finnes i `schema.py` er **implementering, ikke duplisering**.
Den skal ikke fjernes under henvisning til T5.

#### Regelen

> Enhver enumerasjon finnes nøyaktig **to** steder: som prosa i CLAUDE.md for
> mennesket, og som konstant i `etl/schema.py` for maskinen. Ingen tredje kopi.

`validate.py`, `normalize.py` og alt annet importerer fra `schema.py` og
definerer aldri egne lister. Skriver du `["measured", "reported", ...]` i en
annen fil, har du laget den tredje kopien.

Endres en enumerasjon, endres begge stedene i samme commit.

---

## 4. Mappestruktur

```
etl/
  sources/          Én modul per kilde. Kun henting + råformat-parsing.
  schema.py         Enumerasjonene i kode. Alt annet importerer herfra (T5).
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
| K2 | GWIS (JRC/Copernicus) | Global | 2012– | `measured` | Kryssjekk mot K1, og ukesoppløsning til S3 |
| K3 | EFFIS, landtotaler | Europa, Midtøsten, Nord-Afrika | — | `reported` | Nasjonalt rapporterte totaler |
| K4 | EFFIS, Burnt Areas | Europa | — | `reported` | Grunnlag for brannstørrelsesfordeling |
| K5 | NIFC | USA | 1983– | `reported` | Lang nasjonal serie |
| K6 | Natural Earth, admin-0 | Global | — | — | Geometri og landarealer. Public domain |
| K7 | CNFDB / NBAC | Canada | — | `reported` | Krever sluttbrukeravtale — akseptert |
| K8 | FireCCILT11 (ESA Fire_cci) | Global | 1982–2018, uten 1994 | `beta` | Statisk. Selve produktet er merket beta av produsenten |
| K9 | GFED5 | Global | 1997–2022 | `measured` | Statisk. GFED5.1 for 1997–2022 er en publisert utgivelse dokumentert i Scientific Data. Beta-merkingen gjelder kun produsentens `ext_Beta`-kataloger fra 2023, som vi holder ute |
| K10 | Global Charcoal Database | Global | — | `reconstructed` | Proxy. Statisk |

### Statiske kilder

K8, K9 og K10 er **statiske**. De skal aldri inn i den månedlige ETL-kjøringen.
Datasettene er avsluttede utgivelser, ikke løpende serier — å hente dem på nytt
hver måned gir ingen nye data og bare unødig last. De hentes én gang, ved en
manuelt utløst workflow, og oppdateres kun hvis produsenten faktisk publiserer
en ny versjon.

### Avgrensninger per kilde

- **K6 Natural Earth** leverer ikke branndata. Den brukes til kartgeometri og
  til landarealer, som er nevneren i `burned_area_share_land`. Den tegnes ikke
  som egen serie, og står derfor ikke i kildekolonnen i § 8.
- **K2 GWIS** har to roller.

  Den ene er **kryssjekk mot K1**, som en ETL-validering: spriker K1 og K2 mer
  enn 5 % for samme enhet og år, produseres en avviksrapport. Rapporten er et
  arbeidsverktøy for redaktøren, ikke innhold på siden. Den publiseres ikke,
  og K2 tegnes ikke i noen figur i denne rollen.

  Den andre er som datagrunnlag for **S3**, der ukesoppløsningen brukes. Det er
  den eneste seksjonen der K2 er synlig for leseren.
- **K9 GFED5** brukes kun for årene **1997–2022**, og har `quality`
  `measured`. GFED5.1 for denne perioden er en publisert utgivelse,
  dokumentert i Scientific Data. Produsentens `ext_Beta`-kataloger fra 2023 og
  framover holdes ute — det er *de* som er foreløpige, ikke datasettet vi
  bruker. Årene **1997–2000** har grovere romlig oppløsning enn resten av
  serien (1° mot 0,25° fra 2001), og skal alltid ha `f_resolution_change`.

  K8 er derimot `beta` fordi selve produktet er merket slik av produsenten.
  Skillet er hvem som har merket hva: en produsents beta-merking på et annet
  datasett i samme katalog smitter ikke over.
- **K10 Global Charcoal Database** er et *proxy*: sedimentært kull som
  indirekte spor etter brann, ikke en måling av brent areal. Alltid
  `f_proxy`.

### Påkrevd sitering

Flere kilder stiller krav til hvordan de siteres. Siteringene under skal
gjengis **ordrett**: ikke oversettes, ikke forkortes, ikke omskrives. De skal
stå både i kildelinjen under figurer som bruker kilden, og i
attribusjonsblokken i sidefoten.

Dette er et vilkår for bruk, ikke en høflighet. En figur som bruker en av
disse kildene uten siteringen skal ikke publiseres.

**K7 — CNFDB / NBAC.** Sluttbrukeravtalen er akseptert.

> Canadian Forest Service. 2021. Canadian National Fire Database – Agency Fire
> Data. Natural Resources Canada, Canadian Forest Service, Northern Forestry
> Centre, Edmonton, Alberta. https://cwfis.cfs.nrcan.gc.ca/ha/nfdb

**K9 — GFED5.**

> van der Werf et al., Landscape fire emissions from the 5th version of the
> Global Fire Emissions Database (GFED5), Scientific Data

**K10 — Global Charcoal Database.**

> Blarquez, O., Vannière, B., Marlon, J.R., Daniau, A.-L., Power, M.J.,
> Brewer, S. & Bartlein, P.J. (2014). paleofire: an R package to analyse
> sedimentary charcoal records from the Global Charcoal Database to
> reconstruct past biomass burning. Computers & Geosciences 72: 255–261.

**K3 og K4 — EFFIS.** Har egen datalisens som må gjengis. Lenken til
lisensteksten legges i `data/_sources.json`, og lisensteksten refereres i
attribusjonsblokken.

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
- `unit`: `km2` | `share` | `zscore`

### Indikatorer

Hver `indicator` har nøyaktig én tillatt `unit`. Kombinasjoner utenfor tabellen
er en feil.

| `indicator` | `unit` | Vises som | Kilde | Merknad |
|---|---|---|---|---|
| `burned_area_km2` | `km2` | km² | K1–K5, K7–K9 | Brent areal |
| `burned_area_share_land` | `share` | prosent | avledet, nevner fra K6 | Brent areal som andel av landareal. Gjør små og store land sammenlignbare |
| `charcoal_index` | `zscore` | enhetsløst tall | K10 | Z-score |

`unit` er en kodeverdi, ikke visningstekst. `share` lagres som andel mellom 0
og 1, men vises for leseren i prosent — omregningen skjer i visningslaget, som
er den ene formen for enhetsbehandling som ikke hører hjemme i `normalize.py`,
fordi den ikke endrer den lagrede verdien.

`charcoal_index` er en **z-score**: hvor mange standardavvik en verdi ligger
over eller under gjennomsnittet for serien. Den har ingen enhet og kan ikke
sammenlignes med et areal.

Derfor: `charcoal_index` får **alltid egen akse** og skal **aldri** tegnes i
samme figur som en km²-serie. Å legge dem oppå hverandre antyder en
sammenlignbarhet som ikke finnes. Vil du vise dem sammen, bruk to figurer
under hverandre med felles tidsakse.

`burned_area_share_land` beregnes i `normalize.py` med landareal fra K6 som
nevner.

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
| S1 | Hvor mye brenner det på jorden | Overskriftstall for siste fullstendige år, og globalt brent areal per år over hele perioden i én oversiktsfigur med synlige brudd | K1, K8, K9 |
| S2 | Hvor på kloden | Geografisk fordeling: kart og rangering av land | K1 |
| S3 | Året gjennom | Sesongvariasjon innenfor året — kumulativ kurve mot median og persentilbånd, i ukesoppløsning | K2 |
| S4 | Europa | Land- og regionnivå, brent areal og andel av landareal, sorterbar tabell, brannstørrelsesfordeling | K3, K4 |
| S5 | Den lange linjen | De samme seriene som i S1, pluss de nasjonale og proxyen, vist **hver for seg** i separate figurer med hver sin akse og hver sin dekningsperiode | K1, K5, K7, K8, K9, K10 |
| S6 | Om dataene | Kildeoversikt, definisjoner, ordliste, alle fotnoter samlet, nedlastingslenker til alle bearbeidede CSV-filer, lenke til repoet | alle |

**Hva kildekolonnen betyr.** Kolonnen lister **kun kilder som faktisk tegnes i
seksjonens figurer**. Kilder som brukes til validering, geometri eller
avledning står ikke der — de er beskrevet under sin egen kildeoppføring i § 5.

Derfor står ikke K6 i S2 og S4, selv om kartene tegnes med geometri derfra og
`burned_area_share_land` bruker landarealene som nevner. Og derfor står ikke
K2 i S1, selv om den brukes til å kryssjekke K1. Kolonnen svarer på «hva ser
leseren», ikke «hva var involvert».

**Overskriftene er beskrivende, ikke tolkende.** «Hvor mye brenner det på
jorden» stiller et spørsmål dataene kan svare på. Den svarer ikke på om det er
mye eller lite — det er en vurdering siden ikke gjør (P1).

### S1 — to figurer

**Figur 1: overskriftstallet.** Globalt brent areal for siste fullstendige år,
i km². Kilde K1. Sammen med tallet vises arealsammenligningen fra
`insights.json`, som gir leseren en fysisk referanse.

Både arealet og sammenligningslandet er maskinelt avledet (P3). Ingen av
tallene skrives for hånd, og sammenligningslandet velges ikke redaksjonelt.
Inneværende år brukes aldri her — «siste fullstendige år» er en avledning, ikke
en antakelse om hvilket år det er nå.

**Figur 2: oversiktsfiguren.** Globalt brent areal per år over hele den
tilgjengelige perioden, 1982–. Bygger på K8, K9 og K1.

De tre kildene dekker hver sin del av perioden og har ulikt opphav. De skal
tegnes som **tre serier med synlige brudd**, hver etter sin egen
`quality`-verdi — K8 med redusert opasitet (`beta`), K9 og K1 heltrukket
(`measured`). Ingen sammenskjøting til én kurve, verken visuelt eller i data.

Bruddene er poenget med figuren, ikke en skjønnhetsfeil ved den. En
sammenhengende kurve fra 1982 til i dag ville sett ut som én måling av verden
over førti år, og det finnes ikke. Overlapper to serier i tid, vises begge —
avviket mellom dem er informasjon om målingene.

Trend beregnes ikke på tvers av de tre seriene (se § 7).

### Arbeidsdelingen mellom S1 og S5

De to seksjonene bruker delvis de samme seriene, og det er lett å ende opp med
at den ene gjentar den andre.

- **S1 gir helheten:** de globale seriene sammen i én oversiktsfigur, med
  synlige brudd.
- **S5 gir oppløsningen per serie:** K8, K9, K1, K5, K7 og K10 vist **hver for
  seg**, i separate figurer med hver sin akse og hver sin dekningsperiode,
  pluss `charcoal_index` (K10) som sin egen figur.

Samme data, ulik oppgave. **S5 skal ikke gjenta S1s oversiktsfigur.** Trenger
en leser å se seriene sammen, er det S1 som svarer på det.

**S5 er den seksjonen som lettest bryter reglene.** Seriene der har ulik kilde,
ulik `quality`, ulike startår og ulike definisjoner. Hver av dem skal ha
tydelig markering av at de ikke er direkte sammenlignbare, og trender beregnes
per serie, innenfor én kilde og én `quality`.

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
- `f_resolution_change` — dataenes romlige oppløsning er grovere i den
  tidligste delen av serien, noe som gir større usikkerhet

`f_missing_year` gjelder blant annet 1994 i K8. Et manglende år vises som
brudd i kurven, aldri som 0 og aldri som interpolert verdi.

`f_resolution_change` gjelder K9 for **1997–2000**, der oppløsningen er 1° mot
0,25° fra 2001.

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
- [ ] Påkrevde siteringer gjengis ordrett der kilden brukes (K7, K9, K10,
      og EFFIS-lisensen for K3/K4)
- [ ] Identifikatorer er engelske, alt leseren ser er norsk
- [ ] Ingen kodefil gjentar regler fra CLAUDE.md — den refererer til dem (T5)
- [ ] Enumerasjoner importeres fra `etl/schema.py`, aldri definert på nytt i
      en annen fil (T5)

---

## 12. Status

Prosjektet er i oppstartsfasen. Kun mappestruktur, konfigurasjon og dette
dokumentet finnes. ETL-koden er **ikke** skrevet ennå — `etl/*.py` inneholder
kun beskrivelser av ansvarsområde. Skriv den ikke uten at det er bedt om det.
