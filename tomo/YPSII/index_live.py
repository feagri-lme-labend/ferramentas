import streamlit as st
import json
import numpy as np
from matplotlib.path import Path
import matplotlib.pyplot as plt
import io
import zipfile
from datetime import datetime
import pandas as pd
import unicodedata
import re
import os

# --- CONFIG ---
st.set_page_config(
    page_title="YPS II - Live Tree",
    layout="wide",
    page_icon="https://static.vecteezy.com/system/resources/thumbnails/068/754/722/small/flowing-red-and-yellow-waves-create-a-warm-vibrant-abstract-background-free-vector.jpg"
)

# --- INTERPOLADORES ---
from inter import (
    du_interpolation_simple,
    du_interpolation_compensated,
    linear_back_projection,
    art_reconstruction,
    sirt_reconstruction,
    rbf_interpolation,
    ebsi_interpolation,
    du_2018_segmented_rays,
    kriging_interpolation,
    ray_kriging_interpolation,
    beam_divergence_interpolation
)

def slugify_filename(text):
    # 1. Normalize unicode characters to decompose combined characters (like 'á' to 'a' + '´')
    normalized = unicodedata.normalize('NFKD', text)
    
    # 2. Encode to ASCII and ignore non-ASCII characters (removes the accents)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # 3. Replace any character that is NOT a letter, number, dot, or hyphen with an underscore
    filename = re.sub(r'[^a-zA-Z0-9.-]', '_', ascii_text)
    
    # 4. Remove duplicate underscores and strip them from the ends
    return re.sub(r'_+', '_', filename).strip('_')

# ---------------------------------------------------------
# FUNÇÃO PARA GERAR ELIPSE
# ---------------------------------------------------------

def generate_ellipse_transducers(
        n_transducers,
        d_major_cm,
        d_minor_cm,
        start_angle_deg,
        clockwise
):

    a = d_major_cm / 200
    b = d_minor_cm / 200

    angles = np.linspace(0, 2*np.pi, n_transducers, endpoint=False)

    if clockwise:
        angles = -angles

    angles += np.deg2rad(start_angle_deg)

    coords = []

    for theta in angles:

        x = a * np.cos(theta)
        y = b * np.sin(theta)

        coords.append((x, y))

    coords = np.array(coords)

    t = np.linspace(0, 2*np.pi, 200)

    poly = np.column_stack([
        a * np.cos(t),
        b * np.sin(t)
    ])

    return coords, poly


# ---------------------------------------------------------
# CARREGAMENTO JSON
# ---------------------------------------------------------

@st.cache_data
def load_local_json():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_uploaded_json(file_bytes):
    return json.loads(file_bytes.decode("utf-8"))


def load_data():

    if os.path.exists("data.json"):
        st.sidebar.success("📂 Using local data.json")
        return load_local_json()

    st.sidebar.info("Upload JSON")

    uploaded = st.sidebar.file_uploader("Upload JSON", type="json")

    if uploaded:
        return load_uploaded_json(uploaded.read())

    st.stop()


data = load_data()

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("YPS II - Live Tree")
st.sidebar.header("📂 Data selection")

species = sorted({t["especie"] for t in data["trees"]})

selected_species = st.sidebar.selectbox(
    f"Specie ({len(species)})",
    options=species
)

trees_filtered = [
    t for t in data["trees"]
    if t["especie"] == selected_species
]

tree_options = {
    f"{t['especie']} — Tree {t['id_arvore']}": t
    for t in trees_filtered
}

selected_tree = tree_options[
    st.sidebar.selectbox(
        f"Tree ({len(trees_filtered)})",
        options=list(tree_options.keys())
    )
]

# ---------------------------------------------------------
# SEÇÕES
# ---------------------------------------------------------

sections_tree = []

for scan in data["scans"]:
    if scan["id_arvore"] == selected_tree["id_arvore"]:
        sections_tree.extend(scan["sections"])

dates = sorted({
    s["acquisition_time"].split("T")[0]
    for s in sections_tree
})

selected_date = st.sidebar.selectbox(
    f"Acquisition date ({len(dates)})",
    options=dates
)

sections_date = [
    s for s in sections_tree
    if s["acquisition_time"].startswith(selected_date)
]

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
        f"Cross-sectional height ({len(sec_opts)})",
        options=list(sec_opts.keys())
    )
]

# ---------------------------------------------------------
# GEOMETRIA DA ÁRVORE VIVA
# ---------------------------------------------------------

st.sidebar.header("🌳 Tree geometry")

d_major = st.sidebar.number_input(
    "Major diameter (cm)",
    10,
    300,
    80
)

