"""Opret-dokumenter: Word, Excel, PowerPoint og PDF.

## Hvorfor de bor her

Bjørn 27/10-2026: *«dem skal vi osse have»* — efter en måling af hvad
ChatGPT kan i chat mode. Huset kunne LÆSE fem Google-formater gennem
connectorer, men der fandtes **ingen** værktøj der kunne oprette en fil.
`pdf_read` fandtes; `pdf_create` gjorde ikke. Målt: nul opret-værktøjer i
hele kataloget.

## Arkitekturen: én skriver, fire formater

Hvert værktøj gør præcis to ting — genererer en fil i en midlertidig mappe,
og sender stien videre til `publish_file`. Udleveringen, per-bruger-mappen,
URL'en og ærligheds-vagten bor allerede dér (`publish_file_tool.py`), og en
fjerde kopi af den regel ville drive fra de tre andre. Derfor ingen egen
fil-skrivning, ingen egen URL-opbygning.

## Hvorfor formaterne er sikre i chat mode

De skriver KUN til den kaldende brugers egen udgivelses-mappe, gennem den
ene funktion der kender layoutet. De kan ikke læse en vilkårlig sti, ikke
overskrive en anden brugers fil og ikke ramme uden for mappen. Det er
derfor de hører i den åbne base og ikke i owner-strippet — i modsætning til
`pdf_read`, der læser hvad som helst.

## Tekst-formatet (docx + pdf)

`indhold` er linje-baseret og forudsigeligt:

    # Overskrift på niveau 1
    ## Overskrift på niveau 2
    - punktopstilling
    1. nummereret punkt
    almindelig tekst bliver et afsnit

Tomme linjer adskiller afsnit. Ukendt syntaks behandles som tekst — en
formaterings-fejl må aldrig koste indholdet.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── fælles ────────────────────────────────────────────────────────────────

def _udgiv(sti: Path, filnavn: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send en genereret fil gennem den ene udlevering der findes.

    TUREN SKAL MED. `publish_file` hæfter filen på svaret gennem
    `published_files.note()`, og den returnerer STRAKS hvis run_id er tom.
    Uden `_runtime_turn_id` blev filen altså udgivet helt korrekt — med en
    URL der virker — men der blev ikke lagt nogen post på turen, så svaret
    bar ingen filblok, og klienten havde intet at vise eller klikke på.

    Målt 27/10-2026 (Bjørn: *«der er ikk noget øje? intet at klikke på?»*):
    `visningsflade-test.pdf` blev dannet med `url_verified: true`, og der var
    intet øje i tråden. De fire dokument-værktøjer kalder
    `_exec_publish_file` DIREKTE og springer dermed det executor-lag der
    stempler `_runtime_turn_id` ind i argumenterne. `vis_graf`,
    `vis_widget` og `render_mermaid` sender den selv — derfor har de en
    flade, og derfor er det kun disse fire der mangler én.
    """
    from core.tools.publish_file_tool import _exec_publish_file

    _args: dict[str, Any] = {"source_path": str(sti), "filename": filnavn}
    for noegle in ("_runtime_turn_id", "_runtime_run_id", "_runtime_tool_use_id"):
        vaerdi = str((args or {}).get(noegle) or "")
        if vaerdi:
            _args[noegle] = vaerdi
    return _exec_publish_file(_args)


def _filnavn(raa: str, standard_navn: str, endelse: str) -> str:
    """Sikrér en brugbar fil-endelse; ellers tilføj den."""
    navn = (raa or "").strip() or standard_navn
    navn = Path(navn).name or standard_navn
    if not navn.lower().endswith(endelse):
        navn = f"{navn}{endelse}"
    return navn


def _linjer(indhold: Any) -> list[str]:
    """Normalisér `indhold` til linjer — accepterer streng eller liste."""
    if isinstance(indhold, list):
        return [str(x) for x in indhold]
    return str(indhold or "").splitlines()


