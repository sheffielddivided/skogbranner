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

**km² er primærenheten for areal.** Arealindikatorer vises alltid i km² — i
aksetitler, tabeller, tooltips, nedlastbare CSV-filer under `data/processed/`
og avledede tall.

Indikatorer uten fysisk enhet følger sin egen `unit`, slik den står i
indikatortabellen i § 6.

All enhetskonvertering skjer i `etl/normalize.py`. Aldri i visningslaget, aldri
i JavaScript, aldri i en malfil. Kommer en kilde med hektar eller acres,
konverteres den én gang under normalisering, og den konverterte verdien er den
eneste som finnes videre i pipelinen.

Referanse: 1 km² = 100 ha. 1 acre = 0,00404686 km².

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
  derive.py         Maskinelle avledninger → data/processed/insights.json
  validate.py       Kontrollerer at output er gyldig før publisering
  run.py            Kjører pipelinen: hent → normaliser → valider → publiser
data/
  raw/              Uendrede kildefiler. GITIGNORERT. Aldri committet.
  processed/        Kanoniske serier siden faktisk leser. Committes.
  geo/              Forenklet geometri for kart. Committes.
    land_no.json    Entitetskode → norsk navn og nivå. Delt av alle kilder.
  _sources.json     Kildemetadata: lisens, lenke, dekning, nedlastingsdato
  _status.json      Siste kjørestatus per kilde, for degradert visning
src/                Nettsidens kildekode
public/             Statiske ressurser som kopieres uendret
.github/workflows/  ETL-kjøring og deploy
```

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
| K3 | EFFIS, landtotaler | Europa, Midtøsten, Nord-Afrika | — | `reported` | Nasjonalt rapporterte totaler |
| K4 | EFFIS, Burnt Areas | Europa | — | `reported` | Grunnlag for brannstørrelsesfordeling |
| K5 | NIFC | USA | 1983– | `reported` | Lang nasjonal serie |
| K6 | Natural Earth, admin-0 | Global | — | — | Geometri og landarealer. Public domain |
| K7 | CNFDB / NBAC | Canada | — | `reported` | Krever sluttbrukeravtale — akseptert |
| K8 | FireCCILT11 (ESA Fire_cci) | Global | 1982–2018, uten 1994 | `beta` | Statisk. Selve produktet er merket beta av produsenten |
| K9 | GFED5 | Global | 1997–2022 | `measured` | Statisk. GFED5.1 for 1997–2022 er en publisert utgivelse dokumentert i Scientific Data. Beta-merkingen gjelder kun produsentens `ext_Beta`-kataloger fra 2023, som vi holder ute |
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

- **K6 Natural Earth** leverer ikke branndata. Den brukes til kartgeometri og
  til landarealer, som er nevneren i `burned_area_share_land`. Den tegnes ikke
  som egen serie, og står derfor ikke i kildekolonnen i § 8.
- **K2 GWIS** har to roller.

  Den ene er **kryssjekk mot K1**, som en ETL-validering: spriker K1 og K2 mer
  enn 5 % for samme enhet og år, produseres en avviksrapport. Rapporten er et
  arbeidsverktøy for redaktøren, ikke innhold på siden. Den publiseres ikke,
  og K2 tegnes ikke i noen figur i denne rollen.

  Terskelen er `CROSSCHECK_THRESHOLD` i `etl/schema.py`. Valideringskoden
  importerer konstanten og skriver aldri tallet selv (T5).

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

> van der Werf, G.R., Randerson, J.T., van Wees, D., Chen, Y., Giglio, L.,
> Hall, J., Vernooij, R., Mu, M., Binte Shahid, S., Barsanti, K.C.,
> Yokelson, R. & Morton, D.C. (2025). Landscape fire emissions from the 5th
> version of the Global Fire Emissions Database (GFED5).
> Scientific Data 12, 1870. https://doi.org/10.1038/s41597-025-06127-w

Når K9 hentes, legges følgende i `data/_sources.json`:

- `doi`: `10.1038/s41597-025-06127-w`
- Den publiserte rettelsen som **eget felt**: Publisher Correction, Scientific
  Data 13, 44 (15. januar 2026),
  `https://doi.org/10.1038/s41597-026-06613-9`

