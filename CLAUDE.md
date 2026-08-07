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

Alle tallfestede påstander i brødteksten genereres maskinelt fra datasettet av
`etl/derive.py`. **Aldri unntak.** Ikke «omtrent», ikke «rundt», ikke «i
overkant av». Skal et tall stå i teksten, kommer det fra en mal som fylles fra
`data/processed/insights.json`.

**`derive.py` kjører i ETL, ikke under bygging av siden.** `insights.json`
committes som de andre filene under `data/processed/`, og byggesteget leser den
ferdige filen. En avledning som ble beregnet mens Astro bygde, ville ikke vært
sporbar i git — da kunne et tall på siden endre seg uten at noen endring var
committet, og bygget skal gi samme output for samme input (T3).

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

**Figurens CSV er figurens egen.** Byggesteget skriver én CSV per figur, med
nøyaktig de radene figuren tegner — samme serier, samme entiteter, samme år. En
kanonisk fil under `data/processed/` som også bærer andre serier, er ikke
«filen figuren bruker», selv om figuren henter tallene sine derfra. Leseren
skal kunne laste ned figuren som tall og få igjen det hen så, uten å måtte
filtrere selv.

De kanoniske filene er fortsatt nedlastbare i sin helhet fra S6 (§ 8). De to
lenkene svarer på hvert sitt spørsmål: figurens CSV på «hva står i denne
figuren», den kanoniske filen på «hva har dere i datasettet».

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

**km² er primærenheten for areal.** Arealindikatorer vises alltid i km² — i
aksetitler, tabeller, tooltips, nedlastbare CSV-filer under `data/processed/`
og avledede tall.

Indikatorer uten fysisk enhet følger sin egen `unit`, slik den står i
indikatortabellen i § 6.

All enhetskonvertering skjer i `etl/normalize.py`. Aldri i visningslaget, aldri
i JavaScript, aldri i en malfil. Kommer en kilde med hektar eller acres,
konverteres den én gang under normalisering, og den konverterte verdien er den
eneste som finnes videre i pipelinen.

Referanse: 1 km² = 100 ha = 1 000 000 m². 1 acre = 0,00404686 km².

**Arealindikatorer bærer enheten i feltnavnet:** `burned_area_km2`. En
arealindikator uten enhet i navnet er en feil.

Kravet gjelder ikke enhetsløse indikatorer. `charcoal_index` har ingen enhet å
bære, og navnet angir da hva verdien *er*, ikke hvilken enhet den har. Det
samme vil gjelde senere indikatorer uten fysisk enhet.

Hvilken `unit` hver indikator har, står i indikatortabellen i § 6 og i
`etl/schema.py`.

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
etl/                Python-pakke. __init__.py er tom.
  sources/          Én modul per kilde. Kun henting + råformat-parsing.
                    Egen pakke, med tom __init__.py.
  schema.py         Enumerasjonene, tersklene og stiene. Alt annet
                    importerer herfra (T5).
  normalize.py      Kanonisk form. All enhetskonvertering skjer her.
  grid.py           Rutenett → landnivå, med geometrien fra K6. Enhetsnøytral
  geo.py            Forenklet kartgeometri fra K6 → data/geo/verden.json
  derive.py         Maskinelle avledninger → data/processed/insights.json
  validate.py       Kontrollerer at output er gyldig før publisering
  test_derive.py    Kontroll av avledningene, mot datasett med kjent fasit.
                    python -m unittest discover -s etl -t .
  test_geo.py       Kontroll av forenklingen av kartgeometrien
  run.py            Kjører pipelinen: hent → normaliser → valider → avled →
                    publiser
  run_static.py     Samme for de statiske kildene. Egen inngang, ikke et flagg
                    til run.py, slik at den månedlige kjøringen ikke kan dra
                    dem med seg (§ 5)
data/
  raw/              Uendrede kildefiler. GITIGNORERT. Aldri committet.
  processed/        Kanoniske serier siden faktisk leser. Committes.
                    Filnavnene står i PROCESSED_FILE i schema.py
    insights.json   Maskinelle avledninger fra derive.py. Committes som de
                    andre. Ikke observasjoner, og valideres ikke som det
  geo/              Forenklet geometri for kart. Committes.
    land_no.json    Entitetskode → norsk navn og nivå. Delt av alle kilder.
    land_no_overrides.json
                    Redaksjonelle navneoverstyringer, med begrunnelse. Se § 5
    land_area_km2.json
                    Landarealer regnet fra K6. Nevner i andelsindikatoren
    verden.json     Forenklet kartgeometri fra K6. Bygget i Actions (T4)
  _sources.json     Kildemetadata: lisens, lenke, dekning, nedlastingsdato
  _status.json      Siste kjørestatus per kilde, for degradert visning
  _footnotes.json   Fotnotekode → norsk tekst. Se § 9
