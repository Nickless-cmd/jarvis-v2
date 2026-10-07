"""Telemetri for den synlige prompts assembly: hvad fylder, og hvad koster cache.

Udskilt fra `prompt_contract.py` 6/10-2026 (Boy Scout — filen var 5.006 linjer).
Enheden er sammenhaengende: den udleder et navn pr. stykke, rangordner dem,
udsender `prompt.assembly_size`, skriver de to journal-linjer, og afleverer
sektionerne til impact-telemetrien. Ét ansvar: maale og rapportere en assembly.

To ting her er lektier, ikke smag:

* **Navnet afledes af INDHOLDET.** Den gamle udgave zippede `derived_inputs`
  mod `parts` paa indeks, men de to lister vokser ikke i takt (25
  `parts.append` mod 42 `derived_inputs.append`, plus `extend`). Hvert navn sad
  derfor paa et vilkaarligt andet stykke. Tegnet: `quick_facts` blev maalt til
  7.051 tegn, mens dens builder havde et loft paa 1.800. Et kort der peger
  forkert er vaerre end intet kort — man skaerer det forkerte sted.
* **Raekkefoelgen i parts-linjen er ASSEMBLY-raekkefoelgen, aldrig sorteret.**
  Stoerrelsen siger hvad der fylder; raekkefoelgen siger hvad der oedelaegger
  cachen. DeepSeek matcher fra begyndelsen, saa en del der skifter stoerrelse
  — eller kommer og gaar — forskyder alt EFTER sig. Sorterer man listen, kan
  man ikke skelne «ligger tidligt, koster hele praefikset» fra «ligger sidst,
  koster ingenting».
"""

from __future__ import annotations

import sys


def label_of(text: str) -> str:
    """Stykkets navn, udledt af dets FOERSTE LINJE — som ikke kan komme ud af
    trit med stykkets eget indhold."""
    head = (text or "").lstrip().split("\n", 1)[0].strip()
    head = head.lstrip("#").strip().rstrip(":").strip()
    return (head[:48] or "(uden overskrift)").replace(" ", "_")


def hale_tegn(assembled_text: str) -> int:
    """Tegn i den DO-NOT-CACHE-hale som forbrugeren flytter ud af praefikset.

    `visible_model._split_dynamic_tail` flytter alt efter sentinel'en ned foran
    den aktuelle bruger-besked, saa `[system + historik]` bliver et stabilt
    cachebart praefiks — og halens tegn bliver miss-tokens paa HVERT kald.

    Regnes med samme find/slice/strip som forbrugeren, ellers maaler vi noget
    andet end det der faktisk er ucachet. Invarianten er pinnet i
    `tests/test_prompt_assembly_telemetri.py`. Uden sentinel: 0.
    """
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

    text = str(assembled_text or "")
    i = text.find(DYNAMIC_TAIL_SENTINEL)
    if i < 0:
        return 0
    return len(text[i + len(DYNAMIC_TAIL_SENTINEL):].strip())


def rangordn(parts: list[str]) -> list[tuple[str, int]]:
    """(navn, tegn) pr. ikke-tomt stykke, stoerste foerst. Navnet er stykkets eget."""
    return sorted(
        ((label_of(part), len(part)) for part in parts if part),
        key=lambda kv: kv[1], reverse=True,
    )


def rapporter_assembly(
    parts: list[str],
    *,
    assembled_text: str,
    compact: bool,
    session_id: str,
    assembly_ms: float | int,
) -> None:
    """Udsend event + journal-linjer + aflevér sektionerne til impact-telemetrien.

    Self-safe hele vejen: telemetri maa aldrig vaelte en prompt-build.
    """
    per_part_chars = [len(p) for p in parts if p]
    total_chars = len(assembled_text)
    approx_tokens = total_chars // 4  # rough heuristic — close enough for triage
    tail_chars = hale_tegn(assembled_text)
    largest = rangordn(parts)[:8]

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("prompt.assembly_size", {
            "mode": "visible_chat",
            "compact": compact,
            "total_chars": total_chars,
            "approx_tokens": approx_tokens,
            "part_count": len(per_part_chars),
            # Maalt 6/10-2026: det varme cache-miss-gulv er 4,1 %, og 52 smaa
            # sektioner vejede 20.904 tegn af en median-prompt paa 126.652 —
            # ogsaa 4,1 %. Sammenfaldet var indicier; disse to felter afgoer det.
            "dyn_tail_chars": tail_chars,
            "cached_prefix_chars": total_chars - tail_chars,
            "largest_sections": [
                {"label": label, "chars": chars} for label, chars in largest if chars > 0
            ],
            "assembly_ms": assembly_ms,
        })
    except Exception:  # telemetri maa aldrig vaelte en build
        pass

    print(
        f"prompt-assembly-size chars={total_chars} approx_tokens={approx_tokens} "
        f"parts={len(per_part_chars)} hale={tail_chars}",
        file=sys.stderr,
        flush=True,
    )
    # Fordelingen paa ÉN linje, saa et doegns journal kan summeres uden at parse
    # flere linjer sammen. Nul-dele tages med: en del der altid er tom er lige
    # saa interessant som en der fylder. I ASSEMBLY-RAEKKEFOELGE — se modulets
    # docstring for hvorfor sortering oedelaegger signalet.
    print(
        "prompt-assembly-parts " + " ".join(
            f"{label_of(part)}={len(part)}" for part in parts if part
        ),
        file=sys.stderr,
        flush=True,
    )

    # Husk sektionerne til `prompt.section_answer_impact`. Den oprindelige
    # placering i prompt_contract kaldte den nested `_label_of` foer den var
    # bundet → UnboundLocalError, fanget stille → 0 events nogensinde
    # (verificeret live 4/9 efter to aegte ture). Her kan det ikke gentage sig:
    # `label_of` er modul-niveau.
    try:
        from core.services.prompt_section_impact import remember_prompt_sections
        remember_prompt_sections(
            session_id=session_id or "",
            sections=[(label_of(part), part) for part in parts if part],
        )
    except Exception:  # impact-telemetri maa aldrig vaelte en build
        pass
