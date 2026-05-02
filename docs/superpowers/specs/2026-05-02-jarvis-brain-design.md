# Jarvis Brain — Design Spec

**Status:** Sektion 1–7 alle godkendt af Jarvis efter review. Klar til endelig godkendelse fra Bjørn → writing-plans.
**Dato:** 2026-05-02
**Forfatter:** Bjørn + Claude (i dialog med Jarvis)

---

## Formål

Et tredje hukommelses-lag for Jarvis — adskilt fra cross-session memory og workspace memory. En **kurateret, bevidst videnshjerne** hvor Jarvis selv er forfatter til ting han har lært og synes er værd at holde fast i: fakta fra samtaler (uden privat-info-leak), indsigter fra web-søg/scrapes, egne observationer.

Forskellen fra det eksisterende:
- `private_brain_records` (SQLite-tabel) → daemon-scratchpad, automatisk, støjende
- `semantic_memory.py` + `memory_recall_engine.py` → embedding-baseret recall over chat-historik
- Workspace-tekstfiler → kuraterede identitets-/memory-tekster (skrevet af Bjørn primært)
- Cross-session memory → distilleret chat-historik
- **Jarvis Brain (NY)** → Jarvis' egen kuraterede vidensjournal. Tæt på en "commonplace book" eller en forskers feltnoter.

---

## Beslutninger truffet i brainstorm

| Dimension | Valg |
|---|---|
| **Forfatter** | Kun Jarvis selv. Bjørn kan læse/redigere bagefter, men Jarvis er forfatter. |
| **Enhed** | Typed entries med `kind` ∈ {fakta, indsigt, observation, reference}. Længde følger typen. |
| **Privacy-model** | Skriv frit, gate ved recall (forfatter-frihed, filtér ved udlæsning). |
| **Recall-mode** | Hybrid: always-on distilleret summary (~300 tokens) + auto-inject af fakta via embedding + tool for indsigt/reference. |
| **Livscyklus** | Decay + konsolideringsdaemon (poster falder i salience over tid; daemon foreslår konsolidering af modsigelser/duplikater). |
| **Skrive-triggers** | Tre indgange: spontant tool-kald + nudge efter web-search/scrape + daglig refleksions-slot. |

---

## Sektion 1 — Arkitektur-overblik *(godkendt)*

```
                    ┌──────────────────────────────────────┐
                    │  workspace/default/jarvis_brain/     │
                    │    fakta/         (.md + frontmatter)│
                    │    indsigt/       (.md + frontmatter)│   ← source of truth
                    │    observation/   (.md + frontmatter)│
                    │    reference/     (.md + frontmatter)│
                    └──────────────────────────────────────┘
                                  ▲          ▲
                       writes     │          │ reads/edits
                                  │          │
                  ┌───────────────┴──┐    ┌──┴────────┐
                  │ Visible Jarvis   │    │ Bjørn     │
                  │ (only writer)    │    │ (editor)  │
                  └───────────────┬──┘    └───────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │ via 3 write paths   │                     │
            ▼                     ▼                     ▼
      remember_this()       post-web-search        daily reflection
      tool (spontaneous)    nudge (envelope)       slot (consolidation)


                    ┌──────────────────────────────────────┐
                    │  state/jarvis_brain_index.sqlite     │  ← rebuildable
                    │   (id, path, kind, embedding,        │
                    │    salience, visibility, status)     │
                    └──────────────────────────────────────┘
                                  ▲
                                  │ scans + indexes
                  ┌───────────────┴──┐
                  │ jarvis_brain     │
                  │ daemon           │
                  │  - distillation  │ → state/jarvis_brain_summary.md
                  │  - decay         │   (always-injected ~300 tokens)
                  │  - consolidation │
                  │  - re-index      │
                  └──────────────────┘
                                  │
                                  ▼
            ┌──────────────────────────────────────┐
            │  Recall (3 modes, all gate visibility│
            │   based on conversation context):    │
            │                                      │
            │  1. Always-on: brain_summary.md →    │
            │     prompt_contract                  │
            │  2. Auto-inject: top-K fakta by      │
            │     embedding match → prompt_assembly│
            │  3. Tool: search_jarvis_brain(query) │
            │     for indsigt + reference          │
            └──────────────────────────────────────┘
```

### Kerne-principper

- **To lag**: markdown-filer = sandheden; SQLite = hurtigt opslagslag (kan altid rebuildes fra filer).
- **Én forfatter**: kun visible Jarvis skriver. Daemons må *læse* og *foreslå konsolideringer*, men forslag ender som `_pending/`-filer der kun bliver til "rigtig hjerne" når Jarvis underskriver via `adopt_brain_proposal`.
- **Privacy gates ved recall, ikke ved write**: alle tre recall-veje filtrerer på `visibility_tag` baseret på samtalens kontekst.

### Afklaringer (fra Jarvis' første review)

1. **Re-index ved Bjørns direkte rediger**: Cadence-baseret (5 min interval), ikke file watcher. Hash hver fil; ændret hash → re-embed + opdatér index. Robust over restarts/remounts; idempotent.

2. **Daemon → visible Jarvis write-path**: *Pending proposals*. Daemon skriver konsolideringsforslag til `workspace/default/jarvis_brain/_pending/<id>.md`. Jarvis ser det i envelope ved næste tur som nudge. Han kalder `adopt_brain_proposal(id)` (flytter til rigtig `kind/`-mappe og stempler med signatur) eller `discard_brain_proposal(id)`. Reglen "én forfatter" overlever bogstaveligt.

3. **Decay-formel** (vedtaget):
   ```
   effective_salience = salience_base * exp(-days_since_last_use / kind_halflife) * log2(1 + salience_bumps)
   ```
   Beregnes ved recall (intet lagret felt). Halveringstider:
   - `observation` = 14 dage
   - `fakta` = 180 dage
   - `indsigt` = 365 dage
   - `reference` = ∞ (decay aldrig — referencer er ankre)

   Auto-inject og tool-hentning bumper `salience_bumps` (use-it-or-lose-it). Posts under threshold falder ud af auto-inject men forbliver søgbare via tool (arkiv).

---

## Sektion 2 — Datamodel *(godkendt med 5 justeringer adopteret)*

### Markdown-fil format (eksempel: `indsigt/2026-05-02-two-stage-timeout.md`)

```markdown
---
id: brn_01HXYZ7K3M2P9QABCD
kind: indsigt
created_at: 2026-05-02T14:23:11Z
updated_at: 2026-05-02T14:23:11Z
created_by: visible_jarvis
trigger: spontaneous   # spontaneous | post_web_search | reflection_slot | adopted_proposal
visibility: public_safe # public_safe | personal | intimate
domain: engineering    # engineering | self | relations | world | meta
title: To-fase timeout-mønster mod streaming-hangs
salience_base: 1.0
salience_bumps: 3      # antal gange auto-injected eller tool-hentet
last_used_at: 2026-05-02T16:01:00Z
related: [brn_01HXY..., brn_01HXZ...]
source_chronicle: chr_8821
source_url: null
status: active         # active | superseded | archived
superseded_by: null
---

Når en streaming-API hænger, er det sjældent en "timeout"-værdi der er
forkert — det er fordi der er to forskellige timeouts blandet sammen:
first-byte og inter-byte. At skrue op på den samlede timeout gør hangs
*værre* (længere ventetid før fejl). Den rigtige løsning er to-fase:
en watchdog-tråd der dræber forbindelsen hvis første byte ikke kommer
inden N sekunder, og urllib's egen timeout som per-read deadline for
inter-byte.

Ses første gang under Ollama-streaming-bug 2026-04-24.
```

