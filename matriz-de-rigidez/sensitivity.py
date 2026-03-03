import streamlit as st
import numpy as np
import pandas as pd
import importlib
import plotly.graph_objects as go

st.set_page_config(page_title="Sensibilidade — Impacto do Δ_real", layout="wide")
st.title("🔬 Sensibilidade das Propriedades → Impacto do Δ_real por Par (tabela abaixo do gráfico)")

# -------------------------
# Carregar dados_amostras.py
# -------------------------
try:
    importlib.invalidate_caches()
    dados_mod = importlib.import_module("dados_amostras")
    importlib.reload(dados_mod)
    dados = dados_mod.dados
except Exception as e:
    st.error(f"Erro ao carregar 'dados_amostras.py': {e}")
    st.stop()

# -------------------------
# Núcleo físico de cálculo
# -------------------------
def processar_amostra(dados_amostra, angulo_rad):
    import numpy as _np
    massa = dados_amostra["massa"]
    volume = dados_amostra["volume"]
    rho = massa / volume

    medidas = dados_amostra["medidas"]
    vel = {k: medidas[k]["dist"] / medidas[k]["tempo"] for k in medidas}

    V_LL = vel["LL"]
    V_RR = vel["RR"]
    V_TT = vel["TT"]
    V_LR = (vel["LR"] + vel["RL"]) / 2
    V_LT = (vel["LT"] + vel["TL"]) / 2
    V_RT = (vel["RT"] + vel["TR"]) / 2
    V_12a = (vel["RL1"] + vel["RL2"]) / 2
    V_13a = (vel["LT1"] + vel["LT2"]) / 2
    V_23a = (vel["RT1"] + vel["RT2"]) / 2

    C11 = rho * V_LL**2
    C22 = rho * V_RR**2
    C33 = rho * V_TT**2
    C44 = rho * V_RT**2
    C55 = rho * V_LT**2
    C66 = rho * V_LR**2

    n1 = np.sin(angulo_rad)
    n2 = np.cos(angulo_rad)
    n3 = np.cos(angulo_rad)

    C12 = (
        np.sqrt(
            (C11*n1**2 + C66*n2**2 - rho*V_12a**2) *
            (C66*n2**2 + C22*n1**2 - rho*V_12a**2)
        ) - C66*n1*n2
    ) / (n1*n2)

    C13 = (
        np.sqrt(
            (C11*n1**2 + C55*n3**2 - rho*V_13a**2) *
            (C55*n1**2 + C33*n3**2 - rho*V_13a**2)
        ) - C55*n1*n3
    ) / (n1*n3)

    C23 = (
        np.sqrt(
            (C22*n2**2 + C44*n3**2 - rho*V_23a**2) *
            (C44*n2**2 + C33*n3**2 - rho*V_23a**2)
        ) - C44*n2*n3
    ) / (n2*n3)

    C = np.array([
        [C11, C12, C13, 0,   0,   0],
        [C12, C22, C23, 0,   0,   0],
        [C13, C23, C33, 0,   0,   0],
        [0,   0,   0,   C44, 0,   0],
        [0,   0,   0,   0,   C55, 0],
        [0,   0,   0,   0,   0,   C66]
    ])

    S = np.linalg.inv(C)

    E = { "L": 1.0/S[0,0], "R": 1.0/S[1,1], "T": 1.0/S[2,2] }
    G = { "RT": 1.0/S[3,3], "LT": 1.0/S[4,4], "LR": 1.0/S[5,5] }
    nu = {
        "LR": -S[0,1]/S[0,0], "LT": -S[0,2]/S[0,0],
        "RL": -S[1,0]/S[1,1], "TL": -S[2,0]/S[2,2],
        "RT": -S[1,2]/S[1,1], "TR": -S[1,2]/S[2,2]
    }

    return {"E":E, "G":G, "nu":nu, "rho": rho, "C": C, "S": S, "vel": vel}


# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Configurações")
    amostra_sel = st.selectbox("Amostra", list(dados.keys()))
    amostra = dados[amostra_sel]

    prop_options = [
        "E_L","E_R","E_T",
        "G_LR","G_LT","G_RT",
        "nu_LR","nu_LT","nu_RL","nu_TL","nu_RT","nu_TR"
    ]
    prop_sel = st.selectbox("Propriedade (gráfico)", prop_options)

    pares = [
        ("LR","RL"), ("LT","TL"), ("RT","TR"),
        ("RL1","RL2"), ("LT1","LT2"), ("RT1","RT2")
    ]
    opcoes = ["Todos"] + [f"{a}-{b}" for a,b in pares]
    par_sel = st.selectbox("Par recíproco a perturbar (gráfico)", opcoes)

    angulo_deg = st.slider("Ângulo oblíquo (°)", 15.0, 45.0, 45.0)
    angulo_rad = np.deg2rad(angulo_deg)

    n_points = st.slider("Número de pontos (gráfico)", 10, 401, 81, step=10)

    delta_perturb_max = st.slider("Δ_perturb máximo (µs)", 0.0, 50.0, 20.0)