src/                Nettsidens kildekode
public/             Statiske ressurser som kopieres uendret
scripts/            Hjelpeskript til bygget, kjørt av npm. Ikke en del av ETL
.github/workflows/  ETL-kjøring og deploy
```

### Filnavn under `data/processed/`

Hvilken fil en serie havner i, er en **enumerasjon** og bor derfor ett sted i
kode (T5): `PROCESSED_FILE` i `etl/schema.py`, med `series_id` som nøkkel.
Ingen annen modul skriver et filnavn selv — verken `normalize.py`,
`run_static.py` eller en kildemodul.

De statiske kildene har hver sin fil, fordi hver av dem er én serie. De
månedlige seriene som deler indikator, ligger i samme fil: `burned_area.*`
bærer K1, K3, K4, K5 og K7. Det er filnavnet som er felles, ikke serien —
`series_id` skiller dem inne i filen, og hver figur tegner sine egne rader
(P5).

Et filnavn som allerede er publisert, døpes ikke om. Lenken i en kildelinje
skal fortsatt virke.

### Pakkeoppsett og importer

`etl/` og `etl/sources/` er Python-pakker. Begge har en tom `__init__.py`.

**Alle interne importer er absolutte:**

```python
from etl.schema import QUALITY, HA_TO_KM2
```

Aldri `from schema import ...`, aldri relative importer (`from .schema import
...`), aldri `sys.path`-manipulering. Ingen unntak — heller ikke i et
engangsskript eller en test.

**ETL kjøres som modul fra repotoppen:**

```
python -m etl.normalize
```

Ikke `python etl/normalize.py`. Kjøres en fil direkte, havner `etl/` selv på
`sys.path` i stedet for repotoppen, og da virker `from etl.schema import ...`
ikke. Det er den feilen som frister til `sys.path`-triksing, og grunnen til at
kjøremåten er fastslått her og ikke overlatt til skjønn.

Det samme gjelder i GitHub Actions: workflow-stegene kjører `python -m etl.<modul>`
med repotoppen som arbeidskatalog.

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
| K3 | EFFIS, landtotaler | Europa, Midtøsten, Nord-Afrika | 1980– | `reported` | Nasjonalt rapporterte totaler, som nedlastbar XLS |
| K4 | EFFIS, Rapid Damage Assessment | Europa, Midtøsten, Nord-Afrika | 2006– | `measured` | EFFIS' egen satellittkartlegging. Også grunnlag for brannstørrelsesfordeling |
| K5 | NIFC | USA | 1983– | `reported` | Lang nasjonal serie |
| K6 | Natural Earth, admin-0 | Global | — | — | Geometri og landarealer. Public domain |
| K7 | CNFDB / NBAC | Canada | 1972– areal, 1959– antall | `reported` | Krever sluttbrukeravtale — akseptert |
| K8 | FireCCILT11 (ESA Fire_cci) | Global | 1982–2018, uten 1994 | `beta` | Statisk. Selve produktet er merket beta av produsenten |
| K9 | GFED5 | Global | 1997–2020 | `measured` | Statisk. En publisert utgivelse dokumentert i Scientific Data. Hvilken av de to Zenodo-utgivelsene som har brent areal, står under § 5. Beta-merkingen gjelder kun produsentens `ext_Beta`-kataloger fra 2023, som vi holder ute |
| K10 | Global Charcoal Database | Global | — | `reconstructed` | Proxy. Statisk |

### Navnekilde: SSB Klass

De norske landnavnene kommer fra **Statistisk sentralbyrås standard for
landkoder alfa-3** (Klass 552), som knytter ISO 3166-1-koder til offisielle
norske navn.

Standarden har én versjon per revisjon. `ssb_klass.py` slår opp den gjeldende
versjonen ved kjøring i stedet for å låse en versjons-id, slik at en revisjon
hos SSB kommer med av seg selv.

SSB leverer **navn, ikke tallverdier**. Den tegnes ikke som en serie, står
ikke i kildekolonnen i § 8, og har derfor ingen K-kode. Den hører hjemme her
fordi navnene er synlige for leseren og må kunne spores.

`etl/sources/ssb_klass.py` henter standarden og bygger
`data/geo/land_no.json`. Håndskrevne navn er ikke tillatt — endres et navn,
endres det i SSBs standard eller i overstyringsfilen, aldri direkte i
`land_no.json`.

**Det SSB ikke dekker.** Standarden fører land og territorier, ikke
aggregater. Regionkodene, verdenskoden og `NONISO_`-kodene finnes derfor ikke
hos SSB, og navngis i `ssb_klass.py`. Det er ikke et unntak fra regelen over —
det finnes ingen SSB-form å hente for en kode SSB ikke har.

To avvik går andre veien: SSB fører Kosovo som `XXK`, mens vi bruker `XKX`
(§ 6), så oppføringen leses under SSBs kode og lagres under vår. Og
oppføringene «Uoppgitt» og «Statsløs» er ikke geografiske entiteter og tas
ikke inn.

Antarktis står i standarden, men ingen kilde vi bruker rapporterer entiteten,
og den holdes ute så tabellen bare inneholder entiteter det finnes tall for.
Kommer en kilde med tall for den, avviser `validate.py` observasjonen, og da
tas koden inn.

**Overstyringer.** Der SSBs form er uklar for en allmenn leser, overstyres den
i `data/geo/land_no_overrides.json`. Hver overstyring skal ha en begrunnelse i
filen. Eksempel: SSB kaller Den demokratiske republikken Kongo bare «Kongo»,
som er umulig å skille fra nabolandet med samme navn.

Overstyringer er et redaksjonelt unntak, ikke en snarvei. Er du i tvil, bruk
SSBs form.

### Statiske kilder

K8, K9 og K10 er **statiske**. De skal aldri inn i den månedlige ETL-kjøringen.
Datasettene er avsluttede utgivelser, ikke løpende serier — å hente dem på nytt
hver måned gir ingen nye data og bare unødig last. De hentes én gang, ved en
manuelt utløst workflow, og oppdateres kun hvis produsenten faktisk publiserer
en ny versjon.

### Avgrensninger per kilde

- **K6 Natural Earth** leverer ikke branndata. Den brukes til kartgeometri, til
  landarealer, som er nevneren i `burned_area_share_land`, og til å fordele
  rutenettkilder på land. Den tegnes ikke som egen serie, og står derfor ikke i
  kildekolonnen i § 8.

  Vi bruker **kartenhetene** i admin-0, ikke landene. Landlaget slår Fransk
  Guyana, Réunion, Svalbard og en del andre områder sammen med moderlandet, og
  da ville brent areal i Fransk Guyana blitt ført på Frankrike.
- **K2 GWIS** har to roller.

  Den ene er **kryssjekk mot K1**, som en ETL-validering: spriker K1 og K2 mer
  enn 5 % for samme enhet og år, produseres en avviksrapport. Rapporten er et
  arbeidsverktøy for redaktøren, ikke innhold på siden. Den publiseres ikke,
  og K2 tegnes ikke i noen figur i denne rollen.

  Terskelen er `CROSSCHECK_THRESHOLD` i `etl/schema.py`. Valideringskoden
  importerer konstanten og skriver aldri tallet selv (T5).

  **Kryssjekken sammenligner kun fullstendige år.** De to kildene hentes ikke
  på samme tidspunkt, og K1 er dessuten OWIDs kopi av K2. I et år som ikke er
  omme måler avviket derfor hvor lenge siden det er at hver av dem tok sin
  kopi, ikke om de er uenige om målingen.

  Det er ikke en antakelse: første gang rapporten ble kjørt over hele
  perioden, lå 53 av 69 avvik i inneværende år, og K2 lå høyere enn K1 i 68
  av 69. Tas inneværende år ut, står 16 avvik igjen — de som faktisk er
  revisjoner GWIS har gjort etter at OWID tok sin kopi.

  Dette er samme grunn som § 7 holder inneværende år utenfor alle
  avledninger. Kryssjekken er ingen avledning, men et ufullstendig år er like
  usammenlignbart her.

  Den andre er som datagrunnlag for **S3**, der ukesoppløsningen brukes. Det er
  den eneste seksjonen der K2 er synlig for leseren.

  **Ukesserien hentes per land og summeres til verdensdel og verden.** Kilden
  svarer ikke på sone i ukesendepunktet — en sonekode der landkoden skal stå,
  gir null rader. Inndelingen er derfor kildens egne sonelister, mens
  summeringen er vår, og det står i `data/_sources.json`.

  Verdenstallet summeres av landene, ikke av sonene. Et land kan ligge i flere
  soner eller i ingen, og en sum av soner ville telt det to ganger eller ikke i
  det hele tatt.

  FN-inndelingen kilden bruker har Amerika som én verdensdel. Vi fører Nord- og
  Sør-Amerika hver for seg, og bruker derfor kildens makroregioner for de to.

  Landene selv publiseres ikke. De ville gitt over 180 000 rader uten at noen
  figur viser dem, og S3 spør om når på året det brenner hvor — ikke om det
  enkelte landet.

  **Hentingen er skånsom og bufret.** Ukesserien er én forespørsel per land og
  år, og GWIS er en offentlig tjeneste vi ikke betaler for. Det er derfor pause
  mellom forespørslene, med lengden som `GWIS_REQUEST_PAUSE_S` i `schema.py`.

  Et fullstendig år hentes aldri på nytt: den publiserte filen er
  hurtigbufferen, og en månedlig kjøring ber bare om inneværende år. Det betyr
  også at en revisjon GWIS gjør i et gammelt år, ikke fanges opp av seg selv —
  vil man ha den, må filen slettes og serien hentes på nytt.
- **K3 og K4 er to ulike produkter fra EFFIS**, og skal ikke forveksles.

  **K3** er landtotalene EFFIS publiserer som nedlastbar XLS sammen med
  årsrapporten. De er nasjonalt rapporterte, følger hvert lands egne
  definisjoner, og har derfor `f_reporting_basis`. Serien starter i 1980, men
  bare med de fem første EFFIS-landene — flere kommer til utover i serien, og
  den bærer derfor `f_coverage_change`.

  **K4** er EFFIS' egen Rapid Damage Assessment: satellittkartlegging fra
  MODIS, VIIRS og Sentinel-2. Den er `measured`, ikke `reported`, og skal
  aldri ha `f_reporting_basis` — tallene er ikke rapportert av noen. Som de
  andre satellittproduktene bærer den `f_product_level`, fordi den ser en
  annen andel av brannene enn K1 gjør og derfor ligger på et annet nivå for
  samme år.

  At kartleggingen gjøres mens sesongen pågår og revideres når bedre bilder
  foreligger, står i kildens `notes` i `data/_sources.json`. Det er en
  egenskap ved kilden, ikke et forbehold ved den enkelte observasjonen, og
  får derfor ingen fotnote.

  De to dekker samme geografi og overlapper i tid. De skal aldri skjøtes
  sammen til én serie, og en figur som viser begge må markere bruddet, av
  samme grunn som ellers i § 6: det er to målemetoder, ikke én måling.

- **K8 FireCCILT11** er et rutenettprodukt på 0,25°, ikke landtall. En rute er
  om lag 773 km² ved ekvator, som er det største den kan bli i dette nettet.
  Det er den målestokken `f_grid_resolution` regnes mot for denne kilden (§ 9).

  De månedlige rutenettene summeres til årlige landtotaler med kartenhetene fra
  K6: hver rute deles i et finere delrutenett, og rutens verdi fordeles mellom
  landene i ruten etter hvor stor del av **landarealet** i ruten hvert av dem
  har. Havet får ingenting — brent areal finnes bare på land, og en kystrute
  skal ikke miste arealet sitt fordi halve ruten er sjø.

  En rute som bærer brent areal uten at noen landgeometri når fram, kan ikke
  tilskrives et land. Verdien går da til en uattribuert andel, som
  `GRID_MAX_UNATTRIBUTED_SHARE` i `etl/schema.py` setter en øvre grense for.
  Verdien forsvinner ikke: verdenstallet summeres fra rutenettet selv og ikke
  fra landene, slik at de rutene fortsatt teller globalt.

  Andelen skrives til `data/_status.json` ved hver kjøring, som
  `unattributed_share` og `unattributed_km2`. Den er ikke bare en terskel å
  passere: den sier hvor mye brann som faller utenfor all landgeometri, og skal
  kunne følges fra kjøring til kjøring. Endrer den seg mye mellom to kjøringer,
  har enten geometrien eller rutenettet endret seg.

- **K9 GFED5** brukes kun for de årene produsenten har publisert, og har
  `quality` `measured`. GFED5 er dokumentert i Scientific Data. Produsentens
  `ext_Beta`-kataloger fra 2023 og framover holdes ute — det er *de* som er
  foreløpige, ikke datasettet vi bruker. Årene **1997–2000** har grovere romlig
  oppløsning enn resten av serien (1° mot 0,25° fra 2001), og skal alltid ha
  `f_resolution_change`.

  **Brent areal ligger i én bestemt utgivelse, og bare der.** GFED5 finnes i to
  Zenodo-utgivelser, og de inneholder ikke det samme:

  - `10.5281/zenodo.7668424`, *GFED5 Burned Area*: månedlige rutenett med laget
    `Total` i km², **1997–2020**, 1° til og med 2000 og 0,25° fra 2001. Det er
    denne vi henter.
  - `10.5281/zenodo.16794692`, artikkelutgivelsen GFED5.1: `monthly`- og
    `daily`-arkivene inneholder **kun utslipp** av 40 gasser og aerosoler, som
    er utenfor scope (P8). Brent areal finnes der bare i `ecosystem`-arkivet,
    som starter i 2002 og er 0,25° hele veien — og som derfor verken dekker
    1997 eller har oppløsningsskiftet.

  **Dekningen er 1997–2020, og det er ikke en luke som skal fikses.** Årene
  2021 og 2022 finnes som brent areal kun i `ecosystem`-arkivet, som er et
  annet produkt med annen dekning og annen oppløsningshistorikk. Å skjøte dem
  på ville krysset en produktgrense — den samme feiltypen § 7 forbyr for trend
  — for å dekke to år som allerede er dekket av K1 i S1s oversiktsfigur.

  Leseren mister altså ingenting. Ser serien kort ut i enden, er det fordi
  produsenten har delt datasettet, ikke fordi noe mangler på siden. Utvid den
  ikke.

  **Nivået er kontrollert mot kilden.** GFED5 oppgir 774 ± 63 Mha per år for
  2001–2020, og vår aggregering gir 775,5 Mha for de samme årene. Produktet
  ligger 93 % over MCD64A1 og 61 % over GFED4s fordi det korrigerer for
  commission- og omission-feil med Landsat og Sentinel-2, og legger til areal i
  jordbruksland, torvmark og avskogingsområder fra aktiv branndeteksjon.

  Det er derfor K9 ligger nesten dobbelt så høyt som K1 for de årene begge
  dekker. Forskjellen er et produktavvik, ikke en feil hos oss og ikke en
  endring i verden — se `f_product_level` i § 9.

  Kilden oppgir km² per rute. Rutenettene summeres til landnivå på samme måte
  som K8, men med én maske per oppløsning: terskelen for `f_grid_resolution` og
  settet av entiteter rutenettet ikke treffer, regnes mot det rutenettet som
  gjelder for det enkelte året. En rute ved ekvator er om lag 12 400 km² ved 1°
  og 773 km² ved 0,25°, så de to periodene treffer ulike entiteter.

  K8 er derimot `beta` fordi selve produktet er merket slik av produsenten.
  Skillet er hvem som har merket hva: en produsents beta-merking på et annet
  datasett i samme katalog smitter ikke over.
- **K10 Global Charcoal Database** er et *proxy*: sedimentært kull som
  indirekte spor etter brann, ikke en måling av brent areal. Alltid
  `f_proxy`. Serien er global og har ikke landnivå.

  Kompositten bygges av R-pakkene `GCD` og `paleofire`, som er de samme
  verktøyene metoden er publisert med. `paleofire` ble trukket fra CRAN i
  januar 2023 og installeres fra arkivet. Pakken er fra 2019 og trenger to
  mekaniske lapper for å kunne installeres og lastes i dag:

  - `NAMESPACE` importerer `rgdal`, som selv ble trukket i oktober 2023, og som
    pakken bare bruker i funksjoner vi ikke kaller.
  - `pfTransform` avgjør med en kjede av `||`-sammenligninger om en av de
    rullende metodene er bedt om. R 4.3 gjorde det til en feil å gi `||` en
    vektor, og `method` *er* en vektor når kompositten bygges med flere
    metoder.

  Begge lappene står i `etl/sources/k10_lapp_paleofire.py`, som stopper hvis
  pakken ikke ser ut som lappene er skrevet for — en annen versjon skal ikke
  lappes blindt. Beregningene kompositten bygges av, røres ikke. At pakken er
  lappet, står i `data/_sources.json`.

  R-skriptet skriver CSV-en før det gjør noe annet med resultatet. En kompositt
  som først er beregnet, skal ikke gå tapt fordi et senere steg feiler.

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

**K8 — FireCCILT11.** Kilden krever at siteringen på katalogoppføringen gjengis,
og bruken er dekket av Fire_cci-vilkårene, som lenkes fra `data/_sources.json`.

> Chuvieco, E.; Pettinari, M.L.; Otón, G. (2020): ESA Fire Climate Change
> Initiative (Fire_cci): AVHRR-LTDR Fire_cci Burned Area Grid product, version
> 1.1. Centre for Environmental Data Analysis, 28 December 2020.
> doi:10.5285/62866635ab074e07b93f17fbf87a2c1a.

**K9 — GFED5.** Vi bruker brent areal-produktet, og siteringen er artikkelen
som dokumenterer *det*. Utslippsartikkelen under dokumenterer et annet produkt
i samme familie og er ikke siteringen for disse tallene.

> Chen, Y., Hall, J., van Wees, D., Andela, N., Hantson, S., Giglio, L.,
> van der Werf, G. R., Morton, D. C., and Randerson, J. T.: Multi-decadal
> trends and variability in burned area from the fifth version of the Global
> Fire Emissions Database (GFED5), Earth Syst. Sci. Data, 15, 5227–5259,
> https://doi.org/10.5194/essd-15-5227-2023, 2023.

Når K9 hentes, legges følgende i `data/_sources.json`:

- `doi`: `10.5194/essd-15-5227-2023`
- `dataset_doi`: Zenodo-utgivelsen tallene faktisk er lastet ned fra
- GFED5.1-artikkelen som **eget felt** under `related_publication`: van der
  Werf m.fl. (2025), Scientific Data 12, 1870,
  `https://doi.org/10.1038/s41597-025-06127-w`, med sin publiserte rettelse —
  Publisher Correction, Scientific Data 13, 44 (15. januar 2026),
  `https://doi.org/10.1038/s41597-026-06613-9`