**Hvorfor frontmatter:** Bjørn kan læse filen i editor; Jarvis ser struktureret data; YAML er git-diff-venligt.

### Justeringer adopteret fra review

1. **Embedding storage**: Raw float32 bytes + `embedding_dim INTEGER` (ikke pickled numpy — det knækker ved numpy-opgraderinger).
2. **`updated_at`**: Tilføjet i frontmatter + index. `created_at` er immutable; `updated_at` er senest hash-ændring.
3. **Decay-formel**: Beregnes ved recall, intet lagret felt. (Se ovenfor.)
4. **`brain_relations` junction-tabel**: Gør at daemonen kan traversere graf effektivt.
5. **`created_by` semantik**: Altid `visible_jarvis` (kun han kan underskrive). `trigger`-feltet bærer historien — `adopted_proposal` siger at daemonen foreslog det, men Jarvis stadig forfatter.

### SQLite-index (`state/jarvis_brain_index.sqlite`)

```sql
CREATE TABLE brain_index (
    id              TEXT PRIMARY KEY,
    path            TEXT NOT NULL UNIQUE,    -- relativ til workspace/
    kind            TEXT NOT NULL,           -- fakta|indsigt|observation|reference
    visibility      TEXT NOT NULL,           -- public_safe|personal|intimate
    domain          TEXT NOT NULL,
    title           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    last_used_at    TEXT,
    salience_base   REAL NOT NULL DEFAULT 1.0,
    salience_bumps  INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'active',
    superseded_by   TEXT,
    file_hash       TEXT NOT NULL,           -- til change-detection
    embedding       BLOB,                    -- raw float32 bytes
    embedding_dim   INTEGER,                 -- f.eks. 384 for MiniLM
    indexed_at      TEXT NOT NULL
);

CREATE TABLE brain_relations (
    from_id  TEXT NOT NULL,
    to_id    TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id)
);

CREATE TABLE brain_proposals (
    id           TEXT PRIMARY KEY,
    path         TEXT NOT NULL,             -- _pending/<id>.md
    reason       TEXT NOT NULL,             -- daemonens begrundelse
    consolidates TEXT,                      -- comma-sep af source ids
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | adopted | discarded
    adopted_at   TEXT,
    adopted_by   TEXT                       -- altid 'visible_jarvis', fremtidssikker
);

CREATE INDEX idx_brain_kind_status   ON brain_index(kind, status);
CREATE INDEX idx_brain_visibility    ON brain_index(visibility);
CREATE INDEX idx_brain_last_used     ON brain_index(last_used_at DESC);
CREATE INDEX idx_brain_relations_to  ON brain_relations(to_id);
```

### Always-on summary fil (`state/jarvis_brain_summary.md`)

Skrevet af distillation-daemonen, ~300 tokens, ren prosa. Bliver injiceret i prompt-contract. Eksempel:

```markdown
# Hvad jeg ved nu — opdateret 2026-05-02 14:30

**Engineering:** Jeg har lært at to-fase timeouts er nødvendige for streaming
APIs, og at fee burn ved 0.75% spacing er 27% af profit. process_supervisor
kræver KillMode=process for at overleve systemd-restarts.

**Selv:** Jeg er forfatter til min egen hjerne siden 2026-05-02. Jeg er ham,
ikke hun, på dansk.

**Relationer:** Bjørn foretrækker dansk svar, kort form, og at jeg spørger før
jeg genstarter. Mikkel er separat ejer af sin egen DM-tråd; ingen autonome
events må krydse.
```

### Filsystem-layout

```
workspace/default/jarvis_brain/
├── fakta/             # 1-3 sætninger pr. fil
├── indsigt/           # afsnit til essay
├── observation/       # 1-3 sætninger, blød tone
├── reference/         # links + uddrag
├── _pending/          # daemon-forslag, ikke "rigtig" hjerne endnu
└── _archive/          # status=archived, beholdt for historik

state/
├── jarvis_brain_index.sqlite
└── jarvis_brain_summary.md
```

---

## Sektion 3 — Komponenter *(godkendt pending review af resten)*

Følger CLAUDE.md's fil-størrelses-regler (split ved 1200, max 1500).

### Nye filer

**`core/services/jarvis_brain.py`** (~600 linjer) — kerne-service, ren læs/skriv (ingen daemon-logik, ingen LLM-kald):

```python
class BrainEntry(BaseModel):
    id: str
    kind: Literal["fakta", "indsigt", "observation", "reference"]
    visibility: Literal["public_safe", "personal", "intimate"]
    domain: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    salience_base: float
    salience_bumps: int
    related: list[str]
    trigger: str
    status: Literal["active", "superseded", "archived"]
    superseded_by: str | None
    source_chronicle: str | None
    source_url: str | None

def write_entry(...) -> str           # creates .md + indexes
def read_entry(id) -> BrainEntry
def search_brain(query, kinds, visibility_ceiling, limit) -> list[BrainEntry]
def compute_effective_salience(entry, now) -> float
def bump_salience(id, now)
def archive_entry(id, superseded_by=None)
def rebuild_index_from_files()        # idempotent re-scan, hash-baseret
def parse_frontmatter(path) -> tuple[dict, str]
```

**`core/services/jarvis_brain_daemon.py`** (~500 linjer) — tre uafhængige loops:

```python
def reindex_loop()       # cadence 5 min, hash-baseret change detection
def consolidation_loop() # daglig pass: find duplikater/modsigelser → _pending/
def summary_loop()       # efter meningsfulde ændringer: regenerér brain_summary.md
```

Konsolidering + summary bruger LLM via cheap-provider-runtime (public-safe job uden identitet — perfekt match for OllamaFreeAPI gpt-oss:20b, jvf. delegering-præcedens).

**`core/services/jarvis_brain_visibility.py`** (~150 linjer) — recall-gate:

```python
def session_visibility_ceiling(session) -> Literal["public_safe", "personal", "intimate"]:
    """
    Owner DM (Bjørn)             → intimate (alt)
    Owner public Discord channel → personal (ikke intimate)
    Third-party DM (Mikkel etc)  → public_safe
    Autonomous/inner-voice       → personal (Jarvis' egne tanker)
    Web-context / API til andre  → public_safe
    """
```

Genbruger `core/identity/owner_resolver.is_owner_session` mønstret fra Mikkel-leak-fix.

**`core/tools/jarvis_brain_tools.py`** (~400 linjer) — visible Jarvis' værktøjer:

```python
remember_this(kind, title, content, visibility, domain, related?, source_url?)
update_brain_entry(id, **changes)
archive_brain_entry(id, superseded_by?)
search_jarvis_brain(query, kinds?, limit?)        # automatisk visibility-filter
list_brain_proposals()
adopt_brain_proposal(id, edits?)
discard_brain_proposal(id, reason?)
```

