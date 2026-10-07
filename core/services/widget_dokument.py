"""Pak model-skrevet HTML i et dokument der ikke kan naa noget.

Trin 3 af «visuelle svar» (Bjoern 6/10-2026). Det er den foerste gang
model-skrevet markup renderes i en af hans klienter, og husets hidtidige regel
har vaeret et klart NEJ: `MermaidBlock`s egen kommentar siger at
`dangerouslySetInnerHTML` sidder paa «bibliotekets tilsigtede API, ikke
model-HTML», og ANSI-renderen bygger React-spans netop saa «et fjendtligt
vaerktoejsresultat ikke kan smugle markup ind».

Reglen bliver ikke droppet — den faar en graense i stedet. **To uafhaengige lag:**

1. **Her:** HTML'en pakkes i et dokument med en CSP der naegter ALT netvaerk
   (`default-src 'none'`). Selv en perfekt sandkasse-omgaaelse kan derfor ikke
   sende noget ud, og widget'en kan ikke hente noget ind.
2. **I klienten:** dokumentet renderes i en sandkasse med en ugennemsigtig
   origin — iframe `sandbox="allow-scripts"` i desk, WebView i mobilen. Den
   har dermed ingen adgang til desks DOM, hans token eller nogen storage.

Laget her ligger paa SERVEREN med vilje: begge klienter faar samme dokument,
saa de ikke kan drive fra hinanden. En CSP glemt i én klient ville ellers vaere
et hul kun paa den flade — praecis moenstret fra
[[reference_tool_text_two_copies]].

**Der sanitiseres IKKE.** En saniteringsliste er en kapløb mod opfindsomhed og
taber. En ugennemsigtig origin uden netvaerk er en graense, ikke et gaet. Det
er ogsaa derfor `allow-same-origin` ALDRIG maa staa sammen med
`allow-scripts`: tilsammen ophaever de sandkassen.
"""

from __future__ import annotations

import json as _json

#: Et dokument er en visning, ikke en applikation. 256 KB er rigeligt til en
#: tabel, et diagram eller en lille beregner — og lille nok til at en
#: loebsk generering ikke fylder hans vedhaeftninger.
MAX_HTML_BYTES = 256 * 1024

#: Ingen netvaerk. `data:` er tilladt for billeder og fonte, saa en widget kan
#: baere sit eget indhold uden at hente noget. `unsafe-inline` for style og
#: script er netop hvad en selvstaendig widget ER — og den kan ikke misbruges
#: til exfiltration naar `default-src 'none'` staar foran.
CSP = (
    "default-src 'none'; "
    "style-src 'unsafe-inline'; "
    "script-src 'unsafe-inline'; "
    "img-src data:; "
    "font-src data:; "
    "form-action 'none'; "
    "base-uri 'none'"
)


#: Hvad en widget-initieret besked maerkes med.
#:
#: Staaende regel (Bjoern 3/10-2026): «alt der ikk er mig der har skrevet fra
#: composer skal mærkes som fra systemet». Hans begrundelse var konkret: umaerket
#: injiceret tekst startede runder i hans navn, fordi Jarvis troede beskederne
#: var hans.
#:
#: Memoryen navngiver tre fejl i den note der udloeste reglen, og maerket her
#: undgaar alle tre: det er MAERKET (praefikset siger hvem der skrev), det er
#: IKKE i jeg-form (det er en kilde-angivelse, ikke en stemme), og det baerer
#: INGEN invitation (ingen «sig til, saa…» der paa naeste runde laeses som om
#: nogen har sagt til).
#:
#: Teksten bygges HER paa serveren og bages ind i dokumentet, saa desk og mobil
#: kun saetter den foran. Et format skrevet i to klienter driver fra hinanden —
#: det er praecis `tool_text_two_copies`.
def maerke(titel: str = "") -> str:
    # `<` og `>` fjernes som i <title>-elementet. Ikke for sikkerhedens skyld —
    # JSON-indbagningen i scriptet daekker det — men fordi maerket ender som
    # praefiks paa en besked i HANS chat, og HTML-skrald dér er stoej.
    t = (titel or "").replace("<", "").replace(">", "").strip()
    return f"[fra widget «{t}»]" if t else "[fra widget]"


