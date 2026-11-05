# Godkendelses-kort: hvor mange går reelt tabt? (målt 5/11-2026)

Dette er en MÅLE-note. Der er ikke ændret kode.

## Konklusion

Antallet af kort der kan dokumenteres som tabt er **lille: 8 af 2.349 (0,34 %) på 30 dage**. Målingen kan ikke se ægte «kortet blev aldrig tegnet», kun «kortet blev aldrig besvaret». Anbefalingen er derfor **ikke at bygge en ny kø**, men at gøre gaten sessions-bevidst (se nederst).

## To rettelser til opgavens præmis

1. **Tabellen i opgaven er den forkerte.** `tool_intent_approval_requests` har 18 rækker i alt, nyeste fra 2026-08-17, altså **0 rækker de sidste 30 dage**. De levende kort bor i `approval_claims` (kolonner `kind`, `state`, `session_id`, `created_at`, `expires_at`, `decided_at`). Det stemmer med at `/chat/approvals/pending` svarer fra `visible_runs.godkendelser_nu()` via `approval_runtime.pending_for_owner`, ikke fra `tool_intent_approval_requests`.
2. **Gaten er allerede delvist rettet.** `StreamContext.tsx:589` (`if (pendingApproval || !config.apiBaseUrl) return`) står endnu, men der er kommet en udløbs-timer ved `StreamContext.tsx:633`. Den rydder `pendingApproval` ved `expires_at + 6 s`, hvorefter polling genoptages. Et uset kort fra en anden session blokerer altså ikke for evigt. Det blokerer indtil det udløber (`DEFAULT_TTL_S`, målt til 3600 s på de udløbne rækker).

   `GodkendelsesKort.tsx:28` har stadig session-filteret (`p.sessionId !== sessionId`). Mekanismen er dermed intakt: ét kort fra en anden samtale skjuler alle senere kort, indtil det første løses eller udløber.

## Målinger

DB: `/home/bs/.jarvis-v2/state/jarvis.db`, åbnet read-only. Vindue: `created_at >= datetime('now','-30 days')`. Kørt 5/11-2026.

| Mål | Tal |
|---|---|
| `approval_claims`, `kind='approval'`, 30 dage | 2.349 |
| ...heraf `completed` | 2.335 |
| ...heraf `expired` (aldrig besvaret) | **8** |
| ...heraf `denied` / `failed` / `outcome_unknown` | 2 / 2 / 2 |
| `kind='auto'` (intet kort) | 3.079 |
| Samtidigt ventende kort i FORSKELLIGE sessioner | **6 par**, hver overlappende 1 til 10 s |
| `chat_messages` `role='approval_request'` 30 dage (persisteres først fra 31/10) | 256 |
| `agent_approvals` i alt | 13 (9 cancelled, 4 consumed, ingen i `pending`) |

Svartid fra `created_at` til `decided_at` (2.341 rækker med `decided_at`):

| Median | p90 | p99 | Max |
|---|---|---|---|
| 1,6 s | 5,4 s | 310 s | 2.741 s |

Rækker over 5 s: 251. Over 30 s: 73. Over 60 s: 56. Over 300 s: 24. Over 900 s: 10.

De 8 udløbne fordeler sig på kun **2 sessioner**: `chat-f6b595cd…` (1 kort, 16/10) og `chat-0b84af79…` (7 kort, 26-27/10, med ca. 5 min mellem de første fire). Mønsteret ligner et løb uden nogen foran skærmen, ikke et kort der blev skjult. Ingen af de 8 har en `approval_request`-række i `chat_messages`, fordi den persistering først kom 31/10. Jeg kan derfor ikke afgøre ud fra rækkerne om Desk var åben.

### Kommandoer

```python
# /home/bs/miniconda3/envs/ai/bin/python3 -I
c = sqlite3.connect('file:/home/bs/.jarvis-v2/state/jarvis.db?mode=ro', uri=True)
W = "created_at>=datetime('now','-30 days')"
c.execute(f"select kind,state,count(*) from approval_claims where {W} group by 1,2 order by 3 desc")
c.execute(f"select state,count(*),round(avg((julianday(expires_at)-julianday(created_at))*86400)) "
          f"from approval_claims where {W} and state like '%expir%' group by 1")
c.execute("select approval_id,state,session_id,created_at,decided_at,expires_at from approval_claims "
          f"where kind='approval' and {W}")
# svartid = decided_at - created_at. Overlap = par af (created_at, decided_at eller expires_at)-intervaller
# med forskellig session_id, der overlapper i tid.
c.execute("select count(*) from tool_intent_approval_requests where requested_at>=datetime('now','-30 days')")  # = 0
```

## Hvad målingen IKKE kan afgøre

- **Om et kort blev tegnet.** Serveren registrerer kun at et kort blev besvaret eller udløb, ikke at en klient viste det. De 251 svar over 5 s og de 24 over 300 s kan være Bjørn der tænkte sig om, eller kort der lå skjult. Det kan kun skilles med klient-telemetri («kort modtaget» og «kort tegnet»), som ikke findes.
- **Bjørns symptomer «chat mode» og «efter app genstart».** Genstart og notifikationer er ikke dækket af disse tal, og notifikationsvejen er ikke målt her.
- **`composer_choices`-spørgsmålet** (341 accepteret / 478 eget / 250 vist). Det er ikke afklaret i denne note og er ikke rørt.

## Anbefaling

**Byg ikke en ny kø.** 8 udløbne af 2.349 (0,34 %), fordelt på 2 sessioner, og kun 6 tilfælde af samtidige kort på tværs af sessioner (alle højst 10 s), retfærdiggør ikke et nyt subsystem. Den eksisterende genoprettelses-rute (`GET /chat/approvals/pending`) er tilstrækkelig, fordi den svarer fra den levende tilstand.

Hullet er reelt, men smalt: ét kort fra session B skjuler et kort i session A, indtil det første løses eller udløber efter op til 1 time. Overlap-tallet viser at det i praksis har været sjældent. Hvis der skal rettes, så den mindste ændring:

1. Behold `pendingApproval`-gaten i `StreamContext.tsx:589`, men gør den sessions-bevidst: fortsæt med at polle (med de eksisterende `maaPolle`-loft på 20 s) når `pendingApproval.sessionId` ikke er den session brugeren står i. Så kan et kort for den aktuelle session findes bag et fremmed kort.
2. Eller lad `/chat/approvals/pending` tage `session_id` og returnere den aktuelle sessions kort først, ellers nyeste.
3. Test: en der fejler på nuværende adfærd. Sæt `pendingApproval` til en anden session, lad serveren returnere et kort for den aktuelle, og forvent at det tegnes.

Før en eventuel ændring bør der tilføjes et tæller-event «kort modtaget af klient, ikke tegnet pga. session-mismatch». Så kan rate måles frem for at udledes.
