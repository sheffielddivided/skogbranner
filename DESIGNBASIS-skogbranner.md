# Designbasis: Redaksjonell datanettside om skogbranner

**Status:** Utkast til beslutningsgrunnlag
**Formål:** Grunnlagsdokument for implementering (GitHub Pages + GitHub Actions + Cloudflare Worker)
**Språk på siden:** Norsk (bokmål)

---

## 1. Redaksjonelle prinsipper

Disse prinsippene er bindende for all implementering og skal håndheves i kodegjennomgang.

1. **Ingen tese.** Siden fremmer ikke et standpunkt. Den viser hva dataene måler, hvor langt tilbake de går, og hvor de er usikre.
2. **Data har forrang.** Hver seksjon åpner med visualiseringen. Forklarende tekst ligger under eller ved siden av, aldri foran.
3. **Konklusjoner er maskinelt avledet.** Enhver tallfestet påstand i brødteksten genereres deterministisk fra datasettet ved byggetidspunkt (se § 7). Ingen håndskrevne tall i teksten.
4. **Nøytralt språk.** Unngå ord som «paradoks», «alarmerende», «dramatisk», «rekord» (med mindre «rekord» er maskinelt avledet og definert). Beskriv retning og størrelse, ikke betydning.
5. **Alt er sporbart.** Hver figur har synlig kildehenvisning med direkte lenke til kilden, nedlastingsdato og lenke til den CSV-filen figuren faktisk bruker.
6. **Forbehold som fotnoter.** Metodiske begrensninger vises som nummererte fotnoter knyttet til den enkelte figuren, ikke samlet i en generell ansvarsfraskrivelse.
7. **Leseren er allmennheten.** Begreper som «brent areal», «aktiv branndeteksjon», «hotspot» og «brannsesong» forklares første gang de brukes, i en ordliste og som tooltip.
8. **Ikke i scope:** utslipp, klimadrivere, klimaattribusjon, egen Norden-seksjon.

---

## 2. Arkitektur

```
GitHub-repo (public)
├── /etl              Python-skript som henter og normaliserer data
├── /data             Ferdig normaliserte, committede datafiler (JSON + CSV)
│   ├── /raw          Uendrede kildefiler med hash og hentedato
│   └── /processed    Kanoniske serier som siden leser
├── /src              Nettsidekildekode
├── /public           Statiske ressurser
└── .github/workflows
    ├── etl.yml       Cron: månedlig (1. i md. kl. 04:00 UTC) + manuell trigger
    └── deploy.yml    Bygg og deploy til Pages ved push til main
```

**Dataflyt:** ETL kjører som egen Actions-jobb, skriver til `/data/processed`, åpner en pull request ved endringer. Du reviewer og merger. Merge trigger deploy. Dette gir revisjonsspor i git for hver datavariant og gjør at siden aldri går i stykker av en feilende kilde.

**Feilhåndtering:** Hvis en kilde feiler, beholdes forrige datasett, ETL logger feilen i `/data/processed/_status.json`, og siden viser en diskret merknad om at akkurat den serien ikke er oppdatert siden dato X.

**Sanntidslag:** Cloudflare Worker fungerer som proxy mot NASA FIRMS. Workeren holder API-nøkkelen skjult, cacher svaret i 15–30 minutter, og setter CORS-headere. Siden kaller kun workeren.

**Kjente Pages-rammer:** anbefalt 1 GB repo og publisert side, myk grense på 100 GB båndbredde per måned, deploy timeout 10 minutter. Byggegrensen på 10 per time gjelder ikke ved egendefinert Actions-workflow.

---

## 3. Datakilder – fase 1 (umiddelbart nedlastbart)

| # | Kilde | Geografi | Dekning | Format | Rolle på siden |
|---|-------|----------|---------|--------|----------------|
| K1 | **Our World in Data** (grapher-API) | Global, land og regioner | 2012–d.d. | CSV via `…/grapher/<slug>.csv`, metadata via `.metadata.json`. CC BY 4.0 | Hovedserie for globale og nasjonale årstall |
| K2 | **GWIS Statistics Portal** (JRC/Copernicus) | Global, land og regioner | 2012–d.d. | Portal/tabell; landtotaler og gjennomsnitt | Kryssjekk mot K1, ukesoppløsning i sesong |
| K3 | **EFFIS – landtotaler** | Europa, Midtøsten, Nord-Afrika | Årlige totaler | XLS-nedlasting | Europa-seksjonen |
| K4 | **EFFIS – Burnt Areas database** | Samme | Løpende oppdatert | Shapefile / SpatiaLite | Kartlag Europa, brannstørrelsesfordeling |
| K5 | **NASA FIRMS** | Global | MODIS fra nov. 2000, VIIRS fra jan. 2012 | REST-API, gratis MAP_KEY, 5 000 kall per 10 min | Sanntidskart |
| K6 | **NIFC** | USA | 1983–d.d. | CSV/tabell | Lang nasjonal serie |
| K7 | **CNFDB / NBAC** (NRCan) | Canada | Punktdata 1980–2025; NBAC regnes som beste kilde for areal fra 1972 | Nedlasting fra CWFIS Datamart | Lang nasjonal serie |

