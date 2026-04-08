import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("$\\text{[Análise] Ensaios de Conexões}$")

# =====================================================
# CACHE
# =====================================================

@st.cache_data
def carregar_csv(file):
    return pd.read_csv(file)

# =====================================================
# SESSION STATE
# =====================================================

if "ensaios" not in st.session_state:
    st.session_state.ensaios = {}

# =====================================================
# UPLOAD
# =====================================================

uploaded_files = st.sidebar.file_uploader(
    "$\\text{Carregar CSV}$",
    type="csv",
    accept_multiple_files=True
)

if uploaded_files:

    for file in uploaded_files:

        if file.name not in st.session_state.ensaios:

            df = carregar_csv(file)

            st.session_state.ensaios[file.name] = {
                "df": df,
                "pontos": {
                    "v01":1,
                    "v04":1,
                    "v14":1,
                    "v11":1,
                    "v21":1,
                    "v24":1
                },
                "invert_x":"Normal",
                "invert_y":"Normal",
                "resultados":None
            }
else:
    st.info("Aguardando carregamento de arquivos")
    st.stop()

if len(st.session_state.ensaios) == 0:
    st.info("Carregue arquivos CSV.")
    st.stop()

# =====================================================
# ESCOLHER ENSAIO
# =====================================================

arquivo_atual = st.sidebar.selectbox(
    "$\\text{Selecionar ensaio}$",
    list(st.session_state.ensaios.keys())
)

dados = st.session_state.ensaios[arquivo_atual]
df = dados["df"]

# =====================================================
# COLUNAS
# =====================================================

st.sidebar.subheader("$\\text{Colunas}$")

colunas = df.columns.tolist()

col_tempo = st.sidebar.selectbox("$\\text{Tempo}$", colunas)
col_desloc = st.sidebar.selectbox("$\\text{Deslocamento}$", colunas)
col_forca = st.sidebar.selectbox("$\\text{Força}$", colunas)

tempo = df[col_tempo].to_numpy()
desloc = df[col_desloc].to_numpy()
forca = df[col_forca].to_numpy()

# vetor com o índice de cada ponto da série
indices = np.arange(len(df))

# =====================================================
# INVERTER EIXOS
# =====================================================

st.sidebar.subheader("$\\text{Eixos}$")

invert_x = st.sidebar.selectbox(
    "$\\text{Deslocamento}$",
    ["Normal","Invertido"],
    index=0 if dados["invert_x"]=="Normal" else 1
)

invert_y = st.sidebar.selectbox(
    "$\\text{Força}$",
    ["Normal","Invertido"],
    index=0 if dados["invert_y"]=="Normal" else 1
)

dados["invert_x"] = invert_x
dados["invert_y"] = invert_y

if invert_x == "Invertido":
    desloc = -desloc

if invert_y == "Invertido":
    forca = -forca

# =====================================================
# FMAX
# =====================================================

Fmax = np.max(forca)

F06 = 0.6 * Fmax
F08 = 0.8 * Fmax

idx_fmax = np.argmax(forca)

# procura apenas até o pico
forca_sub = forca[:idx_fmax]

idx_v26 = np.where(forca[:idx_fmax] >= F06)[0][0]
idx_v28 = np.where(forca[:idx_fmax] >= F08)[0][0]

# =====================================================
# PONTOS
# =====================================================

st.sidebar.subheader("$\\text{Índices}$")

n = len(df)

def escolher(nome):

    valor = st.sidebar.number_input(
        nome,
        min_value=1,
        max_value=n,
        value=dados["pontos"][nome],
        step=1
    )

    dados["pontos"][nome] = valor

    return valor - 1

v01_i = escolher("v01")
v04_i = escolher("v04")
v14_i = escolher("v14")
v11_i = escolher("v11")
v21_i = escolher("v21")
v24_i = escolher("v24")

# =====================================================
# VALORES
# =====================================================

v01 = desloc[v01_i]
v04 = desloc[v04_i]
v14 = desloc[v14_i]
v11 = desloc[v11_i]
v21 = desloc[v21_i]
v24 = desloc[v24_i]

v26 = desloc[idx_v26]
v28 = desloc[idx_v28]

# =====================================================
# RIGIDEZ
# =====================================================

F04 = forca[v04_i]
F11 = forca[v11_i]

# =====================================================
# PARÂMETROS
# =====================================================

v_i = v04
v_i_mod = (4/3)*(v04 - v01)

v_s = v_i - v_i_mod
v_e = (2/3)*(v14 + v24 - v11 - v21)

Fest = F04/.4

ki = F04 / v_i
ks = F04 / v_i_mod

v06_mod = v26 - v24 + v_i_mod
v08_mod = v28 - v24 + v_i_mod

