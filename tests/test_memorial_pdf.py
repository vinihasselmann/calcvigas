import pandas as pd

from engine.structural_frame import run_frame_cases, sample_frame_table
from ui.memorial_pdf import export_memorial_pdf


def test_export_memorial_pdf_generates_pdf_for_frame_beams():
    results = run_frame_cases(sample_frame_table())

    pdf = export_memorial_pdf(results)

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Memorial de calculo" in pdf
    assert b"Solicitacoes e verificacoes" in pdf
    assert b"Armaduras e taxas" in pdf
    assert b"Momento solicitante" in pdf
    assert b"Tensoes de servico" in pdf


def test_export_memorial_pdf_handles_no_beams():
    pdf = export_memorial_pdf(pd.DataFrame([{"tipo_elemento": "LAJE", "status": "PASSA"}]))

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Nao ha vigas" in pdf