d_minor = st.sidebar.number_input(
    "Minor diameter (cm)",
    10,
    300,
    70
)

start_angle = st.sidebar.selectbox(
    "Start position of transducer 1",
    [0, 90, 180, 270]
)

direction = st.sidebar.radio(
    "Numbering direction",
    ["Counter-clockwise", "Clockwise"]
)

clockwise = direction == "Clockwise"

# ---------------------------------------------------------
# MODELOS
# ---------------------------------------------------------

st.sidebar.header("⚙️ Model settings")

# NOVO CONTROLE DE CLASSES
n_classes = st.sidebar.number_input(
    "Velocity classes",
    min_value=2,
    max_value=12,
    value=6
)

# slider só faz sentido com 2 classes
if int(n_classes) == 2:

    threshold_pct = st.sidebar.select_slider(
        "Damage sensitivity (%)",
        options=list(range(20, 81)),
        value=45
    )

else:

    st.sidebar.info("Multiclass mode: threshold not used")
    threshold_pct = 45

nomes_modelos = [
    "Du 2015",
    "Du 2015 (Compensado)",
    "EBSI (Base)",
    "Du 2018",
    "LBP (Linear)",
    "ART (Iterativo)",
    "SIRT (Simultâneo)",
    "RBF (Suave)",
    "Kriging",
    "Kriging (Ray-based)",
    "Beam Divergence"
]

metodo = st.sidebar.selectbox(
    "Model",
    options=nomes_modelos,
    index=3
)

ecc, comp_val, ray_tol, art_iter, art_relax = 1.05, 2.5, 0.02, 15, 0.1
beam_angle = np.deg2rad(30)
radial_decay = 2.0

# sliders específicos
if "Du" in metodo or "EBSI" in metodo:

    ecc = st.sidebar.slider("Eccentricity of ellipse",1.01,1.3,1.05)

    if "Compensado" in metodo:
        comp_val = st.sidebar.slider("Compensation factor",1.0,5.0,2.5)

elif metodo in ["ART (Iterativo)", "SIRT (Simultâneo)", "LBP (Linear)"]:

    ray_tol = st.sidebar.slider("Ray width (m)",0.005,0.05,0.02)

    if metodo != "LBP (Linear)":
        art_iter = st.sidebar.slider("Iterations",1,50,15)
        art_relax = st.sidebar.slider("Relaxation",0.01,0.5,0.1)

elif "Kriging" in metodo:

    var_model = st.sidebar.selectbox(
        "Variogram",
        ["linear","gaussian","spherical","exponential"]
    )

    if metodo == "Kriging (Ray-based)":

        n_seg = st.sidebar.slider("Points per ray",5,10,5)

        ani_ratio = st.sidebar.slider("Anisotropy",1.0,10.0,3.0)

elif metodo == "Beam Divergence":

    beam_angle = np.deg2rad(
        st.sidebar.slider("Beam angle",5,60,30)
    )

    radial_decay = st.sidebar.slider(
        "Radial attenuation",0.5,5.0,2.0
    )

# ---------------------------------------------------------
# GEOMETRIA ELÍPTICA
# ---------------------------------------------------------

n_transducers = len(section["transducers"])

coords, poly = generate_ellipse_transducers(
    n_transducers,
    d_major,
    d_minor,
    start_angle,
    clockwise
)

# ---------------------------------------------------------
# MATRIZ DE TEMPOS
# ---------------------------------------------------------

T = np.zeros((n_transducers, n_transducers))

for p in section["propagation_paths"]:

    i = p["i"] - 1
    j = p["j"] - 1

    T[i, j] = T[j, i] = p["time"] / 1e6

# ---------------------------------------------------------
# DOMÍNIO
# ---------------------------------------------------------

a = d_major / 200
b = d_minor / 200

margin_cm = st.sidebar.slider("Domain margin (cm)",1,20,5)

margin = margin_cm / 100

x_min = -a - margin
x_max = a + margin

y_min = -b - margin
y_max = b + margin

nx = 200
ny = 200

dx = (x_max - x_min) / nx
dy = (y_max - y_min) / ny

grid_x = np.linspace(x_min + dx/2, x_max - dx/2, nx)
grid_y = np.linspace(y_min + dy/2, y_max - dy/2, ny)

# ---------------------------------------------------------
# EXECUÇÃO DO MODELO
# ---------------------------------------------------------

