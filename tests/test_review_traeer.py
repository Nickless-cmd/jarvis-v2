"""To huller i /review/changes, lukket 16/9-2026.

1. `git diff HEAD` ser kun SPOREDE filer. En helt ny fil — den slags der opstår
   hver gang Jarvis skriver et nyt modul — talte ikke med, og ruden sagde
   «ingen ændringer» over et træ fuldt af nye filer.
2. Ruten kørte kun på SERVERENS repo. Arbejdede Jarvis i Bjørns workspace, stod
   ruden tom uden at det var sandt.

Testene her rammer parsingen og formen. De kan ikke se broen — det er derfor
rutetesten nedenunder stubber den og kræver at en DØD bro siger fejl frem for
at ligne et rent træ.
"""
from apps.api.jarvis_api.routes import review_traeer as t


def test_stien_bliver_ET_ENESTE_shell_argument():
    """Stien kommer fra klienten og havner i en shell paa hans maskine.

    Foerste udgave af denne test ledte efter «; rm -rf ~» i kommandoen og
    dumpede — men shlex.quote pakker HELE stien i apostroffer, saa tegnet er
    inert netop dér. Kravet er ikke at tegnet er vaek; det er at stien er ét
    argument. Det maales med shlex.split, som er den samme regel shellen selv
    bruger.
    """
    import shlex
    for sti in ("/home/bs/mine ting/repo", "/tmp; rm -rf ~", "/x$(whoami)", "/y`id`"):
        cmd = t.kommando_for(sti)
        foerste = cmd.split(" 2>/dev/null", 1)[0]          # "cd <sti>"
        dele = shlex.split(foerste)
        assert dele[0] == "cd"
        assert dele[1] == sti, f"{sti!r} blev til {dele[1:]!r}"
        assert len(dele) == 2, f"{sti!r} blev til flere argumenter: {dele!r}"


def test_alle_fire_segmenter_i_én_kommando():
    cmd = t.kommando_for("/x")
    for stump in ("rev-parse --abbrev-ref HEAD", "diff --numstat HEAD",
                  "status --porcelain", "git diff HEAD"):
        assert stump in cmd
    assert cmd.count(t.SKILLE) == 3


def test_et_halvt_svar_kaster_ikke():
    # Et afbrudt svar er stadig bedre end ingenting — kalderen kan se at
    # grenen mangler.
    gren, numstat, status, diff = t.parse_segmenter("main")
    assert gren == "main" and numstat == "" and status == "" and diff == ""


def test_segmenterne_deles_paa_det_rigtige_sted():
    ud = f"main\n{t.SKILLE}\n3\t1\tsrc/a.py\n{t.SKILLE}\n?? ny.py\n{t.SKILLE}\ndiff --git a/src/a.py b/src/a.py\n--- a\n+++ b\n"
    gren, numstat, status, diff = t.parse_segmenter(ud)
    assert gren == "main"
    assert "src/a.py" in numstat
    assert "?? ny.py" in status
    # Diff'en indeholder selv «---» og «+++»; skilletegnet maa ikke forveksles.
    assert diff.strip().startswith("diff --git")


def test_utrackede_filer_findes_i_porcelain():
    porcelain = " M sporet.py\n?? ny.py\n?? \"med mellemrum.py\"\n?? nogen/mappe/\n"
    assert t.utrackede_fra_status(porcelain) == ["ny.py", "med mellemrum.py"]


def test_mapper_springes_over():
    # En mappe er ikke én fil, og at taelle linjer i den giver ingen mening.
    # (node_modules/ som utracket mappe maa ikke udloese en rekursiv gennemgang.)
    assert t.utrackede_fra_status("?? node_modules/\n") == []


def test_en_ny_fil_taeller_sine_linjer_som_tilfoejede():
    post = t.ny_fil_post("ny.py", b"en\nto\ntre\n")
    assert post == {"path": "ny.py", "added": 3, "removed": 0, "binary": False, "ny": True}


def test_en_ny_fil_uden_afsluttende_linjeskift_taelles_med():
    assert t.ny_fil_post("x.txt", b"kun en linje")["added"] == 1


def test_en_tom_ny_fil_er_nul_linjer_ikke_én():
    assert t.ny_fil_post("tom.txt", b"")["added"] == 0


def test_en_binaer_ny_fil_faar_ikke_opdigtede_linjetal():
    post = t.ny_fil_post("logo.png", b"\x89PNG\r\n\x1a\n\x00\x00")
    assert post["binary"] is True and post["added"] == 0


