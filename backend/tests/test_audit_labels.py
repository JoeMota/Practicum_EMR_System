from app.services.audit_labels import action_label, format_detail


def test_action_labels_are_human():
    assert action_label("chart.view") == "Opened patient chart"
    assert action_label("roster.add_member") == "Added person to course"
    assert "Cosign" in action_label("note.cosign") or "Co-signed" in action_label("note.cosign")


def test_format_detail_roster_import():
    text = format_detail("roster.import", {"added": 3, "alreadyEnrolled": 1, "result": "ok"})
    assert text is not None
    assert "3 added" in text
    assert "1 already enrolled" in text


def test_format_detail_skips_result_only():
    assert format_detail("chart.view", {"result": "ok"}) is None
