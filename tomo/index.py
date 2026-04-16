import streamlit as st
import json
import hashlib
import numpy as np
import plotly.graph_objects as go
from matplotlib.path import Path

# Importação de todos os modelos do seu ficheiro interpoladores.py
from interpoladores import (
    du_interpolation_simple, 
    du_interpolation_compensated, 
    linear_back_projection,
    art_reconstruction,
    sirt_reconstruction,
    rbf_interpolation,
    ebsi_interpolation,       # EBSI Base do Artigo
    du_2018_segmented_rays    # Modelo Proposto em 2018
)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="LME Tomografia - Painel de Diagnóstico", 
    layout="wide", 
    page_icon="🌳"
)

# --- SISTEMA DE CACHE ---
def get_file_hash(path):
    try:
        with open("data.json", "rb") as f: 
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError: 
        return None

@st.cache_data
def load_data(file_hash):
    if file_hash is None: return None
    with open("data.json", "r", encoding="utf-8") as f: 
        return json.load(f)

data = load_data(get_file_hash("data.json"))

if not data:
    st.error("Ficheiro 'data.json' não encontrado.")
    st.stop()

# --- SIDEBAR: SELEÇÃO ---
st.sidebar.header("📂 Dados")
tree_options = {f"{t['especie']} (ID: {t['id_arvore']})": t for t in data["trees"]}
selected_tree_label = st.sidebar.selectbox("Árvore", options=list(tree_options.keys()))
selected_tree = tree_options[selected_tree_label]

scan = next((s for s in data["scans"] if s["id_arvore"] == selected_tree["id_arvore"]), None)
if scan:
    secoes = sorted(scan["sections"], key=lambda x: x["acquisition_time"])
    sec_opts = {f"📅 {s['acquisition_time'][:10]} | 📏 {s['height_cm']} cm": s for s in secoes}
    section = sec_opts[st.sidebar.selectbox("Tomografia", options=list(sec_opts.keys()))]
else:
    st.sidebar.warning("Nenhum dado disponível."); st.stop()

# --- SIDEBAR: CONFIGURAÇÕES E DICIONÁRIO LAMBDA ---
st.sidebar.divider()
st.sidebar.header("⚙️ Parâmetros")

# Captura de parâmetros da UI antes de definir o dicionário
threshold_pct = st.sidebar.select_slider("Sensibilidade ao Dano (%)", options=[35, 40, 45, 50, 55, 60, 65, 70], value=45)
res = st.sidebar.select_slider("Resolução", options=[50, 80, 100, 120], value=80)

# Parâmetros padrão iniciais
ecc, comp_val, ray_tol, art_iter, art_relax = 1.05, 2.5, 0.02, 10, 0.1

# Lista de modelos atualizada
nomes_modelos = [
    "Du Clássico", 
    "Du Compensado", 
    "EBSI (Base do Artigo)", 
    "Du 2018 (Modelo Proposto)", 
    "LBP (Linear)", 
    "ART (Iterativo)", 
    "SIRT (Simultâneo)", 
    "RBF (Suave)"
]
metodo = st.sidebar.selectbox("Modelo de Interpolação", options=nomes_modelos, index=3) # Du 2018 padrão

if "Du" in metodo or "EBSI" in metodo:
    ecc = st.sidebar.slider("Excentricidade (e)", 1.01, 1.25, 1.05)
    if "Compensado" in metodo:
        comp_val = st.sidebar.slider("Fator Compensação", 1.0, 5.0, 2.5)
elif metodo in ["ART (Iterativo)", "SIRT (Simultâneo)", "LBP (Linear)"]:
    ray_tol = st.sidebar.slider("Largura do Raio (m)", 0.01, 0.05, 0.02)
    if metodo != "LBP (Linear)":
        art_iter = st.sidebar.slider("Iterações", 1, 30, 10)
        art_relax = st.sidebar.slider("Relaxação", 0.05, 0.5, 0.1)

