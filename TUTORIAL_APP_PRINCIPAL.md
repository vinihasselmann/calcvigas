# Tutorial completo — modelagem e uso do Cassol PreCalc

Este guia descreve o fluxo completo do **app principal de quadro estrutural**, desde a
preparação do modelo no Revit até a conferência dos resultados e a devolução das taxas
`TAXA-CA` e `TAXA-CP` ao modelo.

> O aplicativo é uma ferramenta de estudo e pré-dimensionamento. Os resultados devem ser
> conferidos e validados pelo engenheiro responsável antes de serem usados em projeto,
> fabricação ou orçamento.

## 1. Visão geral do fluxo

1. Modelar vigas e pisos estruturais no Revit.
2. Identificar cada laje alveolar por uma marca única.
3. Relacionar as lajes às vigas por `LAJE_Marca_E` e `LAJE_Marca_D`.
4. Exportar uma tabela de vigas e outra de pisos.
5. Importar as duas tabelas no app.
6. Calcular e analisar `PASSA`, `NAO PASSA` e `ERRO`.
7. Exportar o XLSX e o memorial PDF.
8. Importar as taxas aprovadas no Revit com o Dynamo de taxas.

## 2. Preparação do ambiente

### 2.1 Instalar o app

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2.2 Iniciar

```powershell
streamlit run app.py
```

O navegador deve abrir a tela principal do Cassol PreCalc. Se não abrir, use o endereço
local mostrado pelo Streamlit no terminal, normalmente `http://localhost:8501`.

## 3. Preparação do modelo no Revit

### 3.1 Modelar as vigas

Modele as vigas na categoria **Quadro estrutural**. Cada viga precisa ter:

- identificador único, preferencialmente em `ID_ELEMENTO`;
- tipo reconhecível como `VPL`, `VPT` ou `VR`;
- seção inicial, altura e largura coerentes;
- vão estrutural;
- referências das lajes apoiadas, quando aplicável.

Use IDs estáveis, como `V01`, `V02` e `V03`. Não reutilize o mesmo ID para vigas
diferentes.

### 3.2 Classificar os tipos de viga

O app aceita uma coluna explícita `TIPO_ELEMENTO`, que é a forma mais segura:

| Valor | Elemento | Uso |
|---|---|---|
| `VPL` | Viga tipo L | Laje apoiada em um lado ou solução do catálogo VPL |
| `VPT` | Viga tipo T protendida | Lajes apoiadas à esquerda e à direita |
| `VR` | Viga retangular | Cargas lineares informadas diretamente |

Sem `TIPO_ELEMENTO`, o app tenta inferir o sistema por `NOME_TIPO` ou `SECAO`: nomes
iniciados por `L`, `T` ou `R` são interpretados como VPL, VPT ou VR. Para evitar
ambiguidades, prefira preencher `TIPO_ELEMENTO`.

### 3.3 Modelar e identificar as lajes alveolares

As peças alveolares devem estar em **Quadro estrutural** e ser reconhecíveis por `Modelo`,
nome de família ou nome de tipo como:

- `LP15`;
- `LP20`;
- `LP26,5`;
- `LP32`;
- `LP40`;
- `LP50`.

Todas as peças de 1,25 m que formam o mesmo painel ou conjunto de laje devem receber a
mesma `Marca de tipo`, por exemplo `LA01`. Outra laje deve usar outra marca, como `LA02`.

### 3.4 Criar os parâmetros de relacionamento

Em **Gerenciar > Parâmetros do projeto**, crie ou vincule à categoria **Quadro
estrutural**:

- `LAJE_Marca_E`: parâmetro de instância, tipo Texto;
- `LAJE_Marca_D`: parâmetro de instância, tipo Texto.

Para uma viga de borda, informe a única laje em `LAJE_Marca_E`. Para uma VPT interna,
informe as lajes dos dois lados. Se a mesma laje estiver nos dois lados, a mesma marca pode
aparecer nos dois campos.

O preenchimento pode ser manual ou automático pelo Dynamo documentado em
[`revit_laje_viga_dynamo/README.md`](revit_laje_viga_dynamo/README.md).

### 3.5 Parâmetros para devolver as taxas ao Revit

Crie os parâmetros compartilhados de **tipo**:

- `TAXA-CA` — Densidade de massa;
- `TAXA-CP` — Densidade de massa.