class WidgetFejl(ValueError):
    """En HTML vi ikke vil pakke. Beskeden gaar tilbage til Jarvis."""


def pak(html: str, *, titel: str = "") -> str:
    """Model-HTML → et komplet dokument med CSP, klar til en sandkasse."""
    raa = (html or "").strip()
    if not raa:
        raise WidgetFejl("html er tom — der er ingenting at vise")
    n = len(raa.encode("utf-8"))
    if n > MAX_HTML_BYTES:
        raise WidgetFejl(
            f"html er {n} bytes (hoejst {MAX_HTML_BYTES}) — en widget er en visning, "
            f"ikke en applikation"
        )
    if "<!doctype" in raa[:200].lower() or "<html" in raa[:200].lower():
        # Et helt dokument ville baere sin EGEN <head> og dermed sin egen
        # (manglende) CSP. Vi pakker fragmenter, saa CSP'en altid er vores.
        raise WidgetFejl(
            "send et HTML-FRAGMENT uden <html>/<head>/<!doctype> — dokumentet "
            "og dets sikkerheds-politik laegges af serveren"
        )
    t = (titel or "widget").replace("<", "").replace(">", "").strip() or "widget"
    # Maerket bages ind som en JSON-streng, saa en titel med citationstegn eller
    # en afsluttende `</script>` ikke kan bryde ud af scriptet.
    _SEND_PROMPT_JS = _SEND_PROMPT_JS_TMPL % _json.dumps(
        maerke(titel), ensure_ascii=False
    ).replace("</", "<\\/")
    return (
        "<!doctype html>\n<html><head><meta charset=\"utf-8\">\n"
        f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
        f"<title>{t}</title>\n"
        "<style>\n"
        "  :root { color-scheme: light dark; }\n"
        "  html,body { margin:0; padding:0; background:transparent; }\n"
        # 7/10-2026 (Bjoern): «widget i desk boer foelge stoerrelsen paa
        # widget'et — det ender i en frame med scroll». Aarsagen var her:
        # uden en overflow-regel kunne dokumentet selv scrolle internt, og
        # `scrollHeight` maaler saa kun det SYNLIGE — hoejden blev meldt for
        # lavt, og rammen fik sit eget rullepanel. Dokumentet skal vokse med
        # sit indhold, ikke klippe det: klienten saetter hoejden.
        "  html,body { overflow:hidden; }\n"
        "  body { font:14px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;\n"
        "         color:#8a8a8a; padding:12px; }\n"
        "  a { pointer-events:none; text-decoration:none; color:inherit; }\n"
        "</style>\n"
        f"<script>{_SEND_PROMPT_JS}</script>\n"
        "</head><body>\n"
        f"{raa}\n"
        "</body></html>\n"
    )


#: `jarvis.sendPrompt(tekst)` — widget'ens eneste vej TILBAGE i samtalen.
#:
#: Maerket foelger med i beskeden, saa klienten ikke skal kende formatet.
#: Klienten validerer alligevel afsender, form og takt: en widget koerer
#: model-skrevet JS, og en loekke der kalder sendPrompt ville ellers kunne
#: spamme samtalen.
_SEND_PROMPT_JS_TMPL = """
(function () {
  var MAERKE = %s;
  function send(tekst) {
    if (typeof tekst !== 'string') return false;
    var t = tekst.trim();
    if (!t) return false;
    var pakke = { type: 'jarvis-widget-prompt', tekst: t, maerke: MAERKE };
    try {
      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify(pakke));
      } else {
        parent.postMessage(pakke, '*');
      }
      return true;
    } catch (e) { return false; }
  }
  window.jarvis = Object.freeze({ sendPrompt: send });
})();
"""
