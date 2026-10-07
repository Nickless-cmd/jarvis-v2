---
status: foreslaaet
slags: arkitektur
dato: 2026-10-07
anmelder: opus
spec: ../../../specs/2026-10-07-agentorkestrering-og-subagenter.md
tidligere-gennemgang: 2026-10-07-jarvis-review-af-agentorkestrering.md
metode: to paastande talt i spec-kilden, to invarianter laest i den eksisterende kode paa main
---

# Review: agentorkestrering og subagenter

Status: foreslaaet

## Problem

Jarvis har gennemgået spec'en samme dag og efterprøvet §3's påstande mod koden.
Hans fire fund står ved magt, og jeg gentager dem ikke. Denne gennemgang dækker
to ting han ikke rørte, og ét forbehold om §11.1.

Begge fund har samme form, og det er den form der kostede mest i dag: **spec'en
beskriver en mekanisme der allerede findes, uden at nævne den.** Når en ny
mekanisme bygges ved siden af en gammel, er resultatet to sandheder — og den
ene er den man glemmer.

## Fund 1 — vække-stien findes allerede, og dens vigtigste regel står ikke i spec'en

§6 indfører en **ventekontrakt**: parenten gemmer konkrete `assignment_id`'er og
en vækkebetingelse før runslut, og et opfyldt ventepunkt giver «højst ét nyt
parentrun».

Målt i spec'en:

    ventekontrakt               5 forekomster
    in_flight_runs              0
    visible_run_recovery        0
    claim_due_recovery          0
    session_boot_reconciler     0

Den eksisterende maskine nævnes altså ikke én gang. Og den har præcis den
invariant spec'en forsøger at opnå — skrevet ned fordi den blev brudt:

> *Før kunne en fortsættelse starte to steder fra: den detachede kørsels egen
> afslutning og boot-forligeren. To veje til samme handling betyder enten to
> kørsler for samme opgave, eller ingen — afhængigt af hvem der nåede først.*
> — `visible_run_recovery_dispatcher.py`

Og prisen, målt i drift:

> *Målt 17/9-2026 i produktionen: den samme opgave blev genoptaget TRE gange —
> 21:48:12, 21:50:13, 21:52:14 — og hver gang svarede Jarvis færdigt på det
> samme spørgsmål. Afstanden var præcis lejemålets 120 sekunder. Tre betalte
> ture på ét spørgsmål.* — `visible_runs_sections/detached_run.py`

Ventekontrakten ville være **en tredje vej** ind i den samme handling. Det er
ikke et argument mod ventekontrakten — §6's formulering er bedre end den
nuværende, fordi den er eksplicit og varig. Det er et argument for at spec'en
skal sige hvad der sker med den gamle: afløser ventekontrakten
`claim_due_recovery`, eller lever de side om side? Lever de side om side, skal
spec'en sige hvem der vinder når begge mener de må vække.

**Konkret:** §11's leverance B («kobling af inbox til aktivt og inaktivt
synligt run») er stedet. Den bør nævne `in_flight_runs` og
`visible_run_recovery_dispatcher` ved navn og afgøre migreringen, præcis som
Jarvis noterede at §4's fire identiteter er en migrering af `agent_registry`,
`agent_runs`, `agent_messages` og `session_inbox` — ikke et grønt felt.

## Fund 2 — «supervisoren» er ikke én proces, og det er allerede gået galt

§6 og §9 lægger meget på en supervisor: den opretter terminalbeskeden efter
crash, følger op på parkerede runs, scanner for udløbne leases og sammenholder
DB, transcript, artefakter og klientkvitteringer.

Spec'en siger tre gange «supervisoren» og aldrig **hvilken proces** det er.

`jarvis-api` og `jarvis-runtime` kører samme kode i hver sin proces. Det er ikke
en detalje: den eksisterende dispatcher har en regel om netop det, som den
første linje i sin kontrakt —

> *Kun API-processen dispatcher. Runtime-processen må gerne forlige og skrive,
> men den må ikke starte en synlig fortsættelse; ellers ville begge processer
> gøre det efter en genstart.*

Og `state_store.med_laas` har sin egen begrundelse af samme slag: *«jarvis-api
og jarvis-runtime kører samme kode i hver sin proces og deler disse filer.»*

Jeg ramte det selv i dag. Jeg lagde en besked→run-kobling i et kort i
hukommelsen med den begrundelse at «begge ender er i api-processen». Målt
bagefter på en autonom kørsel: beskeden bar intet run-id, fordi autonome runs
persisteres i `jarvis-runtime` mens snapshottet bygges i `jarvis-api`. Jeg havde
skrevet begrundelsen ned i en docstring, og den var forkert.