**Merknad til K7:** CNFDB krever aksept av en sluttbrukeravtale. Må avklares før publisering (se § 10).

### Fase 2 (krever forprosessering – ikke i første leveranse)

| Kilde | Dekning | Merknad |
|-------|---------|---------|
| **FireCCILT11** (ESA Fire_cci) | 1982–2018, uten 1994 | Global lang serie fra AVHRR-LTDR, 0,05° og 0,25°. Nedlasting krever registreringsskjema. Gir den lengste konsistente satellittserien |
| **GFED5** | 1997–2022 (+ beta til d.d.) | NetCDF via Zenodo/SFTP. Brent areal per rutenett; krever aggregering til land |
| **European Fire Database** (EFFIS) | 22 land, lange nasjonale serier | Ikke åpent nedlastbar – må bestilles via JRCs kontaktpunkt |
| **Global Paleofire Database / GCD** | Årtusener | Sedimentært kull som proxy. Redaksjonelt sterkt, men krever egen forklaringsramme |

---

## 4. Kanonisk datamodell

Alle kilder normaliseres til ett langformat før publisering:

```json
{
  "entity": "NOR",              // ISO3, eller regionkode (EUR, WLD, …)
  "entity_name": "Norge",
  "level": "country",           // country | region | world
  "period": "2024",             // ISO 8601: YYYY, YYYY-MM, YYYY-Www
  "indicator": "burned_area_ha",
  "value": 971,
  "unit": "ha",
  "source_id": "K1",
  "series_id": "owid_annual_area_burnt",
  "quality": "measured",        // measured | reported | reconstructed
  "sensor": "MODIS+VIIRS",      // der relevant
  "footnotes": ["f_sensor_break", "f_min_fire_size"]
}
```

**Indikatorer i fase 1:**
- `burned_area_ha` – brent areal
- `burned_area_share_land` – brent areal som andel av landareal (muliggjør sammenligning mellom store og små land)
- `fire_count` – antall registrerte branner
- `active_detections` – aktive branndeteksjoner (kun sanntidslag)

**Kvalitetsflagget `quality` er sentralt.** Det skal styre visuell fremstilling: målte serier tegnes med heltrukket linje, rapporterte med stiplet, rekonstruerte med eget bånd og separat akse. Serier med ulikt kvalitetsflagg skal aldri slås sammen til én kurve uten synlig markering av bruddet.

**Ulike startår er akseptert og skal synliggjøres**, ikke skjules. Hver graf viser dekningsperioden eksplisitt, og land uten data for et gitt år vises som «ingen data», ikke som null.

---

## 5. Sidestruktur

Én lang side med sticky innholdsnavigasjon. Seks seksjoner:

**S1 – Hva brenner nå**
Kart med aktive branndeteksjoner siste 24–48 timer (FIRMS via Worker). Teller for antall deteksjoner. Umiddelbar forklaring av hva en «deteksjon» er og hva den ikke er.

**S2 – Årets sesong mot normalen**
Kumulativ kurve for inneværende år lagt over medianen og 10–90-persentilbåndet for tilgjengelige år. Velger for verden / Europa / valgt land.

**S3 – Europa**
Kart på landnivå med brent areal, og andel av landareal som alternativ visning. Sorterbar tabell. Tidsserie per land med mulighet for å sammenligne inntil fem land. Norge og Norden inngår som ordinære land uten særbehandling.

**S4 – Verden**
Globalt brent areal over tid, brutt ned på kontinent. Kart. Rangering av land. Ingen tolkende overskrift – kun beskrivende.

**S5 – Den lange linjen**
De nasjonale seriene som går lengst tilbake (USA fra 1983, Canada fra 1972/1980), vist hver for seg med tydelig markering av at de ikke er direkte sammenlignbare. Forklaring av hvorfor globale data først begynner i 1997/2012.

**S6 – Om dataene**
Kildeoversikt, definisjoner, ordliste, alle fotnoter samlet, nedlastingslenker til alle bearbeidede CSV-filer, og lenke til repoet.

---

## 6. Visualisering