# DICIONÁRIO DE MODELOS USANDO LAMBDA
modelos = {
    "Du Clássico": lambda c, t, gx, gy: du_interpolation_simple(c, t, gx, gy, ecc),
    "Du Compensado": lambda c, t, gx, gy: du_interpolation_compensated(c, t, gx, gy, ecc, comp_val),
    "EBSI (Base do Artigo)": lambda c, t, gx, gy: ebsi_interpolation(c, t, gx, gy, ecc),
    "Du 2018 (Modelo Proposto)": lambda c, t, gx, gy: du_2018_segmented_rays(c, t, gx, gy, ecc),
    "LBP (Linear)": lambda c, t, gx, gy: linear_back_projection(c, t, gx, gy, ray_tol),
    "ART (Iterativo)": lambda c, t, gx, gy: art_reconstruction(c, t, gx, gy, art_iter, art_relax, ray_tol),
    "SIRT (Simultâneo)": lambda c, t, gx, gy: sirt_reconstruction(c, t, gx, gy, art_iter, art_relax, ray_tol),
    "RBF (Suave)": lambda c, t, gx, gy: rbf_interpolation(c, t, gx, gy)
}

# --- PROCESSAMENTO ---
contour = section["contour_nodes"]
node_map = {n["id"]: (n["x"]/100.0, n["y"]/100.0) for n in contour}
coords = np.array([node_map[s["contour_node_id"]] for s in section["sensors"]])
poly = np.array([(n["x"]/100.0, n["y"]/100.0) for n in contour])
num_sensors = len(coords)

T = np.zeros((num_sensors, num_sensors))
for p in section["propagation"]:
    i, j = p["i"]-1, p["j"]-1
    T[i, j] = T[j, i] = p["time"] / 1e6

grid_x = np.linspace(poly[:, 0].min(), poly[:, 0].max(), res)
grid_y = np.linspace(poly[:, 1].min(), poly[:, 1].max(), res)

# Execução unificada via Lambda
X, Y, v_field = modelos[metodo](coords, T, grid_x, grid_y)

# --- LÓGICA DE CORES E DIAGNÓSTICO ---
mask_tronco = Path(poly).contains_points(np.vstack([X.ravel(), Y.ravel()]).T).reshape(X.shape)
has_data = (v_field > 0) & mask_tronco

if np.any(has_data):
    v_max = np.nanmax(v_field[has_data])
    v_min = np.nanmin(v_field[has_data])
    
    # Threshold Adaptativo: Fundamental para modelos de segmentação e baseados em integral
    if any(m in metodo for m in ["2018", "EBSI", "SIRT", "RBF"]):
        v_threshold = v_min + (v_max - v_min) * (threshold_pct / 100.0)
    else:
        v_threshold = v_max * (threshold_pct / 100.0)
else:
    v_max, v_threshold = 1.0, 0.5

diagnostic_field = np.full_like(v_field, np.nan)
diagnostic_field[has_data & (v_field >= v_threshold)] = 1
diagnostic_field[has_data & (v_field < v_threshold)] = 0

# --- VISUALIZAÇÃO ---
st.title(f"🌳 Tomografia: {selected_tree['especie']}")
st.markdown(f"**Análise:** {metodo} | **Vmax:** {v_max:.0f} m/s")

fig = go.Figure()
fig.add_trace(go.Heatmap(x=grid_x, y=grid_y, z=diagnostic_field, colorscale=[[0, 'red'], [1, 'yellow']], showscale=False))
fig.add_trace(go.Scatter(x=np.append(poly[:,0], poly[0,0]), y=np.append(poly[:,1], poly[0,1]), mode="lines", line=dict(color="black", width=3), name="Casca"))
fig.add_trace(go.Scatter(x=coords[:,0], y=coords[:,1], mode="markers+text", text=[str(i+1) for i in range(num_sensors)], marker=dict(size=12, color="white", line=dict(width=2, color="black")), name="Sensores"))

fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=600)
st.plotly_chart(fig, use_container_width=True)

# --- MÉTRICAS ---
p_amostrados = np.count_nonzero(~np.isnan(diagnostic_field))
p_criticos = np.count_nonzero(diagnostic_field == 0)
dano = (p_criticos / p_amostrados * 100) if p_amostrados > 0 else 0

c1, c2, c3 = st.columns(3)
with c1: st.metric("Vmax de Referência", f"{v_max:.0f} m/s")
with c2: st.metric("Corte (Threshold)", f"{v_threshold:.0f} m/s")
with c3: st.metric("Dano Estimado", f"{dano:.1f}%", delta="CRÍTICO" if dano > 15 else "NORMAL", delta_color="inverse")