import streamlit as st
import numpy as np
import pandas as pd
import cv2
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from datetime import datetime
from itertools import combinations
import json
import base64
import zipfile
import io

# ---------------------------------------------------------
# Polygon centroid
# ---------------------------------------------------------

def polygon_centroid(points):

    x = points[:,0]
    y = points[:,1]

    A = 0
    Cx = 0
    Cy = 0

    n = len(points)

    for i in range(n):

        j = (i + 1) % n

        cross = x[i]*y[j] - x[j]*y[i]

        A += cross
        Cx += (x[i] + x[j]) * cross
        Cy += (y[i] + y[j]) * cross

    A *= 0.5

    if A == 0:
        return np.mean(points, axis=0)

    Cx /= (6*A)
    Cy /= (6*A)

    return np.array([Cx, Cy])

# ---------------------------------------------------------
# Propagation paths
# ---------------------------------------------------------

def build_propagation_paths(matrix):

    paths = []

    n = matrix.shape[0]

    for i in range(n):
        for j in range(i+1,n):

            t = matrix[j,i]

            if t is None:
                continue

            paths.append({
                "i": i+1,
                "j": j+1,
                "time": float(t)
            })

    return paths

st.set_page_config(layout="wide")

st.title("YPS I — Tree Tomography Preprocessor")

# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "polygon_pixels" not in st.session_state:
    st.session_state.polygon_pixels = None

if "scale_cm_per_pixel" not in st.session_state:
    st.session_state.scale_cm_per_pixel = None

if "transducers" not in st.session_state:
    st.session_state.transducers = []

# ---------------------------------------------------------
# Upload image
# ---------------------------------------------------------

uploaded = st.file_uploader(
    "Upload trunk image",
    type=["png","jpg","jpeg"]
)

if uploaded is None:
    st.stop()

image = Image.open(uploaded)
img_np = np.array(image)

h, w = img_np.shape[:2]

# reset quando nova imagem é carregada
if "last_uploaded_name" not in st.session_state:
    st.session_state.last_uploaded_name = uploaded.name

if uploaded.name != st.session_state.last_uploaded_name:
    st.session_state.last_uploaded_name = uploaded.name
    st.session_state.polygon_pixels = None
    st.session_state.transducers = []

# ---------------------------------------------------------
# Polygon canvas
# ---------------------------------------------------------

st.subheader("Define the polygon")

canvas = st_canvas(
    fill_color="rgba(255,165,0,0.3)",
    stroke_width=2,
    stroke_color="#ff0000",
    background_image=image,
    height=h,
    width=w,
    drawing_mode="polygon",
    update_streamlit=True,
    key="canvas",
)

# ---------------------------------------------------------
# Extract polygon
# ---------------------------------------------------------

def extract_polygon(json_data):

    if json_data is None:
        return None

    objects = json_data["objects"]

    if len(objects) == 0:
        return None

    obj = objects[0]

    if obj["type"] != "path":
        return None

    pts = []

    for p in obj["path"]:
        if p[0] in ["M","L"]:
            pts.append([p[1],p[2]])

    return np.array(pts)

if canvas.json_data is not None:

    polygon = extract_polygon(canvas.json_data)

    # novo polígono desenhado
    if polygon is not None:

        if (
            st.session_state.polygon_pixels is None
            or len(polygon) != len(st.session_state.polygon_pixels)
        ):
            st.session_state.polygon_pixels = polygon.copy()

    # usuário apagou usando lixeira
    elif polygon is None:
        st.session_state.polygon_pixels = None

points = st.session_state.polygon_pixels

if points is None:
    st.info("Draw a polygon to continue.")
    st.stop()

# ---------------------------------------------------------
# Sidebar - polygon editing
# ---------------------------------------------------------

st.sidebar.header("Polygon Editing")

n_nodes = len(points)

node_id = st.sidebar.slider(
    "Select node",
    1,
    n_nodes,
    1
) - 1

