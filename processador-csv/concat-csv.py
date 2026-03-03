import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Concatenador de CSVs", layout="wide")

st.title("📎 Concatenador de Arquivos CSV com Diagnóstico e Formatação")

uploaded_files = st.file_uploader(
    "Selecione os arquivos CSV",
    type=["csv"],
    accept_multiple_files=True
)

def read_csv_safely(file):
    """
    Lê CSV em qualquer separador (automático), sem warnings,
    tentando UTF-8 e fallback para Latin-1.
    """
    try:
        return pd.read_csv(
            file,
            sep=None,        # autodetecta separador
            engine="python"  # necessário para sep=None
        )
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(
            file,
            sep=None,
            engine="python",
            encoding="latin-1"
        )



# -----------------------------
# Escolha do padrão numérico
# -----------------------------
st.subheader("🔧 Configurações de Exportação")

format_option = st.selectbox(
    "Escolha o formato dos números no CSV exportado:",
    [
        "Ponto como separador decimal (padrão internacional)",
        "Vírgula como separador decimal (padrão brasileiro)"
    ]
)

use_comma = (format_option == "Vírgula como separador decimal (padrão brasileiro)")


if uploaded_files:

    dfs = []
    file_info = []
    col_info = {}

    # -----------------------------
    # Processamento dos arquivos
    # -----------------------------
    for f in uploaded_files:
        df = read_csv_safely(f)
        dfs.append(df)

        cols = list(df.columns)
        col_info[f.name] = cols

        file_info.append({
            "Arquivo": f.name,
            "Linhas": df.shape[0],
            "Colunas": df.shape[1],
            "Lista de colunas": ", ".join(cols)
        })

    # -----------------------------
    # Informações individuais
    # -----------------------------
    st.subheader("📄 Informações dos arquivos individuais")
    st.dataframe(pd.DataFrame(file_info), width="stretch")

    # -----------------------------
    # Comparação das colunas
    # -----------------------------
    st.subheader("🔍 Comparação das colunas entre arquivos")

    all_columns = set().union(*col_info.values())
    comparison_df = pd.DataFrame(
        index=list(col_info.keys()),
        columns=sorted(all_columns)
    )

    for fname, cols in col_info.items():
        for col in comparison_df.columns:
            comparison_df.loc[fname, col] = "✔️" if col in cols else "❌"

    st.dataframe(comparison_df, width="stretch")

    # -----------------------------
    # Concatenação
    # -----------------------------
    st.subheader("📌 Resultado da concatenação")

    try:
        df_concat = pd.concat(dfs, ignore_index=True)
        valid_concat = True
    except Exception as e:
        valid_concat = False
        st.error(f"Erro ao concatenar: {e}")

    if valid_concat:
        st.success("Concatenação realizada com sucesso!")
        st.write(f"**Total de linhas:** {df_concat.shape[0]}")
        st.write(f"**Total de colunas:** {df_concat.shape[1]}")
        st.dataframe(df_concat.head(), width="stretch")

        # -----------------------------
        # Formatação numérica para exportação
        # -----------------------------
        df_export = df_concat.copy()

        if use_comma:
            # Converte apenas colunas numéricas
            num_cols = df_export.select_dtypes(include="number").columns
            df_export[num_cols] = df_export[num_cols].apply(
                lambda col: col.map(lambda x: f"{x}".replace(".", ",") if pd.notna(x) else x)
            )

        # -----------------------------
        # Exportação
        # -----------------------------
        output = BytesIO()
        df_export.to_csv(output, index=False, encoding="utf-8-sig", sep=';')
        output.seek(0)

        st.download_button(
            label="📥 Baixar CSV Concatenado",
            data=output,
            file_name="concatenado.csv",
            mime="text/csv"
        )
