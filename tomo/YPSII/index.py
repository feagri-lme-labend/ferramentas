import streamlit as st
import json
import numpy as np
from matplotlib.path import Path
import io
import matplotlib.pyplot as plt
from datetime import datetime
import zipfile
import unicodedata
import os

# --- CONFIGURAÇÃO E CACHE ---
st.set_page_config(page_title="YPS II", layout="wide", page_icon="https://static.vecteezy.com/system/resources/thumbnails/068/754/722/small/flowing-red-and-yellow-waves-create-a-warm-vibrant-abstract-background-free-vector.jpg")

from inter import (
    du_interpolation_simple, du_interpolation_compensated, 
    linear_back_projection, art_reconstruction, 
    sirt_reconstruction, rbf_interpolation,
    ebsi_interpolation, du_2018_segmented_rays
)

# ---------------------------------------------------------
# CARREGAMENTO AUTOMÁTICO DO JSON
# ---------------------------------------------------------

@st.cache_data
def load_local_json():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_uploaded_json(file_bytes):
    return json.loads(file_bytes.decode("utf-8"))

def load_data():

    # EXECUÇÃO LOCAL
    if os.path.exists("data.json"):
        st.sidebar.success("📂 Usando data.json local")
        return load_local_json()

    # STREAMLIT CLOUD
    st.sidebar.info("☁️ Envie o arquivo data.json")

    uploaded_file = st.sidebar.file_uploader(
        "Upload do JSON",
        type="json"
    )

    if uploaded_file is not None:
        return load_uploaded_json(uploaded_file.read())

    st.stop()


data = load_data()

# --- SIDEBAR ---
st.sidebar.title("YPS II")
st.sidebar.header("📂 Data selection")

# -------------------------
# FILTRO DE ESPÉCIE
# -------------------------

species = sorted({t["especie"] for t in data["trees"]})

selected_species = st.sidebar.selectbox(
    "Specie",
    options=species
)

trees_filtered = [
    t for t in data["trees"]
    if t["especie"] == selected_species
]

tree_options = {
    f"{t['especie']} — Árvore {t['id_arvore']}": t
    for t in trees_filtered
}

selected_tree = tree_options[
    st.sidebar.selectbox(
        "Tree",
        options=list(tree_options.keys())
    )
]

# -------------------------
# COLETAR TODAS AS SEÇÕES DA ÁRVORE
# -------------------------

sections_tree = []

for scan in data["scans"]:
    if scan["id_arvore"] == selected_tree["id_arvore"]:
        sections_tree.extend(scan["sections"])

# -------------------------
# FILTRO DE DATA DE AQUISIÇÃO
# -------------------------

dates = sorted({
    s["acquisition_time"].split("T")[0]
    for s in sections_tree
})

selected_date = st.sidebar.selectbox(
    "Acquisition date",
    options=dates
)

sections_date = [
    s for s in sections_tree
    if s["acquisition_time"].startswith(selected_date)
]

# -------------------------
# FILTRO DE ALTURA
# -------------------------

sections_sorted = sorted(
    sections_date,
    key=lambda x: x["height_cm"]
)

sec_opts = {
    f"{s['height_cm']} cm": s
    for s in sections_sorted
}

section = sec_opts[
    st.sidebar.selectbox(
        "Cross-sectional height",
        options=list(sec_opts.keys())
    )
]

st.sidebar.header("⚙️ Model settings")
threshold_pct = st.sidebar.select_slider("Damage sensitivity (%)", options=list(range(30, 81, 5)), value=45)

nomes_modelos = [
    "Du 2015", 
    "Du 2015 (Compensado)", 
    "EBSI (Base)", "Du 2018",
    "LBP (Linear)",
    "ART (Iterativo)",
    "SIRT (Simultâneo)",
    "RBF (Suave)"
]

metodo = st.sidebar.selectbox("Model", options=nomes_modelos, index=3)

# --- RECUPERANDO OS SLIDERS ESPECÍFICOS ---
ecc, comp_val, ray_tol, art_iter, art_relax = 1.05, 2.5, 0.02, 15, 0.1