if "edit_x" not in st.session_state or "edit_y" not in st.session_state:
    st.session_state.edit_x = int(points[node_id][0])
    st.session_state.edit_y = int(points[node_id][1])
# atualiza quando troca o nó
if "last_node" not in st.session_state:
    st.session_state.last_node = node_id

if st.session_state.last_node != node_id:
    st.session_state.edit_x = int(points[node_id][0])
    st.session_state.edit_y = int(points[node_id][1])
    st.session_state.last_node = node_id

x_val = st.sidebar.slider(
    "X coordinate",
    0,
    w,
    st.session_state.edit_x,
    key="edit_x"
)

y_val = st.sidebar.slider(
    "Y coordinate",
    0,
    h,
    st.session_state.edit_y,
    key="edit_y"
)

points[node_id][0] = x_val
points[node_id][1] = y_val

st.session_state.polygon_pixels = points

# ---------------------------------------------------------
# Sidebar - calibration
# ---------------------------------------------------------

st.sidebar.header("Calibration")

node_a = st.sidebar.slider("Node A",1,n_nodes,1) - 1
node_b = st.sidebar.slider("Node B",1,n_nodes,min(2,n_nodes)) - 1

real_dist = st.sidebar.number_input(
    "Real distance (cm)",
    min_value=0.0,
    value=10.0,
    step=0.1
)

p1 = points[node_a]
p2 = points[node_b]

pixel_dist = np.linalg.norm(p1 - p2)

if pixel_dist > 0:

    scale = real_dist / pixel_dist
    st.session_state.scale_cm_per_pixel = scale

    st.sidebar.write(f"Pixel distance: {pixel_dist:.2f}")
    st.sidebar.write(f"Scale: {scale:.4f} cm/pixel")

# ---------------------------------------------------------
# Sidebar - segmentation
# ---------------------------------------------------------

st.sidebar.header("Segmentation")

blur_kernel = st.sidebar.slider(
    "Blur (kernel)",
    1,
    31,
    5,
    step=2
)

sigma = st.sidebar.slider(
    "Sigma of blur",
    0.0,
    10.0,
    1.0
)

threshold_val = st.sidebar.slider(
    "Threshold",
    0,
    255,
    120
)

# ---------------------------------------------------------
# Sidebar - transducers
# ---------------------------------------------------------

st.sidebar.header("Transducers")

transducers = []

for i in range(n_nodes):

    if st.sidebar.checkbox(f"Node {i+1}", value=False):

        transducers.append(i)

st.session_state.transducers = transducers

# ---------------------------------------------------------
# Visualization columns
# ---------------------------------------------------------

col1, col2 = st.columns([3, 1])

pts_int = points.astype(int)

# ---------------------------------------------------------
# Column 1 - polygon + diffraction mesh
# ---------------------------------------------------------

with col1:

    img_draw = img_np.copy()

    cv2.polylines(
        img_draw,
        [pts_int],
        True,
        (0,0,255),
        2
    )

    if len(transducers) >= 2:

        for i,j in combinations(transducers,2):

            p1 = tuple(pts_int[i])
            p2 = tuple(pts_int[j])

            cv2.line(
                img_draw,
                p1,
                p2,
                (200,200,200),
                1
            )

    for i,(x,y) in enumerate(pts_int):

        if i in transducers:
            color = (255,255,0)
        else:
            color = (255,255,255)

        cv2.circle(img_draw,(x,y),8,color,-1)

        cv2.putText(
            img_draw,
            str(i+1),
            (x-4,y+4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0,0,0),
            1
        )

    mesh_img = img_draw.copy()
    
    st.image(img_draw,use_container_width=True)

# ---------------------------------------------------------
# Column 2 - zoom node
# ---------------------------------------------------------