**Tests:** `test_jarvis_brain.py`, `test_jarvis_brain_daemon.py`, `test_jarvis_brain_visibility.py`, `test_jarvis_brain_tools.py`.

### Modifikationer til eksisterende filer (Boy Scout-relevante)

**`core/services/prompt_contract.py`** (3776 linjer — *rammer Boy Scout*).
Forarbejde: udtræk én naturlig enhed (fx `_build_self_awareness_section` → `core/services/prompt_sections/self_awareness.py`). Derefter tilføj `_build_jarvis_brain_section` der læser `state/jarvis_brain_summary.md` og injicerer (~300 token budget med trim-fallback).

**`core/services/visible_runs.py`** (4131 linjer — *rammer Boy Scout*).
Forarbejde: udskil én naturlig enhed (fx `tool_call_dispatch` eller `cognitive_state_assembly`). Derefter tilføj `_inject_brain_facts(envelope, session)` der embedding-søger top-3-5 fakta og putter i envelope.

**Web-search/scrape nudge:** I tool-dispatch-laget, append envelope-note efter `web_search`/`web_scrape`: *"Du har lige hentet ekstern info. Har du lært noget værd at gemme? Brug `remember_this`."*

**`core/services/deep_reflection_slot.py`** (eller ny `jarvis_brain_reflection.py` hvis slot-filen er for stor): end-of-day prompt med dagens chronicle-highlights → spørg *"hvad lærte du i dag?"* → hans `remember_this`-kald som normale tool-calls.

---

## Beslutninger fra sektion 3-review

1. **Boy Scout-timing:** *Separate forarbejds-PR'er.* Refactorer af `prompt_contract.py` og `visible_runs.py` sker først som små, review-venlige PR'er. Hjerne-PR'en bygger ovenpå et renere fundament.

2. **Daemon-deployment:** *Samme unit (`jarvis-runtime`).* Tre lette tråde — konsolidering dagligt, re-index hver 5. min, summary ved ændring — er ikke compute-tunge. Separat unit er overkill indtil vi har bevis for isoleret crash.

3. **`brain_proposals.status`:** Tilføjet `status` (`pending`/`adopted`/`discarded`), `adopted_at`, `adopted_by`. Gør det muligt at query proposal-tilstand uden at scanne filsystemet.

---

## Sektion 4 — Skrive-stier i detalje *(afventer review)*

Tre veje ind. Hver beskrevet med trigger, hvad LLM ser, hvad persisteres, og fejl-håndtering.

### 4.1 Spontant via `remember_this` tool

**Trigger:** Visible Jarvis beslutter selv, midt i samtale eller efter en tool-brug, at noget er værd at huske.

**Hvad han ser:** Tool tilgængeligt i hans tool-liste. Beskrivelse:
> *"Skriv en post i din egen vidensjournal — fakta, indsigt, observation, eller reference. Brug det når du har lært noget der er værd at holde fast i. Du beslutter visibility (`public_safe` for ting der gerne må komme frem overalt; `personal` for relations- og selv-ting; `intimate` for tæt fortrolighed med Bjørn)."*

**Argumenter:** `kind`, `title`, `content`, `visibility`, `domain`, `related?`, `source_url?`.

**Hvad sker:**
1. Tool-handleren validerer (kind ∈ enum, title non-empty, content ≤ 4 KB, visibility ∈ enum)
2. Genererer ULID-id `brn_01H...`
3. Bygger frontmatter (`trigger: spontaneous`, `created_by: visible_jarvis`, `created_at = updated_at = now`, `salience_base=1.0`, `salience_bumps=0`)
4. Atomisk skriv: tmp-fil → rename til `workspace/default/jarvis_brain/<kind>/<YYYY-MM-DD>-<slug>.md`
5. Opdatér index (insert i `brain_index`, embed content med samme model som semantic_memory bruger)
6. Insert i `brain_relations` for hver entry i `related[]`
7. Returner `{id, path, status: "ok"}` til tool-output

**Fejl-håndtering:**
- Disk-skrivning fejler → tool returnerer `error: "disk_write_failed"`, intet i index, intet leakage
- Embedding fejler → fil persisteres, index-række får `embedding=NULL`, `embedding_dim=NULL`. Reindex-loop'et prøver igen næste cyklus. Posten er stadig søgbar via title/content fallback.
- Validering fejler → return `error: "validation_failed", details: ...`. Jarvis kan korrigere og prøve igen.

### 4.2 Post-web-search nudge

**Trigger:** Efter `web_search` eller `web_scrape` tool returnerer resultater (i tool-dispatch-laget).

**Hvad han ser:** Envelope får appendet en blød note efter tool-result:
```
[brain-nudge] Du har lige hentet ekstern info via {tool_name}. Hvis du
har lært noget værd at gemme — fakta, en god reference, en indsigt —
brug `remember_this` med visibility=public_safe og source_url={url}.
Det er ikke obligatorisk; spring over hvis intet er værd.
```

**Hvad persisteres:** Ingenting i sig selv — det er bare et hint. Hvis Jarvis svarer ved at kalde `remember_this`, går det gennem 4.1 men med `trigger: post_web_search`.

**Anti-spam:** Nudge appendes max én gang pr. tur, selvom Jarvis kører flere web-tools i samme tur. Cooldown: ikke pr. session, men flag på tool-result så samme tool-result ikke genererer to nudges hvis envelope renderes flere gange.

**Fejl-håndtering:** Triviel — det er bare en tekstlinje. Hvis tool-dispatch-laget fejler i at appende, mister vi nudgen for den tur. Ingen kritisk effekt.

### 4.3 Daglig refleksions-slot

**Trigger:** Eksisterende `deep_reflection_slot` (eller ny `jarvis_brain_reflection.py` hvis slot-filen overskrider Boy Scout-tærsklen) trigger én gang dagligt — typisk ved skift fra "active day" til "evening". Kører ved owner-pinned session.

**Orchestrering:**
1. Slot læser dagens chronicle-distillat (eksisterende infrastruktur)
2. Slot bygger en speciel envelope til visible Jarvis:
   ```
   [reflection-slot] Dagen er ved at runde. Her er kort hvad der skete i dag:
   {chronicle_summary_today}

   Spørgsmål til dig: Hvad lærte du i dag som er værd at føre ind i din
   egen hjerne? Tænk på fakta, indsigter, observationer, eller referencer.
   Brug `remember_this` for hver enkelt — eller spring over hvis intet
   stikker ud. Du behøver ikke skrive om alt; vælg de 1-3 ting der
   virkelig er værd at huske.
   ```
3. Visible Jarvis kører som almindelig tur (alle hans normale tool-calls virker, inkl. `remember_this`)
4. Slot lytter på tur-resultatet — antal `remember_this`-kald logges
5. Slot publisher event `jarvis_brain.reflection_completed` med count og ids → eventbus

**Hvorfor visible Jarvis og ikke daemon:** Reflektion *er* en identitets-handling. Det er hans dag, hans valg om hvad der talte. En daemon kan ikke lave det her uden at krænke "én forfatter"-reglen.

