# Code mode backend: sandbox- og genstartsstatus (2026-11-22)

## Sandboxmåling

Målt i assignment-worktree med den samme Python-runtime som testene:

```text
enabled_default=true
available=true
runnable=false
reason=bwrap: No permissions to create a new namespace, likely because the kernel does not allow non-privileged user namespaces.
```

En reel kommando blev derefter kørt med argv fra
`core.services.bash_sandbox.wrap_bwrap(...)`. Den returnerede exitkode 1 med
samme namespace-fejl og producerede intet stdout. `enforcement(...)` meldte:

```json
{"requested": true, "actual": false, "available": true, "enabled": true, "honored": false}
```

Beslutning: sessionsvejen er ikke ændret. En sikker udvidelse skal starte hele
`bash_session`-daemonen inde i bwrap, bevare dens tilsigtede levetid på tværs af
API-genstarter og kunne bevise via daemonens IPC, at en allerede kørende daemon
har samme confinement-policy som den aktuelle konfiguration. At pakke kun nye
sessioner eller kun daemon-spawnet ville efterlade eksisterende daemoner
uindespærrede og skabe præcis den halve dækning modulets docstring advarer imod.
Kernel/user-namespace-fejlen skal desuden løses, før laget kan håndhæves her.

## Cloud-/Task-genoptagelse

Der er to eksisterende, varige spor:

1. Synlige runs journalføres i `in_flight_runs`; API-opstart kører
   `session_boot_reconciler`, og `visible_run_recovery_dispatcher` tager et
   atomisk recovery-claim, fornyer lease og starter en ny detached fortsættelse.
   Runtime-processen afviser selv at starte dispatcheren.
2. Agent assignments har DB-leases med fencing-token. `supervise()` kalder
   `reconcile_expired_leases()`: et forsøg uden åbent tool-kald kan køres igen
   (højst to sikre forsøg); et startet, uafsluttet tool-kald bliver
   `outcome_unknown`/`waiting` og genudføres ikke blindt. Ved API-opstart bliver
   legacy-agenter med `persistent=true` requeued, mens ikke-persistente markeres
   failed.

Det der ikke findes, er transparent genoptagelse af den samme modelproces midt
i en tur. Mekanikken starter et nyt forsøg/nyt synligt run fra den durable
opgave og kontekst; ved et muligt side-effect kræves menneskelig afgørelse.
Det er den sikre grænse og bør ikke erstattes af automatisk replay.
