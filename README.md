# TESTESVIGAS

Aplicativo Streamlit para calculo e verificacao de elementos estruturais pre-moldados.

## Tutorial de uso

O fluxo completo de modelagem no Revit, preparacao das tabelas, calculo, conferencia e
retorno das taxas ao modelo esta em [TUTORIAL_APP_PRINCIPAL.md](TUTORIAL_APP_PRINCIPAL.md).

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
