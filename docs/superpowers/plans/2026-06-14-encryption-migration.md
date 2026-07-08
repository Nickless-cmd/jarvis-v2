---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# §16 Kryptering — encrypt-on-write migration (Lag 3, DATA-TOUCHING)

> Spec §16. **ADVARSEL:** denne fase rører ægte bruger-data. En key-management- eller
> migrations-fejl = UIGENKALDELIGT data-tab. Følg rækværket nøje. Kør ALDRIG forhastet.

## Forudsætninger (skal være opfyldt FØR migration)
- [ ] §16 Lag 1 (encryption.py) + Lag 2 (keyring_store KEK/DEK) committet + testet ✓
- [ ] **Verificeret, gendannelig backup** af HELE `~/.jarvis-v2/` (workspaces + DB +
      config) — test at backup'en kan gendannes, ikke bare at den findes
- [ ] KEK genereret + backet op SEPARAT (uden KEK er krypteret data tabt for evigt)
- [ ] Dry-run-flag: migration kan køre i "rapportér hvad jeg VILLE gøre"-mode først

## Princip: kun ANDRE brugeres data krypteres (§16.2)
- Owner (Bjørn) workspace = **plaintext** (urørt). Migration springer owner over.
- Member-workspaces, member-chat-historik, private brain-records = krypteres.
- I dag findes INGEN member-data (kun Bjørn) → migration er reelt en no-op nu, men
  koden skal være klar så NYE member-data krypteres-ved-oprettelse.

## Strategi: krypter-ved-skrivning (ikke big-bang re-encrypt)
Hellere end at masse-kryptere eksisterende filer (risikabelt), hook ind ved
SKRIVNING for member-workspaces, så data fødes krypteret. Eksisterende owner-data
forbliver plaintext (korrekt). Member-data opstår først fremover → fødes krypteret.

### Task 3.1: workspace-fil I/O wrapper
- `core/services/workspace_crypto.py`: `read_workspace_file(path, user_id)` /
  `write_workspace_file(path, content, user_id)`. Hvis user er non-owner → krypter
  (.enc) med get_user_key(user_id); ellers plaintext. Dekryptér KUN i memory (§16.5).
- Test: owner→plaintext-fil; member→.enc-fil + roundtrip; forkert user kan ikke læse.

### Task 3.2: wire memory-laget (MEMORY.md/USER.md læs/skriv)
- Find de centrale workspace-fil-sites (workspace_paths/memory-services) og rut dem
  gennem workspace_crypto. ÉN sti ad gangen, test efter hver. Owner-sti UÆNDRET.

### Task 3.3: chat-historik (DB) per-session kryptering
- Krypter `chat_messages.content` for member-sessioner ved skrivning; dekryptér ved
  læsning i-session. Owner-sessioner urørt. Migration-kolonne: `encrypted BOOLEAN`.

### Task 3.4: private brain-records
- Brain-records krypteres per §16.2 (Jarvis' indre verden, krypteret selv for owner
  i andre sessioner). Kræver Jarvis' egen "session-key".

### Task 3.5: GDPR-sletning ende-til-ende
- user-delete → keyring_store.delete_user_key → krypterede filer ulæselige → slet filer.
- Test: efter delete kan data IKKE dekrypteres.

## Rækværk pr. task
1. Dry-run først (rapportér, rør intet).
2. Kør på en KOPI af workspaces/ før den ægte.
3. Verificér roundtrip (krypter → dekryptér → identisk) FØR originalen slettes.
4. Behold plaintext-backup til migrationen er bekræftet stabil i et døgn.

## Checkpoints
- Efter 3.1: wrapper testet på kopi-data, ingen produktionsdata rørt.
- Efter 3.2: member-workspace-skrivning krypteret, owner verificeret uændret.
- Før 3.3/3.4: ny backup + Bjørn-godkendelse (DB + brain er de mest kritiske).