with col2:

    st.subheader(f"Zoom node {node_id+1}")

    zoom_size = 60

    x,y = pts_int[node_id]

    x1 = max(0,x-zoom_size)
    x2 = min(w,x+zoom_size)

    y1 = max(0,y-zoom_size)
    y2 = min(h,y+zoom_size)

    zoom = img_np[y1:y2, x1:x2]

    if zoom.size > 0:
        zoom = np.ascontiguousarray(zoom)

    cv2.circle(
        zoom,
        (min(zoom_size,x-x1),min(zoom_size,y-y1)),
        6,
        (0,0,255),
        -1
    )

    if zoom is not None and zoom.size > 0:
        st.image(zoom, use_container_width=True)
    else:
        st.warning("Nenhuma região válida para exibir. Ajuste o polígono ou gere um novo.")

# ---------------------------------------------------------
# Cropped and Segmented
# ---------------------------------------------------------

st.subheader("Cropped")

mask = np.zeros((h,w),dtype=np.uint8)
cv2.fillPoly(mask,[pts_int],255)

masked = cv2.bitwise_and(img_np,img_np,mask=mask)

x_min = np.min(pts_int[:,0])
x_max = np.max(pts_int[:,0])
y_min = np.min(pts_int[:,1])
y_max = np.max(pts_int[:,1])

cropped = masked[y_min:y_max,x_min:x_max]

col3, col4 = st.columns(2)

# Cropped image
with col3:

    st.image(cropped,use_container_width=True)

# ---------------------------------------------------------
# Propagation times
# ---------------------------------------------------------

st.subheader("Propagation times (µs)")

transducers = st.session_state.transducers
nT = len(transducers)

if nT < 2:

    st.info("Select at least two transducers to input propagation times.")

else:

    labels = [f"T{i+1}" for i in range(nT)]

    # -----------------------------------------------------
    # Initialize matrix
    # -----------------------------------------------------

    if "propagation_matrix" not in st.session_state or \
       st.session_state.propagation_matrix.shape != (nT,nT):

        mat = np.empty((nT,nT), dtype=object)

        for i in range(nT):
            for j in range(nT):

                if j < i:
                    mat[i,j] = 0.0
                else:
                    mat[i,j] = None

        st.session_state.propagation_matrix = mat

    mat = st.session_state.propagation_matrix

    # -----------------------------------------------------
    # Build dataframe
    # -----------------------------------------------------

    df = pd.DataFrame(mat, columns=labels, index=labels)

    edited = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            col: st.column_config.NumberColumn(
                col,
                format="%.2f",
                help="Propagation time (µs)"
            )
            for col in labels
        }
    )

    edited_np = edited.values.astype(object)

    # -----------------------------------------------------
    # Enforce triangular rule
    # -----------------------------------------------------

    for i in range(nT):
        for j in range(nT):

            if j >= i:
                edited_np[i,j] = None

    st.session_state.propagation_matrix = edited_np
    