def _blokke(linjer: list[str]) -> list[tuple[str, str, int]]:
    """Parse linjer til (slags, tekst, niveau).

    slags: 'h1' | 'h2' | 'h3' | 'punkt' | 'nummer' | 'tekst' | 'tom'
    """
    ud: list[tuple[str, str, int]] = []
    for linje in linjer:
        s = linje.rstrip()
        if not s.strip():
            ud.append(("tom", "", 0))
            continue
        if s.startswith("### "):
            ud.append(("h3", s[4:].strip(), 3))
        elif s.startswith("## "):
            ud.append(("h2", s[3:].strip(), 2))
        elif s.startswith("# "):
            ud.append(("h1", s[2:].strip(), 1))
        elif s.lstrip().startswith(("- ", "* ")):
            ud.append(("punkt", s.lstrip()[2:].strip(), 0))
        elif s.lstrip()[:2].rstrip(".").isdigit() and "." in s.lstrip()[:4]:
            tekst = s.lstrip().split(".", 1)[1].strip()
            ud.append(("nummer", tekst, 0))
        else:
            ud.append(("tekst", s.strip(), 0))
    return ud


# ── værktøjs-schemaer ─────────────────────────────────────────────────────

_INDEHOLD_PARAM = {
    "type": "string",
    "description": (
        "Indhold, linje for linje. '# ' = overskrift 1, '## ' = overskrift 2, "
        "'- ' = punktopstilling, '1. ' = nummereret punkt, tom linje = afsnitsskift. "
        "Alt andet bliver almindelig tekst."
    ),
}

DOCUMENT_CREATE_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "pdf_create",
            "description": (
                "Opret en PDF-fil og få et download-link. Bruges til rapporter, "
                "oversigter og dokumenter der skal kunne sendes eller printes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {"type": "string", "description": "Dokumentets titel (forside-overskrift)"},
                    "indhold": _INDEHOLD_PARAM,
                    "filnavn": {"type": "string", "description": "Filnavn uden endelse; '.pdf' tilføjes"},
                },
                "required": ["indhold"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docx_create",
            "description": (
                "Opret et Word-dokument (.docx) og få et download-link. Til "
                "redigerbare dokumenter, breve og rapporter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {"type": "string", "description": "Dokumentets titel"},
                    "indhold": _INDEHOLD_PARAM,
                    "filnavn": {"type": "string", "description": "Filnavn uden endelse; '.docx' tilføjes"},
                },
                "required": ["indhold"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "xlsx_create",
            "description": (
                "Opret et regneark (.xlsx) og få et download-link. Et eller flere "
                "ark med kolonne-overskrifter og rækker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {"type": "string", "description": "Titel / standard-arknavn"},
                    "ark": {
                        "type": "array",
                        "description": "Ark-liste. Hvert ark: {navn, kolonner: [...], rækker: [[...], ...]}",
                        "items": {
                            "type": "object",
                            "properties": {
                                "navn": {"type": "string"},
                                "kolonner": {"type": "array", "items": {"type": "string"}},
                                "rækker": {"type": "array", "items": {"type": "array"}},
                            },
                        },
                    },
                    "kolonner": {"type": "array", "items": {"type": "string"}, "description": "Kolonner, når der kun er ét ark"},
                    "rækker": {"type": "array", "items": {"type": "array"}, "description": "Rækker, når der kun er ét ark"},
                    "filnavn": {"type": "string", "description": "Filnavn uden endelse; '.xlsx' tilføjes"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pptx_create",
            "description": (
                "Opret en PowerPoint-præsentation (.pptx) og få et download-link. "
                "Forside + én slide pr. element i `slides`."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "titel": {"type": "string", "description": "Præsentationens titel (forside)"},
                    "undertitel": {"type": "string", "description": "Undertitel på forsiden"},
                    "slides": {
                        "type": "array",
                        "description": "Slides: [{titel, punkter: [...], note}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "titel": {"type": "string"},
                                "punkter": {"type": "array", "items": {"type": "string"}},
                                "note": {"type": "string"},
                            },
                        },
                    },
                    "filnavn": {"type": "string", "description": "Filnavn uden endelse; '.pptx' tilføjes"},
                },
                "required": ["slides"],
            },
        },
    },
]


# ── PDF ───────────────────────────────────────────────────────────────────

def _exec_pdf_create(args: dict[str, Any]) -> dict[str, Any]:
    """Opret en PDF af overskrifter, afsnit og punktopstilling."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (ListFlowable, ListItem, Paragraph,
                                        SimpleDocTemplate, Spacer)
    except Exception as exc:  # en manglende afhaengighed er en DRIFTS-fejl, ikke et tomt svar
        logger.warning("reportlab utilgaengelig: %s", exc)
        return {"status": "error", "error": f"reportlab mangler: {exc}"}

    titel = str(args.get("titel") or args.get("title") or "").strip()
    filnavn = _filnavn(str(args.get("filnavn") or args.get("filename") or titel),
                       "dokument", ".pdf")
    linjer = _linjer(args.get("indhold") or args.get("content"))

    try:
        from xml.sax.saxutils import escape as _esc
        sti = Path(tempfile.mkdtemp(prefix="jarvis-pdf-")) / filnavn
        doc = SimpleDocTemplate(str(sti), pagesize=A4,
                                leftMargin=20 * mm, rightMargin=20 * mm,
                                topMargin=20 * mm, bottomMargin=20 * mm,
                                title=titel or filnavn)
        stil = getSampleStyleSheet()
        flow: list[Any] = []
        if titel:
            flow.append(Paragraph(_esc(titel), stil["Title"]))
            flow.append(Spacer(1, 6 * mm))

        punkter: list[Any] = []

        def _tom_punkter() -> None:
            if punkter:
                flow.append(ListFlowable(
                    [ListItem(Paragraph(_esc(t), stil["BodyText"])) for t in punkter],
                    bulletType="bullet", start="•", leftIndent=12,
                ))
                punkter.clear()

        for slags, tekst, _n in _blokke(linjer):
            if slags == "punkt":
                punkter.append(tekst)
                continue
            _tom_punkter()
            if slags == "tom":
                flow.append(Spacer(1, 3 * mm))
            elif slags == "h1":
                flow.append(Paragraph(_esc(tekst), stil["Heading1"]))
            elif slags == "h2":
                flow.append(Paragraph(_esc(tekst), stil["Heading2"]))
            elif slags == "h3":
                flow.append(Paragraph(_esc(tekst), stil["Heading3"]))
            elif slags == "nummer":
                flow.append(Paragraph(_esc(f"• {tekst}"), stil["BodyText"]))
            else:
                flow.append(Paragraph(_esc(tekst), stil["BodyText"]))
        _tom_punkter()
        if not flow:
            flow.append(Paragraph(_esc(filnavn), stil["BodyText"]))
        doc.build(flow)
    except Exception as exc:
        logger.warning("pdf_create fejlede: %s", exc)
        return {"status": "error", "error": f"kunne ikke bygge PDF: {exc}"}

    return _udgiv(sti, filnavn, args)


# ── Word ──────────────────────────────────────────────────────────────────

def _exec_docx_create(args: dict[str, Any]) -> dict[str, Any]:
    """Opret et Word-dokument af overskrifter, afsnit og punktopstilling."""
    try:
        import docx
    except Exception as exc:  # en manglende afhaengighed er en DRIFTS-fejl, ikke et tomt svar
        logger.warning("python-docx utilgaengelig: %s", exc)
        return {"status": "error", "error": f"python-docx mangler: {exc}"}

    titel = str(args.get("titel") or args.get("title") or "").strip()
    filnavn = _filnavn(str(args.get("filnavn") or args.get("filename") or titel),
                       "dokument", ".docx")
    linjer = _linjer(args.get("indhold") or args.get("content"))

    try:
        sti = Path(tempfile.mkdtemp(prefix="jarvis-docx-")) / filnavn
        d = docx.Document()
        if titel:
            d.add_heading(titel, level=0)
        for slags, tekst, niveau in _blokke(linjer):
            if slags == "tom":
                continue
            if slags in ("h1", "h2", "h3"):
                d.add_heading(tekst, level=niveau)
            elif slags == "punkt":
                d.add_paragraph(tekst, style="List Bullet")
            elif slags == "nummer":
                d.add_paragraph(tekst, style="List Number")
            else:
                d.add_paragraph(tekst)
        d.save(str(sti))
    except Exception as exc:
        logger.warning("docx_create fejlede: %s", exc)
        return {"status": "error", "error": f"kunne ikke bygge Word: {exc}"}

    return _udgiv(sti, filnavn, args)


# ── Excel ─────────────────────────────────────────────────────────────────

def _exec_xlsx_create(args: dict[str, Any]) -> dict[str, Any]:
    """Opret et regneark. `ark` = [{navn, kolonner, rækker}] eller `rækker`."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception as exc:  # en manglende afhaengighed er en DRIFTS-fejl, ikke et tomt svar
        logger.warning("openpyxl utilgaengelig: %s", exc)
        return {"status": "error", "error": f"openpyxl mangler: {exc}"}

    titel = str(args.get("titel") or args.get("title") or "").strip()
    filnavn = _filnavn(str(args.get("filnavn") or args.get("filename") or titel),
                       "regneark", ".xlsx")

    # Normalisér til en liste af ark. Bagudkompatibelt: en flad `rækker`-liste
    # giver ét ark, så et enkelt kald ikke kræver det fulde format.
    ark_raw = args.get("ark") or args.get("sheets")
    if isinstance(ark_raw, dict):
        ark_raw = [ark_raw]
    if not isinstance(ark_raw, list) or not ark_raw:
        raekker = args.get("rækker") or args.get("rows") or []
        kolonner = args.get("kolonner") or args.get("columns") or []
        ark_raw = [{"navn": titel or "Ark1", "kolonner": kolonner, "rækker": raekker}]

    try:
        sti = Path(tempfile.mkdtemp(prefix="jarvis-xlsx-")) / filnavn
        wb = Workbook()
        wb.remove(wb.active)
        hoved = Font(bold=True, color="FFFFFF")
        fyld = PatternFill("solid", fgColor="2F4F6F")

        for i, spec in enumerate(ark_raw):
            if not isinstance(spec, dict):
                continue

            # æ/ø/å i JSON-feltnavne er en tavs fælde: schemaet skriver
            # `rækker`, men den der kalder skriver naturligt `raekker`, og en
            # manglende match gav en fil med OVERSKRIFTER OG NUL RÆKKER —
            # ingen fejl, bare en tom tabel der ser ud som en tabel. Målt
            # 27/10-2026 på det første rigtige kald. Begge stavemåder læses.
            def _felt(*noegler: str) -> Any:
                for k in noegler:
                    v = spec.get(k)
                    if v:
                        return v
                return []

            navn = str(_felt("navn", "name") or f"Ark{i + 1}")[:31]
            kol = _felt("kolonner", "columns")
            rk = _felt("rækker", "raekker", "rows")
            if isinstance(kol, str):
                kol = [k.strip() for k in kol.split(",") if k.strip()]
            if not isinstance(kol, list):
                kol = []
            if not isinstance(rk, list):
                rk = []

            ws = wb.create_sheet(title=navn)
            start = 1
            if kol:
                for c, navn_k in enumerate(kol, start=1):
                    cell = ws.cell(row=1, column=c, value=str(navn_k))
                    cell.font = hoved
                    cell.fill = fyld
                    cell.alignment = Alignment(horizontal="left")
                start = 2
            elif rk and isinstance(rk[0], list):
                # Ingen header angivet: brug første række som header — den
                # læses som tabel af både mennesker og Excel.
                for c, navn_k in enumerate(rk[0], start=1):
                    cell = ws.cell(row=1, column=c, value=str(navn_k))
                    cell.font = hoved
                    cell.fill = fyld
                rk = rk[1:]
                start = 2

            for r, raekke in enumerate(rk, start=start):
                if isinstance(raekke, (list, tuple)):
                    for c, vaerdi in enumerate(raekke, start=1):
                        ws.cell(row=r, column=c, value=vaerdi)
                else:
                    ws.cell(row=r, column=1, value=raekke)

            # Kolonnebredde efter længste værdi — en tabel der er klippet af
            # skærmen er teknisk korrekt og praktisk ubrugelig.
            bredder: dict[int, int] = {}
            for raekke in ws.iter_rows(values_only=True):
                for c, vaerdi in enumerate(raekke, start=1):
                    if vaerdi is None:
                        continue
                    bredder[c] = max(bredder.get(c, 8), min(len(str(vaerdi)) + 2, 60))
            for c, b in bredder.items():
                ws.column_dimensions[get_column_letter(c)].width = b

        if not wb.sheetnames:
            wb.create_sheet(title="Ark1")
        wb.save(str(sti))
    except Exception as exc:
        logger.warning("xlsx_create fejlede: %s", exc)
        return {"status": "error", "error": f"kunne ikke bygge regneark: {exc}"}

    return _udgiv(sti, filnavn, args)


