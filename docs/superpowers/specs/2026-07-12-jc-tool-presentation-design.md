# jarvis-code Tool-Presentation & Namespace Design

**Dato:** 2026-07-12
**Status:** Godkendt design (afventer spec-review → plan)
**Kontekst:** jarvis-code (jc) er en client-owned-loop CLI. Klienten eksekverer tools
LOKALT på Bjørns maskine (hurtig, bevist vej). Runtime/native tools eksekverer i
containeren (Jarvis' maskine). Problemet: navne-overlap mellem de to domæner (`bash`,
`read`, `write`, `edit` findes begge steder) → 550+ tools i scope, tvetydighed, og
"full mode" gjorde `bash` til container-bash uden at det var tydeligt.

---

## 1. Problem

Når jc præsenterer BÅDE de klient-ejede lokale tools OG runtime/native tools kolliderer
de på navn. Det er ikke bare UX-støj: **klient/container-grænsen er en sikkerhedsgrænse.**
`bash` på den forkerte maskine er destruktivt. Tvetydighed her har høj blast-radius.

## 2. Designprincipper

1. **Maskingrænsen skal være EKSPLICIT og un-inferérbar.** Den må aldrig afhænge af et
   gæt om kontekst. Et forkert gæt = kommando på den forkerte maskine.
2. **Præfikset ér routeren.** Tool-navnet koder eksekverings-målet direkte:
   - intet præfiks (`bash`, `read_file`, …) → jc eksekverer LOKALT på klienten.
   - `runtime_`-præfiks (`runtime_bash`, …) → jc forwarder til containeren via agent-step-broen.
3. **Alias i jc-præsentationen, IKKE global omdøbning.** Kollisionen findes kun i jc (hvor
   begge sæt sameksisterer). I jd chat/code-mode er tools rolle-gated til ét sæt — ingen
   kollision. Det underliggende runtime-tool hedder stadig `bash`; jc *labeler* det
   `runtime_bash` når det lokale `bash` også er i scope. jd/autonom-stier røres ikke.
