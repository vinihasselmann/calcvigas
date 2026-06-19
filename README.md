# TESTESVIGAS

Aplicativo Streamlit para calculo e verificacao de elementos estruturais pre-moldados.

## Requisitos

- Python 3.11 ou superior
- Git

## Instalar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Executar

```powershell
streamlit run app.py
```

## Testar

```powershell
python -m pytest
```

## Observacoes para versionamento

O repositorio ignora caches, ambientes virtuais, saidas geradas, bancos SQLite locais e arquivos de debug em `data/debug_inputs/`.

Arquivos essenciais mantidos no versionamento incluem codigo-fonte, testes, `requirements.txt`, configuracao publica do Streamlit e a planilha base `data/laje_alv_base.xlsx`.