modelos = {

    "Du 2015": lambda: du_interpolation_simple(coords,T,grid_x,grid_y,ecc),

    "Du 2015 (Compensado)": lambda:
        du_interpolation_compensated(coords,T,grid_x,grid_y,ecc,comp_val),

    "EBSI (Base)": lambda:
        ebsi_interpolation(coords,T,grid_x,grid_y,ecc),

    "Du 2018": lambda:
        du_2018_segmented_rays(coords,T,grid_x,grid_y,ecc),

    "LBP (Linear)": lambda:
        linear_back_projection(coords,T,grid_x,grid_y,ray_tol),

    "ART (Iterativo)": lambda:
        art_reconstruction(coords,T,grid_x,grid_y,art_iter,art_relax,ray_tol),

    "SIRT (Simultâneo)": lambda:
        sirt_reconstruction(coords,T,grid_x,grid_y,art_iter,art_relax,ray_tol),

    "RBF (Suave)": lambda:
        rbf_interpolation(coords,T,grid_x,grid_y),

    "Kriging": lambda:
        kriging_interpolation(coords,T,grid_x,grid_y,variogram=var_model),

    "Kriging (Ray-based)": lambda:
        ray_kriging_interpolation(
            coords,T,grid_x,grid_y,
            n_segments=n_seg,
            variogram=var_model,
            anisotropy_ratio=ani_ratio
        ),

    "Beam Divergence": lambda:
        beam_divergence_interpolation(
            coords,T,grid_x,grid_y,
            beam_angle,
            radial_decay
        )
}

X, Y, v_field = modelos[metodo]()

# ---------------------------------------------------------
# MÁSCARA
# ---------------------------------------------------------

mask_tronco = Path(poly).contains_points(
    np.vstack([X.ravel(),Y.ravel()]).T
).reshape(X.shape)

has_data = (v_field > 0) & mask_tronco

v_vals = v_field[has_data]

if len(v_vals):

    v_max = np.nanmax(v_vals)
    v_min = np.nanmin(v_vals)

    v_threshold = v_min + (v_max - v_min) * threshold_pct / 100

else:

    v_max = 1
    v_threshold = 0.5

# ---------------------------------------------------------
# DIAGNÓSTICO (BINÁRIO)
# ---------------------------------------------------------

diag_field = np.full_like(v_field,np.nan)

diag_field[has_data & (v_field >= v_threshold)] = 1
diag_field[has_data & (v_field < v_threshold)] = 0

# ---------------------------------------------------------
# CAMPO MULTICLASSE PARA VISUALIZAÇÃO
# ---------------------------------------------------------

viz_field = np.full_like(v_field,np.nan)

if len(v_vals):

    if int(n_classes) == 2:

        viz_field[has_data & (v_field >= v_threshold)] = 1
        viz_field[has_data & (v_field < v_threshold)] = 0

        bins = [v_min, v_threshold, v_max]

    else:

        bins = np.linspace(v_min,v_max,int(n_classes)+1)

        for i in range(int(n_classes)):

            if i == int(n_classes)-1:
                mask = has_data & (v_field >= bins[i]) & (v_field <= bins[i+1])
            else:
                mask = has_data & (v_field >= bins[i]) & (v_field < bins[i+1])

            viz_field[mask] = i


col1, col2, = st.columns(2)
# --- INTERFACE VISUAL ---
col1.info(f"""
    #### 🌳 Tree infos
    ###### Specie: `{selected_tree['especie']}`
    ###### Description: `{selected_tree['description'] if selected_tree['description'] not in ["", None] else "Sem descrição"}`
    ###### Condition: `{selected_tree['condition'] if selected_tree['condition'] not in ["", None] else "Não especificada"}`
""")

col2.info(f"""
    ###### Latitude: `{selected_tree['location']['latitude'] if selected_tree['location']['latitude'] not in ["", None] else "Não especificada"}`
    ###### Longitude: `{selected_tree['location']['longitude'] if selected_tree['location']['longitude'] not in ["", None] else "Não especificada"}`
    ###### Altitude (m): `{selected_tree['location']['altitude_m'] if selected_tree['location']['altitude_m'] not in ["", None] else "Não especificada"}`
""")

# ---------------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------------

p_total = np.count_nonzero(~np.isnan(diag_field))
p_dano = np.count_nonzero(diag_field == 0)

dano = (p_dano / p_total * 100) if p_total else 0

m1,m2,m3 = st.columns(3)

m1.metric("V-max",f"{v_max:.0f} m/s")
m2.metric("Threshold",f"{v_threshold:.0f} m/s")
m3.metric("Damage",f"{dano:.1f}%")

# ---------------------------------------------------------
# VISUALIZAÇÃO
# ---------------------------------------------------------

fig,ax = plt.subplots(figsize=(6,6))

