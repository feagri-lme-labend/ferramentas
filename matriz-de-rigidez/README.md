# 🌳 Calculadora Interativa de Propriedades Elásticas para Madeira (Ortotropia)

![Getting Started](https://github.com/renansg67/matriz-de-rigidez/blob/master/figuras/captura_de_tela.png?raw=true)

Este é um aplicativo web interativo construído com Streamlit para calcular as **9 Constantes Elásticas (Módulos de Elasticidade e Coeficientes de Poisson)** e as **Matrizes de Rigidez ($\bm{C}_{ij}$) e Flexibilidade ($\bm{S}_{ij}$)** de amostras de madeira, com base em medições de velocidade de ondas ultrassônicas (método de Christoffel).

<div style="text-align: center;">
  <img src="https://github.com/renansg67/matriz-de-rigidez/blob/master/figuras/front-view.png?raw=true" width="45%" alt="Imagem 1" /> 
  <img src="https://github.com/renansg67/matriz-de-rigidez/blob/master/figuras/top-view.png?raw=true" width="45%" alt="Imagem 2" />
  <p style="font-style: italic; color: #555; margin-top: 10px;">
        Poliedro de 26 lados com vistas frontal e superior, respectivamente.
    </p>
</div>

O objetivo é fornecer uma ferramenta de análise de dados limpa, interativa e robusta, que inclui validações diagnósticas e opções de visualização científica.

## ✨ Recursos Principais

* **Cálculo Automático de Velocidade:** O input do usuário requer apenas `Distância (cm)` e `Tempo (μs)`. A velocidade ($V = D/T$) é calculada internamente, eliminando redundância na entrada de dados.
* **Edição Interativa:** Permite editar os dados brutos de distância, tempo e densidade diretamente na interface web antes de executar o cálculo, facilitando a correção de erros.
* **Verificação de Condições de Ordem:** O algoritmo inclui uma função de diagnóstico que verifica se a Matriz de Rigidez ($\mathbf{C}$) calculada atende às três relações de ordem esperadas para materiais ortotrópicos com simetria da madeira ($\mathbf{C}_{11} > \mathbf{C}_{22} > \mathbf{C}_{33}$, etc.).
* **Visualização Científica:** Opção de alternar a exibição das Matrizes de Rigidez e Flexibilidade entre um `DataFrame` tabular (padrão) e a **renderização $\LaTeX$** usando `st.latex()`.
* **Exportação de Código $\LaTeX$:** Um `st.expander` (retraído por padrão) é fornecido acima de cada matriz $\LaTeX$ para que o usuário possa copiar o código da matriz e usá-lo diretamente em relatórios ou artigos.
* **Renderização $\LaTeX$ em Tabelas:** As constantes elásticas ($E_L$, $G_{LR}$, $\nu_{LR}$, etc.) e as regras de diagnóstico são exibidas em tabelas (`st.table`) com renderização $\LaTeX$ embutida.

## 🛠️ Tecnologias Utilizadas

* **Python 3.x**
* **Streamlit:** Framework para criação do aplicativo web interativo.
* **Pandas:** Para manipulação e tratamento dos dados de entrada (CSV).
* **NumPy:** Para cálculos vetoriais e matriciais (inversão e cálculo da Matriz $\mathbf{C}$).

## ⚙️ Instalação e Execução

### Pré-requisitos

Certifique-se de ter o Python 3 instalado.

### 1. Clonar o Repositório

```bash
git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git)
cd SEU_REPOSITORIO
```

### 2. Criar e Ativar o Ambiente Virtual (Recomendado)

```bash
python -m venv venv
# No Windows
.\venv\Scripts\activate
# No Linux/macOS
source venv/bin/activate
```

### 3. Instalar as Dependências

```bash
pip install streamlit pandas numpy
```

### 4. Executar o Aplicativo

```bash
streamlit run app.py
```

O aplicativo será aberto automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

## 📥 Formato do Arquivo de Entrada (CSV)

O aplicativo espera um arquivo CSV (separador vírgula `,` e decimal vírgula `,`) com as seguintes colunas obrigatórias:

| **Coluna**        | **Descrição**                                         | **Exemplo de Valor** |
|-------------------|-------------------------------------------------------|----------------------|
| Amostra           | Identificação única da amostra                        | AM03KDX               |
| Densidade (kg/m³) | Densidade da amostra                                  | 1028,97              |
| Direção           | Direção de propagação da onda (LL, RR, LR, RL2, etc.) | LL                   |
| Distância (cm)    | Distância percorrida pela onda                        | 4,681                |
| Tempo (μs)        | Tempo de trânsito medido (micro segundos)             | 8,67                 |

## 🔬 O Processo de Análise

1. Carregar: Suba o arquivo CSV.
2. Editar: Corrija quaisquer valores de densidade,
distância ou tempo no st.data_editor.
3. Selecionar: Escolha as amostras que deseja analisar.
4. Alternar Visualização: Marque o checkbox na barra lateral se desejar a visualização das matrizes em $\LaTeX$.
5. Executar: Clique em "Executar Análise".

## 🔍 Seção de Diagnóstico

O algoritmo verifica a estabilidade e a ordem física da Matriz de Rigidez. O diagnóstico é exibido em uma tabela que verifica as seguintes condições esperadas para madeiras:

| Condição             | Regra Esperada                                                     |
|----------------------|--------------------------------------------------------------------|
| Rigidez Normal       | $C_{11} > C_{22} > C_{33}$ (Longitudinal > Radial > Tangencial)    |
| Rigidez Cisalhamento | $C_{44} < C_{55} < C_{66}$ (Geralmente $G_{RT} < G_{LT} < G_{LR}$) |
| Rigidez Mútua        | $C_{12} > C_{13} > C_{23}$                                         |

## 💡 Próximas Implementações (Roadmap)

1. Validação por Espécie: Adicionar uma funcionalidade para que o usuário insira valores de referência (Mínimo/Médio/Máximo) para os Módulos de Elasticidade da espécie e compare os valores calculados, gerando um relatório de conformidade da amostra.
2. Exportação de Resultados: Opção para baixar as Matrizes Calculadas e as Constantes Elásticas em um novo arquivo CSV ou XLSX.
3. Visualização Gráfica: Adicionar gráficos de dispersão (e.g., $E$ vs. $\rho$) para visualização de tendências.