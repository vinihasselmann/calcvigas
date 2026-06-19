# Identificacao de lajes apoiadas em vigas - Revit 2020

Ferramenta independente para Dynamo/Revit. Esta pasta nao importa nem se comunica com o aplicativo Streamlit.

## Objetivo

O script trabalha somente com elementos da categoria **Quadro estrutural**. Ele separa as vigas das pecas alveolares de 1,25 m, procura quais pecas apoiam em cada lado da viga e grava:

- `LAJE_Marca_E`: marca da laje do lado esquerdo;
- `LAJE_Marca_D`: marca da laje do lado direito.

A marca e lida prioritariamente de `Marca de tipo` da familia alveolar. As varias pecas com a mesma marca sao tratadas como uma unica laje. Quando existe laje somente de um lado, ela e gravada em `LAJE_Marca_E`; quando pecas da mesma laje aparecem nos dois lados, a marca e gravada em ambos.

## Compatibilidade

Esta versao foi preparada para:

- Autodesk Revit 2020;
- Dynamo 2.x fornecido com o Revit 2020;
- no **Python Script** tradicional com IronPython 2.7;
- API do Revit 2020, que trabalha internamente em pes.

Nao use o no `Python Script 3`, CPython ou pacotes externos. Eles nao fazem parte da instalacao padrao do Revit 2020. O script evita recursos de Python 3 e APIs de unidades introduzidas em versoes posteriores do Revit.

## Requisitos no Revit

1. Dynamo instalado e aberto pelo Revit 2020.
2. Parametros de texto de instancia `LAJE_Marca_E` e `LAJE_Marca_D` aplicados a categoria **Quadro estrutural**.
3. Pecas alveolares modeladas como **Sistema de vigas / Quadro estrutural**.
4. Parametro `Modelo`, nome de tipo ou nome de familia identificando `LP15`, `LP20`, `LP26,5`, `LP32`, `LP40` ou `LP50`.
5. `Marca de tipo` preenchida nas pecas alveolares. Todas as pecas que formam a mesma laje devem possuir a mesma marca.
6. Vigas e pecas alveolares no mesmo arquivo Revit. Modelos vinculados nao sao tratados nesta primeira versao.

## Criacao dos parametros

Antes de executar o Dynamo, confirme no Revit 2020:

1. Abra **Gerenciar > Parametros do projeto**.
2. Crie ou adicione `LAJE_Marca_E` como parametro de **instancia**, tipo **Texto**.
3. Aplique o parametro a categoria **Quadro estrutural**.
4. Repita para `LAJE_Marca_D`.
5. Confirme que os tipos das pecas alveolares possuem `Marca de tipo` preenchida.

## Montagem do grafo no Dynamo do Revit 2020

1. No Revit 2020, abra **Gerenciar > Dynamo**.
2. Crie um grafo novo e altere o modo de execucao para **Manual**.
3. Adicione o no **Core > Scripting > Python Script**. Use o no tradicional, baseado em IronPython 2.7.
4. Use o botao `+` do no Python para deixar cinco portas de entrada, de `IN[0]` ate `IN[4]`.
5. Clique com o botao direito no no e escolha **Editar**.
6. Apague o codigo de exemplo e cole todo o conteudo de `dynamo_python/identificar_lajes_apoio.py`.
7. Crie cinco **Code Block** e conecte os valores indicados abaixo.

| Entrada | Valor | Padrao |
|---|---|---|
| `IN[0]` | Lista opcional de vigas; `null` coleta todas | `null` |
| `IN[1]` | Lista opcional de pecas alveolares; `null` classifica automaticamente | `null` |
| `IN[2]` | Folga alem da face da viga, em cm | `5` |
| `IN[3]` | Tolerancia vertical de busca, em cm | `150` |
| `IN[4]` | Gravar parametros | `false` |

Nos Code Blocks, digite exatamente `null`, `null`, `5`, `150` e `false`. Com os dois valores `null`, o script coleta todos os elementos de Quadro estrutural e os separa automaticamente entre vigas e pecas alveolares.

Fluxo recomendado:

1. Execute com `IN[4] = false`.
2. Confira o relatorio retornado em `OUT`.
3. Corrija marcas ausentes e casos ambiguos.
4. Execute com `IN[4] = true` para gravar.
5. Gere novamente a tabela de vigas do Revit.

Salve o grafo como, por exemplo, `Identificar_Lajes_Apoiadas_2020.dyn`.

## Como a deteccao funciona

- Usa cinco amostras ao longo do eixo de cada viga.
- Calcula a normal esquerda/direita a partir do sentido da curva da viga.
- Posiciona as amostras alem da face da viga.
- Reconhece como alveolares os elementos cujo `Modelo`, tipo ou familia comeca por LP15, LP20, LP26,5, LP32, LP40 ou LP50, ou contem `Laje alveolar`.
- Intersecta linhas verticais com os solidos das pecas alveolares candidatas.
- Agrupa as varias pecas de 1,25 m pela `Marca de tipo` e escolhe a marca encontrada na maioria das amostras.
- Empates sao marcados como `AMBIGUO` e nao sao gravados.

O sentido esquerda/direita acompanha o sentido interno da curva da viga no Revit. Para o dimensionamento, a ordem permanece consistente por viga; vigas de borda sempre recebem a unica laje em `LAJE_Marca_E`.

Todas as conversoes de centimetros para pes sao feitas diretamente pelo script, sem utilizar `UnitTypeId`, que nao existe na API do Revit 2020.

## Saida

Cada item de `OUT` informa o ID da viga, as marcas detectadas, o status e uma mensagem. Status previstos:

- `RESUMO`: quantidades de vigas e pecas alveolares reconhecidas e marcas disponiveis;
- `PREVIA`: deteccao concluida, sem gravacao;
- `GRAVADO`: parametros atualizados;
- `SEM_LAJE`: nenhuma laje encontrada;
- `AMBIGUO`: mais de uma laje teve a mesma quantidade de amostras;
- `ERRO`: geometria ou parametros invalidos.

## Diagnostico de parametros

O relatorio inclui `parametros_laje`, com os nomes que a API encontrou em cada viga. A busca ignora diferencas de maiusculas, espacos, hifens e sublinhados. Se a gravacao retornar `ERRO`, expanda `mensagem` e `parametros_laje` no Watch:

- se a lista estiver vazia, os parametros nao estao vinculados a instancia de **Quadro estrutural** naquele arquivo;
- se aparecer somente um dos nomes, crie ou vincule o outro;
- se os dois aparecerem, a mensagem indicara se sao somente leitura, de outro tipo de armazenamento ou se a API recusou a gravacao.
