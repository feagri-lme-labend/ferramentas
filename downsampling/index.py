# =============================================================
#   Downsampling CSV (LTTB) — Multi-Arquivo com Métricas
#   Validação automática: Modo 3 (FLEX) — exige apenas X e Y existirem
# =============================================================

import streamlit as st
import pandas as pd
import numpy as np
import math
import zipfile
import io

st.set_page_config(layout="wide", page_title="Downsampling CSV (LTTB) - FLEX validation")


# ----------------------------
# Funções LTTB
# ----------------------------
def lttb_select_indices(values_x, values_y, threshold):
    n = len(values_x)
    if threshold >= n or threshold < 3:
        return np.arange(n, dtype=int)

    sampled = np.zeros(threshold, dtype=int)
    sampled[0] = 0
    sampled[-1] = n - 1

    bucket_size = (n - 2) / (threshold - 2)
    a = 0

    for i in range(threshold - 2):
        start = int(math.floor((i + 1) * bucket_size)) + 1
        end = int(math.floor((i + 2) * bucket_size)) + 1
        end = min(end, n - 1)

        if start >= end:
            sampled[i + 1] = start
            a = start
            continue

        ax, ay = values_x[a], values_y[a]
        bx, by = values_x[end], values_y[end]

        area_max = -1
        chosen = start

        for idx in range(start, end):
            px, py = values_x[idx], values_y[idx]
            area = abs((ax - px) * (by - ay) - (ax - bx) * (py - ay)) * 0.5
            if area > area_max:
                area_max = area
                chosen = idx

        sampled[i + 1] = chosen
        a = chosen

    return sampled


def lttb_downsample_df(df, xcol, ycol, target):
    if df is None or len(df) < 3:
        return df.copy()

    n = len(df)
    target = max(3, min(target, n))

    if target >= n:
        return df.copy()

    xs = df[xcol].to_numpy()
    ys = df[ycol].to_numpy()

    idx = np.sort(np.unique(lttb_select_indices(xs, ys, target)))
    return df.iloc[idx].reset_index(drop=True)


# ----------------------------
# Interface
# ----------------------------
st.title("📉 Downsampling Inteligente (LTTB) — Multi-Arquivo")
st.markdown("Validação automática FLEX: exige apenas que as colunas X e Y selecionadas existam em cada arquivo.")

uploaded_files = st.file_uploader(
    "Selecione múltiplos arquivos CSV (mesma estrutura):",
    accept_multiple_files=True,
    type=["csv"]
)

densidade = st.slider(
    "Densidade desejada (% dos pontos originais):",
    min_value=1, max_value=100, value=10, step=1
)

st.markdown("---")

if not uploaded_files:
    st.info("Envie ao menos um arquivo CSV…")
    st.stop()


# ----------------------------
# Preparar primeiro arquivo para escolher X/Y globais
# ----------------------------
# leitura segura do primeiro arquivo
file0 = uploaded_files[0]
try:
    file0.seek(0)
except Exception:
    pass

try:
    df0 = pd.read_csv(file0)
except Exception as e:
    st.error(f"Erro ao ler o primeiro arquivo: {e}")
    st.stop()

cols_num = df0.select_dtypes(include=np.number).columns.tolist()
if len(cols_num) < 2:
    st.error("Os CSVs devem conter ao menos 2 colunas numéricas no arquivo modelo.")
    st.stop()

st.subheader("🎯 Selecione as colunas globais para o LTTB (válidas para todos os arquivos)")

# selectboxes lado a lado; Y exclui X
col1, col2 = st.columns(2)
with col1:
    xcol_global = st.selectbox("Coluna X", cols_num, index=0)
with col2:
    y_options = [c for c in cols_num if c != xcol_global]
    # se por algum motivo y_options vazio (improvável), desabilitar
    if not y_options:
        st.error("Não há colunas disponíveis para Y (todas iguais a X).")
        st.stop()
    ycol_global = st.selectbox("Coluna Y", y_options, index=0)

st.markdown("---")


# ----------------------------
# Métricas pré-processamento (sem estimativa)
# ----------------------------
st.subheader("📊 Métricas dos Arquivos Carregados")

metrics_list = []
total_input_size = 0

for file in uploaded_files:
    # robust get size
    fsize = getattr(file, "size", None)
    if fsize is None:
        try:
            file.seek(0, io.SEEK_END)
            fsize = file.tell()
            file.seek(0)
        except Exception:
            fsize = 0

    total_input_size += fsize

    try:
        file.seek(0)
        df = pd.read_csv(file)
        cols_num_df = df.select_dtypes(include=np.number).columns
        metrics_list.append({
            "Arquivo": file.name,
            "Tamanho (KB)": round(fsize / 1024, 2),
            "Linhas": len(df),
            "Colunas": len(df.columns),
            "Colunas Numéricas": len(cols_num_df),
        })
    except Exception:
        metrics_list.append({
            "Arquivo": file.name,
            "Tamanho (KB)": round(fsize / 1024, 2),
            "Linhas": "ERRO",
            "Colunas": "ERRO",
            "Colunas Numéricas": 0,
        })

