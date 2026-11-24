"""Fælles leksikalsk mekanisme: hvad er et fagord, og hvad er maskinstatus.

Flyttet hertil 24/11-2026 fra ``core/services/behavioral_decisions.py``, hvor den
levede som ``_RELEVANS_STOPORD`` / ``_STRUKTURELLE_ORD`` / ``_relevans_ord``.
Flytningen er ikke kosmetisk: de samme to begreber — «ord der ikke bærer
betydning» og «ord der er maskinens egen status» — blev genopfundet i tolv andre
moduler, hver gang med en liste der *næsten* lignede de andres. To af dem
(``thought_thread`` og ``avoidance_detector``) har begge en ``_STOPWORDS_DA`` der
adskiller sig på syv ord uden at nogen af dem kan forklare hvorfor. Den fælles
mekanisme ejer skellet ét sted, så en udvidelse rammer alle der bruger den.

TO NIVEAUER, og forskellen er målt — ikke stilistisk:

1. ``RELEVANS_STOPORD`` — funktionsord. De **fjernes**. De bærer intet signal i
   nogen sammenhæng, og en score bygget på dem er støj.
2. ``STRUKTURELLE_ORD`` — maskinens statusbeskrivelse. De **vægtes lavere**, de
   fjernes ikke. «active» kan sagtens være sagen i en tur der handler om at noget
   er aktivt — men den kan ikke bære beviset alene, fordi den står i hver eneste
   heartbeat-kontekst. Det er forskellen mellem et ord der er *tomt* og et ord der
   er *overalt*.

Skellet blev målt 24/11-2026: da de strukturelle ord blev fjernet i stedet for
vægtet, fejlede en eksisterende test med rette — «private signal pressure is
high» er INFORMATION om turen, ikke en tæller. En beslutning om signal-pres ER
relevant når presset er højt. Det er tællerne («has 1560 proposed items») og
identiteten («main», «inspect-working-tree») der ikke bærer en sag.
"""

from __future__ import annotations

import re
from typing import Any

#: Ord der ikke bærer betydning på tværs af beslutninger og ture.
#:
#: 23/11-2026: første version havde kun pronominer og konjunktioner. Målt gav det
#: falske hit: en HILSEN («hej Bjorn hvordan gaar det») vakte fire beslutninger,
#: fordi «hvordan» står i 4 af 138 beslutninger og derfor fik HØJ IDF — sjælden
#: og betydningsløs på samme tid. IDF kan ikke skelne de to; kun en liste kan.
#: Derfor er spørgeord, høflighedsfraser og tidsvendinger ekskluderet her.
RELEVANS_STOPORD = frozenset({
    # pronominer, konjunktioner, præpositioner
    "jeg", "det", "der", "som", "og", "at", "en", "et", "den", "de", "til",
    "for", "med", "fra", "skal", "kan", "ikke", "naar", "hvad", "hvor",
    "min", "mit", "mine", "sig", "sin", "sine", "har", "have", "var", "blev",
    "bliver", "vaere", "vaeret", "ogsaa", "kun", "men", "eller", "saa", "hvis",
    "denne", "dette", "disse", "man", "selv", "op", "ud", "ind", "ned",
    "the", "and", "with", "that", "this", "not", "are", "was", "have",
    # spørgeord og meta-ord — de beskriver samtalen, ikke sagen
    "hvordan", "hvorfor", "hvornaar", "hvilken", "hvilket", "hvilke",
    "gerne", "lige", "godt", "sadan", "vaere", "bliver", "siger", "sige",
    "synes", "tror", "ved", "kender", "handler", "gaelder", "drejer",
    # høflighed og hilsner
    "hej", "tak", "mojn", "godmorgen", "godaften", "velkommen",
    # tidsvendinger uden fagligt indhold
    "idag", "igaar", "imorgen", "aften", "morgen", "natten", "ugen",
    "maaned", "aaret", "timen", "gang", "igen", "stadig", "allerede",
    # Maskinelle tilstandstokens (24/11-2026, målt i heartbeat-stien).
    # Heartbeat scorer IKKE mod en brugerbesked men mod `tool_intent` og
    # `loop_runtime` — korte, maskinelle strenge som «idle active 2». Målt:
    # «active» står i 1 af 138 beslutninger og fik derfor IDF 4,24, hvilket
    # lod den passere enkeltords-reglen. Resultatet var at de SAMME to
    # beslutninger (`active_dreams`, `bgActive`) blev valgt på hver eneste
    # kontekst — en falsk forbindelse på et strukturelt token. Det er samme
    # fejlklasse som «hvordan» i en hilsen: sjælden OG betydningsløs.
    # `success` er BEHOLDT: den rammer beslutningen der netop handler om
    # `applied`/`ok`/`success`-felter, så dér er ordet et ægte signal.
    "active", "idle", "executed", "completed", "none", "standby",
    "dispatched", "noop", "true", "false",
})


