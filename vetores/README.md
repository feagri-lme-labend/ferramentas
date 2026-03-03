# 🎨 [IPE] Figuras vetorizadas para LaTeX 📐

## ✨ Visão Geral do Projeto

Este repositório armazena uma coleção de **figuras e diagramas vetorizados** criados com o software **IPE (Ipe extensible drawing editor)**.

O objetivo principal é fornecer assets de alta qualidade em formato **PDF nativo e vetorizado**, garantindo:
* 🌟 **Resolução Independente:** Escalabilidade perfeita (zoom infinito!) sem perda de qualidade.
* ✍️ **Integração LaTeX:** Textos, fórmulas e fontes são renderizados de forma consistente pelo motor LaTeX do seu documento.

---

## 🚀 Como Utilizar (LaTeX)

Use o pacote `graphicx` em seu documento, compilando com `pdflatex` ou `lualatex`.

### 1. Pacote
Adicione no preâmbulo:
```latex
\usepackage{graphicx}
```

### 2. Inclusão
Aponte para o diretório `/pdf`, omitindo a extensão `.pdf` para flexibilidade:

```latex
\begin{figure}[h!]
    \centering
    \includegraphics[width=0.85\textwidth]{pdf/nome_do_diagrama} 
    \caption{Diagrama esquemático gerado no IPE.}
    \label{fig:diagrama_ipe}
\end{figure}
```

---

## 📁 Estrutura de Diretórios

O repositório está organizado para separar as fontes editáveis dos arquivos finais.

| Diretório | Conteúdo | Propósito |
| :--- | :--- | :--- |
| `/pdf` | Arquivos .pdf vetorizados finais. | 🎯 PRONTO PARA USO. |
| `/src` | Arquivos fonte .ipe (XML editável). | 🛠️ Para modificação e manutenção. |

---

## 🤝 Contribuição

Contribuições são bem-vindas! Para adicionar uma nova figura, você deve incluir **ambos** os arquivos:
1. O arquivo editável **.ipe** em /src/.
2. O arquivo de saída **.pdf** exportado em /pdf/.

Abra um **Pull Request (PR)** com o novo par de arquivos.