Vincule ambos a **Quadro estrutural**. O preenchimento automático após o cálculo é descrito
em [`revit_taxas_dynamo/README.md`](revit_taxas_dynamo/README.md).

## 4. Montagem das tabelas do Revit

O app principal recebe **dois arquivos separados**: um de vigas e outro de pisos. Não
inclua linhas de laje na tabela de vigas.

Na própria tela inicial, os botões **Baixar modelo de vigas** e **Baixar modelo de pisos**
geram exemplos compatíveis. Eles são a melhor referência para conferir nomes e formato.

### 4.1 Tabela de vigas

Campos básicos recomendados para todas as vigas:

| Campo | Unidade/conteúdo | Observação |
|---|---|---|
| `ID_ELEMENTO` | Texto | Identificador único, como `V01` |
| `TIPO_ELEMENTO` | `VPL`, `VPT` ou `VR` | Recomendado para classificação inequívoca |
| `NOME_TIPO` | Texto | Pode ser `L`, `T`, `R` ou nome da família/tipo |
| `PECA-Altura Pre` | cm | Altura da seção pré-moldada |
| `PECA-Largura Pre` | cm | Largura da seção pré-moldada |
| `VAO_VIGA_CM` | cm | Valores acima de 100 são convertidos de cm para m |
| `TAXA-CA` | kg/m³ | Pode iniciar em zero; não controla a otimização |
| `TAXA-CP` | kg/m³ | Pode iniciar em zero; não controla a otimização |

Para VPL e VPT, acrescente:

| Campo | Uso |
|---|---|
| `LAJE_Marca_E` | Marca da laje esquerda ou da única laje de borda |
| `LAJE_Marca_D` | Marca da laje direita; principalmente para VPT |

Para VR, as cargas são lineares e podem ser fornecidas diretamente:

| Campo | Unidade | Uso |
|---|---|---|
| `carga_fechamento_kgf_m` | kgf/m | Fechamento ou parede |
| `carga_permanente_kgf_m` | kgf/m | Carga permanente adicional |
| `carga_variavel_kgf_m` | kgf/m | Carga variável linear |

Como alternativa para a carga de fechamento da VR, podem ser usados `h_parede`,
`esp_parede` e `peso_parede_kgf_m3`.

### 4.2 Tabela de pisos

A tabela de pisos possui cinco campos obrigatórios:

| Campo no Revit | Conteúdo | Regra |
|---|---|---|
| `Marca de tipo` | `LA01`, `LA02`, etc. | Obrigatório, preenchido e sem duplicidade |
| `Modelo` | `LP15`, `LP20`, `LP26,5`, `LP32`, `LP40` ou `LP50` | Deve existir no catálogo do app |
| `LAJE-Sobrecarga` | kgf/m² | Carga total exportada, no mínimo 200 kgf/m² |
| `LAJE-Vão` | cm ou m | Acima de 100 é interpretado como cm |
| `LAJE_Psi` | `0`, `1` ou `2` | Classe de combinação de ações |

No fluxo atual, o app interpreta `LAJE-Sobrecarga` como carga total e separa
**200 kgf/m²** como revestimento. Exemplo: um valor exportado de 800 kgf/m² resulta em
600 kgf/m² de carga acidental e 200 kgf/m² de revestimento.

Valores de `LAJE_Psi`:

| Código | Ocupação |
|---|---|
| `0` | Locais sem predominância de pesos/equipamentos ou concentração de pessoas |
| `1` | Locais com predominância de pesos/equipamentos ou concentração de pessoas |
| `2` | Bibliotecas, arquivos, oficinas e garagens |

### 4.3 Conferência antes da exportação

Antes de gerar os arquivos, confirme:

- cada viga possui um `ID_ELEMENTO` único;
- cada marca de piso aparece uma única vez na tabela de pisos;
- toda marca usada em `LAJE_Marca_E` ou `LAJE_Marca_D` existe na tabela de pisos;
- a VPT possui as duas referências de laje, quando houver dois lados distintos;
- não há células vazias nos cinco campos obrigatórios dos pisos;
- `LAJE-Sobrecarga` é igual ou superior a 200 kgf/m²;
- `LAJE_Psi` contém somente `0`, `1` ou `2`;
- as unidades das colunas estão coerentes.

