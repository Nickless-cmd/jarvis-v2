"""Samtykke til at røre Bjørns mus og tastatur — én gang pr. samtale.

## Hvorfor den findes (21/9-2026)

Bjørn bad om ægte computer-use «som i cc desktop». Målt samme dag: de 55
operator-værktøjer FANDTES, men nut.js var aldrig installeret, så hvert eneste
kald døde med «Cannot find module». Værktøjerne blev tilbudt til modellen
alligevel.

Da jeg så på sikkerheden — som han foreslog, ved at læse Claude Desktops egen
kode — viste den noget vigtigt: deres `cowork-vm-service` vælger backend i
rækkefølgen bwrap → KVM → host-uden-isolation som SIDSTE udvej, binder /usr og
/etc read-only, og giver en TOM hjemmemappe. Claude Desktop giver altså aldrig
agenten brugerens rigtige mus og tastatur; den giver den et isoleret miljø.

Det Bjørn beder om er en STÆRKERE rettighed end den. Og i dag lå
`operator_mouse_click` og `operator_keyboard_type` i den tilladte liste uden
nogen godkendelse pr. handling — kun en global on/off.

## Hvad porten gør

Hans valg, ordret: «godkendelse første gang pr. session». Første gang Jarvis
vil RØRE mus eller tastatur i en samtale, kommer der ét kort. Svarer han ja,
er resten af samtalen fri — ellers ville en enkelt opgave koste hundredvis af
kort, og så bliver computer-use ubrugelig.

At LÆSE er frit: et skærmbillede, musens position, skærmens størrelse,
vindueslisten. Det er dem modellen skal bruge for overhovedet at kunne se hvor
den skal klikke, og de ændrer ingenting.

Samtykket lever i hukommelsen og dør med processen. Det er med vilje: en
genstart skal koste ét kort, ikke give varig adgang til hans maskine.
"""
from __future__ import annotations

import threading

#: De værktøjer der HANDLER — de kræver samtykke.
HANDLENDE: frozenset[str] = frozenset({
    "operator_mouse_click", "operator_mouse_move", "operator_mouse_drag",
    "operator_mouse_scroll", "operator_keyboard_type", "operator_keyboard_press",
    "operator_clipboard_write", "operator_focus_window", "operator_launch_app",
})
#: De værktøjer der kun LÆSER — de er frie. Modellen skal kunne se skærmen
#: for at kunne pege på noget; et skærmbillede ændrer ingenting.
LAESENDE: frozenset[str] = frozenset({
    "operator_screenshot", "operator_screenshot_window", "operator_screen_size",
    "operator_mouse_position", "operator_list_windows", "operator_ocr_region",
    "operator_find_image", "operator_clipboard_read",
})

_laas = threading.Lock()
_givet: set[str] = set()


def kraever_samtykke(vaerktoej: str) -> bool:
    """Er dette et værktøj der rører hans maskine?"""
    return str(vaerktoej or "") in HANDLENDE


def har_samtykke(session_id: str) -> bool:
    with _laas:
        return str(session_id or "") in _givet


def giv_samtykke(session_id: str) -> None:
    """Kaldes når han har sagt ja. Gælder resten af samtalen i denne proces."""
    sid = str(session_id or "").strip()
    if not sid:
        return
    with _laas:
        _givet.add(sid)


def traek_tilbage(session_id: str = "") -> None:
    """Stop-knappen. Tom session_id trækker ALT tilbage — nødbremsen."""
    sid = str(session_id or "").strip()
    with _laas:
        if sid:
            _givet.discard(sid)
        else:
            _givet.clear()


def aktive_samtaler() -> list[str]:
    """Hvilke samtaler har adgang lige nu? Desk viser mærket ud fra den her."""
    with _laas:
        return sorted(_givet)
