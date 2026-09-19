import { useContext, useSyncExternalStore } from 'react'
import { StreamContext, type StreamContextValue } from '../contexts/StreamContext'

export function useStream(): StreamContextValue {
  const lager = useContext(StreamContext)
  if (!lager) throw new Error('useStream must be used within StreamProvider')
  // Abonnér på lageret i stedet for at læse en kontekst-værdi: kun DENNE
  // komponent renderes om ved en stream-opdatering (lib/vaerdiLager).
  return useSyncExternalStore(lager.abonner, lager.hent, lager.hent)
}