if any(m in metodo for m in ["Du", "EBSI"]):
    ecc = st.sidebar.slider("Eccentricity of the ellipse (e)", 1.01, 1.30, 1.05)
    if "Compensado" in metodo:
        comp_val = st.sidebar.slider("Compensation factor", 1.0, 5.0, 2.5)

elif metodo in ["ART (Iterativo)", "SIRT (Simultâneo)", "LBP (Linear)"]:
    ray_tol = st.sidebar.slider("Radius width (m)", 0.005, 0.05, 0.02, step=0.005)
    if metodo != "LBP (Linear)":
        art_iter = st.sidebar.slider("Iterations", 1, 50, 15)
        art_relax = st.sidebar.slider("Relaxation factor", 0.01, 0.5, 0.1)

# --- PROCESSAMENTO ---
nodes = section["contour_nodes"]
node_map = {n["id"]: (n["x"]/100.0, n["y"]/100.0) for n in nodes}
coords = np.array([node_map[s["contour_node_id"]] for s in section["transducers"]])
poly = np.array([(n["x"]/100.0, n["y"]/100.0) for n in nodes])

T = np.zeros((len(coords), len(coords)))
for p in section["propagation_paths"]:
    i, j = p["i"]-1, p["j"]-1
    T[i, j] = T[j, i] = p["time"] / 1e6

# -----------------------------
# DOMÍNIO PADRONIZADO (JSON)
# -----------------------------

domain = section["domain"]

origin_x = domain["grid_origin_cm"]["x"] / 100.0
origin_y = domain["grid_origin_cm"]["y"] / 100.0

width = domain["size"]["width_cm"] / 100.0
height = domain["size"]["height_cm"] / 100.0

nx = domain["grid"]["nx"]
ny = domain["grid"]["ny"]

x_min_real = origin_x
x_max_real = origin_x + width

y_min_real = origin_y
y_max_real = origin_y + height

dx = (x_max_real - x_min_real) / nx
dy = (y_max_real - y_min_real) / ny

grid_x = np.linspace(x_min_real + dx/2, x_max_real - dx/2, nx)
grid_y = np.linspace(y_min_real + dy/2, y_max_real - dy/2, ny)

