# Flaggede sideopgaver over Desk-chatten

## Formål

Jarvis kan allerede flagge sideopgaver i `core.services.side_tasks`. Bjørn skal se dem over chatten i Desk, uanset hvilken samtale der er åben, indtil han eller Jarvis markerer dem færdige eller fjerner dem. Flagning starter ikke arbejde automatisk.

## Sandhed og status

`side_tasks` i runtime state er eneste sandhedskilde. En opgave gemmer titel, selvstændig prompt, kort beskrivelse, oprindelig session, oprettelsestid og status. `pending` og `activated` er åbne og vises i Desk. `completed` og `dismissed` er terminale og vises ikke længere. Terminale opgaver kan ikke genåbnes gennem denne funktion. Eksisterende data og værktøjsnavne bevares.

Jarvis' eksisterende `dismiss_side_task` kan tage `decision=completed` eller `decision=dismissed`; standarden forbliver `dismissed` for gamle kald. Derved kan Jarvis afslutte en opgave uden at ændre det store `simple_tools.py`-register. `list_side_tasks` og promptens sideopgaveafsnit viser alle åbne opgaver.

## API og adgang

`GET /cowork/side-tasks` returnerer åbne sideopgaver. `POST /cowork/side-tasks/{id}/status` tager `status` lig `completed` eller `dismissed` og returnerer service-resultatet. Ruterne bruger `_role_owner()` og afviser andre roller med 403, da opgavernes prompt kan indeholde privat kontekst. Blokerende state-adgang køres via `asyncio.to_thread`.

## Desk

En kompakt, fast del af ChatView lige under headeren viser antal og hver åben opgaves titel og korte beskrivelse. Detaljerne kan foldes ud. Hver række har **Færdig** og **Fjern**. Listen vises også i tom/ny chat og har begrænset højde med egen rulning, så den ikke skubber chatten væk. Desk læser fra API'et ved montering og hvert sjette sekund. Efter en vellykket handling fjernes rækken straks og data genhentes. Ved netværksfejl bevares senest kendte liste, og en mislykket handling vises som fejl uden at fjerne opgaven.

Styling bor i en ny CSS-fil; `app.css` er over Boy Scout-grænsen. Ingen lokale kopier af opgavernes status eller nye databaser indføres.

## Verifikation

Test service-overgange, åbne/terminale lister, gamle værktøjskald, API-adgang, Desk-kald, visning i både tom og aktiv chat samt handlingernes succes- og fejlsti. Kør Desk-testpakken, rendererbygning og relevante Python-tests. Se UI med lokale testdata i et skrivebordsvindue.
