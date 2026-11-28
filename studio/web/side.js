// Ogledanje po X osi između žute i plave strane (taktike se pišu za refSide).
export const FIELD_X = 3000;

export function mirrorX(x, side, refSide) {
  return side === refSide ? x : FIELD_X - x;
}