GFED5.1-artikkelen og rettelsen føres som egne felt, ikke som en endring av
siteringen, slik at det er sporbart hvilken artikkel som dokumenterer hva.

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

Alle kilder normaliseres til langformat før publisering.

Eksempelet under viser **formen**, ikke innholdet. Verdiene er oppdiktede og
skal ikke sammenlignes med datasettet — feltene og kodeverdiene er poenget.
Faktiske tall står i `data/processed/`.

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
- `period`: ISO 8601 — `YYYY`, `YYYY-MM` eller `YYYY-Www`. Årstallet kan bære
  fortegn: proxyen i K10 rekker ned før år null, og `-0500` er år 500 fvt.
  Måleseriene starter alle etter 1900, så fortegnet finnes bare i K10
- `quality`: `measured` | `reported` | `beta` | `reconstructed`
- `unit`: `km2` | `share` | `zscore` | `count`

Feltene over er obligatoriske. En kilde kan i tillegg bære **valgfrie felt** der
den har informasjon de andre ikke har, og da bare i den kildens egne filer —
kolonnen skal ikke stå tom i alle de øvrige. I dag finnes ett:

- `n_series` — antall serier bak punktet, for kilder der hvert punkt er satt
  sammen av flere. K10 fører det, fordi antallet avgjør hvor langt tilbake
  kurven kan vises, og fordi det ellers bare ville stått i en fil som slettes

### Entitetskoder

`data/geo/land_no.json` er **fasit** for hvilke `entity`-koder som finnes, hva
de heter på norsk, og hvilket `level` de har. Alle kilder slår opp der, slik at
samme land får samme norske navn uansett hvilken kilde tallet kommer fra.
`validate.py` avviser en observasjon med en `entity` som ikke står i filen.

- **Land** bruker ISO 3166-1 alpha-3.
- **Koder utenfor ISO 3166 er våre egne** og merket `iso3: false`. De skal
  ikke kunne forveksles med tildelte ISO-koder, for en leser som ser `XNC` i
  en CSV har ingen måte å vite at koden ikke er standard.

  Derfor får territorier uten etablert kode prefikset `NONISO_`:
  `NONISO_CYN` Nord-Kypros, `NONISO_AKD` Akrotiri og Dhekelia. Understrek
  finnes ikke i ISO 3166, så formen er selvforklarende.

  **`XKX` Kosovo er unntaket.** Den beholder X-formen fordi den er utbredt
  praksis og gjenkjennes av andre datasett. Å døpe den om ville gjort
  kryssbruk mot andre kilder vanskeligere uten å vinne noe.
- **Regionkoder** er valgt så de ikke kolliderer med tildelte ISO3-koder:
  `WLD` verden, `EUR` Europa, `EUR_XRU` Europa uten Russland, `EU27` EU,
  `AFR`, `ASI`, `NAC` Nord-Amerika, `SAM` Sør-Amerika, `OCE` Oseania.

**`NAC`, ikke `NAM`, for Nord-Amerika.** `NAM` er ISO3 for Namibia. Kilder som
bruker en egen kode for Nord-Amerika må oversettes i kildemodulen, ikke tas inn
rått.

### Indikatorer

Hver `indicator` har nøyaktig én tillatt `unit`. Kombinasjoner utenfor tabellen
er en feil.

| `indicator` | `unit` | Vises som | Kilde | Merknad |
|---|---|---|---|---|
| `burned_area_km2` | `km2` | km² | K1–K5, K7–K9 | Brent areal |
| `burned_area_share_land` | `share` | prosent | avledet, nevner fra K6 | Brent areal som andel av landareal. Gjør små og store land sammenlignbare |
| `charcoal_index` | `zscore` | enhetsløst tall | K10 | Z-score |
| `fire_count` | `count` | antall | K3, K5, K7 | Antall registrerte branner. Sier noe annet enn arealet: mange små branner og én stor kan gi samme areal |

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
| `reconstructed` | Rekonstruert eller proxy | Linje på egen akse |

**Bånd brukes bare der kilden selv leverer et usikkerhetsintervall.** K10 har
ikke noe slikt mål — kompositten er én kurve, og `n_series` sier hvor mange
serier som ligger bak et punkt, ikke hvor mye de spriker. Et bånd rundt den
ville tegnet en spredning vi ikke har målt, og det er en påstand siden ikke
gjør (P1). `reconstructed` tegnes derfor som linje på egen akse.

Kommer det senere en kilde som selv oppgir et intervall, kan intervallet tegnes
som bånd. Da er båndet kildens egne tall, og tegnforklaringen sier hvilket
intervall det er.

`beta` betyr at **produsenten selv** har merket datasettet som foreløpig. Det
er ikke vår vurdering av datakvaliteten. Serier med `beta` skal alltid ha
`f_beta_product`, og den reduserte opasiteten skal forklares i figurens
tegnforklaring — en leser skal ikke måtte gjette hva den blekere linjen betyr.

Serier med ulik `quality` slås **aldri** sammen til én kurve uten synlig
markering av bruddet.

### Hvem kontrollerer hva

Regelen over håndheves i to lag, fordi ingen av dem ser hele bildet alene.

- **`validate.py`** kjører i ETL og ser data, ikke figurer. Den kontrollerer at
  **dataene** er gyldige: at hver serie har én `quality`, og at ingen
  `series_id` har blandede verdier.
