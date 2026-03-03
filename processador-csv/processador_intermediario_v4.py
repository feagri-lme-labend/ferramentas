import os
import csv
import pandas as pd
import streamlit as st

# === CONFIG STREAMLIT ===
st.set_page_config(layout="wide", page_title="🧹 Processador Intermediário de CSVs")

st.title("🧹 Processador Intermediário de CSVs (Seleção Múltipla de Colunas)")
st.markdown("""
Ferramenta para **padronizar e renomear múltiplas colunas** de arquivos CSV antes da análise.  
Permite selecionar várias colunas do arquivo de amostra, renomeá-las e processar toda a pasta com o mesmo padrão.
""")

# === 1. ENTRADAS BÁSICAS ===
st.sidebar.header("📂 Diretórios")
dir_entrada = st.sidebar.text_input("Diretório de entrada (CSV brutos):", "dados_brutos")
dir_saida = st.sidebar.text_input("Diretório de saída (arquivos processados):", "dados_processados")

# Verifica se há arquivos disponíveis
arquivos_disponiveis = []
if os.path.exists(dir_entrada):
    arquivos_disponiveis = [f for f in os.listdir(dir_entrada) if f.lower().endswith(".csv")]

if not arquivos_disponiveis:
    st.warning("Nenhum arquivo CSV encontrado na pasta de entrada.")
    st.stop()

arquivo_amostra = st.sidebar.selectbox("📄 Arquivo de amostra:", arquivos_disponiveis)
caminho_amostra = os.path.join(dir_entrada, arquivo_amostra)

# === 2. DETECÇÃO AUTOMÁTICA DO SEPARADOR ===
def detectar_separador(caminho, enc="utf-8"):
    with open(caminho, "r", encoding=enc, errors="ignore") as f:
        primeira_linha = f.readline()
        sniffer = csv.Sniffer()
        try:
            return sniffer.sniff(primeira_linha).delimiter
        except Exception:
            if ";" in primeira_linha and primeira_linha.count(";") > primeira_linha.count(","):
                return ";"
            elif "," in primeira_linha:
                return ","
            elif "\t" in primeira_linha:
                return "\t"
            else:
                return ";"

# === 3. CONFIGURAÇÕES DE LEITURA ===
st.sidebar.header("⚙️ Parâmetros de leitura")
sep_opcao = st.sidebar.selectbox("Separador", ["auto", ";", ",", "\t (tabulação)"])
linhas_pular = st.sidebar.number_input("Linhas iniciais a ignorar", 0, 1000, 0)
tamanho_preview = st.sidebar.number_input("Tamanho do preview (linhas)", 10, 2000, 100, step=10)
encoding_opcao = st.sidebar.selectbox("Codificação", ["auto", "utf-8", "latin-1", "cp1252"])

processar_tudo = st.sidebar.button("🚀 Processar Todos os Arquivos")

# === 4. FUNÇÕES ===
def ler_csv_robusto(
    caminho: str,
    sep: str = ";",
    skip_rows: int = 0,
    encoding_preferido: str = "auto",
    nrows_preview: int = None
):
    encodings_teste = (
        [encoding_preferido] if encoding_preferido != "auto" else ["utf-8", "latin-1", "cp1252"]
    )
    for enc in encodings_teste:
        try:
            df = pd.read_csv(
                caminho,
                sep=sep,
                header=None,
                skiprows=skip_rows,
                nrows=nrows_preview,
                engine="python",
                comment="#",
                encoding=enc,
            )
            return df, enc
        except Exception:
            continue
    raise UnicodeDecodeError("Não foi possível decodificar o arquivo em nenhum encoding comum.")


def processar_csv(caminho_in, caminho_out, sep, cols_idx, cols_nomes, skip_rows, encoding_preferido):
    try:
        df, enc_usado = ler_csv_robusto(caminho_in, sep, skip_rows, encoding_preferido)
        df = df.map(lambda x: str(x).strip().replace(",", ".") if isinstance(x, str) else x)

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        df_sel = df.iloc[:, cols_idx].copy()
        df_sel.columns = cols_nomes

        os.makedirs(os.path.dirname(caminho_out), exist_ok=True)
        df_sel.to_csv(caminho_out, index=False)
        return True, f"{len(df_sel)} linhas (encoding: {enc_usado})"
    except Exception as e:
        return False, str(e)

