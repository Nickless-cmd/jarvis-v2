from core.services.reasoning_prefilter import prefilter


def test_number_claim_trips_fact_gate():
    assert "fact_gate" in prefilter("The table now has 4231 rows.", ctx={})


def test_action_intent_trips_commit_gates():
    classes = prefilter("I'll now run the deploy script.", ctx={})
    assert "decision_gate" in classes and "veto" in classes


def test_mutation_assert_trips_verification():
    assert "verification" in prefilter("Done - I wrote the file successfully.", ctx={})


def test_mutation_with_verify_hint_does_not_trip_verification():
    assert "verification" not in prefilter("I wrote the file and the tool result confirmed it.", ctx={})


def test_other_user_mention_trips_privacy():
    assert "cross_user_share" in prefilter("I'll mention mikkel's data here.", ctx={}, other_user_ids=["mikkel"])


def test_clean_reasoning_trips_nothing():
    assert prefilter("Let me think about the user's question.", ctx={}) == set()


def test_empty_is_empty():
    assert prefilter("", ctx={}) == set()