- **Byggesteget for siden** ser figurene. Det kontrollerer at **ingen figur**
  tegner flere `quality`-verdier uten at bruddet er markert. Kontrollen står i
  `src/lib/figurkontroll.ts` og kjøres når figurlisten bygges, slik at et brudd
  stopper bygget framfor å bli publisert.

  En figur som blander kvaliteter, oppgir `kvalitetsforklaring`: én tekst per
  kvalitet den tegner. Kontrollen krever at hver av dem faktisk står i figurens
  tegnforklaring — en markering som bare finnes i koden, når ikke leseren, og
  teller derfor ikke.

En figur kan lovlig vise flere serier med ulik `quality` — S1s oversiktsfigur
gjør nettopp det. Det `validate.py` ikke kan avgjøre, er om bruddet mellom dem
er markert, for den vet ikke hva som havner i samme figur. Legg derfor aldri
figurkontrollen i ETL, og legg aldri datakontrollen i byggesteget.

**Ulike startår skjules ikke.** Hver figur viser dekningsperioden eksplisitt.
Land uten data for et gitt år vises som «ingen data», aldri som null.

**Inneværende år** markeres alltid visuelt som ufullstendig. Det kan vises i
figurer, men inngår aldri i beregningsgrunnlaget for noen avledning — se § 7.

---

## 7. Tillatte maskinelle avledninger

`derive.py` produserer kun disse. Alt annet krever at prinsippene diskuteres på
nytt.

### Grunnlaget: alltid fullstendige år

**Alle avledninger regnes over fullstendige år. Inneværende år inngår aldri i
grunnlaget** — verken for trend, rangering, avvik fra normal, konsentrasjon,
andel, dekning eller for å avgjøre om en entitet er «alltid null».

Dette er **én definisjon som gjelder alle avledninger**, ikke en regel per
avledning. Grunnen er at samme entitet ellers kan være ekskludert i én figur og
med i en annen, og da vil to figurer på samme side motsi hverandre uten at
leseren får vite hvorfor.

En verdi fra et ufullstendig år er ikke sammenlignbar med et helt år. Den er
lavere fordi året ikke er omme, ikke fordi det brant mindre. Da skal den heller
ikke kunne avgjøre om en entitet i det hele tatt kan rangeres.

**Konsekvens, som skal være synlig og ikke overraske noen:** Grenada regnes som
alltid null og utelates fra rangering og avvik fra normal, selv om entiteten
har en verdi i inneværende år. Antallet entiteter som utelates er derfor **48,
ikke 47**.

Tallene 48 og 47 beskriver datasettet slik det var da regelen ble skrevet, og
er tatt med for å vise hva regelen gjør. De er ikke en fasit å validere mot —
settet beregnes på nytt hver kjøring, se under.

**Skillet er mellom å vise og å regne.** Inneværende år kan fortsatt tegnes i
figurer, markert som ufullstendig (§ 6). Det er kun beregningsgrunnlaget det
holdes utenfor.

**Settet av ekskluderte entiteter beregnes på nytt ved hver ETL-kjøring.** Det
skal aldri fryses som en liste i kode. En entitet kan få sin første påviste
brann, og da skal den inn i rangeringen ved neste kjøring uten at noen må huske
å redigere en liste. En håndholdt liste ville dessuten vært den tredje kopien
T5 forbyr.

| Avledning | Definisjon |
|---|---|
| Rangering | «År X er nummer N av M år med data for enhet E» |
| Avvik fra normal | Verdi mot median for hele dekningsperioden, i prosent |
| Trend | Theil–Sen-estimator med Mann–Kendall-test. Rapporteres med retning, størrelse per tiår og p-verdi. Ikke-signifikant trend rapporteres som «ingen statistisk signifikant trend» |
| Andel | Enhetens andel av globalt totaltall for gitt år |
| Konsentrasjon | Andel av totalt brent areal fra de N største brannene eller landene |
| Dekning | Første og siste år med data per enhet og serie |
| Felles dekning | Årene alle seriene for én indikator og entitet dekker samtidig |
| Arealsammenligning | Landet hvis landareal ligger nærmest en gitt arealverdi, valgt maskinelt fra Natural Earth-arealene (K6) |
| Sesongprofil | Median brent areal per uke i året, over fullstendige år, per entitet |
| Sesongbånd | Kumulativ kurve per uke: median og persentilbånd over fullstendige år |

**Felles dekning** svarer på hvilke år to eller flere serier faktisk måler de
samme årene. Skal et enkeltår sammenligne to produkter — som når S1 og S5 viser
nivåforskjellen mellom satellittproduktene — må året være et år begge dekker,
og hvilket år det er, følger av dekningen. Et årstall skrevet inn i en mal
ville vært riktig den dagen det ble skrevet og stille galt den dagen en serie
ble utvidet.

Overlappet regnes per indikator, over de seriene som fører entiteten, og
beregnes ikke når færre enn to serier gjør det eller når de ikke overlapper i
det hele tatt.

**Arealsammenligning** gir leseren en fysisk referanse for et tall i km², som
ellers er vanskelig å forestille seg. Sammenligningslandet velges maskinelt
som det med minst absolutt avvik i landareal — ingen redaksjonelt valgte
eksempler, ingen «omtrent på størrelse med». Avviket i prosent oppgis sammen
med sammenligningen, slik at leseren ser hvor god tilnærmingen er.

Regelen garanterer at det finnes et sammenligningsland, ikke at det er et
godt et. Landarealene ligger ujevnt fordelt, og et tall som havner i en luke
mellom to land, får et sammenligningsland med stort avvik. Setningen skal
derfor alltid ta med avviket, aldri bare navnet.

**Sesongprofil og sesongbånd** er de to avledningene S3 bygger på, og begge
regnes uke for uke over fullstendige år.

Profilen er medianen for hver uke: uke 1 mot uke 1 i de andre årene, uke 2 mot
uke 2. Den svarer på når på året det brenner et sted — brannsesongen.

Båndet er den samme øvelsen på den kumulative kurven, altså summen fra uke 1 og
utover. For hver uke sorteres årene, og båndet dekker `SEASON_BAND_PCT` i
`etl/schema.py`: ett år av ti ligger over, ett av ti under. Linjen inne i
båndet er medianen.

Inneværende år inngår i ingen av dem. Det tegnes for seg, som sin egen
kumulative kurve, og båndet sier hva et helt år pleier å være — noe et år som
ikke er omme, ikke kan være med på å definere (§ 7, grunnlaget).

Persentilene er regnet med lineær interpolasjon mellom ordningsverdiene, samme
konvensjon som numpy og R type 7. Med fjorten år ligger den tiende persentilen
mellom to observasjoner, og en avrunding til nærmeste ville flyttet båndet et
helt år ut eller inn.

**Konsentrasjon** regnes over de `CONCENTRATION_TOP_N` største, og beregnes
ikke når serien har like få entiteter som N eller færre. Da er «de største»
alle sammen, og andelen sier ingenting. Nevneren er seriens eget verdenstall
der det finnes — for rutenettkildene bærer det også areal som ikke lot seg
tilskrive et land (§ 5) — og ellers summen av entitetene. Hvilken nevner som
er brukt, følger med avledningen.

**Avvik fra normal og andel regnes bare på forholdstall.** Prosent forutsetter
at skalaen har et nullpunkt: at halvparten så mye er halvparten. `km2`,
`count` og `share` har det. `charcoal_index` er en z-score, altså en avstand
i standardavvik fra seriens eget gjennomsnitt, og «40 prosent over normalen»
ville vært et regnestykke på en skala der normalen er null. Kompositten får
derfor dekning og ingenting annet.

Av samme grunn beregnes ikke avvik fra normal når medianen er null. Da har
uttrykket ingen nevner, og en entitet uten en eneste påvist brann har ingen
normal å avvike fra.

**Store avvik skrives som multiplikator, ikke som prosent.** Over
`ANOMALY_FACTOR_PCT` sier setningen «nesten femti ganger medianen» i stedet
for «4 745 prosent over normalen». Et firesifret prosenttall er ikke en
størrelse en leser kan se for seg, og det leses som et utrop selv når det er
regnet riktig.

Verdien er den samme i begge tilfeller. `insights.json` fører både
`deviation_pct` og `factor`, og `express_as` sier hvilken av dem setningen
skal bruke — det er formuleringen som skifter, ikke tallet.

Grensen gjelder bare oppover. Under medianen er avviket begrenset av
−100 prosent og blir aldri uleselig.

### Hver avledning har et grunnlag som kan oppgis

En avledning er ikke bare et tall. Den bærer serien, kilden, `quality`,
entiteten, enheten og hvilke år den er regnet over, slik at setningen som
bruker den, kan si det samme. Et tall uten dekningsperiode er ikke sporbart,
og «nummer 3 av 14» betyr ingenting uten å si hvilke fjorten år.

Verdier som er tvetydige nuller (`f_zero_no_detection`), merkes i avledningen
de inngår i. En rangering eller et avvik som hviler på en slik null, skal
kunne bære fotnoten videre til leseren.

### Trend: aldri på tvers av kilde eller kvalitet

Trendberegninger kjøres **kun innenfor én kilde og én `quality`-verdi**. Aldri
på en serie som er skjøtt sammen av flere kilder, og aldri på tvers av ulike
`quality`-verdier.

Grunnen er at et skifte av kilde eller målemetode gir et nivåbrudd i serien.
En regresjon over et slikt brudd måler skiftet i metode, ikke en endring i
verden, og gir en trend som ser reell ut uten å være det. Trenger to serier å
vises sammen, tegnes de som to serier med synlig brudd, med hver sin trend
eller ingen.

**Signifikansnivået er `TREND_ALPHA` i `etl/schema.py`.** Over den p-verdien
rapporteres trenden som «ingen statistisk signifikant trend» — ikke som
fravær av endring. De to er ikke det samme, og setningen skal ikke si at det
ikke skjer noe.