# -------------------------
# Extrair propriedade
# -------------------------
def extrai_prop(R, key):
    if key == "E_L": return R["E"]["L"]
    if key == "E_R": return R["E"]["R"]
    if key == "E_T": return R["E"]["T"]
    if key == "G_LR": return R["G"]["LR"]
    if key == "G_LT": return R["G"]["LT"]
    if key == "G_RT": return R["G"]["RT"]
    if key == "nu_LR": return R["nu"]["LR"]
    if key == "nu_LT": return R["nu"]["LT"]
    if key == "nu_RL": return R["nu"]["RL"]
    if key == "nu_TL": return R["nu"]["TL"]
    if key == "nu_RT": return R["nu"]["RT"]
    if key == "nu_TR": return R["nu"]["TR"]
    raise KeyError("Propriedade desconhecida")


# -------------------------
# Baseline simétrico
# -------------------------
medidas0 = amostra["medidas"]
tempo_base = {k: medidas0[k]["tempo"] for k in medidas0}

def make_symmetric_sample(orig):
    temp = {
        k: (v.copy() if isinstance(v, dict) else v)
        for k, v in orig.items()
    }
    temp["medidas"] = {
        k: (v.copy() if isinstance(v, dict) else v)
        for k, v in orig["medidas"].items()
    }

    for a,b in [
        ("LR","RL"),("LT","TL"),("RT","TR"),
        ("RL1","RL2"),("LT1","LT2"),("RT1","RT2")
    ]:
        ta = temp["medidas"][a]["tempo"]
        tb = temp["medidas"][b]["tempo"]
        tmin = min(ta, tb)
        temp["medidas"][a]["tempo"] = tmin
        temp["medidas"][b]["tempo"] = tmin

    return temp


# -------------------------
# NOVA FUNÇÃO: aplicar Δ_real + Δ_perturb
# -------------------------
def aplicar_delta(amostra_base, a, b, delta_real, delta_perturb):
    """
    Mantém o menor tempo fixo e reconstrói o maior:
        t_min
        t_max = t_min + delta_real + delta_perturb
    """
    temp = make_symmetric_sample(amostra_base)

    tA = amostra_base["medidas"][a]["tempo"]
    tB = amostra_base["medidas"][b]["tempo"]

    t_min = min(tA, tB)
    t_max = t_min + delta_real + delta_perturb

    if tA <= tB:
        temp["medidas"][a]["tempo"] = t_min
        temp["medidas"][b]["tempo"] = t_max
    else:
        temp["medidas"][a]["tempo"] = t_max
        temp["medidas"][b]["tempo"] = t_min

    return temp


# -------------------------
# Baseline symmetric properties
# -------------------------
symmetric_sample = make_symmetric_sample(amostra)
R_sym = processar_amostra(symmetric_sample, angulo_rad)
baseline_props = { key: extrai_prop(R_sym, key) for key in prop_options }


# -------------------------
# Tabela única: usando aplicar_delta
# -------------------------
rows = []
pairs_list = [
    ("LR","RL"),("LT","TL"),("RT","TR"),
    ("RL1","RL2"),("LT1","LT2"),("RT1","RT2")
]

for a,b in pairs_list:

    tA = tempo_base[a]
    tB = tempo_base[b]
    delta_real = abs(tA - tB)

    # aplica ONLY delta_real (delta_perturb = 0)
    temp = aplicar_delta(amostra, a, b, delta_real, 0.0)

    try:
        Rp = processar_amostra(temp, angulo_rad)

        deltas = {
            key: (extrai_prop(Rp, key) - baseline_props[key]) / baseline_props[key] * 100
            for key in baseline_props
        }
    except:
        deltas = {key: np.nan for key in baseline_props}

    soma_total = np.nansum(list(deltas.values()))

    rows.append({
        "par": f"{a}–{b}",
        "delta_real_us": delta_real * 1e6,
        **{f"Δ{key} (%)": deltas[key] for key in baseline_props},
        "soma_total_abs_pct": soma_total
    })

df_summary = pd.DataFrame(rows)


# -------------------------
# Gráfico: usando aplicar_delta (mesma lógica)
# -------------------------
if par_sel == "Todos":
    pares_escolhidos = pairs_list
else:
    a0,b0 = par_sel.split("-")
    pares_escolhidos = [(a0,b0)]

delta_perturb_us = np.linspace(0, delta_perturb_max, n_points)
delta_perturb_s = delta_perturb_us * 1e-6

fig = go.Figure()
baseline_prop = baseline_props[prop_sel]

for a,b in pares_escolhidos:

    tA = tempo_base[a]
    tB = tempo_base[b]
    delta_real = abs(tA - tB)

    y_vals = []
    for dp_s in delta_perturb_s:
        temp = aplicar_delta(amostra, a, b, delta_real, dp_s)

        try:
            Rtmp = processar_amostra(temp, angulo_rad)
            val = extrai_prop(Rtmp, prop_sel)
            pct = (val - baseline_prop) / baseline_prop * 100
            y_vals.append(pct)
        except:
            y_vals.append(np.nan)

    fig.add_trace(go.Scatter(
        x = delta_perturb_us,
        y = y_vals,
        mode = "lines",
        name = f"{a} ↔ {b}"
    ))