Exporte as tabelas como `.xlsx`, `.xlsm`, `.xls`, `.csv` ou `.txt`. Para CSV e TXT, use
ponto e vírgula como separador.

## 5. Utilização do app principal

### Passo 1 — Abrir a tela inicial

Inicie o Streamlit e permaneça na página inicial. As páginas laterais VPL, VPT e Lajes ALV
são estudos paramétricos individuais; o fluxo deste tutorial usa a página principal de
**quadro estrutural importado**.

### Passo 2 — Carregar a tabela de vigas

Em **Tabela de vigas do Revit**, selecione o arquivo que contém apenas VPL, VPT e VR.

### Passo 3 — Carregar a tabela de pisos

Em **Tabela de pisos do Revit**, selecione o arquivo com os pisos estruturais. O botão de
cálculo somente é liberado quando os dois arquivos estão presentes.

### Passo 4 — Conferir a prévia

O app mostra as duas tabelas lado a lado. Confira especialmente:

- quantidade de linhas;
- nomes dos cabeçalhos;
- IDs e marcas;
- altura, largura e vão;
- relação das lajes com as vigas;
- sobrecarga e classe `Psi`.

Se houver erro de leitura, corrija o arquivo de origem e faça um novo upload. Alterar um dos
arquivos limpa automaticamente os resultados anteriores.

### Passo 5 — Calcular

Clique em **Calcular quadro estrutural**. A barra de progresso informa quantos elementos já
foram processados.

Cada linha é calculada individualmente. Um erro em uma peça é registrado nessa linha e não
impede o cálculo das demais.

### Passo 6 — Ler o resumo

Ao finalizar, o topo dos resultados apresenta:

- **Elementos**: total processado;
- **PASSA**: soluções aprovadas;
- **NAO PASSA**: peças sem solução aprovada dentro dos critérios e catálogos;
- **ERRO**: linhas com dados ausentes, inválidos ou não reconhecidos;
- **Taxa de aprovação**: percentual de linhas com `PASSA`.

### Passo 7 — Filtrar e analisar

Use os filtros de **Status**, **Tipo de elemento** e **Laje**. Uma sequência prática é:

1. filtrar `ERRO` e corrigir problemas de entrada;
2. filtrar `NAO PASSA` e analisar seção, carga e mensagem;
3. conferir os elementos `PASSA` e as seções sugeridas;
4. revisar as taxas CA e CP e os critérios estruturais.

Campos principais do resultado:

| Campo | Interpretação |
|---|---|
| `secao_original` | Seção recebida do modelo |
| `secao_sugerida` | Alternativa encontrada pelo app |
| `mensagem` | Indicação de aumento, redução ou ausência de solução |
| `Msd`, `MRU`, `MRU_MSD` | Solicitação, resistência e relação resistente/solicitante |
| `Vsd`, `VRd2` | Solicitação e resistência ao cisalhamento |
| `taxa_armadura_passiva` | Taxa CA calculada, em kg/m³ |
| `taxa_armadura_protendida` | Taxa CP calculada, em kg/m³ |
| `Asw`, `Asw_calculada`, `Asw_minima` | Armadura transversal adotada, solicitada e mínima |
| `status` | `PASSA`, `NAO PASSA` ou `ERRO` |
| `erro_msg` | Motivo técnico de uma linha com erro |

Uma `secao_sugerida` vazia normalmente significa que a seção original foi mantida ou que
nenhuma alternativa cadastrada resolveu o caso; confirme pela `mensagem` e pelo `status`.

Para VPT, o motor encontra primeiro a menor seção aprovada e também avalia uma seção da
família imediatamente maior, limitada a 10 cm adicionais de altura e 25% de aumento de
área. A seção maior é preferida quando permite reduzir o número de cordoalhas sem deixar de
atender aos demais critérios.

A ocupação das camadas VPT segue a sequência produtiva: C1 mantém no mínimo duas barras
passivas; C2 somente é usada quando C1 está completa; C3 somente é usada quando C2 está
completa. A camada central C2 pode ser completada com uma quantidade ímpar de cordoalhas.

### Passo 8 — Exportar

Os filtros também controlam o conteúdo exportado. Para gerar o relatório completo, deixe
todos os valores selecionados.

- **Exportar resultados XLSX** gera `resultados_quadro_estrutural.xlsx`, com as abas
  `Lajes`, `VPL`, `VPT`, `VR`, `Resumo` e `Parametros`;
