# 🎯 Caçador de Linearidade — Analisador Interativo de Regressões Locais

## 📘 Descrição Geral

O **Caçador de Linearidade** é uma aplicação interativa em **Streamlit** desenvolvida para detectar automaticamente as **regiões mais lineares** em dados experimentais contidos em arquivos CSV.

A ferramenta foi projetada para uso **local**, analisando múltiplos arquivos em um diretório de entrada, comparando diferentes tamanhos de janelas (percentuais do eixo X) e identificando o intervalo com o maior **coeficiente de determinação (R²)**.

Além disso, o aplicativo calcula o **erro padrão da inclinação (SE_B₁)** para cada regressão linear, fornecendo uma medida adicional de **consistência e precisão das estimativas**.

---

## ⚙️ Estrutura do Projeto

```
.
├── index.py               # Código principal do aplicativo Streamlit
├── dados/                 # Diretório de entrada com arquivos CSV
│   ├── arquivo_1.csv
│   ├── arquivo_2.csv
│   ├── arquivo_3.csv
│   └── ... outros arquivos com a mesma estrutura .csv
├── README.md              # (este arquivo)
```

Cada arquivo CSV dentro de `dados/` deve conter **pelo menos duas colunas numéricas** representando as variáveis independentes (X) e dependentes (Y).  
Durante a execução, o usuário pode escolher quais colunas usar para análise.

---

## 🚀 Execução Local

### 1. Instalar dependências

O aplicativo requer **Python 3.9+** e os seguintes pacotes:

```bash
pip install streamlit pandas numpy plotly
```

### 2. Preparar os dados

Certifique-se de que os arquivos CSV estejam dentro do diretório:
```
./dados/
```

### 3. Executar o aplicativo

Na raiz do projeto, execute:
```bash
streamlit run index.py
```

O navegador abrirá automaticamente em:
```
http://localhost:8501
```

---

## 🧭 Uso Interativo

1. **Selecione os arquivos** que deseja analisar (podem ser múltiplos).
2. **Escolha as colunas** que representam as variáveis X e Y.
3. **Defina o intervalo percentual de Y** (slider duplo na sidebar).
4. O app processa cada arquivo e cada janela percentual de X (100%, 80%, 60%, 40%, 20%),
   identificando a região com maior R² e calculando:
   - R² Máximo
   - Inclinação (B₁)
   - Intercepto (B₀)
   - Erro Padrão da Inclinação (SE_B₁)
5. **Visualize o gráfico interativo** mostrando:
   - Pontos experimentais
   - Região filtrada
   - Reta de regressão otimizada

---

## 📊 Saídas e Resultados

Os resultados são exibidos diretamente no app, mas também podem ser exportados (em versões futuras) como `df_resultados_mestre`, um DataFrame consolidado que armazena todas as janelas e arquivos processados.

Cada linha representa uma combinação de:
```
(arquivo, faixa de Y, percentual de janela X)
```

Com as métricas:
- R² Máx
- B₁ (Angular)
- SE(B₁)
- B₀ (Intercepto)
- Limites de X e Y da região linear

---

## 💡 Observações Técnicas

- O app é totalmente **local** — não requer internet nem upload para a nuvem.
- O diretório `dados/` é lido automaticamente via `os.listdir()`.
- Colunas não numéricas são automaticamente rejeitadas com mensagem de erro.

---

## 📄 Licença

Este projeto é de uso livre para fins acadêmicos, experimentais e de pesquisa.

**Autor:** Renan da Silva Guedes  
**Ano:** 2025
