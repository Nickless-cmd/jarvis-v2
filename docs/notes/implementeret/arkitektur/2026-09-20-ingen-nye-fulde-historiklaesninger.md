# Note: ingen nye synkrone læsninger af en hel samtale-historik

Status: implementeret

## Problem

`get_chat_session(session_id)` henter hele beskedhistorikken i ét synkront
kald. Det var den funktion der gjorde Bjørns og min samtale til en nyttelast
på 21,5 MB, og formen inviterer til det: kalderen beder om «samtalen» og får
alt hvad der nogensinde er sagt.

Målt 20/9-2026: **45 kaldesteder. 14 af dem læser hele historikken for at
bruge ét metadata-felt** — en titel, en ejer, et workspace. De betaler for
hver eneste besked i samtalen for at læse ét felt.

Jeg gjorde i forvejen serialiseringen billigere i dag (21,5 → 11,7 MB). Det
fjernede omkostningen, ikke afhængigheden. Så længe en ny hjælpefunktion kan
skrive `get_chat_session(sid)` for at få fat i en titel, vokser tallet igen.

## Beslutning

Eksisterende kaldere må blive; nye er forbudt.
`scripts/verify_history_reads.py` fastfryser de 44 kaldesteder pr. fil og
afviser flere. Funktionens egen docstring siger det samme, så man ikke skal
ramme hooken for at få det at vide.

Nye domæner designer deres felter og deres PROJEKTION sammen, så tilstanden
kan genskabes uden at læse historikken igennem. De bundne læsere findes
allerede: `get_session_owner`, `session_version`,
`recent_chat_session_messages(limit=N)`,
`chat_session_messages_since_last_compact`.

Skal noget ægte bruge hele historikken — en fork, en eksport — er det stadig
lovligt. Men så skal det skrives ind i grundlinjen som et bevidst valg i
stedet for at opstå ved et uheld.

## Overvejede alternativer

**Migrere alle 45 kaldesteder nu.** Afvist. DeepSeek-harness traf samme valg
9/9-2026 og formulerede hvorfor: at forhindre nye afhængigheder afgrænser
det resterende arbejde uden at gøre hver eneste eksisterende kalder til en
del af samme ændring. De 14 metadata-læsere kan konverteres enkeltvis.

**Kun advare i docstringen.** Afvist. En docstring standser ikke en agent
der har travlt, og vi har målt at tallet ER vokset til 45 uden at nogen
bemærkede det.

**Gøre funktionen doven, så beskederne først hentes ved opslag.** Fristende,
men det flytter problemet ind i et objekt hvor det er sværere at se. En
kalder der itererer over `["messages"]` ville stadig hente alt, og nu uden
at det stod i kaldet.

**Fjerne funktionen helt.** Afvist nu: 31 af kaldene rører faktisk
beskederne, og en tvungen omskrivning af dem på én gang er præcis den slags
stor refaktor der aldrig bliver gjort.

## Konsekvenser

Tallet kan kun falde. Når et kaldested konverteres, skrives det nye tal ind
med `--skriv-grundlinje`.

Vagten beviser at der ikke kommer flere KALD — ikke at de 44 eksisterende er
rimelige, og ikke at en ny projektion er rigtigt designet. Den finder heller
ikke en indirekte vej udenom, fx en ny hjælpefunktion der pakker kaldet ind i
et andet navn i en fil der allerede står i grundlinjen.