st.metric("📦 Tamanho total dos arquivos (KB)", round(total_input_size / 1024, 2))
st.dataframe(pd.DataFrame(metrics_list), width="stretch")

st.markdown("---")


# ----------------------------
# Processamento com validação FLEX (apenas X e Y precisam existir)
# ----------------------------
processar = st.button("🚀 Processar todos os arquivos e gerar ZIP")

if processar:
    zip_buffer = io.BytesIO()
    z = zipfile.ZipFile(zip_buffer, "w")
    status_list = []
    total_processed_bytes = 0

    for file in uploaded_files:
        # robust size
        fsize = getattr(file, "size", None)
        if fsize is None:
            try:
                file.seek(0, io.SEEK_END)
                fsize = file.tell()
                file.seek(0)
            except Exception:
                fsize = 0

        if fsize == 0:
            status_list.append({
                "Arquivo": file.name,
                "Linhas Originais": 0,
                "Linhas Downsample": 0,
                "Status": "❌",
                "Mensagem": "Arquivo vazio."
            })
            continue

        try:
            file.seek(0)
            df = pd.read_csv(file)
        except Exception as e:
            status_list.append({
                "Arquivo": file.name,
                "Linhas Originais": 0,
                "Linhas Downsample": 0,
                "Status": "❌",
                "Mensagem": f"Erro ao ler arquivo: {e}"
            })
            continue

        # VALIDAÇÃO FLEX: apenas requer que X e Y existam
        if xcol_global not in df.columns or ycol_global not in df.columns:
            status_list.append({
                "Arquivo": file.name,
                "Linhas Originais": len(df),
                "Linhas Downsample": 0,
                "Status": "❌",
                "Mensagem": "Arquivo incompatível: colunas X/Y ausentes."
            })
            continue

        # Colunas existem — tenta converter para numérico (coerce) para evitar erros no LTTB
        # Fazemos cópias locais convertidas (sem sobrescrever o CSV original)
        df_local = df.copy()
        df_local[xcol_global] = pd.to_numeric(df_local[xcol_global], errors="coerce")
        df_local[ycol_global] = pd.to_numeric(df_local[ycol_global], errors="coerce")
        # remove linhas onde X ou Y são NaN (não numéricos após coercion)
        df_local = df_local.dropna(subset=[xcol_global, ycol_global]).reset_index(drop=True)

        if df_local.empty:
            status_list.append({
                "Arquivo": file.name,
                "Linhas Originais": len(df),
                "Linhas Downsample": 0,
                "Status": "❌",
                "Mensagem": "Após conversão, nenhuma linha válida para X/Y."
            })
            continue

        # calcula target e aplica LTTB
        target_points = max(3, int(len(df_local) * (densidade / 100)))

        try:
            df_down = lttb_downsample_df(df_local, xcol_global, ycol_global, target_points)
        except Exception as e:
            status_list.append({
                "Arquivo": file.name,
                "Linhas Originais": len(df_local),
                "Linhas Downsample": 0,
                "Status": "❌",
                "Mensagem": f"Erro no LTTB: {e}"
            })
            continue

        # escreve no ZIP
        out_name = f"{file.name.replace('.csv','')}_downsampled.csv"
        content = df_down.to_csv(index=False)
        try:
            z.writestr(out_name, content.encode("utf-8"))
        except Exception:
            z.writestr(out_name, content)

        total_processed_bytes += len(content.encode("utf-8")) if isinstance(content, str) else len(content)
        status_list.append({
            "Arquivo": file.name,
            "Linhas Originais": len(df_local),
            "Linhas Downsample": len(df_down),
            "Status": "✅",
            "Mensagem": "Processado com sucesso"
        })

    z.close()

    # métricas finais de tamanho
    total_output_size = len(zip_buffer.getvalue())
    st.metric("📦 Tamanho total final (ZIP KB)", round(total_output_size / 1024, 2))

    st.success("✅ Processamento concluído!")

    st.subheader("📄 Métricas Pós-Processamento (Status por arquivo)")
    st.dataframe(pd.DataFrame(status_list), width="stretch")

    st.download_button(
        "📥 Baixar ZIP com arquivos reduzidos",
        zip_buffer.getvalue(),
        "downsampled_csv_files.zip",
        mime="application/zip"
    )
