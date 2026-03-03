# 🧹 Processador Intermediário de CSVs  
### *Ferramenta Streamlit para padronizar e renomear múltiplas colunas de arquivos CSV antes da análise automatizada*

---

## 📘 Visão Geral

O **Processador Intermediário de CSVs** é uma aplicação desenvolvida em **Python + Streamlit** para **padronizar arquivos CSV brutos** provenientes de experimentos, máquinas de ensaio ou exportações de software.  
O aplicativo permite selecionar várias colunas de um arquivo de amostra, renomeá-las e processar todos os arquivos de uma pasta com o mesmo padrão.

Ele foi projetado como uma **etapa intermediária** antes da análise principal (como o *Caçador de Linearidade*), criando arquivos de saída limpos e estruturados, prontos para uso.

---

## 🧠 Principais Funcionalidades

| Função | Descrição |
|--------|------------|
| 🧾 **Pré-visualização interativa** | Mostra parte do arquivo bruto (definida pelo usuário) para identificar o início dos dados úteis. |
| 🧩 **Seleção múltipla de colunas** | Permite escolher várias colunas do arquivo e definir nomes personalizados para cada uma. |
| ✏️ **Renomeação dinâmica** | Cada coluna selecionada pode receber um nome customizado no próprio Streamlit. |
| ⚙️ **Configuração de separador e codificação** | Escolha manual ou automática de delimitador (`;`, `,`, `\t`) e codificação (`utf-8`, `latin-1`, `cp1252`). |
| 🧼 **Limpeza automática** | Remove espaços, substitui vírgulas por pontos e converte valores numéricos. |
| 📉 **Preview configurável** | Define quantas linhas do arquivo serão exibidas, útil para casos com cabeçalhos longos. |
| 💾 **Processamento em lote** | Aplica o mesmo padrão de seleção e nomes a todos os arquivos `.csv` da pasta de entrada. |

---

## 🧰 Requisitos

- Python ≥ 3.9  
- Bibliotecas:
  - `streamlit`
  - `pandas`

### Instalação das dependências

```bash
pip install streamlit pandas
```

---

## 🚀 Como Executar

1. Coloque o arquivo **`processador_intermediario_v4.py`** em uma pasta do seu projeto.  
2. Crie uma pasta com seus arquivos brutos (exemplo: `dados_brutos/`).  
3. Crie também uma pasta de saída (exemplo: `dados_processados/`).  
4. Execute o aplicativo com o comando:

```bash
streamlit run processador_intermediario_v4.py
```

5. O navegador abrirá automaticamente em `http://localhost:8501`.

---

## 🧭 Passo a Passo na Interface

### 1️⃣ Diretórios
- **Diretório de entrada:** pasta com os arquivos `.csv` brutos.  
- **Diretório de saída:** onde os arquivos processados serão salvos.

### 2️⃣ Arquivo de Amostra
Escolha um arquivo representativo para definir o padrão de leitura.  
O preview mostrará apenas um trecho configurável do arquivo (útil para arquivos grandes ou com cabeçalho extenso).

### 3️⃣ Ajuste dos Parâmetros
- **Separador:** selecione `auto`, `;`, `,` ou `\t`.  
- **Codificação:** escolha entre `auto`, `utf-8`, `latin-1` ou `cp1252`.  
- **Linhas iniciais a ignorar:** define quantas linhas de cabeçalho devem ser puladas.  
- **Tamanho do preview:** quantas linhas visualizar após o cabeçalho.  

### 4️⃣ Seleção e Renomeação de Colunas
- Use o painel interativo para selecionar várias colunas por índice.  
- Dê um nome a cada coluna (por exemplo, `Tempo`, `Força`, `Deformação`).  
- Veja o preview da tabela resultante com as colunas renomeadas.  

### 5️⃣ Processamento em Lote
- Clique em **🚀 Processar Todos os Arquivos**.  
- O app aplicará as mesmas configurações a todos os arquivos `.csv` do diretório de entrada.  
- O progresso é mostrado em tempo real, com relatório final de status e número de linhas processadas.

---

## 📂 Estrutura de Saída

Cada arquivo processado gera um `.csv` com o mesmo nome no diretório de saída:

```
dados_processados/
├── 1.csv
├── 2.csv
├── 3.csv
└── ...
```

Cada arquivo conterá:

```
Coluna1,Coluna2,Coluna3
<valor1>,<valor2>,<valor3>
...
```

---

## ⚙️ Arquitetura Interna

O app é dividido em módulos funcionais:
1. **Leitura robusta:** tenta múltiplas codificações e detecta o separador.  
2. **Preview rápido:** lê apenas as primeiras N linhas (sem carregar tudo).  
3. **Seleção dinâmica:** permite múltiplas colunas e nomes personalizados.  
4. **Normalização:** limpa strings e converte vírgulas decimais.  
5. **Exportação padronizada:** salva apenas as colunas escolhidas, com nomes definidos.  
6. **Lote:** aplica o mesmo padrão a todos os arquivos da pasta de entrada.

---

## ⚠️ Observações Importantes

- O preview **não carrega o arquivo inteiro**, apenas o trecho necessário para ajuste.  
- Caso o arquivo possua cabeçalho longo, aumente o valor de “Linhas iniciais a ignorar” e/ou “Tamanho do preview”.  
- A detecção automática de separador funciona bem na maioria dos casos, mas é possível selecionar manualmente.  
- Os nomes dos arquivos de saída serão os mesmos dos originais, sobrescrevendo se já existirem no diretório de saída.

---

## 🧩 Exemplo de Uso

Suponha que você tenha um arquivo:

```
Tempo(s);Força(N);Deformação(mm)
0,001;123,45;-0,0012
0,002;124,80;-0,0015
```

Com as configurações:
- Separador: `;`
- Colunas selecionadas: `[0, 1, 2]`
- Nomes: `Tempo`, `Força`, `Deformação`

O arquivo gerado será:

```
Tempo,Força,Deformação
0.001,123.45,-0.0012
0.002,124.80,-0.0015
```

---

## 📄 Licença

Este projeto é distribuído sob a licença MIT.  
Sinta-se à vontade para usar, modificar e integrar em outros sistemas de análise.

---

## ✨ Autor

Desenvolvido para apoiar projetos de análise automatizada de dados experimentais,  
como o **Caçador de Linearidade Interativo**.