**Konkret:** §9 bør navngive supervisorens proces, som dispatcheren gør. Og
§11.1's race-tests bør køre to supervisorer samtidig — ikke to workers alene.
Invarianten «ét gyldigt lease-ejerskab» testes i dag mellem workers; den skal
også testes mellem to supervisorer der ser samme udløbne lease.

## Forbehold til §11.1 — en test kan bestå uden at måle noget

§11.1 slutter stærkt: *«Ingen E2E-test må nøjes med at se en klikbar knap eller
en HTTP 200.»* Den regel rammer én fejlklasse. Jeg fandt tre tilfælde af en
anden i dag, og ingen af dem ville være fanget af den sætning:

* **En test der kun kan bekræfte et fravær.** `test_background_resume`s korte
  sag påstår at der IKKE sendes en alarm. Da sømmen flyttede fra
  `ntfy_gateway` til `alarm_ud`, blev den ved med at bestå — den lyttede det
  forkerte sted, og et fravær ser ens ud uanset hvor man lytter.
* **En test der fanger sin egen forudsætning.** To mermaid-tests påstod at
  dårlig syntaks giver en læsbar fejl. Uden chromium rejser renderen samme
  fejltype med ordet «mermaid» i — så de var grønne af den forkerte grund.
* **En test af funktionen, ikke af ledningen.** Mine egne ni tests for en
  rettelse bestod alle, da jeg fjernede kaldet fra persist-stien. Koden var
  rigtig; ingen kaldte den.

Det er den hyppigste fejlform i dette repo, og den er farligst netop i et
agent-system: de fleste invarianter i §11.1 er **negative** — «ingen tavst tabt
accepteret besked», «ingen dobbelt fjernskrivning», «intet halvt barn». En test
af et fravær der lytter det forkerte sted er grøn for evigt.

**Konkret forslag til §11.1:** hver negativ invariant skal ledsages af en
mutation der får den til at fejle. Ikke som en separat mutations-kørsel, men som
et krav til testen: *den der skriver «ingen dobbelt fjernskrivning» skal vise at
testen fejler når man fjerner idempotens-nøglen.* Ellers måler den sin egen
opsætning.

## Det jeg er enig med Jarvis i

Hans fund 2 — at `route_agent_task()` ikke kender ejeren — er det der skal
rettes først, og af den grund han giver: ellers bygges fallback-logikken oven på
en funktion der ikke kan se hvem den arbejder for. §7.1's ejerafhængige fallback
er spec'ens skarpeste afsnit, og den hviler helt på det ene argument.

Hans fund 3 om fitnessvagten der sluger fejl er samme form som resten af dagen:
en tavs fejl bliver til en værdi man ikke kan skelne fra et lovligt svar.

Og hans prioritering af fund 1 er rigtig: en ubenyttet rute skal besluttes, ikke
patches. At fjerne `agent_loop.py` er en beslutning for Bjørn.

## Beslutning

Spec'en er moden til implementeringsplan — jeg er enig med Jarvis dér, og mine
to fund blokerer ikke leverance A.

Men to spoergsmaal skal afgoeres foer de leverancer der roerer dem, og de hoerer
i §12 frem for at blive opdaget under implementering:

* **Foer leverance B:** afloeser ventekontrakten `claim_due_recovery`, eller
  lever de side om side — og hvem vinder naar begge mener de maa vaekke?
* **Foer leverance C:** hvilken proces ejer supervisoren, og hvad forhindrer to
  i at tage samme udloebne lease?

Og ét krav til §11.1: hver negativ invariant skal kunne vises at fejle.

## Overvejede alternativer

* **Kun at læse spec'en og kommentere formen.** Fravalgt: Jarvis havde allerede
  efterprøvet §3, og en gennemgang der ikke måler noget tilføjer intet. De to
  fund her kommer begge fra at tælle i kilden, ikke fra at læse spec'en.
* **At foreslå ventekontrakten droppet til fordel for den eksisterende
  genoptagelse.** Fravalgt: §6's formulering ER bedre — eksplicit, varig, med
  navngivne betingelser. Problemet er ikke mekanismen, det er at spec'en ikke
  siger hvad der sker med den gamle.
* **At rette de to ting selv.** Fravalgt: begge er specvalg med
  produktkonsekvenser, ikke fejl i kode. §12 er stedet.

## Konsekvenser

To tilføjelser til §12's liste over åbne valg:

1. Afløser ventekontrakten `claim_due_recovery`, eller lever de side om side —
   og hvem vinder når begge mener de må vække?
2. Hvilken proces ejer supervisoren, og hvad forhindrer to i at tage samme
   udløbne lease?

Og ét til §11.1: hver negativ invariant skal kunne vises at fejle.

Ingen af dem blokerer leverance A. Spørgsmål 1 skal afgøres før B, spørgsmål 2
før C.
