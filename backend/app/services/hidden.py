"""Names that must never appear in a response a student can read.

The API speaks camelCase, so both spellings are listed. Notes still use a
`diagnoses` field of their own; that name is not hidden.
"""

HIDDEN_FOR_STUDENTS = {
    "answer_key",
    "answerKey",
    "expected_diagnoses",
    "expectedDiagnoses",
    "expected_cpt_codes",
    "expectedCptCodes",
    "plan_points",
    "planPoints",
    "triggers",
    "rubric",
    "answer_key_released_at",
    "answerKeyReleasedAt",
}


def hidden_keys(payload) -> list[str]:
    found: list[str] = []
    _walk(payload, found)
    return found


def assert_no_hidden(payload) -> None:
    found = hidden_keys(payload)
    if found:
        raise AssertionError(f"Hidden keys leaked: {sorted(set(found))}")


def _walk(node, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in HIDDEN_FOR_STUDENTS:
                found.append(key)
            _walk(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, found)
