"""Vaernet slaar nu op DÉR HVOR FILERNE BOR — Fase 6.

Jarvis pegede paa `simple_tools_explore.py:126`: `if target == "workstation":
tjek_paastande = None`. Vaernet var slaaet HELT fra netop paa den sti hvor han
undersoeger Bjoerns egen maskine — dér hvor en fabrikeret rapport koster mest.

MEN UNDTAGELSEN VAR RIGTIG som den stod. `_rod()` peger paa CONTAINERENS repo,
saa et opslag dér ville have flaget hver eneste sti paa Bjoerns maskine som
opdigtet. Det er den modsatte fejl: falske anklager i stedet for manglende
vaern.

To ting skulle derfor rettes foer vaernet kunne taendes:

  1. Stierne skal slaas op OVER BROEN, ikke i containeren.
  2. Regexen matchede slet ikke ABSOLUTTE stier. En workstation-rapport skriver
     naturligt `/home/bs/projekt/src/main.ts`, saa vaernet ville have vaeret
     koblet paa og alligevel BLINDT.
"""
from __future__ import annotations

from core.services.explore_claim_check import tjek_paastande


# ── 2: absolutte stier ───────────────────────────────────────────────────

def test_absolutte_stier_efterproeves_nu():
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts",
                   findes_fn=lambda s: set_af.append(s) or True)
    assert set_af == ["/home/bs/p/main.ts"]


def test_absolut_sti_MED_linjenummer():
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts:42",
                   findes_fn=lambda s: set_af.append(s) or True)
    assert set_af == ["/home/bs/p/main.ts"]


def test_relative_stier_virker_stadig():
    d = tjek_paastande("se src/app/main.ts", findes_fn=lambda s: False)
    assert d["kontrolleret"] == 1 and d["holder"] is False


def test_URLer_er_ikke_filstier():
    """`https:` fejler paa kolon, `//host` paa den anden skraastreg."""
    assert tjek_paastande("se https://example.com/a/b.js",
                          findes_fn=lambda s: False)["kontrolleret"] == 0


# ── 1: uafgjort er hverken fund eller fejl ───────────────────────────────

def test_UAFGJORT_taeller_hverken_som_fund_eller_fejl():
    """`_operator_file_exists` svarer `None` naar broen ikke kan afgoere det.
    Et vaern der gaetter er vaerre end intet — det ville anklage aegte filer."""
    d = tjek_paastande("se /home/bs/p/main.ts", findes_fn=lambda s: None)
    assert d == {"kontrolleret": 0, "fejl": [], "holder": True}


def test_en_tjekker_der_KASTER_doemmer_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts",
                       findes_fn=lambda s: (_ for _ in ()).throw(RuntimeError("bro nede")))
    assert d["kontrolleret"] == 0 and d["holder"] is True


def test_en_FALSK_sti_over_broen_falder():
    d = tjek_paastande("se /home/bs/p/opdigtet.ts", findes_fn=lambda s: False)
    assert d["holder"] is False
    assert "findes ikke" in d["fejl"][0]


def test_linje_indhold_efterproeves_IKKE_over_broen():
    """Det ville kraeve en fuld filhentning pr. citat. Eksistensen er det
    billige og det vigtigste — «filen findes ikke» er den typiske fabrikation.
    """
    d = tjek_paastande("se /home/bs/p/main.ts:9999:noget der ikke staar der",
                       findes_fn=lambda s: True)
    assert d["holder"] is True


# ── koblingen ────────────────────────────────────────────────────────────

def _kode_uden_kommentarer(fn) -> str:
    """Kommentarerne CITERER den gamle kode for at forklare hvorfor den er
    vaek. En ren tekst-soegning falder derfor over sin egen forklaring — samme
    faelde som ramte `as_completed`-testen i raadet."""
    import inspect
    linjer = [ln for ln in inspect.getsource(fn).splitlines()
              if not ln.lstrip().startswith("#")]
    return "\n".join(linjer)


def test_workstation_slaar_ikke_laengere_vaernet_FRA():
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    # Praecis den gamle to-linjers form. En bredere soegning ramte
    # `egnede_modeller = tjek_paastande = None`, som er import-fejl-faldbacken
    # og skal blive — den har intet med workstation at goere.
    linjer = kode.splitlines()
    for i, ln in enumerate(linjer[:-1]):
        if 'if target == "workstation":' in ln:
            assert "tjek_paastande = None" not in linjer[i + 1], (
                "vaernet slaas stadig helt fra for workstation")
    assert "_operator_file_exists" in kode
    assert "findes_fn=_bro_tjek" in kode


def test_runtime_stien_bruger_stadig_containerens_repo():
    """Broen er KUN for workstation. Et runtime-explore skal slaa op lokalt."""
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    assert 'if target == "workstation":' in kode
    assert "else tjek_paastande(svar)" in kode


# ── citater efterproeves ogsaa over broen — Jarvis' forslag ─────────────
#
# Han spurgte: «er det dyrere end det er vaerd, eller er det den naeste billige
# sejr?» — og bad udtrykkeligt om at det blev maalt, ikke gaettet.
#
# MAALT 10/9-2026 mod hans egen maskine:
#     _operator_file_exists   0,08 s   (kun eksistens)
#     operator_grep           0,08 s   (fil + linjenummer + tekst)
#
# Samme pris, mere i svaret. Den billige sejr var der.


def test_et_citat_der_PASSER_holder():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: True)
    assert d["holder"] is True and d["kontrolleret"] == 1


def test_et_citat_paa_den_FORKERTE_linje_falder():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: False)
    assert d["holder"] is False
    assert "indeholder ikke" in d["fejl"][0]


def test_fragmentet_sendes_NOEGENT_videre():
    """Modellen omskriver whitespace og klipper linjen. Vi soeger paa kernen,
    ikke paa en eksakt streng — samme leniens som den lokale sti bruger."""
    set_af = []
    tjek_paastande("se /home/bs/p/main.ts:42:`const foo(bar)` ",
                   findes_fn=lambda s: True,
                   linje_fn=lambda s, n, f: set_af.append(f) or True)
    assert set_af == ["const foo"]


def test_UAFGJORT_citat_doemmes_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: None)
    assert d["holder"] is True


def test_en_linje_tjekker_der_KASTER_doemmer_ikke():
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True,
                       linje_fn=lambda s, n, f: (_ for _ in ()).throw(RuntimeError("bro nede")))
    assert d["holder"] is True


def test_uden_linje_tjekker_efterproeves_kun_eksistensen():
    """Bagudkompatibelt: en kalder der kun giver `findes_fn` faar samme
    opfoersel som foer."""
    d = tjek_paastande("se /home/bs/p/main.ts:42:const foo",
                       findes_fn=lambda s: True)
    assert d["holder"] is True and d["kontrolleret"] == 1


def test_workstation_stien_giver_BEGGE_tjekkere_med():
    from core.tools import simple_tools_explore as E
    kode = _kode_uden_kommentarer(E._exec_explore)
    assert "linje_fn=_bro_linje" in kode
    assert "_exec_operator_grep" in kode