ext = [
    (x_min - dx/2)*100,
    (x_max + dx/2)*100,
    (y_min - dy/2)*100,
    (y_max + dy/2)*100
]

# colormap

if int(n_classes) == 2:

    cmap = plt.matplotlib.colors.ListedColormap([
        "red",
        "yellow"
    ])

else:

    base_cmap = plt.colormaps["RdYlGn"]

    cmap = plt.matplotlib.colors.ListedColormap(
        base_cmap(np.linspace(0,1,int(n_classes)))
    )

im = ax.imshow(
    viz_field,
    extent=ext,
    cmap=cmap,
    origin='lower',
    vmin=0,
    vmax=int(n_classes)-1,
    zorder=1
)

# contorno
ax.plot(
    np.append(poly[:,0],poly[0,0])*100,
    np.append(poly[:,1],poly[0,1])*100,
    color='black',
    linewidth=2,
    zorder=2
)

# transdutores
ax.scatter(
    coords[:,0]*100,
    coords[:,1]*100,
    s=400,
    color='white',
    edgecolor='black',
    zorder=3
)

# labels
for i,(x,y) in enumerate(coords):

    ax.text(
        x*100,
        y*100,
        str(i+1),
        color='black',
        fontsize=11,
        ha='center',
        va='center',
        fontweight='bold',
        zorder=4
    )

ax.set_aspect('equal')

cbar = plt.colorbar(im, ax=ax)

# posições das classes
ticks = np.arange(int(n_classes))

# converter classes → velocidades
if int(n_classes) == 2:

    tick_labels = [
        f"< {v_threshold:.0f}",
        f"≥ {v_threshold:.0f}"
    ]

else:

    tick_labels = [f"{bins[i]:.0f}" for i in range(int(n_classes))]

cbar.set_ticks(ticks)
cbar.set_ticklabels(tick_labels)

cbar.set_label("Velocity (m/s)")

col1,col2 = st.columns(2)

col1.pyplot(fig)

# ---------------------------------------------------------
# EXPORTAÇÃO
# ---------------------------------------------------------

st.sidebar.markdown("### 📦 Export")
if st.sidebar.button("🎁​ Export ZIP"):

    # -------- JSON DA ANÁLISE --------
    analysis_data = {

        "analysis_info": {
            "timestamp": datetime.now().isoformat(),
            "model": metodo
        },

        "tree": {
            "id": selected_tree["id_arvore"],
            "specie": selected_tree["especie"],
            "description": selected_tree["description"],
            "condition": selected_tree["condition"],
            "location": selected_tree["location"]
        },

        "section": {
            "height_cm": section["height_cm"],
            "acquisition_time": section["acquisition_time"]
        },

        "geometry": {
            "major_diameter_cm": d_major,
            "minor_diameter_cm": d_minor,
            "start_angle_deg": start_angle,
            "clockwise": clockwise,
            "n_transducers": n_transducers,
            "coords": coords.tolist()
        },

        "domain": {
            "margin_cm": margin_cm,
            "nx": nx,
            "ny": ny
        },

        "model_parameters": {
            "eccentricity": ecc,
            "compensation": comp_val,
            "ray_width": ray_tol,
            "iterations": art_iter,
            "relaxation": art_relax
        },

        "velocity_analysis": {
            "v_min": float(v_min),
            "v_max": float(v_max),
            "threshold_velocity": float(v_threshold),
            "damage_percent": float(dano),
            "n_classes": int(n_classes)
        },

        "velocity_field": {
            "grid_x": grid_x.tolist(),
            "grid_y": grid_y.tolist(),
            "velocity_matrix": v_field.tolist()
        }

    }

    json_bytes = json.dumps(analysis_data, indent=2).encode("utf-8")

    # -------- CSV VELOCIDADE --------
    velocity_export = np.where(mask_tronco, v_field, 0)

    df_velocity = pd.DataFrame(velocity_export)
    csv_bytes = df_velocity.to_csv(index=False).encode("utf-8")

    # -------- IMAGEM --------
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, dpi=300, bbox_inches="tight")
    img_buffer.seek(0)

    # -------- ZIP --------
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        zf.writestr("analysis.json", json_bytes)

        zf.writestr("velocity_field.csv", csv_bytes)

        zf.writestr("tomography.png", img_buffer.getvalue())

    zip_buffer.seek(0)

    # -------- DOWNLOAD --------
    st.sidebar.download_button(
        "⬇️ Download ZIP",
        data=zip_buffer,
        file_name=f"YPSII_LT_{slugify_filename(metodo)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip"
    )