/**
 * Kopierer de bearbeidede datafilene til public/, slik at de blir liggende
 * som nedlastbare filer på den publiserte siden.
 *
 * Kildelinjen under hver figur skal lenke til den CSV-filen figuren faktisk
 * bruker (CLAUDE.md P5). Lenken peker hit.
 *
 * Kjøres av npm-skriptet «prebuild». public/data/ er generert og gitignorert.
 */

import { cp, mkdir, readdir, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repotopp = join(dirname(fileURLToPath(import.meta.url)), "..");
const fra = join(repotopp, "data", "processed");
const til = join(repotopp, "public", "data");

await rm(til, { recursive: true, force: true });
await mkdir(til, { recursive: true });

const filer = (await readdir(fra)).filter(
  (navn) => navn.endsWith(".csv") || navn.endsWith(".json"),
);

for (const navn of filer) {
  await cp(join(fra, navn), join(til, navn));
}

console.log(`kopier-data: ${filer.length} filer → public/data/`);
