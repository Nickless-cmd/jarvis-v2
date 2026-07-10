# Security Predicates

> Auto-genereret fra `core/tools/security_predicates.py`. Rediger IKKE i hånden — ret registry'en.

Nummererede tool-sikkerheds-checks. Et deny logges med sit check-id (fx "check #14: dd-disk-write").

| # | Navn | Type | Beslutning | Hvorfor |
|---|------|------|-----------|---------|
| 1 | `curl-pipe-bash` | bash | blocked | Fjern-kode hentet og eksekveret direkte |
| 2 | `wget-pipe-bash` | bash | blocked | Fjern-kode hentet og eksekveret direkte |
| 3 | `sudo-rm` | bash | blocked | Privilegeret sletning |
| 4 | `rm` | bash | destructive | Filsletning |
| 5 | `rm-rf` | bash | destructive | Rekursiv tvungen sletning |
| 6 | `git-reset-hard` | bash | destructive | Kasserer ucommittede ændringer |
| 7 | `git-clean` | bash | destructive | Sletter untracked filer |
| 8 | `git-push-force` | bash | destructive | Overskriver remote-historik |
| 9 | `git-push-f` | bash | destructive | Overskriver remote-historik |
| 10 | `drop-table` | bash | destructive | Sletter database-tabel |
| 11 | `drop-database` | bash | destructive | Sletter hel database |
| 12 | `truncate` | bash | destructive | Tømmer tabel/fil |
| 13 | `mkfs` | bash | destructive | Formaterer filsystem |
| 14 | `dd-disk-write` | bash | destructive | Rå disk-skrivning |
| 15 | `fork-bomb` | bash | destructive | Fork-bomb (resurs-udmattelse) |
| 16 | `shutdown` | bash | destructive | Lukker maskinen ned |
| 17 | `reboot` | bash | destructive | Genstarter maskinen |
| 18 | `poweroff` | bash | destructive | Slukker maskinen |
| 19 | `git-internal` | write | blocked | Skriv i git-interne data |
| 20 | `env-file` | write | blocked | Skriv i miljø-/secret-fil |
| 21 | `credentials` | write | blocked | Skriv i credential-fil |
| 22 | `ssh-keys` | write | blocked | Skriv i SSH-nøgler |
| 23 | `node-modules` | write | blocked | Skriv i dependency-mappe |
| 24 | `pycache` | write | blocked | Skriv i bytecode-cache |
