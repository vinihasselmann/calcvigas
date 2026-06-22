# Importar taxas CA e CP - Revit 2020

Ferramenta Dynamo independente para ler o XLSX exportado pelo app e preencher os parametros de tipo `TAXA-CA` e `TAXA-CP` das vigas no Revit 2020.

Esta pasta nao importa nem se comunica diretamente com o app. A unica integracao e o arquivo `resultados_quadro_estrutural.xlsx`.

## Requisitos

- Autodesk Revit 2020;
- Dynamo 2.x do Revit 2020;
- no tradicional **Python Script**, com IronPython 2.7;
- Microsoft Excel instalado para os nos `ImportExcel`;
- parametros compartilhados de **tipo** `TAXA-CA` e `TAXA-CP`, do tipo **Densidade de massa**, vinculados a **Quadro estrutural**;
- identificador do tipo em `ID_ELEMENTO`, `Marca de tipo` ou, como ultimo recurso, no nome do tipo.

Feche o arquivo XLSX no Excel antes de executar o Dynamo.

## Abas e campos lidos

O script procura os campos pelos cabecalhos, e nao pelas letras das colunas:

| Aba | CA | CP |
|---|---|---|
| `VPL` | `taxa_armadura_passiva` | `taxa_armadura_protendida` |
| `VPT` | `taxa_armadura_passiva` | `taxa_armadura_protendida` |
| `VR` | `taxa_armadura_passiva` | `0` |

Tambem sao usados `id_elemento` e `status`. Somente linhas com `status = PASSA` sao elegiveis para gravacao.

## Montagem do grafo

### 1. Leitura do arquivo

1. Adicione um no **File Path** e selecione `resultados_quadro_estrutural.xlsx`.
2. Conecte-o a **File.FromPath**.
3. Crie tres nos **Data.ImportExcel**. No Revit 2020, este e o nome correto do no de leitura.
4. Conecte a saida de `File.FromPath` ao conector `file` dos tres nos `ImportExcel`.
5. Edite os Code Blocks antes de tentar conecta-los. Um Code Block vazio, exibindo
   `Seu codigo entra aqui`, ainda nao possui porta de saida.
6. Para `sheetName`, use um Code Block diferente em cada no, contendo exatamente
   `"VPL";`, `"VPT";` e `"VR";`.
7. Para `readAsStrings`, conecte um Code Block contendo `false;`.
8. Para `showExcel`, conecte outro Code Block contendo `false;`.
9. A saida `data` de cada `Data.ImportExcel` sera conectada ao no Python.

### 2. No Python

1. Adicione **Core > Scripting > Python Script**.
2. Use o botao `+` para obter cinco entradas, de `IN[0]` a `IN[4]`.
3. Cole todo o conteudo de `dynamo_python/importar_taxas.py`.
4. Conecte:

| Entrada | Conteudo |
|---|---|
| `IN[0]` | saida `data` do `ImportExcel` configurado para VPL |
| `IN[1]` | saida `data` do `ImportExcel` configurado para VPT |
| `IN[2]` | saida `data` do `ImportExcel` configurado para VR |
| `IN[3]` | `false` para previa; `true` para gravar |
| `IN[4]` | numero inteiro usado como gatilho de atualizacao |

5. Conecte `OUT` a um no **Watch**.
6. Mantenha o Dynamo em modo **Manual**.

## Execucao

1. Comece com `IN[3] = false` e `IN[4] = 1`.
2. Execute e confira os itens `PREVIA`, `NAO_ENCONTRADO`, `CONFLITO` e `ERRO`.
3. Se a previa estiver correta, altere `IN[3]` para `true` e execute novamente.
4. Para repetir a importacao depois de editar o XLSX, incremente `IN[4]` para `2`, `3`, etc. Isso impede o cache do Dynamo de reutilizar uma execucao antiga.

## Regras de seguranca

- pecas alveolares LP sao excluidas;
- cada tipo e escrito uma unica vez, mesmo que possua varias instancias;
- linhas `NAO PASSA` e `ERRO` nao sao gravadas;
- IDs duplicados com valores diferentes bloqueiam a gravacao;
- dois tipos Revit com o mesmo identificador sao reportados como conflito;
- os valores em kg/m3 sao convertidos para as unidades internas do Revit 2020;
- antes da gravacao, a taxa CA e arredondada para o multiplo de 5 mais proximo;
  valores exatamente no meio (`2,5`, `7,5`, etc.) sao arredondados para cima
  (por exemplo, `176,1842` vira `175`);
- a taxa CP e arredondada para o inteiro mais proximo, com empate tambem para cima
  (por exemplo, `20,2282` vira `20` e `20,5` vira `21`);
- nenhuma taxa e apagada quando o ID nao existe no XLSX.

## Status do relatorio

- `RESUMO`: totais da importacao;
- `PREVIA`: correspondencia valida, ainda sem gravacao;
- `GRAVADO`: parametros atualizados;
- `IGNORADO_STATUS`: linha do Excel diferente de `PASSA`;
- `NAO_ENCONTRADO`: ID do Excel nao localizado no Revit;
- `CONFLITO`: duplicidade inconsistente;
- `ERRO`: parametro ausente, somente leitura ou unidade invalida.