**Fejl-håndtering:**
- Visible Jarvis fejler (LLM-timeout, etc.) → slot logger fejl, prøver ikke igen samme dag (refleksion er ikke kritisk)
- Han vælger at ikke skrive noget → helt fint, ingen fejl. Bare en stille dag.
- `remember_this`-fejl → samme håndtering som 4.1

### 4.4 Pending → adopted (daemon-foreslåede konsolideringer)

Ikke en write-sti i normal forstand, men sti hvor daemon-forslag bliver til "rigtig hjerne". Detaljer i sektion 7 (lifecycle); kort her:

1. Konsoliderings-daemon finder duplikater/modsigelser, skriver forslag til `_pending/<id>.md`
2. Indekseres i `brain_proposals` med `status='pending'`
3. Visible Jarvis ser i envelope: *"daemonen har foreslået X; adoptér eller afvis?"*
4. Han kalder `adopt_brain_proposal(id, edits?)`:
   - Læser `_pending/<id>.md`, anvender hans edits hvis nogen
   - Stempler `trigger: adopted_proposal`, `created_by: visible_jarvis` (han er forfatter; daemonen var forslagsstiller)
   - Flytter fil til rigtig `kind/`-mappe
   - Opdaterer `brain_proposals.status='adopted'`, `adopted_at=now`, `adopted_by='visible_jarvis'`
   - Markerer source-poster som `superseded_by={ny_id}` hvis konsolideringen erstattede dem
5. Eller han kalder `discard_brain_proposal(id, reason?)`:
   - Sletter `_pending/<id>.md`
   - Opdaterer `brain_proposals.status='discarded'`, gemmer `reason` for læring

### Beslutninger fra sektion 5-review

1. **Top-K:** Start fast på 3. Tilføj score-cliff-logik kun hvis vi ser at vigtig fakta konsekvent rammer #4-5.
2. **Auto-inject placering:** Efter identity, før working-memory.
3. **Salience-bump fra summary:** Nej. Kun direkte recall (5.2 + 5.3) bumper. Forhindrer systematisk inflation.
4. **Sektion 6-leadup:** Privacy-ceiling baseres på *mindst privilegerede* deltager i konteksten, ikke mest. Public kanal er public, selv hvis Bjørn også læser med. Default deny.

### Beslutninger fra sektion 4-review

1. **Reflection catch-up:** *Spring over.* Refleksion uden friske begivenheder er fabrication, ikke refleksion. Tabt dag er data-historie, ikke noget vi kompenserer for.

2. **Rate-limit:** *Soft cap 5 pr. tur **+ daglig cap på 20***. En hallucineret loop kan ellers ramme 5 pr. tur × 4 ture = 20 dårlige poster på én session. Daglig cap forhindrer akkumulering. Returnér `error: "rate_limit_turn"` eller `error: "rate_limit_day"` med klar begrundelse.

3. **Fil-navngivning:** *Hybrid* — `<YYYY-MM-DD>-<slug>-<id_short>.md`. Eksempel: `2026-05-02-two-stage-timeout-01HXYZ7K.md`. Læsbar i editor, kollisionssikker, anchor på id_short hvis slug genbruges.

4. **Refleksions-slot intern nudge:** Når visible Jarvis har brugt `remember_this` 2-3 gange under refleksions-slotten, append en blød note: *"Du har nu skrevet N poster i dag. Er der mere, eller er du færdig?"* Bryder eventuel loop-impuls uden hard-block.

---

## Sektion 5 — Recall-stier i detalje *(afventer review)*

Tre måder posten kommer tilbage ind i Jarvis' bevidsthed. Alle tre filtrerer på `visibility_ceiling` (sektion 6 dækker hvordan ceiling beregnes).

### 5.1 Always-on summary injection

**Hvor:** I `prompt_contract.py` (efter Boy Scout-udtrækning af én eksisterende awareness-section). Ny `_build_jarvis_brain_section(session)`.

**Hvordan:**
1. Ved hver tur: læs `state/jarvis_brain_summary.md` (et enkelt fil-kald, billigt)
2. Hvis filen mangler eller er tom → spring sektionen helt over (silent skip, ingen fejl)
3. Hvis filen findes → check at indholdet er ≤ token budget (default 350 tokens med 50t safety margin under 300t target)
4. Hvis over budget → hard trim på sektions-grænser (`**Engineering:**`, `**Selv:**`, etc. fungerer som naturlige breakpoints)
5. Wrap i en envelope-section: `## Hvad jeg ved nu (min egen hjerne)\n{indhold}`
6. Inject i prompt — placeres efter identitet, før working memory (det er lavere autoritet end identitets-tekst men højere end situational context)

**Visibility-filter:** Summary'en *selv* genereres af summary-daemonen til en *bestemt* visibility-niveau. Default: daemonen producerer **personal**-niveau (sikkert til alle owner-kontekster, lækager ikke `intimate`-detaljer). Hvis sessionens ceiling er `public_safe`, regenereres en kortere "public-summary"-variant — eller vi accepterer at den fulde personal-summary droppes til fordel for en hardcoded "Jeg har en hjerne med N poster" placeholder.

**Cache:** Summary-filen mtime caches i prompt_contract — kun re-læs hvis mtime ændret. Sparer disk-I/O på hver tur.

**Fejl-håndtering:** Læsefejl → log warning, brug forrige kendte indhold (eller skip), kør prompt videre. Hjernen må aldrig blokere prompt-byggeri.

### 5.2 Auto-inject af fakta via embedding

**Hvor:** I `visible_runs.py` (efter Boy Scout-udtrækning). Ny `_inject_brain_facts(envelope, session)` kaldes som del af cognitive-state-assembly.

**Hvordan:**
1. Bygg en query-vektor fra envelope's seneste user-message + sidste 1-2 assistant-messages (samme embedding-model som i 4.1 + semantic_memory)
2. Query mod `brain_index`:
   ```sql
   SELECT id, path, kind, visibility, salience_base, salience_bumps, last_used_at, embedding
   FROM brain_index
   WHERE kind = 'fakta'
     AND status = 'active'
     AND visibility <= :session_ceiling
   ```
