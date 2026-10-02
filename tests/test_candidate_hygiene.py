"""Test af kandidat-hygiejnen (2/10-2026).

Bjørn spurgte «hvorfor så mange, og hvordan filtrerer vi støj fra så det ikke
sker igen». Målingen gav 26.761 rækker for 3.361 unikke nøgler. Testene her
dækker de to hjælpere der bærer rettelsen, og de pinner især de egenskaber
der er lette at ødelægge ved et uheld: idempotensen (domænet normaliseres to
steder i kæden) og filterets konservatisme (en ægte kendsgerning må ikke
forsvinde).
"""
from core.services.candidate_hygiene import (
    candidate_domain_tokens,
    is_transient_line,
    normalize_candidate_domain,
)


def test_normalize_er_idempotent():
    """Domænet normaliseres både hvor forslaget fødes og hvor nøglen bygges.

    Kan de to steder forskyde hinanden, får samme sag to nøgler — præcis den
    fejl der gav 202 domæner for ~3-5 opgaver. Idempotensen er bindeleddet.
    """
    raw = "l-s-adb-outputtet-i-den-synlige-k-rsel-og"
    once = normalize_candidate_domain(raw)
    assert normalize_candidate_domain(once) == once


def test_normalize_fjerner_stopord_men_bevarer_raekkefoelge():
    """Stopord ryger; rækkefølgen bliver.

    Rækkefølgen blev bevidst bevaret efter en måling: sortering flyttede
    ingen af de faktiske dublet-nøgler, men omdøbte hver eksisterende nøgle
    og brød fem tests. `user-name` skal derfor blive `user-name`.
    """
    assert normalize_candidate_domain("user-name") == "user-name"
    assert normalize_candidate_domain("repo-context") == "repo-context"
    assert normalize_candidate_domain("l-s-adb-outputtet-i-den-synlige") == "l-s-adb-outputtet-synlige"


def test_normalize_har_altid_en_vaerdi():
    """Tomt eller ren-stopord-input må ikke give en tom nøgle-del."""
    assert normalize_candidate_domain("") == "carried-context"
    assert normalize_candidate_domain("af i den det") == "carried-context"
    assert normalize_candidate_domain(None) == "carried-context"


def test_normalize_kapper_laengden():
    lang = "-".join(f"ord{index}" for index in range(40))
    assert len(normalize_candidate_domain(lang, max_tokens=5).split("-")) == 5


def test_tokens_taaler_punktum_og_store_bogstaver():
    assert candidate_domain_tokens("Læs ADB-outputtet, og bekræft!") == [
        "læs",
        "adb",
        "outputtet",
        "og",
        "bekræft",
    ]


def test_transient_fanger_dato():
    assert is_transient_line("Fikset i containeren 2026-10-02") is True
    assert is_transient_line("Rettet 2/10") is True


def test_transient_fanger_skabelon_og_ojebliksbillede():
    assert is_transient_line("Bounded chronicle proposal is preparing visible abc123") is True
    assert is_transient_line("Centralen er nu grøn med 123 nerver (tidligere 122)") is True
    assert is_transient_line("The last deep session was 4 days ago") is True


def test_transient_fanger_handlingsverbum():
    assert is_transient_line("Research-lane v2 gap-spec landet og pushet") is True
    assert is_transient_line("Deployet til containeren i nat") is True


def test_transient_fanger_indholdsloes_titel():
    assert is_transient_line("Understanding of tool registry and usage") is True
    assert is_transient_line("Status of Sansernes Arkiv") is True
    assert is_transient_line("Available agent-related tools") is True


def test_transient_lader_varig_viden_passere():
    """Filteret er et net, ikke en mur.

    Prisen for at droppe en ægte kendsgerning er højere end prisen for at
    beholde en støjende linje — især efter upserten blev rettet, hvor en
    gentaget linje ikke længere koster en ny række.
    """
    assert is_transient_line("central_incidents bruger kolonnen ts, ikke created_at") is False
    assert is_transient_line("Bjørn har diskusprolaps") is False
    assert is_transient_line("Desk-klienten kræver 'wasm-unsafe-eval' i production-CSP") is False
    assert is_transient_line("") is False
