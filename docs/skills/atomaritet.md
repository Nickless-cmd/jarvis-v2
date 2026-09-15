# Prompten bad om et værktøj der ikke lå i kaldet

**15/9-2026.** Codex leverede en analyse af hvorfor skill-gaten ikke virker.
Jeg efterprøvede den før jeg byggede.

## Hvad der holdt

Hovedpåstanden, og den er værre end beskrevet:

```
katalog: 471 værktøjer, heraf 24 med «skill» i navnet
«brug pdf skill»               → 48 værktøjer | skill-: INGEN
«lav en analyse af regnearket» → 48 værktøjer | skill-: INGEN
```

Ikke ét skill-værktøj overlevede beskæringen til de 48 i den synlige lane.
Alligevel skriver prompten ordret:

    skill_invoke("<navn>") og læs HELE SKILL.md før du skriver svaret

Jarvis gjorde derfor det rationelle: fandt filen med `explore` og læste
SKILL.md i hånden. Det var ikke ulydighed; det var den eneste vej han kunne se.

Selvmodsigelsen holdt også — hentet ud af den ægte prompt: «du skal ikke kalde
skill_suggest eller skill_gate først», mens decision-gaten kræver det modsatte.

Matcher-påstanden holdt og er skarpere end hans: han fik forkerte match, jeg
fik **ingenting**.

| forespørgsel | match |
|---|---|
| «brug pdf skill» | **intet** — og et PDF-skill findes |
| «lav en pdf rapport» | deep-research (0,65), composio-canvas-design (0,61) |
| «hjælp mig med excel» | excel-automation (0,79) ✓ |

## Hvad der ikke holdt

**«Ingen rigtig `skill_invoke` siden 4. september»** — der er tre, senest
14/9 kl. 18:00:50 (`git-advanced`). Men lasten er kun `{"name": "..."}` uden
run-id, så man kan ikke afgøre om de er ægte eller fra tests. Konklusionen var
for stærk; pointen om sporbarhed er til gengæld præcis rigtig — og er selve
grunden til at det ikke kan afgøres.

**«Døren er fjernet»** — nej. `load_more_tools` **er** blandt de 48, så
værktøjerne er nåelige. Prompten undlader bare at sige at man først skal hente
nøglen. Det gør rettelsen mindre end analysen lægger op til.

## Rettelsen: atomaritet

> Runtimen må aldrig instruere modellen i at kalde et værktøj, som ikke findes
> i den aktuelle request.

`skill_invoke` fæstnes nu i kappen **netop de ture hvor prompten nævner det** —
ikke altid. Uden et match nævner prompten ingen skills, og værktøjet ville være
uden et navn at give det: en spildt plads ud af 48.

Betingelsen er den samme som prompt-sektionens, og de **deler ét opslag**
(memoiseret på beskeden). To opslag kunne give to forskellige svar, og så ville
kontrakten kunne brydes uden at nogen af siderne var forkerte hver for sig.
Sektionen koster 101 ms; beskæreren får svaret gratis.

## Tredje gang mønsteret bider

Kommentaren over `REQUIRED_LAZY_TOOL_NAMES` beskriver præcis det samme for
`explore` den 6/9: «scope tillod det, kataloget nævnte det, prompten anbefalede
det — og pruneren fjernede det fra selve tool-arrayet».

## Og en fejl der skjulte rettelsen

Første forsøg virkede ikke, og målingen viste stadig brud. Årsagen var at
fæstnings-logikken lå i **to kopier i samme funktion** — én i den tidlige
udgang (`remaining <= 0`) og én efter Tier 2. Jeg ramte kun den ene, og det er
netop den tidlige der tages: Tier 1 sprænger kappen alene i cowork-scope.

To kopier af samme beslutning er dobbelt sandhed. Nu er der én, og en test
kræver at der bliver ved med at være det.

## Efter

```
forespørgsel                     prompt nævner   skill_invoke med
hjaelp mig med excel             True            True
lav en pdf rapport               True            True
skriv en rapport om kvartalet    True            True
docker container starter ikke    True            True
brug pdf skill                   False           False
hej                              False           False

kontraktbrud: 0
```

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| betingelsen fjernes | 6 røde |
| fæstnes altid (spilder en plads) | 4 røde |
| den tidlige udgang fæstner ikke | 7 røde |
| kappen håndhæves ikke | 6 røde |
| memoen deles ikke (to opslag) | 1 rød |
| fejl i matcheren fæstner alligevel | 1 rød |

## Udestår — og hvordan det måles

Atomariteten gør værktøjet **tilgængeligt**. Om det er **nok** kan kun afgøres
på rigtige ture. Kæden logges nu i sit manglende led:

    [skill-atomaritet] faestner skill_invoke — match: <navne>

Sammen med `cognitive_state.skill_invoked` giver det: matched → surfaced →
tilgængelig → invoked. Det led der stadig mangler er et **run-id** på
invokeringen; uden det kan en ægte invokering ikke skelnes fra en test.

Ikke rørt endnu, bevidst: matcheren (eksplicit navn resolver ikke),
selvmodsigelsen i prompten, og `skill_autosurface_enabled`. Ét greb ad gangen,
så det kan måles hvad der virkede.