- **Baixar memorial PDF** gera o memorial dos itens atualmente filtrados.

Guarde o XLSX: ele é a entrada do Dynamo que grava as taxas no Revit.

## 6. Retorno dos resultados ao Revit

Use o procedimento de [`revit_taxas_dynamo/README.md`](revit_taxas_dynamo/README.md).

Resumo operacional:

1. selecione `resultados_quadro_estrutural.xlsx`;
2. importe as abas `VPL`, `VPT` e `VR`;
3. conecte `VPL` em `IN[0]`, `VPT` em `IN[1]` e `VR` em `IN[2]`;
4. execute primeiro com gravação `false`;
5. analise `PREVIA`, `NAO_ENCONTRADO`, `CONFLITO` e `ERRO`;
6. execute com gravação `true` somente após validar a prévia.

O Dynamo grava apenas linhas com `status = PASSA`. Na integração atual:

- CA é arredondada ao múltiplo de 5 mais próximo; empate em 2,5 sobe;
- CP é arredondada ao inteiro mais próximo; empate em 0,5 sobe.

## 7. Ciclo recomendado de revisão

1. Corrigir primeiro todas as linhas com `ERRO`.
2. Avaliar as recomendações de seção das linhas `NAO PASSA`.
3. Atualizar tipos e seções no Revit quando a solução for aceita.
4. Exportar novamente as tabelas do Revit.
5. Recalcular o quadro estrutural.
6. Repetir até obter o nível de aprovação esperado.
7. Gerar XLSX e memorial finais.
8. Gravar as taxas no Revit por último.

Não altere somente o XLSX para esconder divergências: o modelo Revit deve continuar sendo a
fonte geométrica e cadastral do estudo.

## 8. Solução de problemas

### “Tabela de pisos sem as colunas obrigatórias”

Confira `Marca de tipo`, `Modelo`, `LAJE-Sobrecarga`, `LAJE-Vão` e `LAJE_Psi`. Use os
modelos baixados na tela inicial como referência.

### “Marca de tipo duplicada na tabela de pisos”

A tabela deve ter uma linha por laje lógica. Agrupe as peças alveolares que possuem a mesma
marca antes da exportação ou ajuste a tabela do Revit para não listar cada peça separadamente.

### “LAJE_Marca não encontrada nas linhas de laje”

A viga referencia uma marca que não está na tabela de pisos. Confira espaços, digitação e
se a laje foi incluída na exportação.

### “Não foi possível identificar o tipo do elemento”

Adicione `TIPO_ELEMENTO` e preencha com `VPL`, `VPT` ou `VR`.

### Valores de vão incorretos

O app interpreta comprimentos maiores que 100 como centímetros e os divide por 100. Use,
por exemplo, `652,46` cm ou `6,5246` m, sem misturar unidades dentro da mesma coluna.

### Muitas linhas com `NAO PASSA`

Analise `mensagem`, seção sugerida, taxas limites, flexão, cisalhamento e ELS. `NAO PASSA`
não é falha de importação: significa que o app não encontrou uma solução aprovada dentro do
catálogo e dos critérios atuais.

### Dynamo retorna `BLOQUEADO`

Expanda os itens `CONFLITO` no Watch. Confirme também a ordem das entradas: `VPL`, `VPT`,
`VR`. Qualquer conflito bloqueia toda a gravação por segurança.

## 9. Checklist final

- [ ] Vigas modeladas como Quadro estrutural.
- [ ] IDs de vigas únicos.
- [ ] Lajes com modelos LP reconhecidos.
- [ ] Uma marca única por laje lógica.
- [ ] `LAJE_Marca_E` e `LAJE_Marca_D` preenchidos.
- [ ] Tabela de vigas sem linhas de laje.
- [ ] Tabela de pisos com os cinco campos obrigatórios.
- [ ] Unidades e cargas conferidas.
- [ ] Prévia dos uploads validada.
- [ ] Linhas com `ERRO` tratadas.
- [ ] Linhas `NAO PASSA` analisadas pelo engenheiro.
- [ ] XLSX completo exportado sem filtros acidentais.
- [ ] Prévia do Dynamo validada antes da gravação.
- [ ] Modelo e memorial revisados pelo responsável técnico.