#: Maskinens EGEN statusbeskrivelse — ord der står i hver eneste heartbeat-tur.
#:
#: HVORFOR (målt i DRIFT 24/11-2026). Gaten valgte de SAMME fem beslutninger i
#: 16 heartbeat-ticks over 95 minutter, mens kontekstens tal ændrede sig
#: (1578 -> 1560 foreslåede). Årsagen var målbar: de fem vandt på `file`,
#: `main`, `memory`, `signal` — tokens der står i statuslinjerne hver gang.
#: `dec_f1047a72079f` ramte UDELUKKENDE `file` + `memory` og scorede 4,31.
#:
#: Listen er ikke gættet: den er udledt af de literaler der GENERERER
#: statuslinjerne (`heartbeat_runtime.py:2390-2520`) — «scheduled heartbeat
#: interval is currently due», «recent governed file writes exist for continuity
#: review», «private signal pressure is …» — plus de workflow-labels
#: (`Preference Updates`, `Memory Promotions`, `Chronicle Drafts`) og
#: `tool_intent`-beskrivelsen (`inspect-working-tree main`). Alle er målt
#: tilstede i den levende kontekst. Et token herfra kan sagtens være en SAG i en
#: anden tur; derfor fjernes de ikke (som `RELEVANS_STOPORD` gør), de vejes
#: lavere og kan ikke bære beviset alene.
#:
#: IKKE på listen: `success` (rammer beslutningen om applied/ok/success-felter),
#: loop-titlenes fagord (`kørende`, `proces`, `prompten`, `relevans`) — de står
#: også i alle 16 kontekster, men fordi loop-titlerne ikke ændrede sig, ikke
#: fordi de er maskinstatus — og TILSTANDSBESKRIVELSERNE (`signal`, `pressure`,
#: `high`, `initiative`, `tension`, `feel`). Skellet er målt: første version
#: havde dem med, og så fejlede en eksisterende test med rette — «private signal
#: pressure is high» er INFORMATION om turen, ikke en tæller. En beslutning om
#: signal-pres ER relevant når presset er højt. Det er tællerne
#: («has 1560 proposed items») og identiteten («main», «inspect-working-tree»)
#: der ikke bærer en sag.
STRUKTURELLE_ORD = frozenset({
    # heartbeat_runtime.py:2402-2516 — statuslinjernes tæller-vokabular
    "manual", "trigger", "requested", "mission", "control",
    "scheduled", "heartbeat", "interval", "currently",
    "capabilities", "still", "require", "approval",
    "proposed", "items", "approved", "awaiting", "apply",
    "recent", "governed", "file", "writes", "exist", "continuity", "review",
    "contract", "available", "context", "latest", "visible", "preview", "carry",
    # workflow-labels der tæller op i hver tur
    "preference", "updates", "memory", "promotions", "chronicle", "drafts",
    # tool_intent — hvilken slags tur det er, ikke hvad sagen er
    "inspect", "working", "tree", "main", "repo",
    # 24/11-2026 (målt): listen var en STIKPRØVE — ti tokens fra den gamle
    # stopord-blok. Resten af statusvokabularet gik gennem filteret som fagord,
    # og en probe på ren maskin-kontekst valgte to open-loop-beslutninger på
    # tokenet `loop` alene. Målt før udvidelsen: `idle active running
    # completed tool_intent loop_state heartbeat pending failed cancelled
    # expired queued` efterlod ['cancelled','expired','failed','intent','loop',
    # 'loop_state','pending','queued','running','state','tool','tool_intent']
    # — 12 af 13 tokens var fagsignaler.
    #
    # Statusfamilien: tilstande en kørsel kan stå i. De beskriver HVOR i en
    # proces noget er, ikke HVAD sagen er — og de står i `loop_runtime` i
    # hver tur. En beslutning der kun rammer én af dem bærer intet.
    "running", "pending", "failed", "cancelled", "expired", "queued",
    # `tool_intent`/`loop_state` og deres dele. Sammensatte former tilføjes
    # både som helhed og som dele (`relevans_ord` splitter på '_'), så alle
    # fire varianter skal stå her — ellers lækker halvdelen.
    "tool", "intent", "tool_intent", "loop", "state", "loop_state",
})