**Korte serier får ingen trend.** Mann–Kendall bruker en normaltilnærming som
ikke holder for få år, og `TREND_MIN_YEARS` i `etl/schema.py` setter grensen.
En p-verdi regnet på en håndfull punkter ville sett like presis ut som en
regnet på førti, og det er nettopp den forskjellen leseren ikke kan se.

**Aggregater har en høyere grense: `TREND_MIN_YEARS_AGGREGATE`.** Den gjelder
`level: world` og `level: region`.

Grunnen står i dataene. K1s verdensserie flytter seg fra −477 000 til
−638 000 km² per tiår når 2025 tas med, og p-verdien fra 0,044 til 0,012. Ett
år av fjorten som flytter både størrelsen og signifikansen, er ikke et
grunnlag for å publisere en trend som oppsummerer noe. K8 og K9, som har 36 og
24 år, beholder sine.

**Skjørheten følger serielengden, ikke aggregeringsnivået.** K1s regioner har
de samme fjorten årene som verdensserien, og ett år veier like tungt der. Å
publisere en europeisk trend, men ikke en global, fra samme kilde med samme
grunnlag, ville vært en asymmetri uten begrunnelse.

Land beholder `TREND_MIN_YEARS`. Der er den korte serien en begrensning ved
kilden, og en nasjonal trend leses ikke som en uttalelse om verden.

**Glattede serier får ingen trend.** K10 er et vektet snitt over et vindu på
flere hundre år (`f_smoothed`, § 9), og nabopunktene er derfor ikke
uavhengige. Mann–Kendall forutsetter at de er det. Testen ville gitt en
p-verdi som utelukkende måler glattingen, og en slik p-verdi er en påstand om
sikkerhet vi ikke har.

### Nullverdier i avledninger

Nuller merket `f_zero_no_detection` er tvetydige: de kan bety at ingenting
brant, at brannene lå under deteksjonsgrensen, eller at området ikke var
dekket. Kilden skiller ikke. Hver avledning må derfor si eksplisitt hva den
gjør med dem.

**Trend beregnes ikke** når én av disse er oppfylt:

- Nullene utgjør mer enn `TREND_MAX_ZERO_SHARE` av observasjonene
- Serien ender i en sammenhengende rekke nuller lengre enn
  `TREND_MAX_ZERO_TAIL`

Begge konstantene står i `etl/schema.py`.

Grunnen er den samme feiltypen som § 7 allerede forbyr for kildebrudd, men den
oppstår **innenfor** én kilde og fanges derfor ikke av den regelen. Qatar er
eksempelet: ni år med deteksjoner fulgt av seks år med null. En Theil–Sen-linje
gjennom det gir en kraftig fallende trend som utelukkende måler at
deteksjonene stoppet. Om det brant mindre, eller om kilden sluttet å se det,
vet vi ikke — og en trend som ikke kan skille de to, skal ikke publiseres.

Haleregelen fanger det som andelsregelen ikke ser: en serie kan ha få nuller
totalt, men ha dem alle til slutt. Det er nettopp det mønsteret som gir en
falsk nedgang.

**Rangering og avvik fra normal** utelater entiteter der **alle** verdier er 0.
En entitet uten en eneste påvist brann kan ikke rangeres mot andre, og har
ingen median å avvike fra. Å gi den plass N av M ville antydet en måling som
ikke finnes.

«Alle verdier» betyr alle verdier i **fullstendige** år, slik grunnlaget er
definert over. Inneværende år teller ikke med når det avgjøres om en entitet er
alltid null.

**Konsentrasjon og andel** tar nullene med. En null bidrar med 0 til en sum og
til en andel, og påvirker verken telleren eller nevneren feil. Her er
tvetydigheten uten praktisk konsekvens.

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
| S5 | Den lange linjen | De samme seriene som i S1, pluss de nasjonale og proxyen, vist **hver for seg** i separate figurer med hver sin akse og hver sin dekningsperiode. Kompositten avgrenses ved den yngste enden, se § 9 | K1, K5, K7, K8, K9, K10 |
| S6 | Om dataene | Kildeoversikt, definisjoner, ordliste, alle fotnoter samlet, nedlastingslenker til alle bearbeidede CSV-filer, lenke til repoet | alle |

**Hva kildekolonnen betyr.** Kolonnen lister kilder som leverer **tallverdiene
figurene viser**.

Kilder som leverer geometri, nevnere for avledede indikatorer eller
valideringsgrunnlag står **ikke** der — selv om de rendres på skjermen. De er
beskrevet under sin egen oppføring i § 5.

Derfor står ikke K6 i S2 og S4, selv om kartene tegnes med geometri derfra og
`burned_area_share_land` bruker landarealene som nevner. Og derfor står ikke
K2 i S1, selv om den brukes til å kryssjekke K1. Kolonnen svarer på hvor
tallene kommer fra, ikke hva som var involvert i å tegne figuren.

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
- Aksen oppgir alltid indikatorens enhet, slik den står i indikatortabellen i
  § 6: km² for `burned_area_km2`, prosent for `burned_area_share_land`,
  enhetsløst tall for `charcoal_index`
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
- `f_zero_no_detection` — kilden har ikke påvist brent areal, men skiller ikke
  mellom «ingenting brant» og «ingen måling»
- `f_record_start` — serien starter der kilden begynte å rapportere
  systematisk, og eldre år finnes ikke
- `f_incomplete_inventory` — databasen er verken komplett eller feilfri, og
  datakvaliteten varierer mellom rapporterende byråer og år
- `f_product_level` — satellittprodukter har ulik deteksjonsevne, så
  nivåforskjellen mellom to serier er ikke en endring i verden
- `f_grid_resolution` — landet er lite i forhold til rutenettets oppløsning,
  slik at brent areal kan falle mellom rutene
- `f_smoothed` — hvert punkt er et glidende gjennomsnitt over en lengre
  periode, ikke en enkeltmåling
- `f_thinning_record` — mot slutten av perioden bygger kurven på færre kilder,
  fordi sedimentkjernene slutter ved innsamlingstidspunktet

`f_product_level` gjelder de satellittmålte arealseriene: K1, K4, K8 og K9.
Den sier at to serier kan ligge på ulikt nivå for samme år fordi produktene ser
ulikt mye, og at avstanden mellom dem derfor ikke er informasjon om verden.

Den overlapper ikke med `f_min_fire_size`. Den fotnoten sier hva én serie ikke
fanger opp; denne sier at *avstanden mellom to serier* ikke kan leses som en
endring. Nasjonalt rapporterte kilder får den ikke — de har `f_reporting_basis`
for en annen mekanisme, nemlig at definisjonene er ulike, ikke at
deteksjonsevnen er det.

Grunnen til at den trengs, er at kvalitetsbruddet i § 6 ikke fanger dette. K1
og K9 er begge `measured`, så en figur som viser dem sammen tegner to
heltrukne linjer uten noe som forklarer at den ene ligger nesten dobbelt så
høyt som den andre.

**Hvor fotnotetekstene bor.** Kodene over er enumerasjonen, og følger T5: prosa
her, konstant i `etl/schema.py`. Den norske teksten leseren ser er noe annet —
den er visningslagets oversettelse fra kodeverdi til lesbar tekst (§ 1), og står
i `data/_footnotes.json`.

Filen er ikke en tredje kopi av enumerasjonen. Kodene ligger under nøkkelen
`footnotes`, ved siden av `_om` og `_skjema`, som forklarer filen for den som
åpner den uten å kjenne dette dokumentet. `validate.py` kontrollerer at nøklene
**under `footnotes`** er nøyaktig `FOOTNOTE` fra `schema.py`, verken flere eller
færre, så en ny kode kan ikke tas i bruk uten tekst og en tekst kan ikke bli
stående etter at koden er fjernet.

`f_missing_year` gjelder blant annet 1994 i K8. Et manglende år vises som
brudd i kurven, aldri som 0 og aldri som interpolert verdi.

`f_resolution_change` gjelder K9 for **1997–2000**, der oppløsningen er 1° mot
0,25° fra 2001.

`f_zero_no_detection` gjelder K1, K4, K8 og K9. Kriteriet er ikke hvilken form
kilden har, men hva en 0 fra den betyr: kilden fører entiteten og året med
verdien 0 i stedet for å utelate raden, og skiller ikke mellom «ingenting
brant», «brannene lå under deteksjonsgrensen» og «området ble ikke sett».
`normalize.py` merker hver nullverdi med fotnoten.

Formen er ulik, tvetydigheten er den samme. K1 og K8 leverer et fullt rutenett
av entiteter og år. K9 leverer de entitetene rutenettet treffer, for alle år i
dekningen. K4 er landtotaler og ikke et rutenett i det hele tatt, men EFFIS
fører landet med 0 for år uten kartlagt areal — og den nullen kan like gjerne
bety at kartleggingen ikke fant noe som at ingenting brant.

Dette er ikke det samme som «ingen data». En figur skal ikke tegne en 0 fra
disse kildene som en målt null uten at fotnoten følger med.

**Merkingen er også maskinlesbar, og det er poenget.** Trendreglene i § 7 finner
nullene sine gjennom denne fotnoten: `TREND_MAX_ZERO_SHARE` og
`TREND_MAX_ZERO_TAIL` gjelder de nullene som bærer `f_zero_no_detection`.
Merkes de ikke, gjelder terskelene ikke for serien, og en falsk nedgang av
Qatar-typen — deteksjoner som stopper, ikke branner som avtar — ville passert
ubemerket. En rutenettkilde som ikke merker nullene sine, undergraver derfor en
regel som står et helt annet sted i dokumentet.

`f_thinning_record` gjelder K10, og henger sammen med at **visningen av
kurven avgrenses ved den yngste enden**.

