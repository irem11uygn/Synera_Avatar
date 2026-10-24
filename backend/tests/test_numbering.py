from app.services.numbering import next_document_no


def test_next_production_order_is_urt_2026_045(session):
    assert next_document_no(session, "URT", 2026) == "URT-2026-045"
    assert next_document_no(session, "URT", 2026) == "URT-2026-046"


def test_cutting_and_sale_numbers_follow_scenario_format(session):
    assert next_document_no(session, "PRC", 2026) == "PRC-2026-012"
    assert next_document_no(session, "SAT", 2026) == "SAT-2026-0101"


def test_new_prefix_or_year_starts_from_one(session):
    assert next_document_no(session, "TRF", 2026) == "TRF-2026-0001"
    assert next_document_no(session, "URT", 2027) == "URT-2027-001"
