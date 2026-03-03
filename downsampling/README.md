# Downsampling CSV (LTTB) — Aplicação Streamlit

Esta aplicação permite realizar downsampling inteligente (LTTB) em múltiplos arquivos CSV padronizados.  
A validação segue o **Modo 3 (FLEX)**, garantindo apenas que as colunas selecionadas para X e Y existam em todos os arquivos.

## Funcionalidades Principais

### ✔ Upload múltiplo de arquivos CSV  
Carregue diversos arquivos padronizados simultaneamente.

### ✔ Seleção global das colunas X e Y  
- Selectboxes exibidas lado a lado  
- A segunda selectbox exclui automaticamente a coluna escolhida na primeira  
- Válido para todos os arquivos (mesma estrutura)

### ✔ Validação FLEX  
A aplicação aceita qualquer estrutura contanto que:
- A coluna X exista  
- A coluna Y exista  

Caso contrário, o arquivo é marcado como **❌ incompatível**.

### ✔ Conversão automática para valores numéricos  
Colunas X e Y são convertidas com `errors='coerce'`  
Linhas inválidas são removidas.

### ✔ Downsampling com LTTB  
A densidade é definida em **percentual**.  
A estimativa pós-downsampling é exibida em **quantidade de pontos**.

### ✔ Métricas antes do processamento  
Para cada arquivo:
- Nome  
- Tamanho (KB)  
- Número de linhas  
- Número de colunas  
- Número de colunas numéricas  

Além disso:
- Tamanho total combinado dos arquivos carregados

### ✔ Métricas pós-processamento  
Para cada arquivo:
- Linhas originais  
- Linhas após downsampling  
- Status (emoji de OK ou erro)  
- Mensagem de erro, se houver

E também:
- Tamanho final do ZIP em KB

### ✔ Download único  
Todos os arquivos processados são salvos dentro de um ZIP único.

---

## Requisitos

- Python 3.9+
- Streamlit
- Pandas
- NumPy

Instalação recomendada:

```bash
pip install streamlit pandas numpy
```

---

## Execução

Com o arquivo `index.py`, execute:

```bash
streamlit run index.py
```

---

## Premissas Importantes

1. **Todos os arquivos devem ter a mesma estrutura**.  
2. Apenas as colunas X e Y são obrigatórias e devem estar presentes.  
3. O usuário deve escolher X e Y com base no primeiro arquivo.  
4. Dados inválidos (strings, NaN) em X ou Y são removidos automaticamente.  
5. A aplicação visa desempenho, portanto previews extensos não são exibidos.

---

## Sobre o LTTB

O algoritmo **Largest Triangle Three Buckets (LTTB)** reduz a quantidade de pontos preservando a forma geral do sinal, excelente para séries temporais e curvas contínuas.

---

## Saída

Um arquivo ZIP contendo:
- Um CSV para cada arquivo de entrada
- Cada CSV já reduzido via LTTB
- Nomes preservados com sufixo `_downsampled.csv`

---

## Licença

Uso livre para fins acadêmicos, de pesquisa ou industriais.

---

## Autor

Aplicação gerada assistivamente com GPT e adaptada para o projeto **Caçador de R²**.