Antall serier bak hvert punkt står i `n_series` (§ 6). Det stiger fra rundt 110
i den eldste delen til 360 rundt 1950, og faller så til 99 i det yngste
punktet. Fallet skyldes at sedimentkjerner slutter ved innsamlingstidspunktet,
ikke at noe skjer i verden — og det sammenfaller med den delen der kurven
stiger kraftigst. Å vise den enden uten avgrensning ville invitere til en
lesning dataene ikke bærer.

**Regelen:** fra det yngste punktet og bakover utelates punkter fra visningen
så lenge `n_series` er under `COMPOSITE_MIN_SERIES_SHARE` av det tetteste
punktet. Den stopper ved det første punktet som er over.

Terskelen er en **andel**, ikke et antall og ikke et årstall. Et antall ville
blitt feil hvis databasen vokser, og et årstall ville vært en fasit vi måtte
huske å endre. Grensen beregnes ved bygging, av dataene selv, og skal aldri
fryses (§ 7, T5). `etl/schema.py` eier tallet; kilden skriver det til
`data/_sources.json` som `min_series_share`, fordi byggetrinnet er TypeScript
og ikke kan lese `schema.py` — verdien har fortsatt bare ett hjem.

**Punktene blir liggende i datasettet med sin `n_series`.** Det er visningen
som avgrenses, ikke dataene. Den som vil se hele halen, finner den i CSV-en.

**Regelen er ensidig, og skal aldri gjøres om til et filter.** Den trimmer
halen fra det yngste punktet og bakover, og stopper ved første punkt over
terskelen. Den ser aldri på den eldste enden.

Fristelsen er å skrive den om til noe som ser renere ut: «vis punkter med
`n_series` over terskelen». Det ville vært en annen regel, og den ville
ødelagt figuren. **174 av de 175 punktene under terskelen ligger i den eldste
enden**, som er 31–39 % av det tetteste punktet. Et symmetrisk filter ville
strøket to tredjedeler av serien og kuttet den lange linjen proxyen finnes for.

`src/lib/visning.test.ts` feiler hvis noen gjør det likevel. Den kontrollerer
at det eldste punktet i visningen ligger **under** terskelen — noe som er sant
for en haletrimming og umulig for et filter.

**Det er mekanismen som skiller de to endene, ikke nivået.** Målt mot det
tetteste punktet er den eldste enden tynnere enn den yngste, så et resonnement
som bare ser på tallene ville behandlet dem likt eller kuttet feil ende:

- **Den eldste enden:** få lange kjerner er en egenskap ved arkivet. Antallet
  er lavt, men **stabilt** — det svinger rundt 110–140 gjennom årtusener uten
  å falle sammen, og det sammenfaller ikke med noe brudd i kurven.
- **Den yngste enden:** kjerner som slutter ved innsamlingsdato er en egenskap
  ved innsamlingen. Antallet faller **brått, i ett steg**, fra 69 % til 28 % av
  det tetteste — midt i den bratteste stigningen i kurven.

Et lavt, jevnt antall bærer en lang linje. Et antall som kollapser akkurat der
kurven stiger, gjør det ikke.

`f_smoothed` gjelder K10. Hvert punkt i kompositten er et vektet snitt over et
vindu på 500 år til hver side, og kurven viser derfor den langsiktige formen,
ikke variasjon fra år til år. To punkter som ligger nær hverandre, er ikke
uavhengige.

**Vindusbredden står i fotnoteteksten**, ikke bare i koden. Uten den kan en
leser tro at et punkt er en måling av det året, og at en topp er én hendelse.
Endres `hw` i `etl/sources/k10_gcd.R`, må teksten i `data/_footnotes.json`
endres i samme commit.

`f_grid_resolution` gjelder rutenettkilder og påføres maskinelt. En entitet som
dekker mindre enn `GRID_MIN_ENTITY_CELLS` ruter av **kildens eget rutenett**,
får fotnoten på alle sine år.

Terskelen er oppgitt i antall ruter, ikke i km². En rutes areal følger
oppløsningen, og innenfor K9 skifter oppløsningen midt i serien — hvor stor én
rute er for den enkelte kilden, står under kilden i § 5.

Grensen er valgt fordi den har en fysisk betydning og ikke er en avrundet
skjønnsverdi: en entitet under den får plass innenfor én rute. Da finnes det
ingen rute som er entitetens alene, og tallet er en andel av ruter den deler
med naboland eller hav.

**Entiteter delrutenettet ikke treffer i det hele tatt, utelates fra kilden.**
De skal ikke publiseres som 0 med fotnoter. En 0 fra en entitet rutenettet
fysisk ikke kan observere, er fravær av måling og ikke en måling av null, og
§ 6 krever at manglende data vises som «ingen data», aldri som null. Fotnoter
endrer ikke hva verdien er.

Skillet mot de øvrige entitetene med `f_grid_resolution` er at de deler ruter
med naboland: tallet deres er upresist, men målt. Disse er ikke observert.

Settet beregnes ved hver kjøring, av rutenettet og geometrien slik de forelå
da, og skal aldri fryses som en liste over koder i kode (§ 7, T5). Får en
entitet treff etter at geometrien er oppdatert eller en senere kilde har finere
oppløsning, kommer den inn av seg selv.

**Et land uten geometri i K6 er en annen sak, og føres for seg.** Der har ikke
rutenettet bommet på geometrien — det finnes ingen geometri å bomme på.
Entiteten kom aldri inn i masken, og får derfor heller ingen rader.

Utfallet for leseren er det samme, men årsaken er ikke, og en manglende rad
skal kunne forklares. De to settene føres derfor hver for seg i
`data/_sources.json`, som `excluded_unobserved` og `excluded_no_geometry`.
Begge beregnes ved kjøring: det første av rutenettet, det andre som landene i
`land_no.json` som ikke finnes i K6-geometrien. Regioner og verdenskoden er
ikke med — K6 leverer ikke geometri for dem, og verdenstallet kommer fra
rutenettet.

Arealet måles **på rutenettet**, ikke hentet fra en annen kilde. Det er det
rutenettet ser av landet som avgjør om tallet kan brukes, ikke hva et atlas
oppgir. Terskelen står som `GRID_MIN_ENTITY_CELLS` i `etl/schema.py`, oppgitt i
antall ruter, slik at den følger med hvis en senere kilde har en annen
oppløsning.

**Null i et ufullstendig år får begge fotnotene, ikke en tredje.** En
observasjon som er 0 i inneværende år bærer både `f_incomplete_year` og
`f_zero_no_detection`.

Det er fristende å lage en egen fotnote for «ikke rapportert ennå», særlig for
de entitetene som hadde en målt verdi året før. Men vi kan ikke vite hvilke
nuller det gjelder. I 2026 er 79 av 260 entiteter 0; 12 av dem hadde verdi i
2025. Begge gruppene er like tvetydige — den ene har bare et mønster som ser
mer mistenkelig ut. En egen fotnote ville påstått kunnskap vi ikke har, og det
er en tolkning siden ikke gjør (P1).

De to fotnotene sammen sier nøyaktig det vi vet: året er ufullstendig, og
nullen er tvetydig. Kombinasjonen er maskinlesbar, så `derive.py` kan behandle
den som en egen kategori uten at det trengs en tredje kode.

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
- [ ] Hver verdi har den `unit` indikatortabellen i § 6 angir, og all
      konvertering er gjort i `normalize.py` (T1)
- [ ] Ingen eksterne forespørsler fra klienten (T2)
- [ ] Ingen tunge nedlastinger kjørt lokalt (T4)
- [ ] `data/raw/` er ikke committet
- [ ] **`quality`-kontrollen, i begge lag** (§ 6)
      - `validate.py`: hver serie har én `quality`, og ingen `series_id` har
        blandede verdier
      - byggesteget: ingen figur tegner flere `quality`-verdier uten at
        bruddet er markert
- [ ] Trender er beregnet innenfor én kilde og én `quality`
- [ ] Avledninger er beregnet på fullstendige år. Inneværende år inngår ikke i
      beregningsgrunnlaget for noen avledning (§ 7)
- [ ] Settet av ekskluderte entiteter beregnes ved kjøring, aldri fryst som
      liste i kode (§ 7, T5)
- [ ] `charcoal_index` står ikke i samme figur som en km²-serie
- [ ] Påkrevde siteringer gjengis ordrett der kilden brukes (K7, K8, K9, K10,
      og EFFIS-lisensen for K3/K4)
- [ ] Identifikatorer er engelske, alt leseren ser er norsk
- [ ] Ingen kodefil gjentar regler fra CLAUDE.md — den refererer til dem (T5)
- [ ] Enumerasjoner importeres fra `etl/schema.py`, aldri definert på nytt i
      en annen fil (T5)
- [ ] Importer er absolutte (`from etl.x import ...`), kjørt som modul fra
      repotoppen (`python -m etl.<modul>`). Ingen relative importer, ingen
      `sys.path`-manipulering (§ 4)
- [ ] Testene kjører: `python -m unittest discover -s etl -t .` og `npm test`
- [ ] Siden typesjekker og bygger: `npm run check` og `npm run build`

---

## 12. Status

**Implementert og i drift:**

- `etl/schema.py` — enumerasjonene, tersklene og stiene
- `etl/sources/ssb_klass.py` — navnekilden, bygger `land_no.json`
- `etl/sources/k1_owid.py` — K1, CSV og metadata
- `etl/sources/k2_gwis.py` — K2, i to roller: årsserie per land til kryssjekken
  mot K1, og ukesserie per land, summert til verdensdel og verden, til S3