def test_ukendt_indhold_paastaar_ikke_et_linjetal():
    # Over broen henter vi ikke filernes indhold (ét kald pr. fil). Saa er
    # linjeantallet UKENDT — og 0 ville vaere et taltriget gaet.
    post = t.ny_fil_post("ny.py", None)
    assert post["ny"] is True and post["added"] == 0


def test_ny_fils_diff_har_git_hovedet_klienten_soeger_efter():
    # Klienten deler den samlede diff op ved at soege efter «diff --git a/<sti>».
    # Uden den linje ville filen staa i listen og vaere tom naar man foldede ud.
    blok = t.ny_fil_diff("src/ny.py", b"en\nto\n")
    assert blok.startswith("diff --git a/src/ny.py b/src/ny.py")
    assert "+++ b/src/ny.py" in blok
    assert "@@ -0,0 +1,2 @@" in blok
    assert blok.endswith("+en\n+to\n")


def test_binaer_ny_fil_faar_en_blok_men_ingen_linjer():
    blok = t.ny_fil_diff("logo.png", b"\x00\x01\x02")
    assert blok.startswith("diff --git a/logo.png")
    assert "Binary files" in blok
    assert "+" not in blok.split("\n")[-2]


def test_numstat_binaer_markeres():
    filer = t.numstat_til_filer("-\t-\tlogo.png\n4\t2\tsrc/a.py\n")
    assert filer[0]["binary"] is True and filer[0]["added"] == 0
    assert filer[1] == {"path": "src/a.py", "added": 4, "removed": 2,
                        "binary": False, "ny": False}


def test_en_doed_bro_siger_FEJL_ikke_rent_trae(monkeypatch):
    """Det vigtigste krav i hele filen.

    Svarer broen ikke, VED vi ikke hvad der er aendret paa hans maskine. Et tomt
    svar ville se ud som et rent trae — og de to er stik modsatte. Samme fejl
    som jobs-ruden havde, foer `bridge_ok` blev laest.
    """
    from apps.api.jarvis_api.routes import review as r
    monkeypatch.setattr("apps.api.jarvis_api.routes.chat._operator_exec",
                        lambda navn, args: {"status": "error", "error": "broen er nede"})
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "bjorn")
    svar = r.review_changes(kilde="maskine", rod="/media/projects/jarvis-v2")
    assert svar["fejl"] == "broen er nede"
    assert svar["files"] == []


def test_uden_sti_gaettes_der_ikke_paa_et_trae(monkeypatch):
    from apps.api.jarvis_api.routes import review as r
    svar = r.review_changes(kilde="maskine", rod="")
    assert "ingen sti" in svar["fejl"]


def test_maskinens_svar_samles_i_SAMME_form_som_serverens(monkeypatch):
    from apps.api.jarvis_api.routes import review as r
    from apps.api.jarvis_api.routes import review_traeer as tt
    stdout = (f"main\n{tt.SKILLE}\n4\t2\tsrc/a.py\n{tt.SKILLE}\n?? ny.py\n{tt.SKILLE}\n"
              "diff --git a/src/a.py b/src/a.py\n@@ -1 +1 @@\n-a\n+b\n")
    monkeypatch.setattr("apps.api.jarvis_api.routes.chat._operator_exec",
                        lambda navn, args: {"status": "ok", "result": {"stdout": stdout}})
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "bjorn")
    svar = r.review_changes(kilde="maskine", rod="/tmp/repo")
    assert svar["branch"] == "main"
    assert svar["kilde"] == "maskine"
    stier = [f["path"] for f in svar["files"]]
    # BEGGE dele med: den sporede OG den utrackede.
    assert stier == ["src/a.py", "ny.py"]
    assert [f for f in svar["files"] if f["path"] == "ny.py"][0]["ny"] is True


def test_serverens_trae_tager_utrackede_filer_med(tmp_path, monkeypatch):
    from apps.api.jarvis_api.routes import review as r
    monkeypatch.setattr(r, "_repo_root", lambda: tmp_path)
    (tmp_path / "ny.py").write_bytes(b"en\nto\ntre\n")

    def falsk_koer(rod, *args):
        if args[:2] == ("rev-parse", "--abbrev-ref"): return "main\n"
        if args[:2] == ("diff", "--numstat"): return ""
        if args[:2] == ("status", "--porcelain"): return "?? ny.py\n"
        return ""
    monkeypatch.setattr(r, "_kør", falsk_koer)

    svar = r.review_changes()
    assert [f["path"] for f in svar["files"]] == ["ny.py"]
    assert svar["added"] == 3            # tidligere: 0 — filen fandtes slet ikke
    assert "diff --git a/ny.py" in svar["diff"]
