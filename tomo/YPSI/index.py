import streamlit as st
import numpy as np
from PIL import Image
import cv2
import json
from datetime import datetime
from inp_out.export_zip import build_export_zip
from inp_out.json_struc import build_section
from geometry.grid import compute_grid_domain, build_binary_grid
from processing.image_processing import auto_resize_image
from visualization.canvas_polygon import polygon_canvas
from core.polygon_state import update_polygon_state
from core.image_state import reset_if_new_image
from domain.segment_section import segment_section
from geometry.zoom import build_zoom_view
from domain.calibration import compute_scale
from geometry.coordinates import convert_points_to_cm
from domain.transducers import build_transducers
from domain.mask import apply_polygon_mask
from domain.validation import run_validations, find_missing_times
from streamlit.errors import StreamlitValueAboveMaxError, StreamlitValueBelowMinError, StreamlitAPIException
from visualization.drawing import draw_polygon_mesh
from utils.utils import (
    hex_to_bgr,
    polygon_centroid
)
from domain.propagation import (
    ensure_propagation_matrix,
    extract_propagation_paths
)

st.set_page_config(layout="wide", page_title="YPS I", page_icon="https://static.vecteezy.com/system/resources/thumbnails/068/754/722/small/flowing-red-and-yellow-waves-create-a-warm-vibrant-abstract-background-free-vector.jpg")

st.markdown("### 🔊 Tomographic Mesh Definitions")