resultados = pd.DataFrame([{
    "arquivo": file.name,

    "vi": v_i,
    "vi_mod": v_i_mod,
    "vs": v_s,
    "ki": ki,
    "ks": ks,
    "ve": v_e,

    "v_0.6": v26,
    "v_0.6_mod": v06_mod,
    "v_0.8": v28,
    "v_0.8_mod": v08_mod,

    # índices escolhidos pelo usuário
    "idx_v01": v01_i,
    "idx_v04": v04_i,
    "idx_v11": v11_i,
    "idx_v14": v14_i,
    "idx_v21": v21_i,
    "idx_v24": v24_i,

    # índices automáticos
    "idx_v26": idx_v26 + 1,
    "idx_v28": idx_v28 + 1,

    # inversões
    "invert_x": invert_x,
    "invert_y": invert_y,

    # metadados úteis
    "Fmax": Fmax,
    "Fest": Fest,
    "n_pontos": n
}])


dados["resultados"] = resultados

# =====================================================
# GRÁFICOS
# =====================================================

col1, col2 = st.columns(2)

# -----------------------------------------------------
# FORÇA VS TEMPO
# -----------------------------------------------------

with col1:

    fig_tempo = go.Figure()

    fig_tempo.add_trace(go.Scatter(
        x=tempo,
        y=forca,
        mode="lines",
        name="Curva",
        customdata=indices,
        hovertemplate=
            "Índice: %{customdata}<br>" +
            "Tempo: %{x}<br>" +
            "Força: %{y}<extra></extra>"
    ))

    pontos_tempo = [
        (tempo[v01_i], forca[v01_i], "01"),
        (tempo[v04_i], forca[v04_i], "04"),
        (tempo[v14_i], forca[v14_i], "14"),
        (tempo[v11_i], forca[v11_i], "11"),
        (tempo[v21_i], forca[v21_i], "21"),
        (tempo[v24_i], forca[v24_i], "24")
    ]

    for x, y, label in pontos_tempo:

        fig_tempo.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            text=[label],
            textposition="top center",
            marker=dict(size=10),
            name=f"Ponto {label}"
        ))

    fig_tempo.add_hline(
        y=F04,
        line_dash="dash",
        line_color="red",
        annotation_text="F04"
    )

    fig_tempo.add_hline(
        y=F11,
        line_dash="dash",
        line_color="green",
        annotation_text="F11"
    )

    fig_tempo.add_hline(
        y=Fest,
        line_dash="dash",
        line_color="magenta",
        annotation_text="Fest"
    )

    fig_tempo.update_layout(
        title="Força vs Tempo",
        xaxis_title="Tempo",
        yaxis_title="Força"
    )

    st.plotly_chart(fig_tempo, width="stretch")

# -----------------------------------------------------
# FORÇA VS DESLOCAMENTO
# -----------------------------------------------------

with col2:

    fig_desloc = go.Figure()

    fig_desloc.add_trace(go.Scatter(
        x=desloc,
        y=forca,
        mode="lines",
        name="Curva",
        customdata=indices,
        hovertemplate=
            "Índice: %{customdata}<br>" +
            "Deslocamento: %{x}<br>" +
            "Força: %{y}<extra></extra>"
    ))

    pontos_desloc = [
        (v01, forca[v01_i], "01"),
        (v04, forca[v04_i], "04"),
        (v14, forca[v14_i], "14"),
        (v11, forca[v11_i], "11"),
        (v21, forca[v21_i], "21"),
        (v24, forca[v24_i], "24"),
        (v26, forca[idx_v26], "26"),
        (v28, forca[idx_v28], "28")
    ]

    for x, y, label in pontos_desloc:

        fig_desloc.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            text=[label],
            textposition="top center",
            marker=dict(size=10),
            name=f"Ponto {label}"
        ))

    fig_desloc.update_layout(
        title="Força vs Deslocamento",
        xaxis_title="Deslocamento",
        yaxis_title="Força"
    )

    st.plotly_chart(fig_desloc, width="stretch")

# =====================================================
# CONSOLIDADO
# =====================================================

st.subheader("$\\text{Resultados consolidados}$")

tabela = []

for nome, dados in st.session_state.ensaios.items():

    if dados["resultados"] is not None:

        r = dados["resultados"].iloc[0]

        linha = r.to_dict()
        linha["arquivo"] = nome

        tabela.append(linha)

if tabela:

    df_final = pd.DataFrame(tabela)

    st.dataframe(df_final)

    st.download_button(
        "$\\text{Exportar CSV}$",
        df_final.to_csv(index=False),
        "resultados_ensaios.csv",
        "text/csv"
    )