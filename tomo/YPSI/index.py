import streamlit as st
import numpy as np
from PIL import Image
import cv2
import json
import zipfile
import io
from datetime import datetime
import hashlib
import base64
from streamlit_drawable_canvas import st_canvas
import pandas as pd

st.set_page_config(layout="wide", page_title="YPS I", page_icon="https://static.vecteezy.com/system/resources/thumbnails/068/754/722/small/flowing-red-and-yellow-waves-create-a-warm-vibrant-abstract-background-free-vector.jpg")

st.markdown("### 🔊 Tomographic Mesh Definitions")

uploaded_file = st.file_uploader("Upload an image", type=["png","jpg","jpeg"])

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)

def polygon_centroid(points):

    x = points[:,0]
    y = points[:,1]

    a = np.dot(x, np.roll(y,-1)) - np.dot(y, np.roll(x,-1))
    A = a / 2

    if abs(A) < 1e-9:
        return np.mean(x), np.mean(y)

    cx = np.sum((x + np.roll(x,-1)) * (x*np.roll(y,-1) - np.roll(x,-1)*y)) / (6*A)
    cy = np.sum((y + np.roll(y,-1)) * (x*np.roll(y,-1) - np.roll(x,-1)*y)) / (6*A)

    return cx, cy

def write_png_to_zip(zf, array, filename, experiment_state=None, key=None):

    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")

    data = buffer.getvalue()

    # escreve no zip
    zf.writestr(filename, data)

    # gera metadados
    meta = {
        "file": filename,
        "sha256": hashlib.sha256(data).hexdigest(),
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "base64": base64.b64encode(data).decode("utf-8")
    }

    # opcional: salva no experiment_state
    if experiment_state is not None and key is not None:

        if "images" not in experiment_state:
            experiment_state["images"] = {}

        experiment_state["images"][key] = meta

    return meta

def session_state_to_json():
    
    export = {}

    for k, v in st.session_state.items():

        if isinstance(v, (int, float, str, bool, type(None))):
            export[k] = v

        elif isinstance(v, (list, tuple)):
            export[k] = v

        elif isinstance(v, np.ndarray):
            export[k] = v.tolist()

        elif isinstance(v, dict):
            export[k] = v

        else:
            export[k] = str(type(v))

    return export


