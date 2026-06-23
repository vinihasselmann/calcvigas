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
    assert b"Memorial de calculo da laje" in pdf
    assert b"Solicitacoes e capacidade" in pdf


def test_export_memorial_pdf_generates_standalone_laje_memorial():
    pdf = export_memorial_pdf(
        pd.DataFrame(
            [
                {
                    "lp_type": "LP26,5",
                    "analise": "sem continuidade",
                    "vao": 8,
                    "sobrecarga": 500,
                    "capa": 5,
                    "fck_capa": 40,
                    "peso_proprio": 370,
                    "carga_capa": 150,
                    "carga_total": 1020,
                    "momento_fletor": 8160,
                    "forca_cortante": 4080,
                    "cabos": "6 x 12,7mm",
                    "status": "PASSA",
                }
            ]
        )
    )

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Memorial de calculo da laje" in pdf
    assert b"Dados da laje e carregamentos" in pdf
    assert b"Diagrama de momento" in pdf


def test_export_memorial_pdf_handles_no_elements():
    pdf = export_memorial_pdf(pd.DataFrame())

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Nao ha elementos" in pdf
