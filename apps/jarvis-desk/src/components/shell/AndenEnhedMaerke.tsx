import { Smartphone } from 'lucide-react'

/** Et lille mærke i headeren: der kører noget på en anden enhed, og vi følger med.
 *
 *  ## Hvorfor det ikke er et banner længere (Bjørn 20/9-2026)
 *
 *  «i toppen af chatview kommer et helt badge med aktiv på en anden enhed …
 *  det må kunne gøres mere diskret med bare et mobil- eller signal-ikon der
 *  kommer og går og lyser op når der er forbindelse? evt. a la central badge i
 *  header, måske endda der?»
 *
 *  Banneret var en fuld linje med tekst og et kryds, og det skubbede hele
 *  samtalen ned hver gang et run startede på telefonen. Oplysningen er ikke
 *  en linje værd — den er et ikon værd. Den bor nu ved siden af Central-mærket,
 *  hvor de andre tilstands-signaler i forvejen står.
 *
 *  Krydset er væk med banneret. Et mærke der forsvinder af sig selv, når
 *  kørslen slutter, har ikke brug for at kunne lukkes — og «skjult» var en
 *  tilstand vi skulle huske og nulstille.
 */
export function AndenEnhedMaerke({ aktiv }: { aktiv: boolean }) {
  if (!aktiv) return null
  return (
    <div
      className="anden-enhed"
      role="status"
      title="Aktiv på en anden enhed — følger med her live"
      data-testid="anden-enhed"
    >
      <Smartphone size={13} aria-hidden="true" />
      <span className="kun-skaermlaeser">Aktiv på en anden enhed — følger med her live</span>
    </div>
  )
}
