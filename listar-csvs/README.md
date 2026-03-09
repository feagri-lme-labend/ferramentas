# Aplicativo Streamlit de Navegação e Listagem de Arquivos Locais

Este é um aplicativo web interativo, construído com **Streamlit** e **Python**, projetado para navegar no sistema de arquivos local (onde o script está sendo executado) e listar os arquivos de um diretório específico separados por vírgula (formato CSV).

## Funcionalidades Principais

* **Seleção de Unidade:** Permite escolher a unidade de disco (C:\, /, etc.) para iniciar a navegação.
* **Navegação com Histórico:** Permite avançar e recuar na hierarquia de pastas com botões de histórico.
* **Subir um Nível:** Botão dedicado para navegar para o diretório pai (..), garantindo o registro no histórico.
* **Layout Otimizado:** Utiliza um Expander e controle de altura para listas grandes de pastas, mantendo o layout da tela limpo.
* **Listagem em CSV:** Exibe a lista final de arquivos do diretório atual em formato de texto separado por vírgulas.
* **Download:** Botão para baixar a lista de arquivos diretamente como um arquivo `.csv`.

## Pré-requisitos

Para rodar esta aplicação, você deve ter o Python instalado e as seguintes bibliotecas:

    pip install streamlit psutil

## Como Executar

1.  Salve o código principal em um arquivo chamado `app.py`.
2.  Abra o terminal na pasta onde você salvou o arquivo.
3.  Execute o comando:

    streamlit run app.py

O aplicativo será aberto automaticamente no seu navegador.

## Uso

1.  **Sidebar:**
    * **Seleção de Unidade:** Escolha a unidade de disco na `selectbox` para definir o ponto de partida.
    * **Controles de Navegação:** Use os botões **Voltar** (⬅️), **Avançar** (➡️) e **Subir um Nível** (⬆️) para navegar no histórico e na hierarquia de pastas.

2.  **Área Principal:**
    * **Pastas:** Clique no nome de uma pasta (exibida no Expander) para avançar para aquele diretório.
    * **Arquivos Encontrados:** A coluna da direita exibe os arquivos encontrados no diretório atual em formato de tabela.
    * **Resultado Final:** A lista de arquivos separados por vírgula é exibida em um bloco de código, pronta para ser copiada ou baixada via botão **"Baixar CSV"**.