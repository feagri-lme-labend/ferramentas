import streamlit as st
import json
import hashlib
import numpy as np
from matplotlib.path import Path
import io
import matplotlib.pyplot as plt
from datetime import datetime
import zipfile
from scipy.ndimage import binary_dilation

# --- CONFIGURAÇÃO E CACHE ---
st.set_page_config(page_title="LME Tomografia - Otimizado", layout="wide", page_icon="🌳")

from interpoladores import (
    du_interpolation_simple, du_interpolation_compensated, 
    linear_back_projection, art_reconstruction, 
    sirt_reconstruction, rbf_interpolation,
    ebsi_interpolation, du_2018_segmented_rays
)

def get_file_hash(path):
    try:
        with open(path, "rb") as f: return hashlib.md5(f.read()).hexdigest()
    except: return None

@st.cache_data
def load_data(file_hash):
    if file_hash is None: return None
    with open("data.json", "r", encoding="utf-8") as f: return json.load(f)

data = load_data(get_file_hash("data.json"))
if not data: st.stop()

# --- SIDEBAR E PARÂMETROS ---
st.sidebar.header("📂 Seleção e Parâmetros")
tree_options = {f"{t['especie']} (ID: {t['id_arvore']})": t for t in data["trees"]}
selected_tree = tree_options[st.sidebar.selectbox("Árvore", options=list(tree_options.keys()))]

scan = next((s for s in data["scans"] if s["id_arvore"] == selected_tree["id_arvore"]), None)
secoes = sorted(scan["sections"], key=lambda x: x["acquisition_time"])
sec_opts = {f"📏 {s['height_cm']} cm": s for s in secoes}
section = sec_opts[st.sidebar.selectbox("Tomografia", options=list(sec_opts.keys()))]

threshold_pct = st.sidebar.select_slider("Sensibilidade ao Dano (%)", options=list(range(30, 81, 5)), value=45)
res_base = st.sidebar.select_slider("Resolução (Lado Maior)", options=[50, 80, 100, 120, 150, 200], value=100)

nomes_modelos = ["Du Clássico", "Du Compensado", "EBSI (Base)", "Du 2018 (Proposto)", "LBP (Linear)", "ART (Iterativo)", "SIRT (Simultâneo)", "RBF (Suave)"]
metodo = st.sidebar.selectbox("Modelo", options=nomes_modelos, index=3)

# --- RECUPERANDO OS SLIDERS ESPECÍFICOS ---
ecc, comp_val, ray_tol, art_iter, art_relax = 1.05, 2.5, 0.02, 15, 0.1

if any(m in metodo for m in ["Du", "EBSI"]):
    ecc = st.sidebar.slider("Excentricidade (e)", 1.01, 1.30, 1.05)
    if "Compensado" in metodo:
        comp_val = st.sidebar.slider("Fator Compensação", 1.0, 5.0, 2.5)

elif metodo in ["ART (Iterativo)", "SIRT (Simultâneo)", "LBP (Linear)"]:
    ray_tol = st.sidebar.slider("Largura do Raio (m)", 0.005, 0.05, 0.02, step=0.005)
    if metodo != "LBP (Linear)":
        art_iter = st.sidebar.slider("Iterações", 1, 50, 15)
        art_relax = st.sidebar.slider("Fator de Relaxação", 0.01, 0.5, 0.1)

# --- PROCESSAMENTO ---
nodes = section["contour_nodes"]
node_map = {n["id"]: (n["x"]/100.0, n["y"]/100.0) for n in nodes}
coords = np.array([node_map[s["contour_node_id"]] for s in section["sensors"]])
poly = np.array([(n["x"]/100.0, n["y"]/100.0) for n in nodes])

T = np.zeros((len(coords), len(coords)))
for p in section["propagation"]:
    i, j = p["i"]-1, p["j"]-1
    T[i, j] = T[j, i] = p["time"] / 1e6

# Grade Proporcional (Calculada com os novos limites)
x_min_real, x_max_real = poly[:, 0].min(), poly[:, 0].max()
y_min_real, y_max_real = poly[:, 1].min(), poly[:, 1].max()
largura_real = x_max_real - x_min_real
profundidade_real = y_max_real - y_min_real

