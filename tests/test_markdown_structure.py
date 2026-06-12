"""Tests for markdown_structure.normalize_markdown_structure.

Baggrund: Jarvis (deepseek) emitterer inkonsistent newlines — ca. halvdelen af
hans svar skriver alt inline med ` - `-bullets og `**X:**`-headers men UDEN
newlines, så CommonMark merger det til én lang linje ("kastet ind"). Denne
normalizer rekonstruerer blok-struktur fra de inline-markører, server-side, før
beskeden gemmes + sendes til alle kanaler. Idempotent på allerede-struktureret
tekst.
"""
from __future__ import annotations

from core.services.markdown_structure import normalize_markdown_structure


def test_inline_bullets_become_list():
    src = "Her er punkterne: - et - to - tre"
    out = normalize_markdown_structure(src)
    lines = out.split("\n")
    assert "- et" in lines
    assert "- to" in lines
    assert "- tre" in lines


def test_single_inline_dash_not_touched():
    # Én enkelt ' - ' er en tankestreg, ikke en liste — må ikke brækkes.
    src = "Det virker fint - næsten altid."
    assert normalize_markdown_structure(src) == src


def test_inline_colon_header_becomes_block():
    src = 'Intro tekst. **Hvad det er:** noget indhold her bagefter'
    out = normalize_markdown_structure(src)
    assert "\n\n**Hvad det er:**\n\n" in out


def test_blank_line_before_list():
    src = "Forklaring her - alpha - beta - gamma"
    out = normalize_markdown_structure(src)
    # Første bullet skal have en blank linje foran så CommonMark starter listen.
    assert "\n\n- alpha" in out


def test_idempotent_on_structured_text():
    src = (
        "### Hvad Android-appen kunne bygge på\n"
        "- **API'et** — eksisterer allerede\n"
        "- **Sessioner** — portable på tværs af enheder\n"
        "- **Auth** — token + rolle fungerer\n"
    )
    assert normalize_markdown_structure(src) == src


def test_code_fence_protected():
    src = "Kør dette:\n```\nfor x - y - z\n```\nog så - a - b - c"
    out = normalize_markdown_structure(src)
    # Indhold inde i fence er urørt
    assert "for x - y - z" in out
    # Men teksten udenfor er normaliseret
    assert "- a" in out.split("```")[-1]


def test_real_cowork_message_gets_list():
    # Den faktiske besked-id 63546 fra databasen (forkortet) — én lang linje.
    src = (
        '**Jeg har kigget på koden.** Cowork er bare chat. '
        '**Hvad det er:** - `messages.tsx` — beskedtråd - `runBox.tsx` — composer '
        '- `output.tsx` — output-bjælke - `permissionsManager.tsx` — gate '
        '**Det er chat + permissions.**'
    )
    out = normalize_markdown_structure(src)
    bullets = [ln for ln in out.split("\n") if ln.startswith("- ")]
    assert len(bullets) >= 3
    assert "\n\n**Hvad det er:**\n\n" in out


def test_multiword_bold_statement_becomes_paragraph():
    src = "noget her (ask/trust) **Det er chat + permissions.** Ingen plans her"
    out = normalize_markdown_structure(src)
    assert "\n\n**Det er chat + permissions.**\n\n" in out


def test_short_inline_emphasis_not_split():
    # Ét-ords emphasis midt i en sætning må IKKE brækkes ud.
    src = "Det er **vigtigt!** at huske det her"
    assert normalize_markdown_structure(src) == src


def test_inline_bold_without_punctuation_not_split():
    src = "Vi bruger **en chat** og det virker godt"
    assert normalize_markdown_structure(src) == src


def test_empty_and_none_safe():
    assert normalize_markdown_structure("") == ""
    assert normalize_markdown_structure("   ") == "   "
