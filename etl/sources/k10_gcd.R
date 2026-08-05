# K10 — Global Charcoal Database: global kompositt-kurve.
#
# Kjøres av etl/sources/k10_gcd.py, som kaller Rscript med utfilen som eneste
# argument. Skriptet gjør én ting: bygger kompositten og skriver den til CSV
# med én gang. Alt annet — enheter, fotnoter, kanonisk form — skjer i Python.
#
# Skriptet skriver CSV-en før det gjør noe som helst annet med resultatet, slik
# at en kompositt som først er beregnet, ikke går tapt om noe senere feiler.
# Pakkene er fra 2019 og 2020, og paleofire ble trukket fra CRAN i 2023.
#
# Metoden er paleofires egen: minimaks-skalering, Box-Cox-transformasjon og
# z-score mot en felles basisperiode, deretter et lavpassfiltrert snitt med
# bootstrappet usikkerhet. Se CLAUDE.md § 5 (K10) og § 7.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Bruk: Rscript k10_gcd.R <utfil.csv>")
utfil <- args[1]

suppressPackageStartupMessages({
  library(GCD)
  library(paleofire)
})

cat("K10: GCD", as.character(packageVersion("GCD")),
    "| paleofire", as.character(packageVersion("paleofire")), "\n")

# Alle sedimentære kullserier i databasen. Ingen redaksjonelt utvalg av
# steder — utvalget er «alt som finnes», slik at kurven ikke bærer et valg vi
# ikke kan begrunne maskinelt (CLAUDE.md P1).
alle <- pfSiteSel()
cat("K10: steder i databasen:", length(alle$id_site), "\n")

# Transformasjon til sammenlignbare serier. Basisperioden er den paleofire
# bruker i sine egne eksempler, og dekker en periode med mange serier.
tr <- pfTransform(
  alle,
  method = c("MinMax", "Box-Cox", "Z-Score"),
  BasePeriod = c(200, 4000),
  verbose = FALSE
)

# Lavpassfiltrert kompositt med bootstrappet konfidensintervall. tarAge er
# alderaksen i kalenderår før 1950 (BP): 0 er 1950, negative verdier er årene
# etter 1950.
maal_alder <- seq(-60, 8000, by = 20)
komp <- pfCompositeLF(
  tr,
  tarAge = maal_alder,
  binhw = 10,
  hw = 500,
  nboot = 1000,
  verbose = FALSE
)

# Feltnavnene er paleofires egne: BootMean er kurven, BootCi er det
# bootstrappede konfidensintervallet, og antall bidragende serier per bin
# telles av de kolonnene som ikke er NA — samme regnestykke som pakkens egen
# plot(add = "sitenum").
ut <- data.frame(
  age_bp = as.numeric(komp$BinCentres),
  composite = as.numeric(komp$BootMean[, 1]),
  lower = as.numeric(komp$BootCi[, 1]),
  upper = as.numeric(komp$BootCi[, 2]),
  n_sites = ncol(komp$BinnedData) - rowSums(is.na(komp$BinnedData))
)

# Skriv med én gang, før noe annet gjøres med resultatet.
write.csv(ut, utfil, row.names = FALSE)
cat("K10: skrev", nrow(ut), "rader til", utfil, "\n")