# Segmented image
with col4:

    gray = cv2.cvtColor(cropped,cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(
        gray,
        (blur_kernel,blur_kernel),
        sigma
    )

    _,th = cv2.threshold(
        blur,
        threshold_val,
        255,
        cv2.THRESH_BINARY
    )

    st.image(th,use_container_width=True)

# ---------------------------------------------------------
# Sidebar - grid resolution
# ---------------------------------------------------------

st.sidebar.header("Grid")

grid_res = st.sidebar.selectbox(
    "Grid resolution (px)",
    [32, 64, 128, 256, 512],
    index=2
)

# ---------------------------------------------------------
# Real coordinates table
# ---------------------------------------------------------

if st.session_state.scale_cm_per_pixel is not None:

    scale = st.session_state.scale_cm_per_pixel

    real_pts = points * scale

    df = pd.DataFrame({
        "node":np.arange(1,n_nodes+1),
        "x_cm":real_pts[:,0],
        "y_cm":real_pts[:,1]
    })

    st.subheader("Real coordinates (cm)")

    st.dataframe(df,use_container_width=True)


# ---------------------------------------------------------
# Export JSON
# ---------------------------------------------------------

st.subheader("Export JSON")

if (
    st.session_state.scale_cm_per_pixel is not None
    and "propagation_matrix" in st.session_state
):

    scale = st.session_state.scale_cm_per_pixel

    # ----------------------------------------
    # contour nodes in cm
    # ----------------------------------------

    real_pts = points * scale

    contour_nodes = []

    for i,(x,y) in enumerate(real_pts):

        contour_nodes.append({
            "id": i+1,
            "x": float(x),
            "y": float(y)
        })

    # ----------------------------------------
    # centroid
    # ----------------------------------------

    centroid_px = polygon_centroid(points)

    centroid_cm = centroid_px * scale

    # ----------------------------------------
    # domain size
    # ----------------------------------------

    width_cm = w * scale
    height_cm = h * scale

    # ----------------------------------------
    # transducers
    # ----------------------------------------

    transducers = []

    for i,node_id in enumerate(st.session_state.transducers):

        transducers.append({
            "id": i+1,
            "contour_node_id": node_id+1
        })

    # ----------------------------------------
    # propagation paths
    # ----------------------------------------

    paths = build_propagation_paths(
        st.session_state.propagation_matrix
    )

    # ----------------------------------------
    # JSON structure
    # ----------------------------------------

    data = {

        "section_id": None,

        "height_cm": None,

        "acquisition_time": None,

        "calibration":{

            "scale_cm_per_pixel": scale,

            "reference_points":{
                "p1_id": node_a+1,
                "p2_id": node_b+1
            },

            "real_distance": real_dist
        },

        "domain":{

            "type":"cartesian",

            "centroid_cm":{
                "x": float(centroid_cm[0]),
                "y": float(centroid_cm[1])
            },

            "grid_origin_cm":{
                "x": 0.0,
                "y": 0.0
            },

            "size":{
                "width_cm": float(width_cm),
                "height_cm": float(height_cm)
            },

            "grid":{

                "nx": grid_res,
                "ny": grid_res,

                "resolution_cm": float(width_cm/grid_res)
            }
        },

        "metadata":{

            "length_unit":"centimeter",
            "time_unit":"microsecond",
            "symmetry":True
        },

        "contour_nodes": contour_nodes,

        "transducers": transducers,

        "propagation_paths": paths
    }

    json_str = json.dumps(data, indent=2)

    st.code(json_str, language="json")

# ---------------------------------------------------------
# Export ZIP
# ---------------------------------------------------------

st.sidebar.header("Export")

if (
    st.session_state.scale_cm_per_pixel is not None
    and "propagation_matrix" in st.session_state
):

    if st.sidebar.button("🎁 Export KIT"):

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer,"w") as z:

            # -------------------------------------------------
            # 0 RAW IMAGE (base64)
            # -------------------------------------------------

            raw_bytes = uploaded.getvalue()
            raw_b64 = base64.b64encode(raw_bytes).decode()

            z.writestr(
                "0_RAW_IMAGE.txt",
                raw_b64
            )

            # -------------------------------------------------
            # 1 THRESHOLD GRID
            # -------------------------------------------------

            th_resized = cv2.resize(
                th,
                (grid_res,grid_res),
                interpolation=cv2.INTER_NEAREST
            )

            _,png = cv2.imencode(".png",th_resized)

            z.writestr(
                "1_THRESHOLD_GRID.png",
                png.tobytes()
            )

            # -------------------------------------------------
            # 2 MESH IMAGE
            # -------------------------------------------------

            _,mesh_png = cv2.imencode(".png",mesh_img)

            z.writestr(
                "2_MESH.png",
                mesh_png.tobytes()
            )

            # -------------------------------------------------
            # 5 EXPERIMENT STATE
            # -------------------------------------------------

            #z.writestr(
            #    "5_EXPERIMENT_STATE.json",
            #    json.dumps(experiment_state,indent=2)
            #)

            # -------------------------------------------------
            # 6 YPSII INPUT
            # -------------------------------------------------

            z.writestr(
                "6_YPSII_INPUT.json",
                json.dumps(data,indent=2)
            )

        buffer.seek(0)

        st.sidebar.download_button(
            "Download ZIP",
            buffer,
            file_name=f"YPSI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )