"""Tegn en graf til PNG — saa den kan leveres som en almindelig billed-blok.

Trin 2 af «visuelle svar» (Bjoern 6/10-2026). Valget af PNG frem for SVG er
ikke smag: desk kan tegne begge, men mobilen har **ingen WebView** og kan derfor
ikke rendere en SVG-streng uden ny native kode. En billed-blok renderes
DERIMOD allerede af baade desk og mobil, saa en PNG naar begge flader uden en
eneste linje klient-kode.

**Model-markup krydser aldrig en graense.** Jarvis skriver DATA — en smal spec
med serier og navne — og matplotlib tegner. Det er samme holdning som
`MermaidBlock`, hvis egen kommentar siger at `dangerouslySetInnerHTML` sidder
paa «bibliotekets tilsigtede API, ikke model-HTML».

**Temaet er et kompromis, ikke en forglemmelse.** En PNG kan ikke foelge
klientens lyse/moerke tema. Baggrunden er derfor gennemsigtig, og akser, tekst
og gitter tegnes i en mellemgraa (`#8a8a8a`) der kan laeses paa baade desks
moerke flade og en lys mobil. Serie-farverne er valgt med samme krav.
"""

from __future__ import annotations

import io
from typing import Any

#: Graenser. En spec er model-skrevet, saa den skal ikke kunne bede om en
#: 50 MB-fil eller en figur der tager et minut at tegne.
MAX_SERIER = 8
MAX_PUNKTER = 500
_FIG_BREDDE = 7.2
_FIG_HOEJDE = 3.4
_DPI = 144

#: Mellemgraa der kan laeses paa baade moerk og lys flade.
_FORGRUND = "#8a8a8a"
#: Serie-farver: maettede nok til moerk baggrund, moerke nok til lys.
_FARVER = ("#4ea1d3", "#e2795b", "#6ab04c", "#c678dd",
           "#d4a017", "#4db6ac", "#ef6292", "#9aa0a6")

SLAGS = ("linje", "soejle", "punkt")


class GrafFejl(ValueError):
    """En spec vi ikke kan tegne. Baerer en besked der kan vises til Jarvis."""


def _tal_liste(v: Any, navn: str) -> list[float]:
    if not isinstance(v, (list, tuple)):
        raise GrafFejl(f"{navn} skal vaere en liste af tal")
    ud: list[float] = []
    for x in v:
        try:
            ud.append(float(x))
        except (TypeError, ValueError):
            raise GrafFejl(f"{navn} indeholder noget der ikke er et tal: {x!r}") from None
    return ud


def _validér(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    slags = str(spec.get("slags") or "linje").strip().lower()
    if slags not in SLAGS:
        raise GrafFejl(f"ukendt slags {slags!r} — vaelg mellem {', '.join(SLAGS)}")
    raa = spec.get("serier")
    if not isinstance(raa, (list, tuple)) or not raa:
        raise GrafFejl("serier skal vaere en ikke-tom liste")
    if len(raa) > MAX_SERIER:
        raise GrafFejl(f"{len(raa)} serier er for mange (hoejst {MAX_SERIER})")
    serier: list[dict[str, Any]] = []
    for i, s in enumerate(raa):
        if not isinstance(s, dict):
            raise GrafFejl(f"serie {i} er ikke et objekt")
        y = _tal_liste(s.get("y"), f"serie {i} y")
        if not y:
            raise GrafFejl(f"serie {i} har ingen y-vaerdier")
        if len(y) > MAX_PUNKTER:
            raise GrafFejl(f"serie {i} har {len(y)} punkter (hoejst {MAX_PUNKTER})")
        x_raa = s.get("x")
        if x_raa is None:
            x: list[Any] = list(range(1, len(y) + 1))
        elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x_raa or [])):
            x = _tal_liste(x_raa, f"serie {i} x")
        else:
            # Tekst-x (maaneder, navne) er helt legitimt for en soejlegraf.
            x = [str(v) for v in (x_raa or [])]
        if len(x) != len(y):
            raise GrafFejl(f"serie {i}: {len(x)} x-vaerdier mod {len(y)} y-vaerdier")
        serier.append({"navn": str(s.get("navn") or f"serie {i + 1}"), "x": x, "y": y})
    return slags, serier


def tegn_graf(spec: dict[str, Any]) -> bytes:
    """Spec → PNG-bytes. Kaster `GrafFejl` paa en spec vi ikke kan tegne.

    Kaster MED VILJE frem for at returnere en tom figur: en graf uden data
    ville se ud som et svar, og en tom graf er en loegn om tallene.
    """
    slags, serier = _validér(spec)

    import matplotlib
    matplotlib.use("Agg")           # ingen skaerm paa CT105
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(_FIG_BREDDE, _FIG_HOEJDE), dpi=_DPI)
    try:
        tekst_x = any(isinstance(v, str) for s in serier for v in s["x"])
        for i, s in enumerate(serier):
            farve = _FARVER[i % len(_FARVER)]
            if slags == "linje":
                ax.plot(s["x"], s["y"], marker="o", markersize=3,
                        linewidth=1.8, color=farve, label=s["navn"])
            elif slags == "punkt":
                ax.scatter(s["x"], s["y"], s=22, color=farve, label=s["navn"])
            else:
                # Soejler forskydes saa flere serier ikke daekker hinanden.
                bredde = 0.8 / len(serier)
                pos = [j + (i - (len(serier) - 1) / 2) * bredde
                       for j in range(len(s["y"]))]
                ax.bar(pos, s["y"], width=bredde, color=farve, label=s["navn"])
                if tekst_x or slags == "soejle":
                    ax.set_xticks(range(len(s["x"])))
                    ax.set_xticklabels([str(v) for v in s["x"]])

        if spec.get("titel"):
            ax.set_title(str(spec["titel"]), color=_FORGRUND, fontsize=11)
        if spec.get("x_navn"):
            ax.set_xlabel(str(spec["x_navn"]), color=_FORGRUND, fontsize=9)
        if spec.get("y_navn"):
            ax.set_ylabel(str(spec["y_navn"]), color=_FORGRUND, fontsize=9)
        if len(serier) > 1:
            lg = ax.legend(frameon=False, fontsize=9)
            for t in lg.get_texts():
                t.set_color(_FORGRUND)

        ax.tick_params(colors=_FORGRUND, labelsize=9)
        for kant in ax.spines.values():
            kant.set_color(_FORGRUND)
            kant.set_linewidth(0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color=_FORGRUND, alpha=0.18, linewidth=0.6)
        ax.set_axisbelow(True)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches="tight")
        return buf.getvalue()
    finally:
        plt.close(fig)      # ellers laekker figurer i en langtlevende proces