# Dicionário de modelos injetando as variáveis dos sliders
modelos = {
    "Du 2015": lambda: du_interpolation_simple(coords, T, grid_x, grid_y, ecc),
    "Du 2015 (Compensado)": lambda: du_interpolation_compensated(coords, T, grid_x, grid_y, ecc, comp_val),
    "EBSI (Base)": lambda: ebsi_interpolation(coords, T, grid_x, grid_y, ecc),
    "Du 2018": lambda: du_2018_segmented_rays(coords, T, grid_x, grid_y, ecc),
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
st.markdown(f"### 🌳 {selected_tree['especie']}")
c_map, c_hist = st.columns([1, 1])

ext_cm = [
    (x_min_real - dx/2) * 100,
    (x_max_real + dx/2) * 100,
    (y_min_real - dy/2) * 100,
    (y_max_real + dy/2) * 100
]

with c_map:
    st.markdown("##### Cross-sectional visualization (cm)")
    fig_ui, ax_ui = plt.subplots(figsize=(6, 6))
    ax_ui.imshow(diag_field, extent=ext_cm, cmap=plt.matplotlib.colors.ListedColormap(['red', 'yellow']), origin='lower')
    ax_ui.plot(np.append(poly[:,0], poly[0,0]) * 100, np.append(poly[:,1], poly[0,1]) * 100, color='black', linewidth=2)
    
    if len(coords) != 0:
        ax_ui.scatter(coords[:,0] * 100, coords[:,1] * 100, color='white', edgecolor='black', s=400, zorder=5)
    else:
        st.error("Transdutores não posicionados.")
        st.stop()
    
    for i, (x, y) in enumerate(coords):
        ax_ui.text(x * 100, y * 100, str(i+1), color='black', fontsize=11, ha='center', va='center', fontweight='bold', zorder=6)
    
    margin_cm = 2
    ax_ui.set_xlim(ext_cm[0] - margin_cm, ext_cm[1] + margin_cm)
    ax_ui.set_ylim(ext_cm[2] - margin_cm, ext_cm[3] + margin_cm)
    ax_ui.set_aspect('equal', adjustable='box')
    st.pyplot(fig_ui)

with c_hist:
    st.markdown("#####  Speed ​​Analysis")
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
m1.metric("V-max", f"{v_max:.0f} m/s")
m2.metric("Threshold", f"{v_threshold:.0f} m/s")
m3.metric("Damage estimation", f"{dano_perc:.1f}%")

# --- NOME SEMÂNTICO DO ZIP ---
species = selected_tree["especie"].replace(" ", "_")
tree_id = f"T{selected_tree['id_arvore']:02d}"

date = datetime.fromisoformat(section["acquisition_time"]).strftime("%Y%m%d")
height = f"H{section['height_cm']}"

# padronizar nome do modelo
model = unicodedata.normalize("NFKD", metodo)\
    .encode("ascii", "ignore")\
    .decode("ascii")\
    .lower()\
    .replace(" ", "_")\
    .replace("(", "")\
    .replace(")", "")

# grid (opcional mas recomendado)
grid = f"G{nx}"

zip_name = f"YPSII_{species}_{tree_id}_{date}_{height}_{model}_{grid}.zip"

# --- EXPORTAÇÃO (KIT DE VALIDAÇÃO) ---
st.sidebar.divider()
st.sidebar.subheader("📦 Export")

if st.sidebar.button("🎁 Export KIT", help="PNG RY, PNG BIN, PNG HM"):

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zf:

        # Garantir que a imagem final tenha exatamente nx × ny pixels
        dpi = 100
        fig_size = (nx / dpi, ny / dpi)

        # limites físicos em cm
        x_min_cm, x_max_cm = x_min_real * 100, x_max_real * 100
        y_min_cm, y_max_cm = y_min_real * 100, y_max_real * 100

        ext_cm = [x_min_cm, x_max_cm, y_min_cm, y_max_cm]

        def save_to_zip(name, data, cmap, bg='white', transparent=False):

            fig = plt.figure(figsize=fig_size, dpi=dpi)
            ax = fig.add_axes([0, 0, 1, 1])

            if not transparent:
                ax.set_facecolor(bg)

            ax.imshow(
                data,
                extent=ext_cm,
                cmap=cmap,
                origin='lower',
                interpolation='nearest'
            )

            ax.set_xlim(x_min_cm, x_max_cm)
            ax.set_ylim(y_min_cm, y_max_cm)
            ax.axis('off')

            buf = io.BytesIO()

            fig.savefig(
                buf,
                format='png',
                dpi=dpi,
                pad_inches=0,
                transparent=transparent,
                facecolor=bg if not transparent else None
            )

            zf.writestr(name, buf.getvalue())
            plt.close(fig)

        # --- 1. MAPA COLORIDO ---
        save_to_zip(
            f"1_COLORFUL_{species}_{tree_id}_{date}_{height}_{model}_{grid}.png",
            diag_field,
            plt.matplotlib.colors.ListedColormap(['red', 'yellow'])
        )

        # --- 2. BINARIZADO P&B ---
        save_to_zip(
            f"2_BW_{species}_{tree_id}_{date}_{height}_{model}_{grid}.png",
            diag_field,
            plt.matplotlib.colors.ListedColormap(['black', 'white'])
        )

        # --- 3. HULL MASK ---
        hull_data = np.where(~np.isnan(diag_field), 1, np.nan)

        save_to_zip(
            f"3_HM_{species}_{tree_id}_{date}_{height}_{model}_{grid}.png",
            hull_data,
            plt.matplotlib.colors.ListedColormap(['white']),
            bg='black'
        )

    st.sidebar.download_button(
        "📥 Download ZIP",
        zip_buffer.getvalue(),
        zip_name,
        "application/zip"
    )