**Bibliotek:** Observable Plot eller ECharts for grafer. MapLibre GL JS for kart. Ingen tunge rammeverk – Astro eller ren Vite/TypeScript holder.

**Krav til hver figur:**
- Tittel som beskriver hva som vises, ikke hva det betyr
- Enhet oppgitt i aksen
- Kildelinje under figuren: kildenavn (lenket) · dekningsperiode · sist oppdatert · lenke til CSV
- Nummererte fotnoter direkte under figuren
- Tastaturnavigerbar, med tabellvisning som alternativ til grafikken
- Fungerer på mobil (grafene må ha egne mobiloppsett, ikke bare skaleres ned)

**Standard fotnoter (gjenbrukbare):**
- `f_sensor_break` – overgang mellom satellittsensorer kan gi brudd i serien
- `f_min_fire_size` – systemet fanger i praksis ikke opp de minste brannene
- `f_incomplete_year` – inneværende år er ufullstendig
- `f_reporting_basis` – nasjonalt rapporterte tall følger andre definisjoner enn satellittmålte
- `f_coverage_change` – antall rapporterende land eller områder har endret seg over tid

**Inneværende år** vises alltid med egen visuell markering og skal aldri inngå i trendberegninger.

---

## 7. Maskinelt avledede konklusjoner

Alle tallfestede påstander i brødteksten genereres ved byggetidspunkt fra en modul (`/etl/derive.py`) som produserer en `insights.json`. Teksten på siden er maler som fylles med disse verdiene. Ingen skjønn.

**Tillatte avledninger:**

| Avledning | Definisjon |
|-----------|------------|
| Rangering | «År X er nummer N av M år med data for enhet E» |
| Avvik fra normal | Verdi mot median for hele dekningsperioden, oppgitt i prosent |
| Trend | Theil–Sen-estimator med Mann–Kendall-test. Rapporteres kun med retning, størrelse per tiår og p-verdi. Ikke-signifikante trender rapporteres som «ingen statistisk signifikant trend» |
| Andel | Enhetens andel av globalt totaltall for gitt år |
| Konsentrasjon | Andel av totalt brent areal som kommer fra de N største brannene / landene |
| Dekning | Første og siste år med data per enhet og serie |

**Ikke tillatt:** årsaksforklaringer, sammenligning mot klimascenarier, prognoser, kvalitative karakteristikker.

Hver genererte setning skal ha en `data-derivation`-attributt i HTML som peker til beregningen, slik at en leser kan se hvordan tallet er utledet.

---

## 8. Ytelse og tilgjengelighet

- Total sidevekt under 2 MB ved førstelast, eksklusive kartfliser
- Data lastes per seksjon (lazy), ikke alt ved oppstart
- Ingen sporing, ingen cookies, ingen tredjeparts analyse-script som krever samtykke
- WCAG 2.1 AA: kontrast, tastaturnavigasjon, `prefers-reduced-motion`, fargeskalaer som fungerer ved fargeblindhet
- Fungerer uten JavaScript i den grad at tekst og tabeller er lesbare

---

## 9. Lisens og attribusjon

- Sidens kode: MIT
- Sidens tekst: CC BY 4.0
- Bearbeidede data: videreformidles under den strengeste av kildelisensene, med kildeangivelse per serie i `/data/processed/_sources.json`
- OWID-data er CC BY 4.0. EFFIS/Copernicus-data har egen datalisens som må gjengis. CNFDB krever sluttbrukeravtale.
- Sidefot skal inneholde en samlet attribusjonsblokk

---

## 10. Åpne punkter som må avklares før implementering

1. **Domene:** `<bruker>.github.io/<repo>` eller eget domene via Cloudflare?
2. **Repo synlighet:** public (kreves for gratis Pages på Free-konto) – greit at ETL-kode og data er åpne?
3. **Tilknytning:** privat prosjekt eller på noen måte koblet til arbeidsgiver? Påvirker ansvarsfraskrivelse i sidefoten og Pages' vilkår om kommersiell bruk.
4. **Sanntidskartets omfang:** globalt eller kun Europa? Globalt gir store datamengder per kall og krever aggregering i workeren.
5. **Kartbakgrunn:** hvilken flisleverandør? OSM-raster, Carto, eller selvhostede Protomaps-fliser (gir null avhengighet, men legger vekt på repoet).
6. **Enhet:** hektar eller km² som primærenhet i grensesnittet?
7. **CNFDB-sluttbrukeravtale:** skal jeg legge den inn som forutsetning, eller droppe Canada i fase 1?
8. **Fase 2-ambisjon:** skal FireCCILT11 (1982–2018) og paleodata inn senere, eller er 2012–d.d. pluss nasjonale serier endelig omfang?