uploaded_file = st.file_uploader("Upload an image", type=["png","jpg","jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file).convert("RGB")
    img_name = uploaded_file.name
    img_np = np.array(img)

    # garantir compatibilidade com OpenCV
    img_np = np.ascontiguousarray(img_np, dtype=np.uint8)

    reset_if_new_image(uploaded_file)

    h, w = img_np.shape[:2]
    scale_img = 1.0
    resized = False

    # escala salva (importante pra debug/futuro)
    st.session_state.scale_img = scale_img

    # -------------------
    # CONFIG
    # -------------------
    st.sidebar.title("YPS I")

    # --- CANVAS PARA DESENHO INICIAL ---
    st.markdown("#### 🖌️ Define the polygon")
    
    polygon_canvas(img_np, h, w)
    
    #st.warning("Aguardando definição de pontos do polígono")
    if "n_pontos" not in st.session_state:
        st.session_state.n_pontos = 1

    expander = st.sidebar.expander("Polygon")
    
    n_pontos = expander.slider("Number of points", min_value=0, max_value=st.session_state.n_pontos, key="n_pontos", disabled=True)
    #st.error("🚨 Polygon error: The number of nodes defined for the polygon is outside the appropriate range for constructing the transducer mesh")
    
    try:
        ponto_ativo = expander.slider("Selected node", 1, n_pontos, 1)
    
        update_polygon_state(n_pontos, w, h, scale_img)

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
        
        st.write(st.session_state)
        # Ao passar o parâmetro 'value', garantimos que o slider sempre inicie 
        # com a coordenada correta do ponto selecionado, ignorando valores antigos.
        x = expander.slider("X", 0, w-1, value=valor_x_atual)
        y = expander.slider("Y", 0, h-1, value=valor_y_atual)

        # Atualiza a lista principal com o valor que o slider acabou de retornar
        st.session_state.pontos[idx] = [x, y]

        pontos = np.asarray(st.session_state.pontos)
        pts = np.array([pontos], dtype=np.int32)

        # -------------------
        # CALIBRAÇÃO
        # -------------------
        expander = st.sidebar.expander("Calibration")

        p1_id = expander.selectbox("Reference node 1", list(range(1, len(pontos)+1)))
        p2_id = expander.selectbox("Reference node 2", list(range(1, len(pontos)+1)))

        dist_real = expander.number_input("Real distance (cm)", 0.1, 1000.0, 10.0)

        escala = compute_scale(pontos, p1_id, p2_id, dist_real)

        expander.write(f"Scale: {escala:.4f} cm/pixel")

        expander = st.sidebar.expander("Grid")
        nx = ny = expander.selectbox("Grid resolution (px)", [128, 256], index=1, key="grid_resolution")

        # -------------------
        # CONVERTER PARA CM
        # -------------------
        centro = polygon_centroid(pontos)
        pontos_cm = convert_points_to_cm(pontos, centro, escala)

        # -------------------
        # SENSORES
        # -------------------
        expander = st.sidebar.expander("Transducers")

        selected_nodes = [
            i + 1
            for i, _ in enumerate(pontos)
            if expander.checkbox(f"Node {i+1}", key=f"sensor_{i}")
        ]

        transducers = build_transducers(selected_nodes)

        result = apply_polygon_mask(img_np, pts)

        # -------------------
        # THRESHOLD
        # -------------------
        expander = st.sidebar.expander("Segmentation")

        blur_size = expander.slider("Blur (kernel)", 1, 31, 5, step=2, key="blur_size")
        blur_sigma = expander.slider("Sigma of blur", 0.0, 10.0, 1.0, key="blur_sigma")

        threshold = expander.slider("Threshold", 0, 255, 120, key="threshold")

        binary = segment_section(
            result,
            blur_size,
            blur_sigma,
            threshold
        )

        img_poly = draw_polygon_mesh(
            img_np,
            pontos,
            transducers,
            idx,
            centro,
            cor_linha,
            espessura_linha,
            raio_ponto,
            font_scale,
            font_thickness
        )

        zoom_img_rgb = build_zoom_view(
            img_np,
            pontos[idx],
            zoom_size,
            zoom_scale,
            w,
            h
        )

        img_poly_rgb = cv2.cvtColor(img_poly, cv2.COLOR_BGR2RGB)
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

        with st.expander("Geometry"):
            col1, col2 = st.columns([2, 1])
            col1.markdown("##### Polygon + Transducers + Mesh")
            col1.image(img_poly_rgb)
            col2.markdown(f"##### Zoom (Node {idx+1})")
            col2.image(zoom_img_rgb)
        
        with st.expander("Cropped + Threshold"):
            col1, col2 = st.columns(2)
            col1.markdown("##### Cropped")
            col1.image(result_rgb)
            col2.markdown("##### Cross-Sectional Threshold")
            col2.image(binary, clamp=True)

        propagation_paths = []

        sensor_ids = sorted(s["id"] for s in transducers)

        if len(sensor_ids) >= 2:

            expander_times = st.expander("Propagation times (µs)")
            labels = [f"T{s}" for s in sensor_ids]

            matrix = ensure_propagation_matrix(labels)

            edited_df = expander_times.data_editor(
                matrix,
                key="propagation_editor",
                width="stretch",
                num_rows="fixed"
            )

            propagation_paths = extract_propagation_paths(sensor_ids, edited_df)

        grid = compute_grid_domain(pontos_cm, nx, ny)

        origin_x = grid["origin_x"]
        origin_y = grid["origin_y"]
        side_cm = grid["side_cm"]
        resolution_cm = grid["resolution_cm"]

        section = build_section(
            escala,
            p1_id,
            p2_id,
            dist_real,
            origin_x,
            origin_y,
            side_cm,
            nx,
            ny,
            resolution_cm,
            pontos_cm,
            transducers,
            propagation_paths
        )

        binary_grid = build_binary_grid(
            binary,
            escala,
            centro,
            origin_x,
            origin_y,
            resolution_cm,
            nx,
            ny,
            w,
            h
        )

        if escala == 0:
            st.warning("⚠️ Awaiting definition of reference points...")

        json_data = section
        json_str = json.dumps(json_data, indent=2)

        expander = st.expander("Generated JSON (YPS II input)")
        expander.code(json_str, language="json")

        st.sidebar.divider()
        st.sidebar.subheader("📦 Export")

        if st.sidebar.button("🎁 Export KIT"):
            missing_times = find_missing_times(propagation_paths)

            validations = [
                (p1_id == p2_id,
                "🚨 Calibration error: Reference nodes must be different."
                ),
                
                (len(missing_times) > 0,
                f"🚨 Propagation time error: {len(missing_times)} propagation times are missing. "
                "Please fill all propagation times before exporting."),

                (len(transducers) == 0,
                "🚨 Transducer error: Position the transducers and set the propagation times before proceeding"),

                (len(propagation_paths) == 0,
                "🚨 Propagation time error: Fill in the null values before exporting"),

                (len(transducers) == 0,
                "🚨 Transducers error: Transducers not positioned.")
            ]

            if not run_validations(validations, st.sidebar.error):
                st.stop()

            zip_buffer = build_export_zip(
                img_name,
                centro,
                pontos,
                pontos_cm,
                escala,
                p1_id,
                p2_id,
                dist_real,
                origin_x,
                origin_y,
                side_cm,
                nx,
                ny,
                resolution_cm,
                transducers,
                propagation_paths,
                st.session_state,
                img_np,
                binary,
                binary_grid,
                img_poly_rgb,
                result_rgb,
                json_str
            )

            st.sidebar.success("✅ ZIP file generated successfully")
            st.balloons()
            st.sidebar.download_button(
                "📥 Download ZIP",
                zip_buffer.getvalue(),
                f"YPSI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                "application/zip"
            )
    except StreamlitAPIException:
        st.sidebar.warning("Awaiting polygon definition")
        st.stop()