Rettelsen føres som eget felt, ikke som en endring av siteringen, slik at det
er sporbart hvilken versjon av artikkelen datasettet er dokumentert av.

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
- `period`: ISO 8601 — `YYYY`, `YYYY-MM` eller `YYYY-Www`
- `quality`: `measured` | `reported` | `beta` | `reconstructed`
- `unit`: `km2` | `share` | `zscore`

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

### Hvem kontrollerer hva

Regelen over håndheves i to lag, fordi ingen av dem ser hele bildet alene.

- **`validate.py`** kjører i ETL og ser data, ikke figurer. Den kontrollerer at
  **dataene** er gyldige: at hver serie har én `quality`, og at ingen
  `series_id` har blandede verdier.
- **Byggesteget for siden** ser figurene. Det kontrollerer at **ingen figur**
  tegner flere `quality`-verdier uten at bruddet er markert.

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
| S5 | Den lange linjen | De samme seriene som i S1, pluss de nasjonale og proxyen, vist **hver for seg** i separate figurer med hver sin akse og hver sin dekningsperiode | K1, K5, K7, K8, K9, K10 |
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

`f_missing_year` gjelder blant annet 1994 i K8. Et manglende år vises som
brudd i kurven, aldri som 0 og aldri som interpolert verdi.

`f_resolution_change` gjelder K9 for **1997–2000**, der oppløsningen er 1° mot
0,25° fra 2001.

`f_zero_no_detection` gjelder K1. Kilden leverer et fullt rutenett av entiteter
og år, og bruker 0 der satellittene ikke har påvist brent areal. En 0 kan
derfor bety at det ikke brant, at brannene var under deteksjonsgrensen, eller
at området ikke er dekket — kilden skiller ikke. `normalize.py` merker hver
nullverdi med fotnoten.

Dette er ikke det samme som «ingen data». En figur skal ikke tegne en 0 fra
denne kilden som en målt null uten at fotnoten følger med.

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
- [ ] Påkrevde siteringer gjengis ordrett der kilden brukes (K7, K9, K10,
      og EFFIS-lisensen for K3/K4)
- [ ] Identifikatorer er engelske, alt leseren ser er norsk
- [ ] Ingen kodefil gjentar regler fra CLAUDE.md — den refererer til dem (T5)
- [ ] Enumerasjoner importeres fra `etl/schema.py`, aldri definert på nytt i
      en annen fil (T5)
- [ ] Importer er absolutte (`from etl.x import ...`), kjørt som modul fra
      repotoppen (`python -m etl.<modul>`). Ingen relative importer, ingen
      `sys.path`-manipulering (§ 4)

---

## 12. Status

**Implementert og i drift:**

- `etl/schema.py` — enumerasjonene, tersklene og stiene
- `etl/sources/k1_owid.py` — K1, henting og råformat
- `etl/normalize.py` — kanonisk form, hektar → km²
- `etl/validate.py` — kontrollene i § 6 og § 11
- `etl/run.py` — pipelinen
- `data/geo/land_no.json` — 260 entiteter med norske navn
- `data/processed/burned_area.json` og `.csv` — K1, 2012–, 3900 observasjoner

Ingen av disse er stubber. De skal ikke skrives på nytt.

**Ikke implementert:** `etl/derive.py` inneholder kun beskrivelse av
ansvarsområde. Ingen nettside finnes ennå — `src/` og `public/` er tomme, og
det er ingen workflow i `.github/workflows/`.

**Neste steg:** `derive.py` og `insights.json`, deretter første seksjon av
siden.