# ── PowerPoint ────────────────────────────────────────────────────────────

def _exec_pptx_create(args: dict[str, Any]) -> dict[str, Any]:
    """Opret en præsentation. `slides` = [{titel, punkter, note}]."""
    try:
        from pptx import Presentation
        from pptx.util import Pt
    except Exception as exc:  # en manglende afhaengighed er en DRIFTS-fejl, ikke et tomt svar
        logger.warning("python-pptx utilgaengelig: %s", exc)
        return {"status": "error", "error": f"python-pptx mangler: {exc}"}

    titel = str(args.get("titel") or args.get("title") or "").strip()
    filnavn = _filnavn(str(args.get("filnavn") or args.get("filename") or titel),
                       "praesentation", ".pptx")

    slides_raw = args.get("slides") or args.get("ark") or []
    if isinstance(slides_raw, dict):
        slides_raw = [slides_raw]
    if not isinstance(slides_raw, list):
        slides_raw = []

    try:
        sti = Path(tempfile.mkdtemp(prefix="jarvis-pptx-")) / filnavn
        prs = Presentation()
        # Layout 0 = titel-slide, layout 1 = titel + indhold.
        forside = prs.slides.add_slide(prs.slide_layouts[0])
        forside.shapes.title.text = titel or filnavn
        if len(forside.placeholders) > 1:
            forside.placeholders[1].text = str(args.get("undertitel") or "")

        for spec in slides_raw:
            if not isinstance(spec, dict):
                continue
            s = prs.slides.add_slide(prs.slide_layouts[1])
            s.shapes.title.text = str(spec.get("titel") or spec.get("title") or "")
            punkter = spec.get("punkter") or spec.get("bullets") or []
            if isinstance(punkter, str):
                punkter = [p.strip() for p in punkter.splitlines() if p.strip()]
            if not isinstance(punkter, list):
                punkter = []
            krop = s.placeholders[1].text_frame
            krop.clear()
            for i, p in enumerate(punkter):
                afsnit = krop.paragraphs[0] if i == 0 else krop.add_paragraph()
                afsnit.text = str(p)
                afsnit.font.size = Pt(18)
            note = str(spec.get("note") or "").strip()
            if note:
                s.notes_slide.notes_text_frame.text = note
        prs.save(str(sti))
    except Exception as exc:
        logger.warning("pptx_create fejlede: %s", exc)
        return {"status": "error", "error": f"kunne ikke bygge præsentation: {exc}"}

    return _udgiv(sti, filnavn, args)
