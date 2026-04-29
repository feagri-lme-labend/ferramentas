import numpy as np
import io
from PIL import Image
import hashlib
import base64
import streamlit as st

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