if largura_real > profundidade_real:
    res_x, res_y = res_base, int(res_base * (profundidade_real / largura_real))
else:
    res_y, res_x = res_base, int(res_base * (largura_real / profundidade_real))

grid_x = np.linspace(x_min_real, x_max_real, res_x)
grid_y = np.linspace(y_min_real, y_max_real, res_y)

# Dicionário de modelos injetando as variáveis dos sliders
modelos = {
    "Du Clássico": lambda: du_interpolation_simple(coords, T, grid_x, grid_y, ecc),
    "Du Compensado": lambda: du_interpolation_compensated(coords, T, grid_x, grid_y, ecc, comp_val),
    "EBSI (Base)": lambda: ebsi_interpolation(coords, T, grid_x, grid_y, ecc),
    "Du 2018 (Proposto)": lambda: du_2018_segmented_rays(coords, T, grid_x, grid_y, ecc),
    "LBP (Linear)": lambda: linear_back_projection(coords, T, grid_x, grid_y, ray_tol),
    "ART (Iterativo)": lambda: art_reconstruction(coords, T, grid_x, grid_y, art_iter, art_relax, ray_tol),
    "SIRT (Simultâneo)": lambda: sirt_reconstruction(coords, T, grid_x, grid_y, art_iter, art_relax, ray_tol),
    "RBF (Suave)": lambda: rbf_interpolation(coords, T, grid_x, grid_y)
}

X, Y, v_field = modelos[metodo]()

mask_tronco = Path(poly).contains_points(np.vstack([X.ravel(), Y.ravel()]).T).reshape(X.shape)
has_data = (v_field > 0) & mask_tronco
v_vals = v_field[has_data]

if len(v_vals) > 0:
    v_max, v_min = np.nanmax(v_vals), np.nanmin(v_vals)
    v_threshold = (v_min + (v_max - v_min) * (threshold_pct / 100.0)) if any(m in metodo for m in ["2018", "EBSI", "SIRT", "RBF"]) else (v_max * (threshold_pct / 100.0))
else: v_max, v_threshold = 1.0, 0.5

diag_field = np.full_like(v_field, np.nan)
diag_field[has_data & (v_field >= v_threshold)] = 1 # Sadio
diag_field[has_data & (v_field < v_threshold)] = 0  # Dano

# --- INTERFACE VISUAL ---
st.title(f"🌳 Tomografia: {selected_tree['especie']}")
c_map, c_hist = st.columns([1, 1])

ext_cm = [x_min_real * 100, x_max_real * 100, y_min_real * 100, y_max_real * 100]

with c_map:
    st.subheader("Visualização do Fuste (cm)")
    fig_ui, ax_ui = plt.subplots(figsize=(6, 6))
    ax_ui.imshow(diag_field, extent=ext_cm, cmap=plt.matplotlib.colors.ListedColormap(['red', 'yellow']), origin='lower')
    ax_ui.plot(np.append(poly[:,0], poly[0,0]) * 100, np.append(poly[:,1], poly[0,1]) * 100, color='black', linewidth=2)
    ax_ui.scatter(coords[:,0] * 100, coords[:,1] * 100, color='white', edgecolor='black', s=150, zorder=5)
    for i, (x, y) in enumerate(coords):
        ax_ui.text(x * 100, y * 100, str(i+1), color='black', fontsize=8, ha='center', va='center', fontweight='bold', zorder=6)
    
    margin_cm = 2
    ax_ui.set_xlim(ext_cm[0] - margin_cm, ext_cm[1] + margin_cm)
    ax_ui.set_ylim(ext_cm[2] - margin_cm, ext_cm[3] + margin_cm)
    ax_ui.set_aspect('equal', adjustable='box')
    st.pyplot(fig_ui)