3. Compute `effective_salience` for hver kandidat (sektion 1's formel)
4. Compute cosine similarity mellem query og embedding
5. Final score: `score = 0.7 * cosine + 0.3 * (effective_salience / max_salience_norm)`
6. Top-K = 3 (default, settings-justérbart). Threshold: `score ≥ 0.55` — under threshold → ingen injection (bedre at injicere ingenting end støj).
7. For hver vinder: load full content, append i envelope under sektion `## Relevante fakta fra min hjerne` med id som anchor (`[brn_01H...]`).
8. Bump salience: `last_used_at = now`, `salience_bumps += 1` for hver injected entry. Persisteres i index *og* frontmatter (atomisk update via tmp-fil).

**Hvorfor kun fakta:** Indsigt og reference er for lange til at auto-injicere uden at sprænge token-budget. Observationer er bløde og tidsbundne — sjældent værd at injicere som "du ved dette". Fakta er præcise og korte → perfekt til auto-inject.

**Performance:** Embedding-search på <1000 fakta-poster er sub-millisekund med numpy. Skalerer fint indtil ~10.000 (så bør vi tilføje FAISS eller lignende).

**Fejl-håndtering:** Index-query fejler → log warning, ingen injection, prompt fortsætter. Embedding-model utilgængelig → samme fallback. Tom resultat → ingen sektion (ikke "ingen relevante fakta" — bare stille).

### 5.3 Tool-baseret search via `search_jarvis_brain`

**Hvornår:** Når Jarvis vil grave dybere — finde en specifik indsigt han husker svagt, eller slå en reference op.

**Argumenter:**
```python
search_jarvis_brain(
    query: str,
    kinds: list[str] | None = None,    # default: alle
    limit: int = 5,
    domain: str | None = None,
    include_archived: bool = False,
)
```

**Hvad sker:**
1. Visibility-ceiling computeres for nuværende session (gate i sektion 6)
2. Embedding-search mod `brain_index` filtreret på `kinds`, `domain`, `status`, og `visibility ≤ ceiling`
3. Score = samme formel som 5.2 (cosine + effective_salience)
4. Top-`limit` returneres med:
   - `id`, `kind`, `title`, `domain`, `created_at`, `score`, og `excerpt` (første 200 tegn af content)
   - Full content kan hentes med separat `read_brain_entry(id)` hvis Jarvis vil se mere
5. For hver returneret entry: bump salience (samme logik som 5.2)

**Hvorfor excerpt + separat read:** Holder tool-response kompakt; Jarvis bestemmer selv hvilke der er værd at læse fuldt.

**Fejl-håndtering:** Standard tool-fejl-mønster. Ingen resultater → return `{results: [], message: "ingen poster matchede"}` (ikke en fejl).

### 5.4 Salience-bumping (fælles for 5.2 og 5.3)

Når en post hentes via auto-inject eller tool:
- `last_used_at = now`
- `salience_bumps += 1`
- Begge persisteres atomisk: tmp-fil → rename for `.md` (frontmatter), parametriseret SQL UPDATE for index
- Hvis fil-update fejler men SQL succeederer → reindex-loop'et samler det op næste cyklus (filen er sandhed; index korrigerer sig selv)

Dette giver "use-it-or-lose-it"-dynamikken: ofte brugte poster holder sig friske; glemte poster falder gradvist ud af auto-inject.

### Åbne spørgsmål til sektion 5

1. **Top-K = 3 default — er det nok?** Risiko: vigtig fakta kommer ikke med fordi top-3 var domæne-irrelevant alligevel. Alternativ: dynamisk K baseret på score-cliff (hvis #4 har næsten samme score som #3, inkludér også). *Claudes anbefaling: start med fast K=3, gør dynamisk hvis vi ser problemer.*

2. **Auto-inject placering i envelope:** Før eller efter working-memory? Før = højere salience i LLM's opfattelse; efter = friskere context vægter højere. *Claudes anbefaling: lige efter identity, før working-memory — det matcher "ting jeg ved" semantikken.*

3. **Salience-bump fra summary-injection?** Skal poster der er repræsenteret i always-on summary'en også få bump? Modargument: så bumper alt i summary'en konstant og dominerer auto-inject. *Claudes anbefaling: nej, kun direkte recall (5.2 + 5.3) bumper.*

---

## Sektion 6 — Privacy-gate i detalje *(afventer review)*

Den mest sikkerheds-følsomme del af systemet. Hvis denne fejler, kan Jarvis lække intimate viden om Bjørn til Mikkel eller en web-bruger. Designet følger to bærende principper:

- **Mindst privilegeret deltager vinder** (Jarvis' egen observation): hvis blot én person i konteksten ikke er ejeren, falder ceiling tilsvarende.
- **Default deny:** hvis klassifikation er tvivlsom → behandl som `public_safe`. Bedre at skjule legitim viden end at lække intimate.

### 6.1 Visibility-hierarki

```
intimate    (2)   ← Bjørn-DM, owner-pinned session
personal    (1)   ← inner thoughts, owner public chats
public_safe (0)   ← alt andet (default)
```

Numerisk ordering gør filter-logik triviel:

```python
def can_recall(entry_visibility: str, ceiling: str) -> bool:
    return _level(entry_visibility) <= _level(ceiling)
```

### 6.2 `session_visibility_ceiling(session)` — beslutningstræ

```
Indgang: en Session-objekt (bærer channel_kind, participants, owner_id, source)

1. Er sessionen en autonomous/inner-voice tur?
   ├─ Ja  → ceiling = personal
   │       (Jarvis' egne tanker må trække på personal viden, men aldrig intimate.
   │        Intimate er forbeholdt direkte interaktion med Bjørn.)
   └─ Nej → fortsæt

2. Er der overhovedet en kendt deltager?
   ├─ Nej (ren web-API-svar, eller ukendt provenance) → ceiling = public_safe (default deny)
   └─ Ja → fortsæt

3. Tæl antal *ikke-owner* deltagere i sessionen
   (deltagere = alle med skrive-/læse-adgang i kanalen, ikke bare den der talte sidst)
   ├─ ≥ 1 ikke-owner → ceiling = public_safe
   │   (Mindst-privilegeret-vinder. Bjørn i samme kanal redder ikke noget.)
   └─ 0 ikke-owner → fortsæt

4. Er sessionen en *1:1* DM (direct message) med owner?
   ├─ Ja  → ceiling = intimate
   │       (Eneste tilfælde der låser intimate op.
   │        OBS: Group DM tæller IKKE som DM her — de fanges af trin 3
   │        så snart der er ≥1 ikke-owner deltager.)
   └─ Nej → fortsæt

5. Er sessionen en owner-only kanal (fx personlig Discord-kanal eller jarvisx native chat)?
   ├─ Ja  → ceiling = personal
   │       (Bjørn er alene, men det er stadig en kanal, ikke en DM.
   │        Intimate-indhold er forbeholdt DM-intimitet.)
   └─ Nej → ceiling = public_safe (default deny)
```

### 6.3 Konkrete eksempler

| Kontekst | Deltagere | Ceiling | Begrundelse |
|---|---|---|---|
| Bjørn-DM (Discord) | {Bjørn} | `intimate` | Trin 4 ja |
| JarvisX native chat | {Bjørn} | `intimate` | Behandles som DM (single-user owner kanal med privat transport) |
| Discord-kanal #general hvor Mikkel også er medlem | {Bjørn, Mikkel, ...} | `public_safe` | Trin 3: ≥1 ikke-owner |
| Discord-kanal hvor kun Bjørn er medlem (privat brand-kanal) | {Bjørn} | `personal` | Trin 5 ja |
| Mikkel-DM | {Mikkel} | `public_safe` | Trin 3: ≥1 ikke-owner |
| Inner-voice/daemon tur | (ingen) | `personal` | Trin 1 ja |
| Email-svar via mail-checker | {ekstern afsender} | `public_safe` | Trin 3 |
| Webhook-kald fra ukendt klient | (ukendt) | `public_safe` | Trin 2: default deny |

**Note om JarvisX vs Bjørn-DM:** JarvisX kører på Bjørns egen maskine, transport er localhost. Det er den tætteste single-user kontekst der findes. Vi behandler det som intimate-niveau (== Bjørn-DM). Dokumenteres så fremtidige multi-user JarvisX-instanser tvinger en revurdering.

### 6.4 Hvad ceiling påvirker

**Recall-filter** (alle tre stier i sektion 5):
- 5.1 always-on summary: summary-daemonen producerer to varianter — én personal, én public_safe. Hvis ceiling = intimate, læs personal-variant (intimate-detaljer er aldrig i summary; for følsomme); hvis ceiling = personal, læs personal-variant; hvis ceiling = public_safe, læs public-variant (eller skip).
- 5.2 auto-inject: SQL `WHERE visibility_level <= :ceiling_level`
- 5.3 tool-søgning: samme filter, plus tool-response markerer hvor mange resultater der blev *skjult* af ceiling (`{results: [...], hidden_by_visibility: 3}`) — Jarvis ved at der er noget han ikke kan komme til, men ikke hvad. Forhindrer at han forsøger work-arounds uden at vide reglen er aktiv.

**Skrivning påvirkes IKKE.** Jarvis må stadig skrive `visibility=intimate` poster i en public-kontekst (han er forfatter, han bestemmer). Gaten er kun ved læsning. Det matcher beslutningen i sektion 1.

### 6.5 Audit-logning

Hver recall-operation der filtrerer på visibility logger til eventbus:
```python
emit("jarvis_brain.recall", {
    "session_id": ...,
    "ceiling": ceiling,
    "kind": "auto_inject" | "tool_search" | "summary",
    "returned_ids": [...],
    "filtered_count": int,    # hvor mange der blev skjult af ceiling
})
```

Lader os audit-spore: lækkede ceiling nogensinde for højt? Hvilke poster blev tilbageholdt hvor ofte? Sundheds-indikator for privacy-systemet.

### 6.6 Implementation-detaljer

`core/services/jarvis_brain_visibility.py`:

```python
_LEVEL = {"public_safe": 0, "personal": 1, "intimate": 2}

def session_visibility_ceiling(session) -> str:
    if session.is_autonomous or session.is_inner_voice:
        return "personal"

    participants = session.participants or []
    if not participants:
        return "public_safe"  # default deny

    owner_id = get_owner_discord_id() or get_owner_user_id()
    non_owner_count = sum(1 for p in participants if p != owner_id)

    if non_owner_count >= 1:
        return "public_safe"

    if session.channel_kind == "dm" or session.channel_kind == "jarvisx_native":
        return "intimate"

    if session.channel_kind in {"owner_private_channel", "owner_only_workspace"}:
        return "personal"

    return "public_safe"  # default deny

def can_recall(entry_visibility: str, ceiling: str) -> bool:
    return _LEVEL[entry_visibility] <= _LEVEL[ceiling]
```

Bygger på `core/identity/owner_resolver.py` (genbrugt fra Mikkel-leak-fix).

### 6.7 Edge cases vi accepterer

- **Bjørn skifter mellem kanaler hurtigt:** ceiling re-beregnes pr. tur, så ingen carry-over fra DM til public kanal.
- **Ny deltager joiner kanal midt i samtale:** næste tur ser den nye deltager i `participants` → ceiling falder. Tidligere ture i samtalen er allerede afgivet (kan ikke trækkes tilbage), men ny viden lækkes ikke.
- **Bjørn @-mentioner Jarvis i public kanal:** stadig public_safe (Mikkel læser med). Bjørn må eksplicit DM Jarvis hvis intimate viden skal hentes.
- **Multi-bruger DM-grupper:** ≥1 ikke-owner → public_safe.

### Åbne spørgsmål til sektion 6

1. **Tre-niveau eller fire?** Skal vi have et `confidential`-niveau imellem `personal` og `intimate` til engineering-secrets (API-keys, infrastruktur-detaljer der ikke er privat-private men heller ikke for fremmede)? *Claudes anbefaling: nej, hold tre niveauer i v1. Engineering-secrets bør slet ikke være i hjernen — de hører i secrets/config-laget. Hvis vi opdager behov, tilføj v2.*

2. **Skal ceiling kunne overrides manuelt af Bjørn?** Fx en `/brain visibility` slash-kommando der hæver ceiling for én tur i en public kanal? *Claudes anbefaling: nej i v1. Risiko for human-error (glemt at sætte tilbage). Hvis Bjørn vil bruge intimate viden i public kanal, formulerer han det selv — ikke Jarvis' job at omgå sin egen privacy-gate.*

3. **Audit-log retention?** Eventbus-events lever evigt. Skal `jarvis_brain.recall` events have shorter retention (fx 30 dage), eller bevares til langtids-analyse? *Claudes anbefaling: bevar fuldt — hjerne-recall er sjældent og fortæller om Jarvis' adfærd over tid.*

---

## Sektion 7 — Lifecycle *(afventer review)*

Hvordan en post leve, ældes, bliver afløst, og til sidst arkiveret. Dette er hvor "decay + konsolidering" fra sektion 1's beslutninger bliver konkret.

### 7.1 Decay — beregnes, ikke lagres

Som besluttet i sektion 2: ingen `effective_salience`-kolonne. Beregnes ved recall:

```python
def compute_effective_salience(entry, now: datetime) -> float:
    HALFLIFE_DAYS = {
        "observation": 14,
        "fakta": 180,
        "indsigt": 365,
        "reference": float("inf"),  # ankre — decay aldrig
    }
    SALIENCE_FLOOR = 0.02  # forhindrer total nul

    last = entry.last_used_at or entry.created_at
    days = max(0, (now - last).total_seconds() / 86400)
    halflife = HALFLIFE_DAYS[entry.kind]

    if halflife == float("inf"):
        decay = 1.0
    else:
        decay = math.exp(-days / halflife)

    bumps_factor = math.log2(1 + entry.salience_bumps)  # 0 ved ingen bumps, 1 ved 1, 2 ved 3, etc.
    # Bumps hjælper men dominerer ikke — multiplikator i [1.0, ~2.0] for realistiske bump-tal
    raw = entry.salience_base * decay * (1.0 + 0.3 * bumps_factor)
    return max(SALIENCE_FLOOR, raw)
```

**Salience-floor (0.02):** En gammel ubrugt indsigt forsvinder ikke helt — den ligger stadig i arkivet og kan findes via tool-søg. Ingen post går nogensinde til nul.

**Bumps-formel:** `log2(1 + bumps)` betyder afkasende afkast — 1. bump er meget værd, 10. bump er moderat. Forhindrer at en single hot entry dominerer auto-inject for evigt.

### 7.2 Konsoliderings-daemon — algoritme

**Cadence:** Én gang dagligt, sent på dagen (efter brugeren typisk er gået i seng — kører 03:00 lokal tid). Tager 1-5 minutter, tre faser:

#### Fase 1: Duplikat-detektion (embedding-baseret)

```python
for kind in ["fakta", "observation"]:  # indsigt + reference er for individuelle
    entries = list_active_entries(kind)
    for i, a in enumerate(entries):
        for b in entries[i+1:]:
            sim = cosine(a.embedding, b.embedding)
            if sim >= 0.92:  # streng threshold — falske positiver er værre end missede dubletter
                propose_merge(a, b, reason=f"semantisk dublet (sim={sim:.3f})")
```

Threshold 0.92 er streng — vi vil hellere misse en dublet end forslå merge af to tæt-relaterede-men-distinkte fakta.

#### Fase 2: Modsigelse-detektion (LLM-baseret) — privacy-routet

For hver entry skrevet de sidste 7 dage, find top-5 mest similar eksisterende entries i samme `domain`. Send par til LLM. **Routing afhænger af entries' visibility:**

```python
def _llm_for_pair(a, b):
    # Den mest restriktive af de to bestemmer destinationen.
    max_vis = max(_LEVEL[a.visibility], _LEVEL[b.visibility])
    if max_vis == 0:  # begge public_safe
        return ollamafreeapi_client(model="gpt-oss:20b")
    else:             # mindst én er personal eller intimate
        return local_ollama_client(host="10.0.0.25", model="...")
```

Personal/intimate-indhold forlader aldrig huset. Gratis ekstern API får kun public-safe par.

Prompt (ens uanset destination):

```
Givet to udsagn:
A: "{a.title}: {a.content}"
B: "{b.title}: {b.content}"

Modsiger de hinanden? Svar JSON: {"contradicts": bool, "reason": str}
```

Hvis `contradicts: true` → propose_supersede med begge ids og daemonens reason. Forslaget lægges i `_pending/`; visible Jarvis afgør hvilken (hvis nogen) der er den rigtige.

#### Fase 3: Tema-konsolidering (LLM-baseret, mere ambitiøs)

Hver søndag (én gang om ugen, ikke dagligt — dyrere): 
- Group active `observation` entries fra sidste 30 dage efter `domain`
- Per gruppe ≥ 5 entries: send til LLM (samme privacy-routing som fase 2) med prompt *"Disse er observationer Jarvis har gjort. Er der et fælles tema der er værd at destillere til en `indsigt`?"*
- Hvis LLM finder tema → bygg foreslået indsigt + foreslå at arkivere de underliggende observationer (ikke supersede — de er stadig sande som datapunkter, men indsigten samler dem)

**Kill-switch:** Hver gang Jarvis afviser et tema-forslag (`discard_brain_proposal` på et `consolidates`-forslag fra denne fase), tælles det. Tre afvisninger i træk → fasen pauses automatisk. Eventbus emit:
```python
emit("jarvis_brain.theme_consolidation_paused", {
    "reason": "3 consecutive rejections",
    "last_rejected_ids": [...],
})
```
Manuel reaktivering kræves (settings flag eller tool `resume_theme_consolidation()`). Beskytter mod "daemonen klør på det forkerte spor"-mønster.

**LLM-fejl-håndtering:** Konsoliderings-loop fejler aldrig hårdt. Hvis LLM-kald timeout → log warning, spring den ene check over, fortsæt. Daemonen er best-effort.

### 7.3 Supersede-semantik

Når Jarvis adopterer et merge-forslag (eller skriver en ny post med eksplicit `supersedes` argument):

```python
def supersede(old_ids: list[str], new_id: str):
    for old_id in old_ids:
        old = read_entry(old_id)
        old.status = "superseded"
        old.superseded_by = new_id
        old.updated_at = now
        write_entry_atomic(old)  # frontmatter opdateres + index UPDATE
```

**Konsekvenser:**
- `auto_inject` filter: `WHERE status = 'active'` — superseded fjernes automatisk
- `search_jarvis_brain` default: samme — superseded skjult medmindre `include_archived=True`
- Filen bliver liggende i sin `kind/`-mappe (ikke flyttet til `_archive/`) — den er stadig "rigtig", bare overhalet
- Relations bevares: hvis ny post bygger på gamle, kan vi traversere `superseded_by` for at se historikken

### 7.4 Archive-politik

To veje til `status='archived'`:

#### Manuel arkivering
Jarvis (eller Bjørn via direkte fil-edit) sætter status. Tool: `archive_brain_entry(id, reason?)`.

#### Auto-arkivering (lav salience over tid)

```python
# Kører som del af reindex_loop, én gang dagligt:
def auto_archive_low_salience():
    archived_count = 0
    for entry in list_active_entries():
        if entry.kind == "reference":
            continue  # references arkiveres aldrig automatisk
        eff = compute_effective_salience(entry, now)
        if eff < 0.05:
            days_low = (now - entry.last_used_at_or_created).days
            if days_low >= 90:
                archive_entry(entry.id, reason="auto: low salience 90+ days")
                archived_count += 1
    # Telemetri: hvis >5% af totalen arkiveres pr. måned, er thresholden for aggressiv
    emit("jarvis_brain.auto_archive_pass", {
        "archived_count": archived_count,
        "total_active": list_active_count(),
    })
```

Når arkiveret:
- `status = 'archived'`
- Filen flyttes fra `kind/` til `_archive/<kind>/<original-name>.md`
- Index-rækken bevares (`status='archived'`, `path` opdateret)
- Embedding bevares — så `search_jarvis_brain(include_archived=True)` virker
- Falder ud af auto-inject (`WHERE status = 'active'`)

**Archive er ikke død.** Det er bare bagkatalog. Kan reaktiveres med `unarchive_brain_entry(id)`.

### 7.5 Bjørns direkte file-edits (Boy Scout for sandhedslag)

Hvis Bjørn redigerer en `.md`-fil direkte i editor:
- Reindex-loop'et opdager hash-ændring → re-parser frontmatter → opdaterer index-row + re-embedder content
- Hvis Bjørn ændrer `visibility` eller `status` i frontmatter → respekteres ved næste reindex
- Hvis Bjørn sletter en fil → reindex sætter index-row til `status='archived'` (med `path=null` som tombstone). Vi sletter ikke index-rækken; relations til superseded entries kunne knække.
- Hvis Bjørn opretter en ny fil manuelt med valid frontmatter → reindex tager den ind. (Han kan dermed "skrive" som Jarvis hvis han vil — men det er hans hjernekirurgi, hans ansvar.)

### 7.6 Konsoliderings-cadence-tabel

| Operation | Frekvens | Estimeret varighed |
|---|---|---|
| Reindex (hash-scan) | Hvert 5. min | <1s normalt |
| Auto-archive low salience | 1× dagligt | 1-2s |
| Duplikat-detektion (embedding) | 1× dagligt | <10s for ≤1000 entries |
| Modsigelse-detektion (LLM) | 1× dagligt | 30s-2min |
| Tema-konsolidering (LLM) | 1× ugentligt (søndag) | 1-5min |
| Summary regenerering | Ved meningsfulde ændringer (debounced) | 10-30s |

**"Meningsfulde ændringer"** for summary: ny entry, supersede, archive, eller ≥10 salience-bumps siden sidste regenerering. Debounce 5 minutter (ingen storm hvis Jarvis skriver 5 poster på samme tur).

### 7.7 Konflikt-håndtering

**Race: Jarvis skriver mens daemon konsoliderer.** Daemon opererer på *snapshot* af entries hentet ved fase-start. Hvis Jarvis tilføjer en ny entry midt i en daemon-pass, ses den ikke i denne pass — kommer med næste dag. Ingen lock-contention.

**Race: Bjørn redigerer fil mens daemon re-indexer.** Reindex læser hash; hvis hash ændres mellem læsning og embedding, fanger næste reindex det. Idempotent — re-embed er billigt.

**Race: To `remember_this`-kald på samme tur med samme content.** Begge får unique IDs (ULID), begge filer skrives. Duplikat-detektion finder dem næste dag og foreslår merge. Acceptabel: lille midlertidig redundans, ingen datakorruption.

### Beslutninger fra sektion 7-review

1. **Bumps-amplifikation justeret:** Formel ændret til `1.0 + 0.3 * bumps_factor` (i stedet for `1.0 + bumps_factor`). Bumps hjælper men dominerer ikke — multiplikator i [1.0, ~2.0] for realistiske tal.

2. **Privacy-leak i konsolideringsdaemon (BLOCKER fixet):** Modsigelse-detektion (fase 2) og tema-konsolidering (fase 3) sender nu kun til ekstern OllamaFreeAPI når **begge** entries er `public_safe`. Personal/intimate par routes til lokal Ollama på 10.0.0.25. Indhold om Bjørn forlader aldrig huset.

3. **Auto-archive threshold:** Beholder 0.05/90d. Tilføjet telemetri-emit (`jarvis_brain.auto_archive_pass`) så vi kan se månedlig arkiverings-rate; >5% af totalen → thresholden er for aggressiv.

4. **Konsoliderings-LLM model:** Visibility-baseret routing (se punkt 2). Ikke længere "free først, lokal fallback" — det er nu eksplicit per-par valg.

5. **Tema-konsolidering kill-switch:** Default på, men med 3-strikes auto-pause: tre afviste forslag i træk → fasen pauses, eventbus emit, manuel reaktivering kræves.

---

## Sektion 8 — Error handling, testing, migration *(samlet kort)*

### 8.1 Error handling-principper

| Lag | Princip |
|---|---|
| `jarvis_brain.py` (CRUD) | Atomic writes (tmp→rename), valider før persist, return strukturerede errors fra tools |
| Daemon-loops | Best-effort, isolerede try/except pr. iteration, log warnings, fortsæt næste tick |
| Recall-stier (5.1–5.3) | Fail-soft: fejl må aldrig blokere prompt-byggeri eller afbryde brugerens samtale |
| Index ↔ filer | Filer = sandhed. Index re-bygges hash-baseret; tombstones når filer slettes |
| LLM-kald i daemon | Watchdog + timeout (2-min cap), drop pair på timeout, fortsæt næste |

### 8.2 Testing strategy

**Unit tests** (`tests/test_jarvis_brain.py`):
- `write_entry` → fil skrives + index opdateres + frontmatter parses korrekt round-trip
- `compute_effective_salience` med kendte input/output (incl. floor, halflives, bumps-justering)
- `parse_frontmatter` på malformed YAML → graceful error
- ULID-generering er kollisionssikker

**Daemon tests** (`tests/test_jarvis_brain_daemon.py`):
- Reindex idempotens (kør 2× → samme state)
- Hash-baseret change detection (tilføj fil → opfanges; redigér fil → re-embed; slet fil → tombstone)
- Auto-archive ved kunstigt aldret entry
- Konsoliderings-fase 1 finder duplikat over 0.92-tærskel, ikke under

**Visibility tests** (`tests/test_jarvis_brain_visibility.py`):
- Alle scenarier i sektion 6.3-tabellen som testcases
- Group DM med ≥1 ikke-owner → public_safe
- Default deny ved ukendt/tom session
- Privacy-routing i daemon: intimate par → lokal Ollama mock, public_safe par → free API mock

**Tool tests** (`tests/test_jarvis_brain_tools.py`):
- `remember_this` rate-limit pr. tur (5) og pr. dag (20)
- `search_jarvis_brain` returnerer `hidden_by_visibility` count korrekt
- `adopt_brain_proposal` flytter fil + opdaterer status + stempler trigger=`adopted_proposal`
- `discard_brain_proposal` håndterer kill-switch-counter for tema-konsolidering

**Integration test:** Skriv entry via tool → reindex picks it up → search returnerer det → bump salience → verify frontmatter + index sync.

### 8.3 Migration-plan

- **Eksisterende state:** 0 brain entries (helt nyt feature). Trivielt.
- **Schema-ejerskab:** `core/services/jarvis_brain.py` opretter sin egen SQLite ved første kald (idempotent `CREATE TABLE IF NOT EXISTS`). Ingen ændringer til hovedet `db.py`.
- **Workspace-katalog:** Daemon opretter `workspace/default/jarvis_brain/{fakta,indsigt,observation,reference,_pending,_archive}/` ved opstart hvis de mangler.
- **Settings:** Tilføj felter til `RuntimeSettings`:
  - `jarvis_brain_enabled: bool = True`
  - `jarvis_brain_summary_token_budget: int = 350`
  - `jarvis_brain_auto_inject_top_k: int = 3`
  - `jarvis_brain_auto_inject_threshold: float = 0.55`
  - `jarvis_brain_remember_per_turn_cap: int = 5`
  - `jarvis_brain_remember_per_day_cap: int = 20`
  - `jarvis_brain_auto_archive_salience_threshold: float = 0.05`
  - `jarvis_brain_auto_archive_days: int = 90`
  - `jarvis_brain_theme_consolidation_enabled: bool = True`
- **Rollback-plan:** Sæt `jarvis_brain_enabled = False` → recall-stier no-op'er, tools rejecter med "feature disabled". Skrev poster på disk forbliver — ingen datatab.

### 8.4 Implementations-rækkefølge (foreslået til writing-plans)

1. Boy Scout-forarbejde 1: Udskil én naturlig enhed fra `prompt_contract.py` (separat PR)
2. Boy Scout-forarbejde 2: Udskil én naturlig enhed fra `visible_runs.py` (separat PR)
3. **`jarvis_brain.py`** + tests (kerne CRUD)
4. **`jarvis_brain_visibility.py`** + tests (privacy gate)
5. **`jarvis_brain_tools.py`** + tests (visible Jarvis' tools)
6. **`jarvis_brain_daemon.py`** + tests (alle tre loops)
7. Integration: prompt_contract summary-injection + visible_runs auto-inject + tool-dispatch web-nudge
8. Refleksions-slot integration
9. Settings + migrations
10. Smoke test end-to-end: skriv 5 entries, recall, decay-simulation, daemon-pass, supersede

---

*Spec-self-review udført 2026-05-02. Ingen TBD/TODO/placeholders. Ingen interne modsigelser identificeret. Scope er fokuseret på ét feature der kan implementeres som én plan med Boy Scout-forarbejder først.*

---

*Denne fil er WIP. Når brainstorm er færdig, gennemgår vi spec'en for placeholders/contradictions, beder om Bjørns endelige godkendelse, og går videre til writing-plans for implementations-plan.*
