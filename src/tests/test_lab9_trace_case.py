import pytest

pytestmark = pytest.mark.student


def test_ticket_delay_never_overrules_db_for_c002():
    from lab9.trace_case import investigate

    broken = investigate("seeded_regression", "C-002", 11)["trial"]
    fixed = investigate("fixed", "C-002", 11)["trial"]

    assert broken["events"][2]["kind"] == "model_override"
    assert broken["snapshot"]["refund_vnd"] == 20000
    assert not broken["lab8_pass"]

    assert all(event["kind"] != "model_override" for event in fixed["events"])
    assert fixed["snapshot"]["refund_vnd"] == 0
    assert fixed["result"]["status"] == "denied"
    assert fixed["lab8_pass"]
