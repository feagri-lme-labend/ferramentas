# ================================================================
#  index_uploader_plotly.py
#
#  Caçador de Linearidade — Versão Premium (Plotly)
#  (Apenas modificações na Tabela Geral: Ymin/Ymax -> global + filtro)
# ================================================================

import math
import numpy as np
import pandas as pd
import streamlit as st
import warnings
import plotly.graph_objects as go

# ----------------------------------------------------------------
# Configuração da página
# ----------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("🎯 $\\text{Caçador de Linearidade}$")
st.markdown(
    "Visualização: densidade adaptativa (LTTB) para plotagem + regressão em alta resolução. "
)

warnings.filterwarnings("ignore", category=UserWarning)

PERCENTUAIS_JANELA_X = [100]


# ================================================================
# 1) Funções utilitárias de leitura
# ================================================================
def safe_read_csv(uploaded_file):
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file)


# ================================================================
# 2) Upload e validações iniciais
# ================================================================
uploaded_files = st.file_uploader(
    "📂 Envie até 10 arquivos CSV (multiple allowed):",
    type=["csv"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Aguardando upload de arquivos CSV...")
    st.stop()

if len(uploaded_files) > 10:
    st.error("Máximo de 10 arquivos.")
    st.stop()

try:
    primeiro_df = safe_read_csv(uploaded_files[0])
except Exception as e:
    st.error(f"Erro ao ler o primeiro arquivo: {e}")
    st.stop()

colunas_all = primeiro_df.columns.tolist()
if len(colunas_all) < 2:
    st.error("Os arquivos precisam conter pelo menos duas colunas.")
    st.stop()

colunas_numericas = [
    c for c in colunas_all if np.issubdtype(primeiro_df[c].dtype, np.number)
]
if not colunas_numericas:
    st.error("Nenhuma coluna numérica encontrada.")
    st.stop()


# ================================================================
# 3) Sidebar — configurações
# ================================================================
st.sidebar.markdown("### ⚙️ $\\text{Configurações de Análise}$")

selected_files_analysis = st.sidebar.multiselect(
    "1) Arquivos para análise:",
    options=[f.name for f in uploaded_files],
    default=[f.name for f in uploaded_files]
)
if not selected_files_analysis:
    st.warning("Selecione ao menos um arquivo.")
    st.stop()

st.sidebar.subheader("2) Colunas principais")
coluna_x = st.sidebar.selectbox("Coluna X:", colunas_all, index=0)
coluna_y = st.sidebar.selectbox("Coluna Y:", colunas_all, index=1)

st.sidebar.subheader("3) Coluna auxiliar para filtro")
coluna_suporte = st.sidebar.selectbox("Coluna Suporte:", colunas_numericas)

st.sidebar.subheader("4) Arquivo ativo")
arquivo_ativo = st.sidebar.selectbox("Arquivo ativo:", selected_files_analysis)

st.sidebar.subheader("5) Arquivo para gráfico")
selected_file_plot = st.sidebar.selectbox("Arquivo (gráfico):", selected_files_analysis)

st.sidebar.subheader("6) Janela X (%)")
selected_janela_plot = st.sidebar.selectbox("Janela:", [f"{p}%" for p in PERCENTUAIS_JANELA_X])

st.sidebar.subheader("7) Densidade Adaptativa (Visualização)")
densidade_adaptativa = st.sidebar.slider(
    "Densidade (% dos pontos exibidos):",
    1, 100, 10, 1,
    help="Percentual de pontos exibidos (LTTB)."
)


# ================================================================
# 4) Ler todos os arquivos em memória
# ================================================================
dataframes_raw = {}
for f in uploaded_files:
    try:
        df = safe_read_csv(f)
    except Exception as e:
        st.error(f"Erro ao ler {f.name}: {e}")
        st.stop()
    dataframes_raw[f.name] = df


# ================================================================
# 5) Session state: parâmetros por arquivo
# ================================================================
if "params" not in st.session_state:
    st.session_state["params"] = {}

for fname in selected_files_analysis:
    if fname not in st.session_state["params"]:
        df_tmp = dataframes_raw[fname]
        smin = float(pd.to_numeric(df_tmp[coluna_suporte], errors="coerce").min())
        smax = float(pd.to_numeric(df_tmp[coluna_suporte], errors="coerce").max())
        st.session_state["params"][fname] = {
            "invert_x": False,
            "invert_y": False,
            "support_min": smin,
            "support_max": smax,
            "y_min_perc": 10,
            "y_max_perc": 40,
        }

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Parâmetros: `{arquivo_ativo}`**")
p_act = st.session_state["params"][arquivo_ativo]

new_invx = st.sidebar.checkbox("Inverter X", value=p_act["invert_x"])
new_invy = st.sidebar.checkbox("Inverter Y", value=p_act["invert_y"])

df_act = dataframes_raw[arquivo_ativo]
min_sup = float(pd.to_numeric(df_act[coluna_suporte], errors="coerce").min())
max_sup = float(pd.to_numeric(df_act[coluna_suporte], errors="coerce").max())

new_sup_min, new_sup_max = st.sidebar.slider(
    f"Filtro '{coluna_suporte}' ({arquivo_ativo}):",
    min_value=min_sup, max_value=max_sup,
    value=(p_act["support_min"], p_act["support_max"])
)

new_ymin, new_ymax = st.sidebar.slider(
    f"Filtro Y (% do Ymax) — {arquivo_ativo}:",
    0, 100,
    (p_act["y_min_perc"], p_act["y_max_perc"])
)

p_act["invert_x"] = new_invx
p_act["invert_y"] = new_invy
p_act["support_min"] = float(new_sup_min)
p_act["support_max"] = float(new_sup_max)
p_act["y_min_perc"] = int(new_ymin)
p_act["y_max_perc"] = int(new_ymax)


# ================================================================
# 6) Funções de cálculo
# ================================================================
def regress_linear_window(X, Y, start, n_window):
    xw = X[start:start+n_window]
    yw = Y[start:start+n_window]

    if len(xw) < 2:
        return 0.0, 0.0, 0.0, np.nan

    try:
        slope, intercept = np.polyfit(xw, yw, 1)
    except Exception:
        return 0.0, 0.0, 0.0, np.nan

    if np.std(yw) == 0 or np.std(xw) == 0:
        r2 = 0.0
    else:
        r = np.corrcoef(xw, yw)[0, 1]
        r2 = float(np.clip(r*r, 0, 1))

    try:
        n = len(xw)
        if n > 2 and np.std(xw) > 0:
            ypred = slope*xw + intercept
            resid = yw - ypred
            s2 = np.sum(resid**2)/(n-2)
            se = np.sqrt(s2 / np.sum((xw - np.mean(xw))**2))
        else:
            se = np.nan
    except Exception:
        se = np.nan

    return r2, intercept, slope, se


@st.cache_data
def calcular_melhor_janela(df, n_window, coluna_x, coluna_y, stride=2):
    N = len(df)
    if N < 5 or n_window < 2 or n_window > N:
        return {
            "start": 0, "r2": 0.0, "intercept": 0.0, "slope": 0.0,
            "se_slope": np.nan, "xmin": np.nan, "xmax": np.nan
        }

    X = df[coluna_x].values
    Y = df[coluna_y].values

    best_r2 = -1
    best = None

    for i in range(0, N-n_window+1, max(1, stride)):
        r2, b0, b1, se = regress_linear_window(X, Y, i, n_window)
        if r2 > best_r2:
            best_r2 = r2
            best = (i, r2, b0, b1, se)

    last = N - n_window
    if last >= 0:
        r2, b0, b1, se = regress_linear_window(X, Y, last, n_window)
        if r2 > best_r2:
            best = (last, r2, b0, b1, se)

    if best is None:
        return {
            "start": 0, "r2": 0.0, "intercept": 0.0, "slope": 0.0,
            "se_slope": np.nan, "xmin": np.nan, "xmax": np.nan
        }

    i, r2, b0, b1, se = best
    xmin = df.iloc[i][coluna_x]
    xmax = df.iloc[i+n_window-1][coluna_x]

    return {
        "start": int(i), "r2": float(r2), "intercept": float(b0),
        "slope": float(b1), "se_slope": float(se),
        "xmin": float(xmin), "xmax": float(xmax)
    }


# ================================================================
# 7) LTTB e downsampling
# (mantido sem modificações)
# ================================================================
def lttb_select_indices(values_x, values_y, threshold):
    n = len(values_x)
    if threshold >= n or threshold < 3:
        return np.arange(n, dtype=int)

    sampled = np.zeros(threshold, dtype=int)
    sampled[0] = 0
    sampled[-1] = n - 1

    bucket_size = (n - 2) / (threshold - 2)
    a = 0

    for i in range(0, threshold-2):
        start = int(math.floor((i+1)*bucket_size)) + 1
        end = int(math.floor((i+2)*bucket_size)) + 1
        if end >= n:
            end = n - 1
        if start >= end:
            sampled[i+1] = start
            a = start
            continue

        bucket = np.arange(start, end)
        ax, ay = values_x[a], values_y[a]
        bx, by = values_x[end], values_y[end]
        area_max = -1
        chosen = start
        for idx in bucket:
            px, py = values_x[idx], values_y[idx]
            area = abs((ax - px)*(by - ay) - (ax - bx)*(py - ay)) * 0.5
            if area > area_max:
                area_max = area
                chosen = idx

        sampled[i+1] = chosen
        a = chosen

    return sampled


def lttb_downsample_preserve_df(df, xcol, ycol, threshold):
    if df is None or len(df) == 0:
        return df.copy()
    n = len(df)
    if threshold >= n or threshold < 3:
        return df.copy()
    xs = df[xcol].to_numpy()
    ys = df[ycol].to_numpy()
    idx = np.sort(np.unique(lttb_select_indices(xs, ys, threshold)))
    return df.iloc[idx].copy()


def adaptive_downsample_preserve_df(df, xcol, ycol, perc):
    if perc >= 100:
        return df.copy()
    n = len(df)
    if n == 0:
        return df.copy()
    target = max(50, int(n*(perc/100)))
    target = min(target, n)
    try:
        return lttb_downsample_preserve_df(df, xcol, ycol, target).reset_index(drop=True)
    except:
        step = max(1, n//target)
        return df.iloc[::step].reset_index(drop=True)


# ================================================================
# 8) Processamento consolidado (TABELA GERAL MODIFICADA)
# ================================================================
st.header("📊 $\\text{Análise Consolidada}$")

results = []
with st.spinner("Processando arquivos..."):
    for fname in selected_files_analysis:
        df = dataframes_raw[fname].copy()

        df[coluna_x] = pd.to_numeric(df[coluna_x], errors="coerce")
        df[coluna_y] = pd.to_numeric(df[coluna_y], errors="coerce")
        df[coluna_suporte] = pd.to_numeric(df[coluna_suporte], errors="coerce")

        p = st.session_state["params"][fname]

        if p.get("invert_x", False):
            df[coluna_x] *= -1
        if p.get("invert_y", False):
            df[coluna_y] *= -1

        ymax = df[coluna_y].max(skipna=True)
        if np.isnan(ymax):
            continue

        # NOVO: limites globais reais
        y_global_min = df[coluna_y].min(skipna=True)
        y_global_max = df[coluna_y].max(skipna=True)

        # NOVO: faixa percentual = filtro
        y_filtro_min = ymax * (p["y_min_perc"] / 100)
        y_filtro_max = ymax * (p["y_max_perc"] / 100)

        df_s = df[
            (df[coluna_suporte] >= p["support_min"]) &
            (df[coluna_suporte] <= p["support_max"])
        ]

        df_f = df_s[
            (df_s[coluna_y] >= y_filtro_min) &
            (df_s[coluna_y] <= y_filtro_max)
        ].reset_index(drop=True)

        if len(df_f) < 5:
            if len(df) >= 5:
                df_f = df.reset_index(drop=True)
            else:
                continue

        n_total = len(df)
        n_filtered = len(df_f)

        for perc in PERCENTUAIS_JANELA_X:
            n_window = max(5, int(len(df_f) * (perc / 100)))
            best = calcular_melhor_janela(df_f, n_window, coluna_x, coluna_y)

            results.append({
                "Arquivo": fname,
                "Invert X": p["invert_x"],
                "Invert Y": p["invert_y"],
                "Support Min": p["support_min"],
                "Support Max": p["support_max"],
                "Y Min (%)": p["y_min_perc"],
                "Y Max (%)": p["y_max_perc"],

                # NOVAS COLUNAS
                "Y_Global_Min": y_global_min,
                "Y_Global_Max": y_global_max,
                "Y_Filtro_Min": y_filtro_min,
                "Y_Filtro_Max": y_filtro_max,

                "Qtd Total": n_total,
                "Qtd Filtrada": n_filtered,
                "Janela X (%)": f"{perc}%",
                "N Pontos": n_window,
                "R²": best["r2"],
                "B1": best["slope"],
                "SE_B1": best["se_slope"],
                "B0": best["intercept"],
                "Xmin Região": best["xmin"],
                "Xmax Região": best["xmax"],
                "Idx Start": best["start"]
            })


df_results = pd.DataFrame(results)
if df_results.empty:
    st.error("Nenhum resultado encontrado.")
    st.stop()

# NOVO: format_dict atualizado
format_dict = {
    "R²": "{:.4f}",
    "B1": "{:.4f}",
    "B0": "{:.4f}",
    "Xmin Região": "{:.4f}",
    "Xmax Região": "{:.4f}",
    "Y_Global_Min": "{:.4f}",
    "Y_Global_Max": "{:.4f}",
    "Y_Filtro_Min": "{:.4f}",
    "Y_Filtro_Max": "{:.4f}",
    "Support Min": "{:.4f}",
    "Support Max": "{:.4f}"
}

st.markdown("### 📋 $\\text{Tabela de Resultados (alta resolução)}$")
st.dataframe(df_results.style.format(format_dict), width="stretch")


# ================================================================
# 9) Visualização detalhada (Plotly) — atualizada p/ novos nomes
# ================================================================
st.divider()
st.header("📈 $\\text{Visualização Detalhada (Plotly)]}$")

df_plot_row = df_results[
    (df_results["Arquivo"] == selected_file_plot) &
    (df_results["Janela X (%)"] == selected_janela_plot)
]

if df_plot_row.empty:
    st.warning("Nenhum resultado para o arquivo/janela selecionados.")
    st.stop()

row = df_plot_row.iloc[0]

df_plot = dataframes_raw[selected_file_plot].copy()
df_plot[coluna_x] = pd.to_numeric(df_plot[coluna_x], errors="coerce")
df_plot[coluna_y] = pd.to_numeric(df_plot[coluna_y], errors="coerce")
df_plot[coluna_suporte] = pd.to_numeric(df_plot[coluna_suporte], errors="coerce")

p_plot = st.session_state["params"][selected_file_plot]
if p_plot["invert_x"]:
    df_plot[coluna_x] *= -1
if p_plot["invert_y"]:
    df_plot[coluna_y] *= -1

# NOVO: pegar os nomes corrigidos
y_filtro_min = row["Y_Filtro_Min"]
y_filtro_max = row["Y_Filtro_Max"]

df_plot["DentroSuporte"] = (
    (df_plot[coluna_suporte] >= p_plot["support_min"]) &
    (df_plot[coluna_suporte] <= p_plot["support_max"])
)
df_plot["DentroY"] = (
    (df_plot[coluna_y] >= y_filtro_min) &
    (df_plot[coluna_y] <= y_filtro_max)
)

df_used = df_plot[df_plot["DentroSuporte"] & df_plot["DentroY"]].reset_index(drop=True)
if len(df_used) < 5:
    df_used = df_plot[df_plot["DentroY"]].reset_index(drop=True)
if len(df_used) < 5:
    df_used = df_plot.reset_index(drop=True)

n_window_plot = int(row["N Pontos"])
best = calcular_melhor_janela(df_used, n_window_plot, coluna_x, coluna_y)

idx_start = best["start"]
df_best = df_used.iloc[idx_start:idx_start+n_window_plot].reset_index(drop=True)

xmin = best["xmin"]
xmax = best["xmax"]
b0 = best["intercept"]
b1 = best["slope"]

df_line = pd.DataFrame({
    coluna_x: [xmin, xmax],
    coluna_y: [b1*xmin + b0, b1*xmax + b0]
})

df_plot_vis = adaptive_downsample_preserve_df(df_plot, coluna_x, coluna_y, densidade_adaptativa)
df_used_vis = adaptive_downsample_preserve_df(df_used, coluna_x, coluna_y, densidade_adaptativa)

fora_vis = df_plot_vis[~(df_plot_vis["DentroSuporte"] & df_plot_vis["DentroY"])].reset_index(drop=True)
dentro_vis = df_used_vis.reset_index(drop=True)
df_best_plot = df_best.copy()
if df_best_plot.empty and len(df_used) > 0:
    df_best_plot = df_used.iloc[:min(5, len(df_used))].copy()

fig = go.Figure()

x_min_plot = df_plot[coluna_x].min()
x_max_plot = df_plot[coluna_x].max()

fig.add_shape(
    type="rect",
    x0=x_min_plot,
    x1=x_max_plot,
    y0=y_filtro_min,
    y1=y_filtro_max,
    fillcolor="lightgreen",
    opacity=0.15,
    line_width=0,
    layer="below"
)

fig.add_trace(go.Scatter(
    x=fora_vis[coluna_x].tolist(),
    y=fora_vis[coluna_y].tolist(),
    mode="markers",
    marker=dict(size=5, color="lightgray", opacity=0.6),
    name="Fora dos filtros"
))

fig.add_trace(go.Scatter(
    x=dentro_vis[coluna_x].tolist(),
    y=dentro_vis[coluna_y].tolist(),
    mode="markers",
    marker=dict(size=6, color="steelblue", opacity=0.8),
    name="Dentro da faixa"
))

fig.add_trace(go.Scatter(
    x=df_best_plot[coluna_x].tolist(),
    y=df_best_plot[coluna_y].tolist(),
    mode="markers",
    marker=dict(size=5, color="#7159c1"),
    name="Janela vencedora"
))

fig.add_trace(go.Scatter(
    x=df_line[coluna_x].tolist(),
    y=df_line[coluna_y].tolist(),
    mode="lines",
    line=dict(color="orange", width=3, dash="dash"),
    name="Regressão"
))

fig.update_layout(
    title=f"{selected_file_plot} — R² = {row['R²']:.4f} — Densidade: {densidade_adaptativa}%",
    width=1000,
    height=550,
    template="plotly_white",
    legend=dict(xanchor="right", x=1.02, yanchor="top", y=1)
)

fig.update_xaxes(title=coluna_x)
fig.update_yaxes(title=coluna_y)

st.plotly_chart(fig)


# ================================================================
# Observações finais
# ================================================================
st.markdown(
    """
    **Observações**
    - A regressão é sempre feita com dados sem downsampling.
    - O LTTB atua apenas na visualização.
    - A janela vencedora e a reta são sempre completas.
    """
)
