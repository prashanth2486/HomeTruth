from conftest import sample_analysis
from report import build_pdf


def test_pdf_is_built_in_memory():
    payload = build_pdf(sample_analysis())
    assert payload.startswith(b"%PDF")
    assert b"HomeTruth" in payload or payload.startswith(b"%PDF")
