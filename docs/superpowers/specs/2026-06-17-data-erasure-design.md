# Data-sletning (GDPR Art. 17 "ret til at blive glemt") — Design

**Dato:** 2026-06-17 · **Status:** design-only (bygges i dagslys — sletning er irreversibel)
**Forfatter:** Claude · Grundlag: [[project_jarvis_desk_roadmap_analysis]], roadmap #2c

---

## 1. Princip

Sletning er **irreversibel** og må ALDRIG hastes eller auto-køres. Derfor: design nu,
byg med klart hoved, test mod en wegkast-bruger før den røres på en ægte konto.
To-trins eksplicit bekræftelse + grace-periode. Hviler på eksisterende byggesten —
intet skal opfindes fra bunden.

## 2. Eksisterende byggesten (verificeret 17. jun)

| Byggesten | Hvad den gør |
|---|---|
| `user_db.delete_user(uid, mode="soft"\|"hard", actor)` | Soft = markér slettet (beholdes); hard = fjern række. Har allerede audit. |
| `connectors.delete_for_user(uid, connector_id)` | Revoke hos provider + lokal token-wipe (GDPR) |
| `oauth_store.revoke_token(uid, provider)` | Wipe ét providers token |
| `keyring_store.delete_user_key(uid)` | Slet brugerens krypteringsnøgle |
| per-bruger `user_id`-kolonner (SECURITY #154) | Gør per-bruger DELETE muligt på tværs af tabeller |
| `workspace_dir(uid)` | Brugerens krypterede workspace-mappe |

## 3. Omfang — hvad slettes

| Data | Handling | Kilde |
|---|---|---|
| Connector-tokens (alle) | `delete_for_user` pr. connector → revoke + wipe | oauth_store |
| Krypteringsnøgle | `delete_user_key(uid)` → resten bliver ulæselig | keyring_store |
| Chat/sessions, hukommelse, noter, sensory, autonomy | `DELETE WHERE user_id=?` pr. tabel | db (#154-scope) |
| Workspace-mappe | rekursiv slet af `workspace_dir(uid)` | filesystem |
| Bruger-række | `delete_user(mode)` | user_db + users.json |

**Kritisk:** Nøgle-sletning FØR DB-sletning er en billig ekstra garanti — selv hvis en
række overlever, er dens krypterede felter uoprettelige uden nøglen.

## 4. To tilstande

- **Soft (standard, omstødelig i grace-periode):** markér `deleted_at`, revoke tokens
  straks, men behold krypteret data i **30 dage** → kan fortrydes. Login spærres.
- **Hard (efter grace ELLER eksplicit "slet permanent nu"):** fysisk DELETE + nøgle-wipe
  + workspace-mappe slettet. Uoprettelig.

En daglig cron promoverer soft→hard når `deleted_at` > 30 dage.

## 5. Orkestrering (ny: `core/services/data_erasure.py`)

```
erase_user(uid, *, mode, actor) -> dict:
  1. assert uid != ""            # ejeren kan ikke self-slettes via denne vej
  2. audit("erase.start", uid, mode, actor)
  3. for c in connectors.list_for_user(uid): delete_for_user(uid, c.id)   # revoke straks
  4. if mode == "hard":
       - for tbl in PER_USER_TABLES: DELETE WHERE user_id=uid
       - shutil.rmtree(workspace_dir(uid), ignore_errors=True)
       - keyring_store.delete_user_key(uid)
  5. user_db.delete_user(uid, mode=mode, actor=actor)
  6. audit("erase.done", uid, mode)  # audit-rækken selv overlever (lovkrav)
```

`PER_USER_TABLES` = eksplicit liste (ikke auto-scan) — gennemgås manuelt mod #154-listen,
så vi aldrig sletter for lidt eller rammer delt data.

## 6. API + UX

- **Bruger (self):** `POST /api/account/erase {confirm: "<email>", mode: "soft"}`
  — kræver at brugeren skriver sin egen email som bekræftelse. Default soft.
  Desk: rød "Slet min konto og data"-knap i Data&privatliv → 2-trins dialog
  ("Skriv din email for at bekræfte") → "Slettet. Du logges ud nu."
- **Admin (owner):** kan hard-slette en member + force-promote soft→hard.
- **Owner self-delete:** BLOKERET (du kan ikke slette systemets ejer via app'en).

## 7. Sikkerhed / edge cases

- Email-bekræftelse forhindrer fejlklik + CSRF-lignende uheld.
- Kører i baggrundstråd (kan tage tid); returnér straks "i gang".
- Idempotent: kør igen på en allerede-slettet bruger = no-op, ikke fejl.
- Audit-rækker (`erase.start/done`) slettes ALDRIG — lovkrav om sporbarhed.
- Google: tokens revokes i trin 3 uanset mode (data hos Google stoppes straks).

## 8. Test-plan (før live)

1. Opret wegkast-bruger, fyld sessions/noter/connector-token.
2. `erase_user(soft)` → login spærret, data stadig krypteret til stede, token revoked.
3. Promote→hard → rækker væk, workspace-mappe væk, nøgle væk.
4. Isolation: en ANDEN brugers data urørt (assert count uændret).
5. Idempotens + owner-block (`erase_user("")` → afvist).

## 9. Hvad bygges IKKE nu

Selve eksekveringen. Dette er design. Byg trin for trin i dagslys med wegkast-bruger først.