#: Hvor meget et strukturelt ord vejer i scoren, relativt til sin IDF.
#:
#: 0,35 er målt, ikke valgt: ved 0,5 faldt `dec_f1047a72079f` (file+memory) ud
#: af de fem, og ved 0,35 stod rangordenen stabilt derefter. Faktoren kan ikke
#: ALENE gøre en ren strukturel match harmløs — den scorer 0,647 selv ved 0,15,
#: altså stadig over gulvet 0,32; først ved ~0,07 ville den falde under, og det
#: er fjernelse, ikke vægtning. Derfor er det BEVISKRAVET i den kaldende gate
#: den bærende regel, og denne faktor kun den sekundære.
STRUKTUREL_VAEGT = 0.35


def relevans_ord(tekst: str) -> set[str]:
    """Betydningsbærende ord i en tekst — lowercase, >=4 tegn, uden stopord.

    23/11-2026 (målt): første version splittede på bindestreg, så
    «prompt-sektionen» blev til «prompt» + «sektionen» og ALDRIG matchede den
    samme sammensatte form i en beslutning. Sammensatte ord bevares derfor som
    ét token, og delene tilføjes OGSÅ — så både «prompt-sektionen» og
    «sektionen» kan ramme.
    """
    tekst = str(tekst or "").lower()
    # 24/11-2026 (målt i DRIFT, ikke i en test): en filsti er ikke et signal.
    # Heartbeats `last_action` bærer stier, og den første produktionslinje
    # (21:17:39) valgte 5 af 137 på ord fra
    # `/tmp/pytest-of-bs/pytest-419/test_approved_sudo_exec_become0/workspaces/default/to`
    # — 9 af 15 tokens kom fra stien alene («pytest-of-bs», «become0»,
    # «workspaces», «default»). Det er samme fejlklasse som «active»: et token
    # der ikke bærer en sag. Stier fjernes derfor FØR tokenisering; et ord som
    # «chmod» uden for en sti bliver tilbage, fordi det KAN være en sag.
    tekst = re.sub(r"/\S*", " ", tekst)
    ord_: set[str] = set()
    for token in re.findall(r"[a-zæøå0-9_-]{4,}", tekst):
        if token in RELEVANS_STOPORD:
            continue
        ord_.add(token)
        # Bindestreg og understregning: tilføj delene, så en sammensat form
        # også matcher når modparten skriver den ene halvdel.
        if "-" in token or "_" in token:
            for del_ in re.split(r"[-_]", token):
                if len(del_) >= 4 and del_ not in RELEVANS_STOPORD:
                    ord_.add(del_)
    return ord_


def ord_frekvens(poster: list[dict[str, Any]]) -> dict[str, int]:
    """Hvor mange poster indeholder hvert ord?

    HVORFOR (målt 23/11-2026). Første version vægtede alle ord lige. Målt gav
    det falske hit: «hvordan» og «faktisk» bandt beslutninger til en hilsen,
    fordi de står i 11-14 af de 138 beslutninger. Et ord der står i en tiendedel
    af alle beslutninger kan ikke skelne noget — det er baggrund, ikke signal.

    Læser `directive` + `trigger_cue`, fordi det er de to felter en beslutning
    beskriver sig selv med. En post uden dem tæller som tom, ikke som fejl.
    """
    freq: dict[str, int] = {}
    for d in poster:
        tekst = f"{d.get('directive') or ''} {d.get('trigger_cue') or ''}"
        for o in relevans_ord(tekst):
            freq[o] = freq.get(o, 0) + 1
    return freq
