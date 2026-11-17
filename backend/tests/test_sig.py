from app.services.sig import medication_sig


def test_medication_sig_abbreviates_common_directions():
    assert medication_sig("10 mg", "PO", "Once daily") == "10 mg PO QD"
    assert medication_sig("1", "oral", "twice daily") == "1 PO BID"
    assert medication_sig("2 puffs", "Inhaled", "Every 4 hours as needed") == "2 puffs INH Q4H PRN"
    assert medication_sig("5 mg", "PO", "at bedtime") == "5 mg PO QHS"


def test_medication_sig_keeps_unknown_frequency_text():
    assert medication_sig("10 mg", "PO", "with breakfast") == "10 mg PO with breakfast"