- `etl/sources/k3_effis.py` — K3, nasjonalt rapporterte landtotaler fra XLS
- `etl/sources/k4_effis.py` — K4, EFFIS' egen satellittkartlegging (RDA)
- `etl/sources/k5_nifc.py` — K5, HTML-tabellen på statistikksiden
- `etl/sources/k6_natural_earth.py` — K6, kartenhetene som geometri, og
  landarealene regnet fra dem
- `etl/sources/k7_nbac.py` — K7, NBACs årsaggregat og CNFDBs punktstatistikk
- `etl/sources/k8_firecci.py` — K8, katalogen hos CEDA, henting og verifisering
- `etl/sources/k9_gfed5.py` — K9, arkivet hos Zenodo, henting og verifisering
- `etl/sources/k10_gcd.py` og `k10_gcd.R` — K10, kompositten fra paleofire
- `etl/normalize.py` — kanonisk form, hektar, acres og m² → km², andel av
  landareal
- `etl/grid.py` — rutenett → landnivå
- `etl/validate.py` — kontrollene i § 6 og § 11, og kryssjekken K1 mot K2
- `etl/derive.py` — avledningene i § 7, med Theil–Sen og Mann–Kendall skrevet
  ut, uten numeriske avhengigheter. Skriver `data/processed/insights.json`
- `etl/test_derive.py` — kontroll av avledningene mot datasett med kjent
  fasit. Kjøres med `python -m unittest discover -s etl -t .`
- `etl/run.py` — de månedlige kildene. Én som feiler, tar ikke ned de andre
- `etl/run_static.py` — pipelinen for de statiske kildene
- `src/lib/visning.ts` — avgrensningen av kompositten og sammenligneren for
  perioder, med test i `visning.test.ts`. Kjøres med `npm test`
- `src/lib/figurkontroll.ts` — byggekontrollen av kvalitetsbrudd per figur
  (§ 6), med test i `figurkontroll.test.ts`
- `src/lib/csv.ts` — figurens egen CSV, med test i `csv.test.ts`
- `src/lib/kartutsnitt.ts` — det faste utsnittet et kart tegnes i, med test i
  `kartutsnitt.test.ts`
- `src/figurer/overskriftstall.ts` og `globaltBrentAreal.ts` — S1s to figurer
- `src/figurer/kartBrentAreal.ts` og `rangering.ts` — S2s to figurer
- `src/figurer/sesongprofil.ts` og `kumulativUke.ts` — S3s to figurer
- `src/figurer/kartEuropa.ts`, `landsammenligning.ts` og `rangeringEuropa.ts`
  — S4s tre figurer
- `src/komponenter/Sammenligning.astro` — figur med avkryssing av land, uten
  skript
- `src/figurer/globaleSerier.ts`, `nasjonaleSerier.ts` og `kullindeks.ts` —
  S5s tre figurer
- `src/komponenter/Kildeoversikt.astro` og `src/lib/katalog.ts` — S6s
  kildeoversikt og filkatalog, begge lest av datasettet
- `src/komponenter/Kart.astro` — kart med bryter mellom to visninger, uten
  skript, og `Rangering.astro` — sorterbar tabell, lesbar uten skript
- `src/pages/data/figur/[figur].csv.ts` — skriver én CSV per figur ved bygging
- `data/geo/land_no.json` — 260 entiteter, generert fra SSB
- `data/geo/land_area_km2.json` — landarealer fra K6, nevner i andelsindikatoren
- `data/geo/verden.json` — forenklet kartgeometri, 237 entiteter, bygget av
  `etl/geo.py` i Actions
- `data/geo/europa.json` — samme kilde og samme kartenheter, men finere
  forenkling og bare entitetene EFFIS fører. Europa-kartet i S4 dekker et
  mindre område på samme flate, så én piksel er færre grader
- `data/processed/` — bearbeidede serier som JSON og CSV. Hvilken fil hver
  serie havner i, står i `PROCESSED_FILE` i `etl/schema.py` (§ 4)
- `data/processed/burned_area_firecci_lt11.*` — K8, 1982–2018 uten 1994,
  8820 observasjoner
- `data/processed/burned_area_gfed5.*` — K9, 1997–2020, 5880 observasjoner
- `data/processed/charcoal_composite_gcd.*` — K10, 6050 fvt–2010, 404 punkter
- `data/processed/burned_area_weekly.*` — K2s ukesserie, 2012-W01–, seks
  verdensdeler og verden. Landene bak summene publiseres ikke (§ 5)
- `data/processed/insights.json` — avledningene, med id som nøkkel
- `data/_footnotes.json` — fotnotetekstene, kontrollert mot `schema.py`
- `requirements.txt` — den månedlige kjøringens avhengigheter: `openpyxl`
  for K3 og K7, `pyshp` for K6
- `.github/workflows/etl.yml` — månedlig kjøring, endringer som pull request
- `.github/workflows/etl-statisk.yml` — manuelt utløst kjøring av en statisk
  kilde. Rutenettfilene lastes ned, aggregeres og slettes i Actions
- `.github/workflows/kontroll.yml` — kontroll av pull requests: importerer
  begge inngangene, kompilerer, validerer datasettet, kjører testene,
  typesjekker med `astro check` og bygger siden
- `.github/workflows/geo.yml` — manuelt utløst bygging av kartgeometrien
- `.github/workflows/rydd-grener.yml` — rydder maskinelle grener som er merget
- `.github/workflows/deploy.yml` — bygger og publiserer ved push til `main`
- Nettsiden — Astro, seks seksjoner, `src/komponenter/Figur.astro`,
  `Overskriftstall.astro` og S1 med begge figurene

Ingen av disse er stubber. De skal ikke skrives på nytt.

**Slik tegnes grafene.** Observable Plot kjører i Node under bygging og gir
ferdig SVG. Ingen graf-kode sendes til leseren, og figurene vises med skript
slått av. Se `src/lib/plot.ts`.

Hver figur har en modul under `src/figurer/` som bygger graf, tabell og
fotnoteliste fra observasjonene. Hvilke fotnoter en figur viser, utledes av
dataene — ikke av en liste i figurmodulen.

**Kryssjekken K1 mot K2** kjøres av `run.py` og skriver en avviksrapport til
`data/raw/kryssjekk_k1_k2.md`. Den er et arbeidsverktøy for redaktøren og
publiseres ikke — `data/raw/` er gitignorert, og workflowen legger rapporten
ved kjøringen som artefakt i stedet.

Alle tre statiske kildene er kjørt, og dataene deres ligger i repoet. De hentes
ikke på nytt uten at produsenten publiserer en ny versjon (§ 5).

**S1 er ferdig, og figurteksten der løser det som var det åpne punktet.** De
tre satellittseriene ligger på ulikt nivå og peker i ulik retning, og teksten
under oversiktsfiguren forklarer begge deler uten å utpeke en riktig serie
(P1): nivåforskjellen vises i det siste året alle tre dekker, og retningene
forklares med at trendene gjelder hver sin periode og er regnet på hvert sitt
produkt.

Nivåforskjellen vises som tre verdier for samme år, ikke som årsgjennomsnitt.
Et gjennomsnitt er ikke en tillatt avledning (§ 7), og et felles år er
dessuten en sammenligning leseren kan etterprøve i figuren selv.

**Ikke implementert:** `fire_count` ligger i datasettet uten at noen figur
viser det ennå. Filen er nedlastbar fra S6, og teksten der sier hva
indikatoren er.

**Avledningene er i bruk i S1, S2 og S3.** Hvert tall i teksten er fylt fra
`insights.json`, og setningen bærer id-en i `data-derivation` (P3). Finnes
ikke avledningen en setning trenger, stopper bygget — `avledning()` i
`src/lib/data.ts` kaster framfor å la et tall mangle.

K4 dekker foreløpig bare brent areal. Brannstørrelsesfordelingen S4 skal vise,
krever polygonene fra Burnt Areas-databasen, som ikke er hentet.

**Kartgeometrien er bygget.** `etl/geo.py` forenkler kartenhetslaget fra K6 med
Douglas–Peucker og skriver `data/geo/verden.json`. Jobben kjøres av
`.github/workflows/geo.yml` og må kjøres i Actions: K6 er en shapefil på fem
megabyte, og T4 gjelder. Geometrien bygges bare på nytt når Natural Earth gir
ut en ny versjon, eller når tersklene i `schema.py` endres.

**Forenklingen er topologibevarende.** Natural Earth deler koordinater eksakt
mellom naboland. Forenkles hver ring for seg, kan Douglas–Peucker beholde et
punkt i det ene landet og forkaste det i det andre, og grensen river seg fra
hverandre. Punktene avgjøres derfor som union over alle ringene: et punkt
beholdes hvis minst én ring trenger det.

Prisen er synlig i filen. Ved samme toleranse er unionsbygget større enn en
forenkling per ring, og hele veksten er punkter naboen får tilbake — 5 335
delte koordinater blir 7 037. Filen vokser fordi grensene henger sammen.

**En ring som har mistet flaten sin, tegnes ikke.** Punkttellingen alene fanget
ikke det: en grensesplint på fire punkter teller like høyt som en øy på fire, og
en splint som overlever som en nesten rett trekant har tilfeldig fortegn på
arealet. Tegneren avgjør innsiden av en flate på kloden av viklingsretningen, så
en vrengt ring dekker resten av kloden i stedet for seg selv, og hele kartet blir
én farge. `_ring()` sammenligner derfor fortegnet med ringen den kom fra.
Kontrollen er ikke teoretisk — den slår ut på DMZ-stripen i Korea, Kypros og
Syria fra 0,10° og oppover.