# === 5. CARREGA O ARQUIVO DE AMOSTRA E PREVIEW ===
try:
    if sep_opcao == "auto":
        sep_detectado = detectar_separador(caminho_amostra)
    else:
        sep_detectado = {";": ";", ",": ",", "\t (tabulação)": "\t"}[sep_opcao]

    df_amostra, enc_usado = ler_csv_robusto(
        caminho=caminho_amostra,
        sep=sep_detectado,
        skip_rows=int(linhas_pular),
        encoding_preferido=encoding_opcao,
        nrows_preview=int(tamanho_preview)
    )

    st.subheader(f"📘 Pré-visualização do arquivo de amostra: `{arquivo_amostra}`")
    st.caption(f"Separador detectado: `{sep_detectado}` • Encoding: `{enc_usado}` • Mostrando até {tamanho_preview} linhas após {linhas_pular} puladas")
    st.dataframe(df_amostra, width="stretch")
    st.markdown("---")

    # Exibe seletor de colunas
    st.subheader("🧩 Selecione as colunas que deseja exportar")
    opcoes_colunas = list(range(df_amostra.shape[1]))
    cols_idx = st.multiselect("Selecione as colunas (por índice):", opcoes_colunas, default=[0, 1])

    cols_nomes = []
    if cols_idx:
        st.markdown("✏️ **Nomeie cada coluna de saída**:")
        for i, idx in enumerate(cols_idx):
            nome = st.text_input(f"Nome para coluna {idx}:", value=f"Coluna_{idx}", key=f"nome_{idx}")
            cols_nomes.append(nome)

        # 🔀 NOVO BLOCO: controle de ordem das colunas
        st.markdown("🔀 **Defina a ordem das colunas de saída:**")
        cols_ordenadas = st.multiselect(
            "Reordene as colunas selecionadas (a ordem escolhida será usada no arquivo final):",
            options=cols_nomes,
            default=cols_nomes
        )

        try:
            df_preview = df_amostra.iloc[:, cols_idx].copy()
            df_preview.columns = cols_nomes
            df_preview = df_preview[cols_ordenadas]  # aplica a ordem escolhida

            # Substituições e conversão segura (sem warnings)
            df_preview = df_preview.map(lambda x: str(x).strip().replace(",", "."))
            for col in df_preview.columns:
                try:
                    df_preview[col] = pd.to_numeric(df_preview[col])
                except Exception:
                    pass

            st.subheader("🔎 Pré-visualização do resultado")
            st.dataframe(df_preview.head(20), use_container_width=True)

            st.success("✅ Pré-visualização gerada com sucesso! Ajuste os parâmetros se necessário.")
        except Exception as e:
            st.error(f"Erro ao selecionar colunas: {e}")
            st.stop()
    else:
        st.info("👈 Selecione pelo menos uma coluna para continuar.")

except Exception as e:
    st.error(f"Erro ao carregar arquivo de amostra: {e}")
    st.stop()


# === 6. PROCESSAMENTO EM LOTE ===
if processar_tudo and cols_idx:
    st.info(f"📄 {len(arquivos_disponiveis)} arquivos detectados. Iniciando processamento...")
    resultados = []
    progress = st.progress(0)

    for i, arquivo in enumerate(arquivos_disponiveis, start=1):
        caminho_in = os.path.join(dir_entrada, arquivo)
        caminho_out = os.path.join(dir_saida, arquivo)
        ok, info = processar_csv(
            caminho_in, caminho_out, sep_detectado, cols_idx, cols_nomes, linhas_pular, encoding_opcao
        )
        resultados.append((arquivo, "✅ OK" if ok else "❌ Erro", info))
        progress.progress(i / len(arquivos_disponiveis))

    st.success(f"🏁 Concluído! Arquivos gerados em: `{dir_saida}`")
    st.dataframe(
        pd.DataFrame(resultados, columns=["Arquivo", "Status", "Detalhes"]),
        hide_index=True,
        width="stretch",
    )
elif processar_tudo:
    st.warning("⚠️ Selecione ao menos uma coluna antes de processar.")
else:
    st.info("👈 Ajuste os parâmetros, selecione e nomeie as colunas, depois clique em **Processar Todos os Arquivos**.")
