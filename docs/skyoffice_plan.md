# SkyOffice: Virtuelt Kontor for Jarvis & Agenter

## Status
- [x] Trin 1: Kør SkyOffice lokalt (installeret, kører)
- [ ] Trin 2: Layout-tilpasning (Tiled kort → Jarvis kontor)
- [ ] Trin 3: Avatar-system (agent-identiteter i 2D)
- [ ] Trin 4: Presence API (agent-state synkronisering)
- [ ] Trin 5: Integration med Jarvis kognitive runtime

## Trin 2 — Layout

### Zoner
| Zone | Formål | Placering |
|------|--------|-----------|
| Council Chamber | Mødelokale til agent-councils | Centralt |
| Workspace Row | Individuelle agent-stationer (6-8 PCs) | Venstre side |
| The Lab | Forskning/ekspirement (whiteboards) | Højre side |
| Commons | Pauseområde, vending machine | Nederst |
| Observatory | Bjørn's desk | Top-højre |

### Ændringer
- map.tmx: Omarrangere Wall/Chair for zoner
- map.tmx: Flere computer-objekter (6-8)
- SkyOffice.ts: Dynamisk computer/whiteboard count fra kortdata
- Nye objekttyper: ZoneSign

## Trin 4 — Presence API

### State-udvidelse
```typescript
export class AgentPlayer extends Player {
  @type('string') role = ''        // council, researcher, worker, observer
  @type('string') status = 'idle'  // idle, working, meeting, away
  @type('string') avatarUrl = ''   // custom agent-portrait
}
```

### Nye messages
- AGENT_ENTER — agent træder ind med rolle/status
- AGENT_UPDATE_STATUS — agent ændrer status
- AGENT_LEAVE — agent forlader

### Presence bridge
Jarvis API → REST/WebSocket → SkyOffice state
Agent-status synkroniseres automatisk når agenter er aktive.

## Kort-struktur (eksisterende)
- Størrelse: 40×30 tiles (32px each = 1280×960)
- Lag: Ground, Wall, Chair, Objects, ObjectsOnCollide, GenericObjects, Computer, Whiteboard, Basement, VendingMachine
- 5 computere, 3 whiteboards, 33 stole, 38 væg-objekter

## State-struktur (eksisterende)
- Player: name, x, y, anim, readyToConnect, videoConnected
- Computer: connectedUser (SetSchema)
- Whiteboard: roomId, connectedUser (SetSchema)
- ChatMessage: author, createdAt, content