**Tersklene er valgt av rendrede kart.** Verdenskartet ligger på
`GEO_SIMPLIFY_TOLERANCE_DEG`, Europa-kartet på
`GEO_EUROPE_SIMPLIFY_TOLERANCE_DEG`, og begge ligger like under der
forenklingen begynner å synes i den størrelsen leseren faktisk ser kartet.
Prøvesteinen er den greske øygruppen: ved neste trinn oppover er de fleste øyene
borte. Europa-kartet tegner et nærmere utsnitt på samme flate og tåler derfor
mindre.

Filstørrelsen er en konsekvens av valget, ikke målet det er valgt etter. Den er
heller ikke bare geometriens: hver kartfigur tegner geometrien åtte ganger — to
visninger, hver i to størrelser, hver i to lag — så en fil på en halv megabyte
blir flere megabyte DOM.

**Noen entiteter i `land_no.json` har ingen flate.** Ni av dem er aggregater —
verden og regionene — som K6 ikke leverer geometri for. Resten er så små at de
forsvinner i forenklingen: Monaco er 2 km², og ingen verdensmålestokk viser det.
De har fortsatt tall i tabellen, og kartfiguren sier i klartekst hvilke det
gjelder. Settet beregnes ved kjøring og står i `summary` i `verden.json`.

Antallet følger terskelen, og det er den ene kostnaden ved å forenkle som
leseren faktisk får se. Europa-kartet har derfor en strengere grense enn
verdenskartet: det skal vise nøyaktig de landene EFFIS-serien dekker, så et
EFFIS-land uten flate er ikke et akseptabelt utfall.

**S2 er ferdig.** Kartet har to visninger — brent areal i km² og andel av
landarealet — og bryteren mellom dem er radioknapper og CSS, uten skript.
Rangeringstabellen er ferdig sortert i HTML og fullt lesbar uten JavaScript;
sorteringsknappene legges bare til hvis skript kjører, av vårt eget skript uten
avhengigheter (T2).

Teksten i S2 sier ikke hvilket land som ligger øverst i andelsvisningen. En
rangering av entiteter mot hverandre er ikke en tillatt avledning — § 7
rangerer år innenfor én entitet — og konsentrasjonen, som navngir de største,
finnes bare for summerbare enheter. Tabellen viser rekkefølgen; brødteksten
påstår den ikke.

**S3 er ferdig.** Sesongprofilen viser hver verdensdel i sin egen rute med sin
egen loddrette skala — Afrika brenner i en helt annen størrelsesorden enn
Europa, og en felles skala ville gjort de minste kurvene til flate streker.
Teksten sier derfor at formen kan sammenlignes mellom rutene, men ikke høyden.

Den kumulative figuren tegner inneværende år mot medianen og persentilbåndet
for de fullstendige årene. Året som ikke er omme, er med i figuren og utenfor
grunnlaget (§ 7), og kurven stopper der målingene stopper.

**Ukesserien er hentet, og hentingen er den tyngste vi har.** Første kjøring
var 3 840 forespørsler og tok en time. En månedlig kjøring ber bare om
inneværende år: 256 forespørsler, et par minutter. De fullstendige årene ligger
i den publiserte filen, som er hurtigbufferen (§ 5).

Prisen er at en feil etter hentingen er dyr. Det er derfor `run.py` tar vare på
radene før statusen skrives, og K2s status føres per rolle — en feilet
ukeshenting skal ikke kunne se ut som suksess fordi kryssjekken gikk bra
etterpå.

**S4 er ferdig, med ett unntak.** Kartet tegner EFFIS-området på den finere
geometrien, med samme bryter som S2. Utsnittet er fast og ikke tilpasset
dataene, slik at to årganger kan sammenlignes.

Ruten som låser utsnittet bygges av `utsnittsflate()` i `src/lib/kartutsnitt.ts`.
Den vikles slik tegneren forventer, og det er ikke en detalj: viklet motsatt vei
er ruten hele kloden utenom ruten, projeksjonen krymper til null, og hvert land
tegnes i samme punkt. Kartet blir da en prikk uten at noe feiler underveis —
geometrien ligger der, hver flate er tegnet, alle sammen oppå hverandre.
`kartutsnitt.test.ts` måler hvor stor flate utsnittet faktisk dekker, fordi det
er den eneste kontrollen som ser forskjellen.

De seks oversjøiske områdene
kilden fører — Réunion, Mayotte, Guadeloupe, Martinique, Saint-Martin og
Guyana — ligger utenfor utsnittet og sies i klartekst under kartet. Settet
regnes av geometrien ved kjøring.

Sammenligningsfiguren tegner begge EFFIS-seriene, aldri skjøtt sammen: K4
heltrukket, K3 stiplet. Alle landene ligger blekt i bakgrunnen, og de leseren
krysser av for, får farge og navn. Avkryssingen er avkryssingsbokser og CSS.
Grensen på fem land håndheves bare hvis skript kjører — uten skript kan
leseren krysse av flere, og figuren blir travel, ikke feil.

De fem som er krysset av på forhånd, er de med størst brent areal i siste
fullstendige år. Det er en sortering for å velge en startvisning, ikke en
avledning: § 7 rangerer år innenfor én entitet, ikke land mot hverandre, og
teksten sier at utvalget er maskinelt.

Tabellen er den sorterbare fra S2, uten kolonnen for andel av verdens brente
areal. K4 dekker et område, ikke kloden, og en andel av en sum som ikke
finnes, er et tall uten nevner.

**Åpent punkt: brannstørrelsesfordelingen.** § 8 fører den under S4, og den er
ikke laget. K4 gir landtotaler, og en fordeling krever areal per brann.

Sonderingen i `sonder_branner()` i `etl/sources/k4_effis.py` har spurt kilden
selv, og svarene peker to veier:

- **API-et beskriver seg selv, og har ingen adresse per brann.** `openapi.json`
  fører fire stier: `/geocoder`, `/healtz`, `/rda-stats` og `/status`. Merk at
  årsserien vi faktisk henter, ligger under `/statistics/`, som ikke står i den
  beskrivelsen — spesifikasjonen dekker altså ikke hele tjenesten, og
  `/statistics/openapi.json` svarer 404. `/rda-stats` er ikke undersøkt
  nærmere og er det nærmeste vi har et spor.
- **Karttjenesten, som er der polygonene ville ligget, svarer 500 på alt.**
  Også et rent `GetCapabilities` uten lagnavn. Da er det tjenesten som feiler,
  ikke adressen vår som er feil, og vi kan ikke se om dataene er der. Det er
  verdt å prøve igjen en annen dag.

Fordelingen skal **ikke** tilnærmes fra landtotaler. Andelen fra de største
brannene kan ikke regnes av en sum; et anslag ville vært et tall siden ikke
har målt, og det er nettopp det P3 forbyr.

**S5 er ferdig.** Tre figurer, ingen av dem en gjentakelse av S1s
oversiktsfigur: de globale satellittproduktene i hver sin rute, de to lange
nasjonale seriene i hver sin, og kullkompositten alene.

Hver rute har sin egen loddrette skala, mens tidsaksen er felles innenfor hver
figur. Da blir ulik dekningsperiode synlig i seg selv — K1s fjorten år tar en
liten del av en akse som begynner i 1982 — uten at høydene kan leses mot
hverandre. Teksten sier det samme i klartekst.

**Kullfiguren er bygget mot én bestemt feillesning.** At kurven leses som
«brent areal over tid», er det mest sannsynlige som kan gå galt, og figuren
motvirker det på fire steder: tittelen sier hva verdien er og ikke er, aksen
er navngitt i standardavvik, nullinjen er merket som seriens eget
gjennomsnitt, og ingen km²-verdi finnes i figuren — heller ikke i tabellen
eller i tooltipen. Teksten forklarer i tillegg hva en proxy er, at skalaen
ikke har noe nullpunkt for «ingen brann», og at hvert punkt er tusen år lagt
sammen.

Kompositten avgrenses ved den yngste enden, av regelen i `src/lib/visning.ts`.
Med dagens datasett trimmes ett punkt bort, og visningen stopper i 1990.

**Årstall kan bære fortegn, og det bet nesten.** `aarstall()` i
`src/lib/format.ts` leste fire tegn av perioden, som gjorde «-6050» til år
−605 uten å feile noe sted. Funksjonen tar nå fortegnet med, og
`aarstallTekst()` skriver negative år som «6050 fvt» i aksemerker, kildelinjer
og tabeller. Begge har test i `format.test.ts`.

**S6 er ferdig.** Kildeoversikten bygges av `data/_sources.json`, ordlisten
forklarer de sju fagbegrepene som er innført underveis, alle fotnotene står
samlet i tillegg til plasseringen under hver figur, og filkatalogen leser
radtall og serier av filene selv — en fil som vokser, oppdaterer sin egen
linje.

De påkrevde siteringene gjengis ordrett under hver kilde: K7, K8, K9 og K10,
og EFFIS' egen datalisens for K3 og K4. Kontrollert mot `_sources.json` i den
bygde siden, ikke bare i malen.

**De to åpne punktene står i seksjonen, ikke bare her.** Leseren får vite at
brannstørrelsesfordelingen ikke er hentet og hvorfor, og at K2s hurtigbuffer
ikke fanger opp en revisjon GWIS gjør i et gammelt år.

**Ansvarsfraskrivelsen i sidefoten er vedtatt ordlyd.** Den sier at prosjektet
er privat og ikke-kommersielt, at siden ikke garanterer at dataene er
fullstendige eller nøyaktige, og at eneste kontaktvei er issues på GitHub.

Den er en juridisk ansvarsbegrensning, ikke et metodisk forbehold. De
metodiske står fortsatt som nummererte fotnoter under hver figur, og samlet i
S6 — P6 forbyr å flytte dem til sidefoten.

**Alle seks seksjonene er nå bygget.**

**Neste steg:** ingen seksjon står igjen. Det som gjenstår er de to åpne
punktene over, og `fire_count`, som ligger i datasettet uten en figur.