with c_hist:
    st.subheader("Análise de Velocidades")
    if len(v_vals) > 0:
        fig_h, ax_h = plt.subplots(figsize=(6, 5))
        ax_h.hist(v_vals, bins=35, density=True, color='gray', alpha=0.5, edgecolor='white')
        ax_h.axvline(v_threshold, color='red', linestyle='--', linewidth=2, label=f'Corte: {v_threshold:.0f} m/s')
        ax_h.legend(); ax_h.grid(axis='y', alpha=0.2)
        st.pyplot(fig_h)

# --- MÉTRICAS ---
p_amostrados = np.count_nonzero(~np.isnan(diag_field))
p_criticos = np.count_nonzero(diag_field == 0)
dano_perc = (p_criticos / p_amostrados * 100) if p_amostrados > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("V-Máxima", f"{v_max:.0f} m/s")
m2.metric("Threshold", f"{v_threshold:.0f} m/s")
m3.metric("Estimativa de Dano", f"{dano_perc:.1f}%")

# --- EXPORTAÇÃO (KIT DE VALIDAÇÃO) ---
st.sidebar.divider()
st.sidebar.subheader("📦 Pacote de Validação")

if st.sidebar.button("🎁 Exportar Kit ZIP (Sem Margens)"):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Fator de escala apenas para renderização do Matplotlib
        scaling = 0.05
        fig_size = (res_x * scaling, res_y * scaling)
        
        # Limites exatos do tronco para remover margens
        x_min_cm, x_max_cm = x_min_real * 100, x_max_real * 100
        y_min_cm, y_max_cm = y_min_real * 100, y_max_real * 100

        # Função auxiliar para manter a consistência
        def save_to_zip(name, data, cmap, bg='white', transparent=False):
            fig = plt.figure(figsize=fig_size)
            ax = fig.add_axes([0, 0, 1, 1])
            if not transparent: ax.set_facecolor(bg)
            ax.imshow(data, extent=ext_cm, cmap=cmap, origin='lower', interpolation='nearest')
            ax.set_xlim(x_min_cm, x_max_cm)
            ax.set_ylim(y_min_cm, y_max_cm)
            ax.axis('off')
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=transparent, facecolor=bg if not transparent else None)
            zf.writestr(name, buf.getvalue())
            plt.close(fig)

        # 1. COLORIDO
        save_to_zip(f"1_COLORIDO_{selected_tree['id_arvore']}.png", diag_field, plt.matplotlib.colors.ListedColormap(['red', 'yellow']))

        # 2. P&B (Dano = Preto, Sadio = Branco)
        save_to_zip(f"2_BINARIZADO_PB_{selected_tree['id_arvore']}.png", diag_field, plt.matplotlib.colors.ListedColormap(['black', 'white']))

        # 3. HULL MASK (Branco no fundo Preto)
        hull_data = np.where(~np.isnan(diag_field), 1, np.nan)
        save_to_zip(f"3_HULL_MASK_{selected_tree['id_arvore']}.png", hull_data, plt.matplotlib.colors.ListedColormap(['white']), bg='black')

        # 4. GABARITO RASTERIZADO (Transparente + 10% Opacidade)
        fig4 = plt.figure(figsize=fig_size)
        ax4 = fig4.add_axes([0, 0, 1, 1])
        inner = ~np.isnan(diag_field)
        border = binary_dilation(inner) ^ inner
        ax4.imshow(np.where(inner, 0.1, np.nan), extent=ext_cm, cmap=plt.matplotlib.colors.ListedColormap([(1,1,1,0.1)]), origin='lower')
        ax4.imshow(np.where(border, 1, np.nan), extent=ext_cm, cmap=plt.matplotlib.colors.ListedColormap([(1,1,1,1.0)]), origin='lower')
        ax4.set_xlim(x_min_cm, x_max_cm); ax4.set_ylim(y_min_cm, y_max_cm); ax4.axis('off')
        buf4 = io.BytesIO()
        fig4.savefig(buf4, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        zf.writestr(f"4_GABARITO_{selected_tree['id_arvore']}.png", buf4.getvalue())
        plt.close(fig4)

    st.sidebar.download_button("📥 Baixar Kit ZIP", zip_buffer.getvalue(), f"KIT_{selected_tree['id_arvore']}.zip", "application/zip")