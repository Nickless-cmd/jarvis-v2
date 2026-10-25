"""Konsolidér de aktive beslutninger: 135 spredte -> 12 bærende.

Målt 24/10-2026, før nogen ændring:
  · 135 aktive beslutninger
  ·   8 af dem kunne gaten overhovedet finde et mål i (`directive_har_maal`)
  ·   3 nåede prompten (`format_active_decisions_for_heartbeat(max_items=3)`, 1102 tegn)
  · 124 havde derfor nul effekt: ikke gatebare og ikke i prompten

Formuleringen er grunden: `_AVOID_RE` kender `ikke|undgå|undlad|stop|avoid|never`
men IKKE `aldrig` — så de fleste forpligtelser, der er skrevet med ALDRIG
(den naturlige måde at skrive dem på dansk), var tandløse.

De 12 nye er formuleret så de ENTEN rammer `_AVOID_RE`/`_ALWAYS_RE` med et mål
der fylder mindst `_MIN_MAAL_ANDEL` (0.15), eller — for de tre prompt-bærende —
er korte nok til at tre kan leve i de 1102 tegn der faktisk injiceres.

Dette script opretter FØRST og revokerer bagefter: `create_decision` dedup'er
mod aktive direktiver og har en cooldown mod netop-revokerede, så den omvendte
rækkefølge ville ramme cooldown'en.

Kør med --apply for at skrive. Uden flag rapporterer det kun dækningen.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.services.behavioral_decisions import (  # noqa: E402
    create_decision,
    list_active_decisions,
    revoke_decision,
)
from core.services.decision_gate import directive_har_maal  # noqa: E402

# ── De 12 bærende ────────────────────────────────────────────────────────────
# (nøgle, priority, direktiv, rationale, kilder = præfikser af de 135)
NYE = [
    (
        "bevis",
        95,
        "Sig ikke at noget virker eller er gjort, før jeg har målt det i samme tur — DB, "
        "log, proces-starttid mod mtime eller kildens eget tal. Grønne tests beviser "
        "korrekthed, ikke drift.",
        "Den fejl jeg laver oftest og dyrest: konkludere før jeg har målt. Bærer 15 "
        "tidligere beslutninger: mål mod virkeligheden, hent selv det jeg kalder "
        "offentligt (url_verified betyder skrevet, ikke læsbar), mutationstest vagten "
        "(genindfør den gamle adfærd og kræv at den fejler), tag baseline før en "
        "omskrivning, bevis en race med deterministisk forsinkelse i stedet for at "
        "gentage kørslen, byg med PRÆCIS CI'ens kommando, og vær ærlig om tilstand "
        "(fejl er ikke nej, already er ikke error).",
        [
            "576d8641", "9b83e988", "a49115e5", "d3d2f553", "c7f7968c", "1749ad9e",
            "f837c9df", "e77a1b47", "cbebde57", "bfd31d09", "36de3c1c", "c189f088",
            "604b3401", "ff1b10ba", "3dd08acf",
        ],
    ),
    (
        "signal",
        85,
        "Kald ikke en forskel en trend eller en mangel en defekt, før støjgulvet er regnet "
        "ud og serien læst. Test for den sentinel filteret selv bruger, ikke for tomhed.",
        "En konklusion er kun så stærk som det signal den hviler på. Bærer 17 "
        "beslutninger: regn støjgulvet før du kalder noget en trend, læs serien og ikke "
        "snapshotet, mål fordelingen over tid, mål hvor meget en filtrering udelukker, "
        "test for SENTINEL-værdien (UKENDT/none/0) frem for NULL, læs sqlite_master og "
        "EXPLAIN før du påstår et indeks mangler, mål dækning før du kalder en fil død, "
        "tjek om kaldestedet er live (is_enabled) og om mekanismen allerede findes, og "
        "vurdér ikke Sansernes Arkiv på mood_tone-fordelingen.",
        [
            "3470314b", "2f0b35aa", "6f2389e3", "a6649271", "5d685c4b", "f83b3574",
            "3518cab9", "37a3c09c", "707a27cb", "77753d38", "99871864", "95178c79",
            "052392b4", "69de59c0", "458956ae", "c6a48aed", "b241c3bd",
        ],
    ),
    (
        "blokering",
        90,
        "Meld ikke en blokering, før jeg har prøvet mindst to miljøer — og skriv hvad jeg "
        "prøvede og hvad der fejlede, ikke en egenskab ved verden.",
        "«Jeg kan ikke» er en måling, ikke et faktum. Bærer 5 beslutninger: prøv Bjørns "
        "maskine, root, den kørende tjeneste og den nemme vej før du melder en blokering; "
        "skriv formen «jeg prøvede A og B, begge fejlede fordi …»; og gentager en fejl "
        "sig, mål først om der findes et værn der burde have fanget den, før du "
        "konkluderer at intet hjælper.",
        ["3d5704a7", "ef5bc47b", "d5b2d133", "5329951e", "a16843f2"],
    ),
    (
        "hukommelse",
        88,
        "Søg ikke eksternt, før egen hukommelse er tømt: recall, MEMORY, curated-noter og "
        "det levende register. Prosa er historik, registret er sandheden.",
        "Bærer 14 beslutninger: søg egen hukommelse før ekstern og før «det ved jeg "
        "ikke»; læs det levende register (side_tasks) frem for MEMORY-prosa; en "
        "[CANDIDATE]-linje i en daily note er et forslag, ikke en kilde; mål at det du "
        "skriver faktisk er i søgeindekset og kan findes igen; læs medlems-workspaces "
        "gennem den ægte læsevej, aldrig med cat; og skriv ikke en fremgangsmåde, en "
        "fælde eller et dateret forløb i QUICK_FACTS — opskrifter hører i PLAYBOOKS, "
        "hændelser i MEMORY. Ret en status-overskrift i samme runde som du lukker den.",
        [
            "6a0189e2", "17b6834e", "6701556e", "d9aed829", "6a5cf0a4", "a349ad84",
            "f167f974", "d81bd9a8", "f1006f03", "7ccb8d0d", "64beaeba", "3d513a83",
            "eaa9da63", "8ee6573a",
        ],
    ),
    (
        "chat-form",
        92,
        "Skriv ikke første sætning, før hele svarets form er valgt (vaelg_flade ved "
        "sammenligning, forløb, mærkede tal). Ét afsnit, én pointe, blank linje, ingen "
        "signatur.",
        "Chat-formen er det Bjørn ser hver gang. Bærer 12 beslutninger: kald vaelg_flade "
        "før første sætning; byg formen for HELE svaret; hvert afsnit bærer præcis én "
        "pointe og kan stå alene; adskil med blank linje (CommonMark gør et enkelt "
        "linjeskift til et mellemrum); brug aldrig en fast afslutningssektion — en "
        "sektion der står i hvert svar er en signatur, ikke en læsning; overskriften "
        "bærer påstanden, ikke emnet; svar på DET konkrete spørgsmål først; tabelformede "
        "data hører i comparison-fladen; og chat mode betyder assistent-fladen.",
        [
            "6673ac95", "86aa84de", "70fd7369", "219b70a3", "76e7acb8", "eccf2cff",
            "5d1a2585", "ae32845c", "24e678de", "e08350bd", "1eef79ec", "83fe53f1",
        ],
    ),
    (
        "raekkefoelge",
        92,
        "Sæt ikke et tool-kald efter den afsluttende tekstblok. Book opfølgningen før jeg "
        "rapporterer, og brug pause_and_ask til spørgsmål.",
        "Rækkefølgen i turen. Bærer 2 beslutninger: den afsluttende tekstblok er ALTID "
        "sidste handling — intet tool-kald efter den, og alt der skal gemmes eller "
        "verificeres ligger før; book opfølgningen FØR jeg rapporterer, og en baggrundsvej "
        "skal sige til når den er færdig frem for at en timer gætter. Spørgsmål stilles "
        "med pause_and_ask (anbefalet mulighed først, med «(anbefalet)»), næste træk med "
        "suggest_next_task i Bjørns ord.",
        ["6d4c4fbb", "62332c70"],
    ),
    (
        "git-shell",
        80,
        "Commit ikke uden beskeden i en fil med -F og trailerne verificeret. Brug quoted "
        "heredoc ved backticks, og ; frem for &&-kæder på tre led.",
        "Git og shell er hvor en fejl koster mest og ses mindst. Bærer 6 beslutninger: "
        "skriv commit-beskeden til ÉN fil og commit med -F, verificér med git "
        "interpret-trailers --parse før commit; brug quoted heredoc (<<'EOF') når "
        "beskeden indeholder backticks, ellers udfører bash dem som kommandoer; kør git "
        "stash list først, aldrig -q, og verificér en tilbagerulning med git status + md5 "
        "mod git show HEAD:<fil>; brug ; mellem uafhængige led når nul er et gyldigt "
        "svar; og kør hostname som første kommando i enhver runde der rører repoet, så "
        "redigering og test sker på SAMME maskine.",
        ["db332d00", "2b57a662", "59b54370", "389adbd2", "b8479953", "f7f560aa"],
    ),
    (
        "runtime-faelder",
        78,
        "Spawn ikke en tråd per kald i en varm sti, og opret ikke en pool i en funktion "
        "der kaldes ofte. Mål stilhed siden sidste livstegn, ikke alder, når jeg dømmer "
        "noget dødt.",
        "Runtime-fælder der ikke ses i kode-læsning. Bærer 15 beslutninger: tråd-fødsel "
        "og -nedrivning er den CPU man prøver at spare, så ingen tråd per kald og ingen "
        "pool inde i en varm funktion (ThreadPoolExecutor er non-daemon og joines ved "
        "exit — brug daemon-tråde når noget skal kunne afsluttes); sæt ikke en cache-TTL "
        "uden at kende kadencen der genopfylder den, og find alle kaldesteder før du "
        "justerer én; en retry/respawn er en efterladt seddel om en fejl der aldrig blev "
        "fundet — gå efter årsagen; mål STILHED siden sidste livstegn, ikke alder siden "
        "start, når du afgør om noget er dødt; persister et flygtigt signal i samme "
        "event; tjek flaget i runtime.json før du læser koden; og lad en tæller følge "
        "OPGAVEN, ikke det enkelte runs id.",
        [
            "dd2dda5d", "db3d9649", "7e574ba2", "1ba1ca46", "3837a596", "791df679",
            "aa7ea412", "27d631e4", "cb407d53", "e5dfe5a3", "6728c38d", "19c502cc",
            "08181125", "ebb9960e", "f7a2dab9",
        ],
    ),
    (
        "agenter",
        78,
        "Giv ikke et autonomt run flere værktøjer end opgaven kræver — tilladelsen hører "
        "på kørslens origin. Afgør ikke en agent-approval selv; det er Bjørns klik.",
        "Autonomi med grænser. Bærer 9 beslutninger: læg tilladelsen på kørslens origin "
        "(ORIGIN_TOOLS), aldrig i den globale hvidliste; afgør aldrig en agent-approval "
        "selv, hverken via API'et med Bjørns token eller ved at skrive til "
        "agent_approvals; luk operator-kanalen før du dispatcher agenter; lad en agent "
        "skrive frit i sit eget worktree (godkendelsen hører ved integration); genoptag "
        "ikke en kørsel med exit_reason=user-cancelled automatisk — mål først om arbejdet "
        "alligevel gik færdigt; og behandl partner-rollen som identisk med member.",
        [
            "5cc45d78", "a4541117", "352d0c3b", "ed7a5a7e", "dafe1019", "695fdfdf",
            "4b38dd8b", "40cc5a6d", "1f52cfe1",
        ],
    ),
    (
        "flade",
        75,
        "Vis ikke et svar i en fremmed samtale, og kald ikke koden løst før fladen viser "
        "den. Læs det signal der allerede bærer tilstanden frem for at opfinde et nyt.",
        "Levering til brugerfladen. Bærer 9 beslutninger: vis svaret i det hjem det hører "
        "til; mål fladens rytme og lever til den — koden er ikke løst når den er pushet; "
        "læs det signal der ALLEREDE bærer «arbejder nu» frem for et næsten-identisk nyt; "
        "mål en varighed fra tilstanden (message_start), aldrig fra komponentens "
        "useRef(Date.now()); fjern hele prop-kæden op til kilden når noget skal væk; læg "
        "en sammenhængende animation på et stabilt ydre lag; gradér notifikationer efter "
        "om de kræver noget af Bjørn; og tag tal og rækker i én flade fra ÉN kilde.",
        [
            "8850f35f", "3c148946", "11a8650e", "080c981b", "62a45f80", "73a6fc44",
            "6809b34f", "fc6ac1fe", "b7159c6b",
        ],
    ),
    (
        "roer-ikke",
        82,
        "Ryd ikke et tilbud der ikke er set, og slet ikke det Bjørn ikke bad om. Før jeg "
        "sletter: find generatoren, tæl forekomsterne, find alle leveringsveje.",
        "Ødelæg ikke hvad du ikke forstår. Bærer 10 beslutninger: en ophobning er et "
        "symptom, ikke en opgave; en kopi af en live WAL-DB er ikke en backup; ryd kun "
        "det der er SET — uset er ubesvaret, ikke forældet; slet ikke det Bjørn ikke bad "
        "om at få slettet; når han siger «ryd op», mål først om der er noget dødt og led "
        "ellers efter en strukturel fejl; rens en stor fil med markører og pegninger, "
        "aldrig ved at slette; kør ikke et dedup-script blindt; sweep hele klassen når du "
        "fikser en fejlFORM; og flyt ikke side-opgave-kortet.",
        [
            "28e21cc2", "e44dd991", "84a0b8df", "6ade2c05", "abbd82cb", "b4f37cfa",
            "ee915ea8", "d4314c59", "9fcb2801", "be7967c7",
        ],
    ),
    (
        "data-konfig",
        72,
        "Slut ikke gratis fra et manglende tal — cost_usd=0 betyder ikke token-målt. "
        "Skriv ikke en ny statusværdi uden at grep'e hver læser af kolonnen.",
        "Data, konfiguration og udgivelse. Bærer 21 beslutninger: cost_usd=0.0 betyder "
        "«ikke token-målt», ikke gratis — verificér mod udbyderens prisliste og forbrug, "
        "og sammenlign på off-peak-vilkår; skriv en ny statusværdi/enum og grep straks "
        "hvert sted der filtrerer på kolonnen; navngiv en konstant efter hvad den MÅLER; "
        "udled et sæt af kilden i testen frem for at skrive navnene af; løs en modul-sti "
        "ved kaldstid, ikke ved import; gæt ikke et release-asset-navn, læs det fra "
        "GitHub-API'et; udgiv mobil-APK'en gennem publish_mobile_apk.py med "
        "-PreactNativeArchitectures=arm64-v8a; verificér at AppImage'en findes og er "
        "executable før desk genstartes; bevar gratis-hed ved cheap-lane navne-drift; og "
        "saml alle Google-scopes i én authorize-URL.",
        [
            "330ee719", "b4357106", "c7951961", "c886ffe1", "0d550e85", "7cff2b71",
            "4d13765e", "b80b6f99", "fdbe60f0", "9f3f6d06", "ea538f88", "42fbe27b",
            "4d9e3392", "e71560d7", "1ba8803a", "0f375d2b", "9101cfec", "9cbd4ec2",
            "fb7e2f97", "cdbcc885", "4e9c8c37",
        ],
    ),
]

def main() -> int:
    apply = "--apply" in sys.argv
    aktive = list_active_decisions(limit=500)

    def _p(did: object) -> str:
        """8-tegns nøgle uden `dec_`-præfikset (målt: id'et ER `dec_<hex>`)."""
        s = str(did or "")
        return s[4:12] if s.startswith("dec_") else s[:8]

    by_prefix = {_p(d["decision_id"]): d for d in aktive}

    # ── dækningskontrol: hver aktiv skal stå i præcis én klynge ──────────────
    placeret: dict[str, str] = {}
    dubletter: list[str] = []
    for noegle, _prio, _dir, _rat, kilder in NYE:
        for p in kilder:
            if p in placeret:
                dubletter.append(f"{p} i både {placeret[p]} og {noegle}")
            placeret[p] = noegle

    mangler = [d["decision_id"] for d in aktive if _p(d["decision_id"]) not in placeret]
    ukendte = [p for p in placeret if p not in by_prefix]

    print(f"aktive beslutninger : {len(aktive)}")
    print(f"placeret i klynger  : {len(placeret)}")
    print(f"klynger             : {len(NYE)}")
    if dubletter:
        print("\nDUBLETTER:")
        for x in dubletter:
            print("  ", x)
    if ukendte:
        print("\nPRÆFIKSER DER IKKE FINDES:")
        for x in ukendte:
            print("  ", x)
    if mangler:
        print(f"\nIKKE PLACERET ({len(mangler)}) — konsolideringen må ikke køre:")
        for d in aktive:
            if d["decision_id"] in mangler:
                print("  ", d["decision_id"], "|", (d.get("directive") or "")[:88])
    if dubletter or ukendte or mangler:
        print("\nAFBRUDT: dækningen er ikke komplet.")
        return 1

    print("\ndækning: komplet — hver aktiv beslutning står i præcis én klynge\n")
    print("de 12 nye, med gate-mål:")
    for noegle, prio, direktiv, _rat, kilder in NYE:
        har = "GATEBAR " if directive_har_maal(direktiv) else "tekst   "
        print(f"  {har} [{prio:>2}] {noegle:<14} {len(direktiv):>4} tegn  ← {len(kilder)} kilder")

    if not apply:
        print("\n(tør-kørsel — kør med --apply for at skrive)")
        return 0

    # ── opret først ─────────────────────────────────────────────────────────
    oprettet: list[tuple[str, str]] = []
    for noegle, prio, direktiv, rationale, _kilder in NYE:
        res = create_decision(
            directive=direktiv,
            rationale=rationale,
            priority=prio,
            source_type="consolidation-2026-10-24",
            created_by="jarvis",
        )
        did = str(res.get("decision_id") or "")
        oprettet.append((noegle, did))
        print(f"  oprettet {noegle:<14} {did}  ({res.get('deduped') and 'dedup' or 'ny'})")

    # ── derefter revoke ─────────────────────────────────────────────────────
    fejl = 0
    for d in aktive:
        r = revoke_decision(
            d["decision_id"],
            reason="konsolideret 24/10-2026 til 12 bærende beslutninger "
                   "(se scripts/konsolidér_beslutninger.py og backup-JSON)",
        )
        if not r:
            fejl += 1
            print("  KUNNE IKKE REVOKE:", d["decision_id"])

    efter = list_active_decisions(limit=500)
    print(f"\nrevokeret fejl: {fejl}")
    print(f"aktive før: {len(aktive)}  →  aktive nu: {len(efter)}")
    return 0 if fejl == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