fig.update_layout(
    title = f"{prop_sel} — variação relativa ao baseline simétrico (Amostra: {amostra_sel})",
    xaxis_title = "Δ_perturb (µs)",
    yaxis_title = f"Δ% em {prop_sel}",
    template="plotly_white",
    height=550
)

st.plotly_chart(fig)


# -------------------------
# Tabela
# -------------------------
st.markdown("### Tabela: impacto do Δ_real de cada par (baseline simétrico)")

fmt_df = df_summary.copy()
for col in fmt_df.columns:
    if col.endswith("(%)") or col == "soma_total_abs_pct" or col == "delta_real_us":
        fmt_df[col] = fmt_df[col].astype(float)

fmt_df_display = fmt_df.rename(columns={
    "delta_real_us": "Δ_real (µs)"
})

st.dataframe(fmt_df_display.style.format({
    "Δ_real (µs)": "{:.3f}",
    "soma_total_abs_pct": "{:.3f}",
    **{col: "{:+.3f}%" for col in fmt_df_display.columns if col.endswith("(%)")}
}))


# -------------------------
# CSV export
# -------------------------
csv = df_summary.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Baixar CSV (impacto do Δ_real)",
    csv,
    file_name=f"impact_delta_real_{amostra_sel}.csv",
    mime="text/csv"
)

# ============================================================
# EXPORTAÇÃO GLOBAL (TODAS AS AMOSTRAS / TODOS OS PARES / TODAS AS PROPRIEDADES / TODOS OS Δ_perturb)
# ============================================================

st.markdown("---")
st.header("📤 Exportar CSV Global (todas as amostras para uso em Overleaf)")

if st.button("Gerar CSV Global"):
    linhas = []

    # propriedades a incluir
    props = [
        "E_L","E_R","E_T",
        "G_LR","G_LT","G_RT",
        "nu_LR","nu_LT","nu_RL","nu_TL","nu_RT","nu_TR"
    ]

    # pares recíprocos
    pairs_list = [
        ("LR","RL"),
        ("LT","TL"),
        ("RT","TR"),
        ("RL1","RL2"),
        ("LT1","LT2"),
        ("RT1","RT2")
    ]

    # vetor de perturbação Δ_perturb (em segundos)
    delta_perturb_us = np.linspace(0.0, delta_perturb_max, n_points)
    delta_perturb_s  = delta_perturb_us * 1e-6

    for nome_amostra, amostraX in dados.items():

        # tempos originais
        medidasX = amostraX["medidas"]
        tempo_baseX = {k: medidasX[k]["tempo"] for k in medidasX}

        # baseline simétrico
        symmetric_sampleX = make_symmetric_sample(amostraX)
        R_symX = processar_amostra(symmetric_sampleX, angulo_rad)

        baseline_propsX = {p: extrai_prop(R_symX, p) for p in props}

        for (a,b) in pairs_list:
            # delta real
            tA = tempo_baseX[a]
            tB = tempo_baseX[b]
            delta_real_s  = abs(tB - tA)
            delta_real_us = delta_real_s * 1e6

            t_min = min(tA,tB)

            # cada ponto do gráfico (para usar no Overleaf)
            for dp_s, dp_us in zip(delta_perturb_s, delta_perturb_us):
                delta_novo = delta_real_s + dp_s
                t_max_novo = t_min + delta_novo

                # construir amostra perturbada
                temp = make_symmetric_sample(amostraX)
                if tA <= tB:
                    temp["medidas"][a]["tempo"] = t_min
                    temp["medidas"][b]["tempo"] = t_max_novo
                else:
                    temp["medidas"][a]["tempo"] = t_max_novo
                    temp["medidas"][b]["tempo"] = t_min

                # calcular propriedades
                try:
                    Rtmp = processar_amostra(temp, angulo_rad)
                    for prop in props:
                        val_base = baseline_propsX[prop]
                        val_new  = extrai_prop(Rtmp, prop)
                        pct = (val_new - val_base) / val_base * 100.0
                        linhas.append({
                            "amostra": nome_amostra,
                            "par": f"{a}-{b}",
                            "propriedade": prop,
                            "delta_real_us": delta_real_us,
                            "delta_perturb_us": dp_us,
                            "pct_variacao": pct
                        })
                except:
                    for prop in props:
                        linhas.append({
                            "amostra": nome_amostra,
                            "par": f"{a}-{b}",
                            "propriedade": prop,
                            "delta_real_us": delta_real_us,
                            "delta_perturb_us": dp_us,
                            "pct_variacao": np.nan
                        })

    # criar dataframe final
    df_global = pd.DataFrame(linhas)

    # exportar
    csv_bytes = df_global.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Baixar CSV Global",
        csv_bytes,
        file_name="sensibilidade_delta_real_global.csv",
        mime="text/csv"
    )

    st.success("CSV global gerado com sucesso!")


st.info("Cada linha mostra o impacto isolado de cada Δ_real sobre todas as propriedades.")
