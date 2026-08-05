/**
 * Seksjonene på siden, i rekkefølge.
 *
 * Rekkefølgen og overskriftene står i CLAUDE.md § 8. Listen ligger her fordi
 * både innholdsnavigasjonen og selve siden må lese den samme rekkefølgen.
 */

export interface Seksjon {
  id: string;
  kode: string;
  tittel: string;
}

export const seksjoner: Seksjon[] = [
  { id: "hvor-mye-brenner-det", kode: "S1", tittel: "Hvor mye brenner det på jorden" },
  { id: "hvor-pa-kloden", kode: "S2", tittel: "Hvor på kloden" },
  { id: "aret-gjennom", kode: "S3", tittel: "Året gjennom" },
  { id: "europa", kode: "S4", tittel: "Europa" },
  { id: "den-lange-linjen", kode: "S5", tittel: "Den lange linjen" },
  { id: "om-dataene", kode: "S6", tittel: "Om dataene" },
];