if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img_name = uploaded_file.name
    img_np = np.array(img)

    # garantir compatibilidade com OpenCV
    img_np = np.ascontiguousarray(img_np, dtype=np.uint8)

    # -------------------
    # RESET SE NOVA IMAGEM
    # -------------------

    file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()

    if st.session_state.get("current_image_hash") != file_hash:

        for k in list(st.session_state.keys()):
            if k.startswith(("x_", "y_", "sensor_", "id_sensor_", "time_")):
                del st.session_state[k]

        if "pontos" in st.session_state:
            del st.session_state["pontos"]

        if "resize_applied" in st.session_state:
            del st.session_state["resize_applied"]

        st.session_state.current_image_hash = file_hash

    # -------------------
    # REDUÇÃO AUTOMÁTICA (PERFORMANCE)
    # -------------------
    max_dim = 800

    h, w = img_np.shape[:2]

    scale_img = 1.0

    if max(h, w) > max_dim:
        scale_img = max_dim / max(h, w)

        new_w = int(w * scale_img)
        new_h = int(h * scale_img)

        img_np = cv2.resize(img_np, (new_w, new_h), interpolation=cv2.INTER_AREA)

        h, w = new_h, new_w

        st.warning(f"⚠️ Image resized to {w}x{h} for better performance")

    # escala salva (importante pra debug/futuro)
    st.session_state.scale_img = scale_img

    # -------------------
    # CONFIG
    # -------------------
    st.sidebar.title("YPS I")

    # --- CANVAS PARA DESENHO INICIAL ---
    st.markdown("#### 🖌️ Define the polygon")
    
    # Configuração do Canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#ff0000",
        background_image=Image.fromarray(img_np),
        update_streamlit=True,
        height=h,
        width=w,
        drawing_mode="polygon",
        key="canvas",
    )

    # --- LOGICA DE SINCRONIZAÇÃO SEM LOOP ---
    if canvas_result.json_data is not None:
        objs = canvas_result.json_data["objects"]
        if len(objs) > 0:
            path = objs[0].get("path", [])
            
            # 1. Extrair os pontos novos do desenho
            novos_pontos = []
            for p in path:
                if isinstance(p, list) and len(p) >= 3:
                    novos_pontos.append([int(p[1]), int(p[2])])
            
            # 2. Só fazemos algo se os pontos tiverem mudado de verdade
            if len(novos_pontos) > 0 and novos_pontos != st.session_state.get("pontos_comparacao"):
                
                # Atualiza o estado principal
                st.session_state.pontos = novos_pontos
                st.session_state.n_pontos = len(novos_pontos)
                
                # Atualiza o "checkpoint" para saber que já processamos isso
                st.session_state.pontos_comparacao = novos_pontos
                
                # 3. ATUALIZAÇÃO DIRETA DOS SLIDERS (Isso resolve o Ponto 1!)
                # Em vez de apagar as chaves, nós forçamos o valor novo para elas
                for i, (x, y) in enumerate(novos_pontos):
                    st.session_state[f"x_{i}"] = x
                    st.session_state[f"y_{i}"] = y
                
                # Não precisamos de st.rerun() aqui, o Streamlit detectará a mudança
                # no session_state e renderizará corretamente na próxima passagem.
            

    expander = st.sidebar.expander("Polygon")

    n_pontos = expander.slider("Number of points", 3, 30, 8, key="n_pontos")
    ponto_ativo = expander.slider("Point number", 1, n_pontos, 1)

    # -------------------
    # GARANTIR INICIALIZAÇÃO DOS PONTOS (FIX)
    # -------------------
    if "pontos" not in st.session_state:
        st.session_state.pontos = [[w//2, h//2] for _ in range(n_pontos)]

    # -------------------
    # RESET ESTADO (INTELIGENTE - NÃO PERDE COORDENADAS)
    # -------------------

    if "pontos" in st.session_state and scale_img != 1.0 and "resize_applied" not in st.session_state:

        novos_pontos = []

        for px, py in st.session_state.pontos:
            novo_x = int(px * scale_img)
            novo_y = int(py * scale_img)

            novos_pontos.append([novo_x, novo_y])

        st.session_state.pontos = novos_pontos
        st.session_state.resize_applied = True



    if "n_pontos_prev" not in st.session_state:
        st.session_state.n_pontos_prev = n_pontos

    if st.session_state.n_pontos_prev != n_pontos:

        pontos_antigos = st.session_state.pontos

        if n_pontos > len(pontos_antigos):

            cx = sum(p[0] for p in pontos_antigos) / len(pontos_antigos)
            cy = sum(p[1] for p in pontos_antigos) / len(pontos_antigos)

            novos = []

            for i in range(n_pontos - len(pontos_antigos)):
                novos.append([int(cx), int(cy)])

            st.session_state.pontos = pontos_antigos + novos

        else:
            st.session_state.pontos = pontos_antigos[:n_pontos]

        for k in list(st.session_state.keys()):
            if k.startswith("x_") or k.startswith("y_"):
                try:
                    idx = int(k.split("_")[1])
                    if idx >= n_pontos:
                        del st.session_state[k]
                except:
                    pass

        st.session_state.n_pontos_prev = n_pontos

    # -------------------
    # ESTILO
    # -------------------

    col1, col2 = st.sidebar.expander("Style").columns(2)

    espessura_linha = col1.slider("Line thickness", 1, 10, 2, key="espessura_linha")
    raio_ponto = col2.slider("Nodes size", 8, 25, 12, key="raio_ponto")

    font_scale = col1.slider("Font size", 0.3, 2.0, 0.5, 0.05, key="font_scale")
    
    font_thickness = col2.slider("Font weight", 1, 5, 1, key="font_thickness")

    cor_linha = hex_to_bgr(col1.color_picker("Line color", "#ff0000", key="cor_linha"))

    col1, col2 = st.sidebar.expander("Point settings").columns(2)

    zoom_size = col1.slider("Window size (px)", 50, 400, 150, key="zoom_size")
    zoom_scale = col2.slider("Zoom", 1, 5, 3, key="zoom_scale")

    # -------------------
    # EDITAR PONTO (CORRIGIDO)
    # -------------------
    idx = ponto_ativo - 1
    
    # Obtém os valores atuais da lista de pontos
    valor_x_atual = int(st.session_state.pontos[idx][0])
    valor_y_atual = int(st.session_state.pontos[idx][1])

    expander = st.sidebar.expander("Coordinate")
    
    # Ao passar o parâmetro 'value', garantimos que o slider sempre inicie 
    # com a coordenada correta do ponto selecionado, ignorando valores antigos.
    x = expander.slider(
        "X", 0, w-1, 
        value=valor_x_atual, 
        key=f"x_{idx}"
    )
    y = expander.slider(
        "Y", 0, h-1, 
        value=valor_y_atual, 
        key=f"y_{idx}"
    )

    # Atualiza a lista principal com o valor que o slider acabou de retornar
    st.session_state.pontos[idx] = [x, y]

    #st.session_state.pontos = [[999,613],[1062,447],[1017,340],[959,251],[845,165],[712,114],[601,88],[452,108],[288,191],[171,341],[121,456],[97,624],[97,624],[97,624]]

    pontos = np.array(st.session_state.pontos)
    pts = np.array([pontos], dtype=np.int32)

    # -------------------
    # CALIBRAÇÃO
    # -------------------
    expander = st.sidebar.expander("Calibration")

    p1_id = expander.selectbox("Reference node 1", list(range(1, len(pontos)+1)))
    p2_id = expander.selectbox("Reference node 2", list(range(1, len(pontos)+2)))

    dist_real = expander.number_input("Real distance (cm)", 0.1, 1000.0, 10.0)

    p1 = pontos[p1_id - 1]
    p2 = pontos[p2_id - 1]

    dist_pixels = np.linalg.norm(p1 - p2)

    escala = dist_real / dist_pixels if dist_pixels > 0 else 0

    expander.write(f"Scale: {escala:.4f} cm/pixel")

    expander = st.sidebar.expander("Grid")
    nx = ny = expander.selectbox("Grid resolution (px)", [128, 256], index=1, key="grid_resolution")

    # -------------------
    # CONVERTER PARA CM
    # -------------------
    centro = polygon_centroid(pontos)

    pontos_cm = []
    for (px, py) in pontos:
        x_cm = (px - centro[0]) * escala
        y_cm = -(py - centro[1]) * escala
        pontos_cm.append([x_cm, y_cm])

    # -------------------
    # SENSORES
    # -------------------
    expander = st.sidebar.expander("Transducers")

    transducers = []
    sensor_counter = 1

    for i in range(len(pontos)):

        if expander.checkbox(f"Node {i+1}", key=f"sensor_{i}"):

            transducers.append({
                "id": sensor_counter,
                "contour_node_id": i + 1
            })

            sensor_counter += 1

    # -------------------
    # MÁSCARA
    # -------------------
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, pts, 255)

    result = img_np.copy()
    result[mask == 0] = 0

    # -------------------
    # THRESHOLD
    # -------------------
    expander = st.sidebar.expander("Segmentation")

    blur_size = expander.slider("Blur (kernel)", 1, 31, 5, step=2, key="blur_size")
    blur_sigma = expander.slider("Sigma of blur", 0.0, 10.0, 1.0, key="blur_sigma")

    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), blur_sigma)

    threshold = expander.slider("Threshold", 0, 255, 120, key="threshold")

    _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)

    binary[result[:,:,0] == 0] = 0

    # -------------------
    # DESENHO
    # -------------------
    img_poly = img_np.copy()
    cv2.polylines(img_poly, pts, True, cor_linha, espessura_linha)

    # -------------------
    # DESENHAR CENTROIDE
    # -------------------

    cx, cy = int(centro[0]), int(centro[1])

    cv2.line(img_poly, (cx-20, cy), (cx+20, cy), (0,255,0), 2)
    cv2.line(img_poly, (cx, cy-20), (cx, cy+20), (0,255,0), 2)
    cv2.circle(img_poly, (cx, cy), 5, (255,0,0), -1)

    cv2.putText(
        img_poly,
        "C",
        (cx+10, cy-10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0,255,0),
        2,
        cv2.LINE_AA
    )
    # ----------------------------------------------

    for i, (px, py) in enumerate(pontos):

        px, py = int(px), int(py)

        is_sensor = None
        for s in transducers:
            if s["contour_node_id"] == i+1:
                is_sensor = s
                break

        if is_sensor is None:
            cv2.circle(img_poly, (px, py), raio_ponto, (255, 255, 255), -1)
            cv2.circle(img_poly, (px, py), raio_ponto, (0, 0, 0), 2)
        else:
            cv2.circle(img_poly, (px, py), raio_ponto + 5, (0, 255, 255), 2)
            cv2.circle(img_poly, (px, py), raio_ponto, (255, 255, 0), -1)

        if i == idx:
            cv2.circle(img_poly, (px, py), raio_ponto + 3, (0, 255, 0), 2)

        text = str(i+1)
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, font_scale, font_thickness)

        cv2.putText(
            img_poly,
            text,
            (px - tw//2, py + th//2),
            font,
            font_scale,
            (0, 0, 0),
            font_thickness,
            cv2.LINE_AA
        )

        if is_sensor is not None:
            sid = is_sensor["id"]
            cv2.putText(
                img_poly,
                f"S{sid}",
                (px + 10, py - 10),
                font,
                0.4,
                (0, 255, 255),
                1,
                cv2.LINE_AA
            )

    sensor_points = []
    for s in transducers:
        node_id = s["contour_node_id"] - 1
        px, py = pontos[node_id]
        sensor_points.append((int(px), int(py)))

    for i in range(len(sensor_points)):
        for j in range(i+1, len(sensor_points)):
            cv2.line(img_poly, sensor_points[i], sensor_points[j], (0, 0, 0), 1, cv2.LINE_AA)

    # -------------------
    # ZOOM
    # -------------------
    px, py = int(pontos[idx][0]), int(pontos[idx][1])

    half = zoom_size // 2

    x1 = max(px - half, 0)
    y1 = max(py - half, 0)
    x2 = min(px + half, w)
    y2 = min(py + half, h)

    if x2 <= x1:
        x2 = x1 + 1

    if y2 <= y1:
        y2 = y1 + 1

    zoom_crop = np.ascontiguousarray(img_np[y1:y2, x1:x2])

    if zoom_crop.size == 0:
        zoom_crop = np.zeros((50,50,3), dtype=np.uint8)

    cv2.circle(zoom_crop, (px - x1, py - y1), 5, (0, 0, 255), -1)

    zoom_img = cv2.resize(
        zoom_crop,
        (zoom_crop.shape[1]*zoom_scale, zoom_crop.shape[0]*zoom_scale),
        interpolation=cv2.INTER_NEAREST
    )

    # posição do ponto no zoom
    zx = (px - x1) * zoom_scale
    zy = (py - y1) * zoom_scale

    # cruz verde
    cv2.line(zoom_img, (0, zy), (zoom_img.shape[1], zy), (0,255,0), 3)
    cv2.line(zoom_img, (zx, 0), (zx, zoom_img.shape[0]), (0,255,0), 3)

    zoom_img_rgb = cv2.cvtColor(zoom_img, cv2.COLOR_BGR2RGB)
    img_poly_rgb = cv2.cvtColor(img_poly, cv2.COLOR_BGR2RGB)
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

    col1, col2 = st.columns([2, 1])
    col1.markdown("##### Polygon + Transducers + Mesh")
    col1.image(img_poly_rgb)
    col2.markdown(f"##### Zoom (Node {idx+1})")
    col2.image(zoom_img_rgb)
    
    col1, col2 = st.columns(2)
    col1.markdown("##### Cropped")
    col1.image(result_rgb)
    col2.markdown("##### Cross-Sectional Threshold")
    col2.image(binary, clamp=True)

    propagation_paths = []

    sensor_ids = sorted([s["id"] for s in transducers])

    if len(sensor_ids) >= 2:

        expander_times = st.expander("Propagation times (µs)")
        labels = [f"T{s}" for s in sensor_ids]

        # inicializar matriz
        if "propagation_matrix" not in st.session_state:

            mat = pd.DataFrame(0.0, index=labels, columns=labels)

            for i in range(len(labels)):
                mat.iloc[i, i] = None

            st.session_state["propagation_matrix"] = mat

        # reconstruir se sensores mudarem
        if list(st.session_state["propagation_matrix"].index) != labels:

            mat = pd.DataFrame(0.0, index=labels, columns=labels)

            for i in range(len(labels)):
                mat.iloc[i, i] = None

            st.session_state["propagation_matrix"] = mat

        edited_df = expander_times.data_editor(
            st.session_state["propagation_matrix"],
            key="propagation_editor",
            width="stretch",
            num_rows="fixed"
        )


        # gerar propagation_paths diretamente do editor
        for i in range(len(sensor_ids)):
            for j in range(i + 1, len(sensor_ids)):

                val = edited_df.iloc[j, i]

                if pd.notna(val):

                    propagation_paths.append({
                        "i": sensor_ids[i],
                        "j": sensor_ids[j],
                        "time": float(val)
                    })

    xs = [p[0] for p in pontos_cm]
    ys = [p[1] for p in pontos_cm]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width_cm = max_x - min_x
    height_cm = max_y - min_y

    side_cm = max(width_cm, height_cm)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    origin_x = cx - side_cm / 2
    origin_y = cy - side_cm / 2

    resolution_cm = side_cm / nx

    section = {
        "section_id": None,
        "height_cm": None,
        "acquisition_time": None,
        "calibration": {
            "scale_cm_per_pixel": escala,
            "reference_points": {"p1_id": int(p1_id), "p2_id": int(p2_id)},
            "real_distance": float(dist_real)
        },
        "domain": {
            "type": "cartesian",
            "centroid_cm": {
                "x": 0.0,
                "y": 0.0
            },
            "grid_origin_cm": {
                "x": round(origin_x, 3),
                "y": round(origin_y, 3)
            },
            "size": {"width_cm": round(side_cm, 10), "height_cm": round(side_cm, 10)},
            "grid": {"nx": nx, "ny": ny, "resolution_cm": round(resolution_cm, 5)}
        },
        "metadata": {"length_unit": "centimeter", "time_unit": "microsecond", "symmetry": True},
        "contour_nodes": [{"id": i+1, "x": round(p[0], 10), "y": round(p[1], 10)} for i, p in enumerate(pontos_cm)],
        "transducers": transducers,
        "propagation_paths": propagation_paths  
    }

    binary_grid = np.zeros((ny, nx), dtype=np.uint8)

    if escala != 0:
        for i in range(ny):
            for j in range(nx):
                curr_x_cm = origin_x + (j * resolution_cm)
                curr_y_cm = origin_y + ((ny - 1 - i) * resolution_cm)

                val_x = (curr_x_cm / escala) + centro[0]
                val_y = centro[1] - (curr_y_cm / escala)

                if not np.isnan(val_x) and not np.isnan(val_y):
                    orig_px_x = int(val_x)
                    orig_px_y = int(val_y)

                    if 0 <= orig_px_x < w and 0 <= orig_px_y < h:
                        binary_grid[i, j] = binary[orig_px_y, orig_px_x]
    else:
        st.warning("⚠️ Awaiting definition of reference points...")

    json_data = section
    json_str = json.dumps(json_data, indent=2)

    expander = st.expander("Generated JSON (YPS II input)")
    expander.code(json_str, language="json")

st.sidebar.divider()
st.sidebar.subheader("📦 Export")

if st.sidebar.button("🎁 Export KIT"):
    # -------------------
    # VALIDAÇÃO DA CALIBRAÇÃO
    # -------------------

    if p1_id == p2_id:
        st.sidebar.error(
            "Calibration error: Reference nodes must be different."
        )
        st.stop()

    # -------------------
    # VERIFICAÇÃO DOS TEMPOS
    # -------------------

    missing_times = [
        p for p in propagation_paths
        if p["time"] is None or p["time"] <= 0
    ]

    if len(missing_times) > 0:

        st.sidebar.error(
            f"🚨 Propagation time error: {len(missing_times)} propagation times are missing. "
            "Please fill all propagation times before exporting."
        )
        st.stop()

    if len(propagation_paths) == 0:
        st.sidebar.error(
            f"🚨 Propagation time error: Fill in the null values ​​before exporting"
        )
        st.stop()

    if len(transducers) == 0:
        st.sidebar.error("🚨 Transducers error: Transducers not positioned. Please specify the positioning before exporting.")
        st.stop()

    else:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zf:

            experiment_state = {
                "app": {
                    "name": "YPS I",
                    "version": "1.0",
                    "timestamp": datetime.now().isoformat()
                },

                "section_id": None,
                "height_cm": None,
                "acquisition_time": None,

                "image": {
                    "name": img_name,
                    "resize_applied": st.session_state.get("resize_applied"),
                    "scale_img": st.session_state.get("scale_img")
                },

                "geometry": {
                    "n_points": st.session_state.get("n_pontos"),
                    "centroid_px": {
                        "x": round(float(centro[0]), 3),
                        "y": round(float(centro[1]), 3)
                    },
                    "centroid_cm": {
                        "x": 0.0,
                        "y": 0.0
                    },
                    "grid_origin_cm": {
                        "x": round(origin_x, 3),
                        "y": round(origin_y, 3)
                    },
                    "polygon_points_px": [
                        {"id": i+1, "x": int(p[0]), "y": int(p[1])}
                        for i, p in enumerate(pontos)
                    ],
                    "polygon_points_cm": [
                        {"id": i+1, "x": round(p[0], 10), "y": round(p[1], 10)} 
                        for i, p in enumerate(pontos_cm)
                    ],
                },

                "style": {
                    "line_color": st.session_state.get("cor_linha"),
                    "line_thickness": st.session_state.get("espessura_linha"),
                    "node_radius": st.session_state.get("raio_ponto"),
                    "font_scale": st.session_state.get("font_scale"),
                    "font_thickness": st.session_state.get("font_thickness")
                },

                "point_settings": {
                    "window_size": st.session_state.get("zoom_size"),
                    "zoom_scale": st.session_state.get("zoom_scale")
                },

                "calibration": {
                    "scale_cm_per_pixel": escala,
                    "reference_points": {"p1_id": int(p1_id), "p2_id": int(p2_id)},
                    "distance_cm": float(dist_real)
                },

                "transducers": transducers,

                "segmentation": {
                    "blur_kernel": st.session_state.get("blur_size"),
                    "blur_sigma": st.session_state.get("blur_sigma"),
                    "threshold": st.session_state.get("threshold")
                },

                "propagation_paths": propagation_paths,

                "domain": {
                    "type": "cartesian",
                    "centroid_cm": {
                        "x": 0.0,
                        "y": 0.0
                    },
                    "grid_origin_cm": {
                        "x": round(origin_x, 3),
                        "y": round(origin_y, 3)
                    },
                    "size": {"width_cm": round(side_cm, 10), "height_cm": round(side_cm, 10)},
                    "grid": {"nx": nx, "ny": ny, "resolution_cm": round(resolution_cm, 5)}
                }
            }

            st.write(experiment_state)

            experiment_state["images"] = {}

            experiment_state["images"]["raw_image"] = write_png_to_zip(
                zf, img_np, "0_RAW_IMAGE.png"
            )

            experiment_state["images"]["threshold_real"] = write_png_to_zip(
                zf, binary, "1_THRESHOLD_REAL.png"
            )

            experiment_state["images"]["threshold_grid"] = write_png_to_zip(
                zf, binary_grid, "2_THRESHOLD_GRID.png"
            )

            experiment_state["images"]["mesh"] = write_png_to_zip(
                zf, img_poly_rgb, "3_MESH.png"
            )

            experiment_state["images"]["cropped"] = write_png_to_zip(
                zf, result_rgb, "4_CROPPED_SECTION.png"
            )

            experiment_json = json.dumps(experiment_state, indent=2)
            zf.writestr("5_EXPERIMENT_STATE.json", experiment_json)

            zf.writestr("6_YPSII_INPUT.json", json_str)

        st.sidebar.success("✅ ZIP file generated successfully")
        st.balloons()
        st.sidebar.download_button(
            "📥 Download ZIP",
            zip_buffer.getvalue(),
            f"YPSI_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip",
            "application/zip"
        )