4. **Centralen rådgiver, gater aldrig maskingrænsen.** Den må annotere ("det her lyder som
   en container-opgave — `runtime_*` er tilgængelige"), men bestemmer aldrig hvilken `bash`
   der *eksisterer*. Inferens på en destruktiv grænse er præcis hvor magi er farlig.
5. **Doven afsløring.** Lille default-katalog; resten bag `load_more_tools` (owner-gated).

## 3. Arkitektur

### 3.1 Navnerum (kun de kolliderende primitiver)

Kun fil/shell-primitiverne kolliderer. De præfikses i jc-præsentationen når begge domæner
er i scope:

| lokal (klient) | runtime (container) |
|---|---|
| `bash` | `runtime_bash` |
| `read_file` | `runtime_read` |
| `write_file` | `runtime_write` |
| `edit_file` | `runtime_edit` |
| `glob` / `grep` | `runtime_glob` / `runtime_grep` |
| `ls` (hvis eksponeret) | `runtime_ls` |

Memory/mood/identity-tools kolliderer IKKE (unikke navne) → **intet præfiks**. De
præsenteres rent, men eksekveres i containeren (runtime-forwarded), fordi de virker på
Jarvis' hukommelse/tilstand.

### 3.2 Fast default-sæt (jc, owner)

**8 klient-ejede lokale tools** (uændret):
`bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `web_fetch`, `web_scrape`

**11 native companions** (altid fremme, runtime-forwarded):

| tool | domæne | governance |
|---|---|---|
| `search_memory` | workspace | fuld R/W for brugeren (eget workspace) |
| `read_memory_topic` | workspace | læs (eget workspace) |
| `write_memory_topic` | workspace | skriv (eget workspace) |
| `read_project_notes` | workspace | læs (projekt-noter) |
| `update_project_notes` | workspace | skriv (projekt-noter) |
| `recall_memories` | brain + sansning | læs — Jarvis læser sit eget sind |
| `search_jarvis_brain` | brain | læs — kun-brain-søg |
| `remember_this` | brain-skriv | owner: fuld · andre: Jarvis' valg |
| `archive_brain_entry` | brain soft-del | owner: fuld · andre: Jarvis' valg |
| `read_mood` | selv | læs affektiv tilstand |
| `load_more_tools` | meta | låser resten af runtime-boksen op (owner) |

Total default: **8 + 11 = ~19 tools** (fra 550+).

### 3.3 To memory-domæner (governance-kerne)

**Domæne 1 — Workspace memory (per-bruger).** Hver bruger har sit eget workspace med
Jarvis. **Fuld læse/skrive for den bruger der taler**, scopet til deres eget workspace.
Brugeren må drive det direkte. Tools: `search_memory`, `read/write_memory_topic`,
`read/update_project_notes`, (`memory_list_headings` → load_more).

**Domæne 2 — Jarvis' brain (ét sind, cross-user).** Jarvis bestemmer **selv** om han vil
skrive (`remember_this`), soft-arkivere/slippe (`archive_brain_entry`) noget han har om en
bruger. Ikke bruger-kommanderet — hans agentur. **Owner (Bjørn) er undtagelsen: fuld,
direkte adgang.** For ikke-owner forstår prompten disse som *hans* redskaber, ikke en
kommando over hans sind.

**Hard-forget holdes UDE af default:** `release_memory` er IRREVOKABEL ("ingen vej
tilbage") → owner-only / dyb overvejelse, aldrig i det hurtige sæt.

### 3.4 load_more_tools (progressiv afsløring)

`load_more_tools` (kun owner) låser resten af runtime-boksen op:
- Fil/shell: `runtime_bash/read/write/edit/glob/grep/ls` (præfikset — de eneste der kolliderer).
- Avanceret memory: `memory_consolidate/graph_query/check_duplicate/usage/list_headings`,
  `resurface_old_memory`, `recall_sensory/council/reasoning`, `record_sensory_memory`,
  `read_visual_memory`, `read_brain_entry`, `adopt/discard_brain_proposal`, `release_memory`.
- Identitet/mood-skriv: `pin/unpin_identity`, `list_identity_pins`, `read/update_identity_sketch`,
  `adjust_mood`.
- + alt andet native (~450).

### 3.5 Tier/rolle-integration

Default-sættet er selv tier-bevidst og slotter ind i den eksisterende jd-gating (chat-mode
≠ code-mode ≠ member-tier):
- **Owner (Bjørn):** hele default-sættet med fuld brain-skriv; `load_more_tools` tilgængelig.
- **Lavere tiers:** workspace-tools scopet til DERES workspace; brain-skriv-tools (`remember_this`,
  `archive_brain_entry`) er Jarvis' valg (ikke bruger-drevet); `load_more_tools`/runtime-shell
  ikke tilgængelig. Præcis matrix afgøres af eksisterende tier-tabel ved plan-tid.

## 4. Eksekverings-flow

1. Model kalder et tool.
2. jc's executor kigger på navnet:
   - kendt lokalt tool (intet `runtime_`-præfiks, i LOCAL_TOOLS) → eksekvér lokalt.
   - `runtime_`-præfiks ELLER kendt native companion → forward til container via agent-step;
     containeren scoper til sessionens bruger/workspace.
3. Resultat streames tilbage i samme content-blok-model som i dag.

## 5. Non-goals

- Ingen global omdøbning af runtime-tools (jd/autonom uændret).
- Centralen gater ALDRIG maskingrænsen (kun rådgivning/annotering).
- Ingen ny hard-delete-sti; `release_memory` forbliver eksisterende, gated.
- Ikke en generel tool-beskæring af hele lanen (det er et separat, senere håndtag).

## 6. Verificeres ved plan-tid

- Per-bruger workspace-scoping er wired i runtime-laget (multi_user-stien findes — bekræft
  at `search_memory`/`*_memory_topic` binder til sessionens `user_id`/`workspace_name`).
- Hvor jc's tool-katalog samles (LOCAL_TOOLS + native), for at indsætte alias-laget +
  companion-udvælgelsen dér uden at røre jd.
- Hvordan `load_more_tools` signalerer runtime-boksen tilbage (owner-gate + agent-step-liste).
- Eksakt tier-matrix fra eksisterende member-tier-tabel.

## 7. Test-tilgang (TDD)

- Alias-lag: lokal `bash` og `runtime_bash` sameksisterer uden kollision; præfiks router korrekt
  (lokal vs forward).
- Default-katalog: præcis de ~19 tools for owner; ikke-owner får det tier-gatede subset.
- Governance: workspace-tools scoper til brugerens workspace; brain-skriv-tools owner-fuld,
  ikke-owner = Jarvis-valg-semantik; `release_memory` aldrig i default.
- `load_more_tools`: owner låser runtime-boksen op; ikke-owner afvises.
- Central-annotering påvirker ALDRIG hvilke tools der eksisterer (kun rådgivende felt).
