import io
import zipfile
import pandas as pd
import streamlit as st
import csv

# === CONFIG STREAMLIT ===
st.set_page_config(layout="wide", page_title="☁️ Processador Intermediário de CSVs (Cloud)")

st.title("☁️ Processador Intermediário de CSVs - Versão Cloud")
st.markdown("""
Envie múltiplos arquivos CSV, visualize um deles como amostra, defina os parâmetros de leitura, 
selecione e renomeie colunas, ajuste a ordem e baixe tudo processado em formato ZIP.
""")

# === 1. UPLOAD DE ARQUIVOS ===
arquivos = st.file_uploader("📂 Envie os arquivos CSV para processar", type="csv", accept_multiple_files=True)

if not arquivos:
    st.info("👈 Envie pelo menos um arquivo CSV para começar.")
    st.stop()

nomes_arquivos = [arq.name for arq in arquivos]
arquivo_amostra_nome = st.selectbox("📄 Escolha um arquivo de amostra para configurar:", nomes_arquivos)
arquivo_amostra = next(arq for arq in arquivos if arq.name == arquivo_amostra_nome)

# === 2. DETECÇÃO AUTOMÁTICA DO SEPARADOR ===
def detectar_separador(arquivo_bytes, enc="utf-8"):
    arquivo_bytes.seek(0)
    linha = arquivo_bytes.readline().decode(enc, errors="ignore")
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(linha).delimiter
    except Exception:
        if ";" in linha and linha.count(";") > linha.count(","):
            return ";"
        elif "," in linha:
            return ","
        elif "\t" in linha:
            return "\t"
        else:
            return ";"

# === 3. CONFIGURAÇÕES DE LEITURA ===
st.sidebar.header("⚙️ Parâmetros de leitura")
sep_opcao = st.sidebar.selectbox("Separador", ["auto", ";", ",", "\\t (tabulação)"])
linhas_pular = st.sidebar.number_input("Linhas iniciais a ignorar", 0, 1000, 0)
tamanho_preview = st.sidebar.number_input("Tamanho do preview (linhas)", 10, 2000, 100, step=10)
encoding_opcao = st.sidebar.selectbox("Codificação", ["auto", "utf-8", "latin-1", "cp1252"])

processar_tudo = st.sidebar.button("🚀 Processar Todos os Arquivos")

# === 4. LEITURA DO ARQUIVO DE AMOSTRA ===
def ler_csv_robusto(file, sep, skip_rows, encoding_preferido, nrows_preview=None):
    encodings_teste = (
        [encoding_preferido] if encoding_preferido != "auto" else ["utf-8", "latin-1", "cp1252"]
    )
    for enc in encodings_teste:
        try:
            file.seek(0)
            df = pd.read_csv(
                file,
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

# Detecta separador e lê amostra
if sep_opcao == "auto":
    sep_detectado = detectar_separador(arquivo_amostra)
else:
    sep_detectado = {";": ";", ",": ",", "\\t (tabulação)": "\t"}[sep_opcao]

try:
    df_amostra, enc_usado = ler_csv_robusto(
        arquivo_amostra, sep_detectado, linhas_pular, encoding_opcao, tamanho_preview
    )

    st.subheader(f"📘 Pré-visualização do arquivo de amostra: `{arquivo_amostra_nome}`")
    st.caption(f"Separador detectado: `{sep_detectado}` • Encoding: `{enc_usado}` • Mostrando até {tamanho_preview} linhas após {linhas_pular} puladas")
    st.dataframe(df_amostra, use_container_width=True)

    st.markdown("---")

    # === 5. SELEÇÃO, RENOMEAÇÃO E ORDEM DAS COLUNAS ===
    opcoes_colunas = list(range(df_amostra.shape[1]))
    cols_idx = st.multiselect("🧩 Selecione as colunas (por índice):", opcoes_colunas, default=[0, 1])

    cols_nomes = []
    if cols_idx:
        st.markdown("✏️ **Nomeie cada coluna de saída:**")
        for i, idx in enumerate(cols_idx):
            nome = st.text_input(f"Nome para coluna {idx}:", value=f"Coluna_{idx}", key=f"nome_{idx}")
            cols_nomes.append(nome)

        st.markdown("🔀 **Defina a ordem das colunas de saída:**")
        cols_ordenadas = st.multiselect(
            "Reordene as colunas selecionadas (a ordem aqui será usada no arquivo final):",
            options=cols_nomes,
            default=cols_nomes
        )

        try:
            df_preview = df_amostra.iloc[:, cols_idx].copy()
            df_preview.columns = cols_nomes
            df_preview = df_preview[cols_ordenadas]

            df_preview = df_preview.map(lambda x: str(x).strip().replace(",", "."))
            for col in df_preview.columns:
                try:
                    df_preview[col] = pd.to_numeric(df_preview[col])
                except Exception:
                    pass

            st.subheader("🔎 Pré-visualização do resultado")
            st.dataframe(df_preview.head(20), use_container_width=True)
            st.success("✅ Pré-visualização gerada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao selecionar colunas: {e}")
            st.stop()
    else:
        st.info("👈 Selecione pelo menos uma coluna para continuar.")

except Exception as e:
    st.error(f"Erro ao carregar arquivo de amostra: {e}")
    st.stop()

# === 6. PROCESSAMENTO EM LOTE ===
def processar_csv_streamlit(file, sep, cols_idx, cols_nomes, cols_ordenadas, skip_rows, encoding_preferido):
    df, enc_usado = ler_csv_robusto(file, sep, skip_rows, encoding_preferido)
    df = df.map(lambda x: str(x).strip().replace(",", ".") if isinstance(x, str) else x)
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass
    df_sel = df.iloc[:, cols_idx].copy()
    df_sel.columns = cols_nomes
    df_sel = df_sel[cols_ordenadas]
    csv_buffer = io.StringIO()
    df_sel.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue(), enc_usado

if processar_tudo and cols_idx:
    st.info(f"📄 {len(arquivos)} arquivos recebidos. Iniciando processamento...")
    resultados = []
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for arquivo in arquivos:
            try:
                conteudo, enc = processar_csv_streamlit(
                    arquivo, sep_detectado, cols_idx, cols_nomes, cols_ordenadas, linhas_pular, encoding_opcao
                )
                zipf.writestr(arquivo.name, conteudo)
                resultados.append((arquivo.name, "✅ OK", f"Encoding: {enc}"))
            except Exception as e:
                resultados.append((arquivo.name, "❌ Erro", str(e)))

    st.success("🏁 Processamento concluído! Baixe o arquivo ZIP abaixo:")
    st.download_button(
        label="⬇️ Baixar arquivos processados (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="csv_processados.zip",
        mime="application/zip"
    )
    st.dataframe(pd.DataFrame(resultados, columns=["Arquivo", "Status", "Detalhes"]), use_container_width=True)
elif processar_tudo:
    st.warning("⚠️ Selecione e nomeie pelo menos uma coluna antes de processar.")
