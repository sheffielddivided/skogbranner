/**
 * Utsnittet et kart tegner, som en flate projeksjonen kan tilpasses.
 *
 * Et fast utsnitt er ikke en detalj: uten det tilpasser projeksjonen seg
 * dataene, og to årganger av samme kart kan ikke sammenlignes fordi de er
 * tegnet i ulik målestokk.
 *
 * **Ringen må vikles med klokken lest i lengde- og breddegrad.** Tegneren
 * avgjør innsiden av en flate på kloden av viklingsretningen, ikke av at
 * punktene ligger i en firkant. Vikles ruten motsatt vei, er den ikke lenger
 * ruten, men hele kloden utenom ruten — og en projeksjon som tilpasses den,
 * krymper til ingenting. Kartet blir da en prikk, uten at noe feiler
 * underveis: geometrien er der, hver flate er tegnet, alle sammen i samme
 * punkt.
 */

export interface Utsnitt {
  vest: number;
  sor: number;
  ost: number;
  nord: number;
}

export interface Utsnittsflate {
  type: "Polygon";
  coordinates: [number, number][][];
}

export function utsnittsflate({ vest, sor, ost, nord }: Utsnitt): Utsnittsflate {
  return {
    type: "Polygon",
    coordinates: [
      [
        [vest, sor],
        [vest, nord],
        [ost, nord],
        [ost, sor],
        [vest, sor],
      ],
    ],
  };
}

/** Ringens signerte areal. Fortegnet er viklingsretningen. */
export function signertAreal(ring: [number, number][]): number {
  let sum = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i]!;
    const [x2, y2] = ring[i + 1]!;
    sum += x1 * y2 - x2 * y1;
  }
  return sum / 2;
}
