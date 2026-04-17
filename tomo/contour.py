import streamlit as st
from PIL import Image
import numpy as np
import io

st.set_page_config(layout="wide")

st.title("Recorte e binarização do tronco")

base_file = st.file_uploader("Imagem base", type=["png","jpg","jpeg"])
contour_file = st.file_uploader("PNG do contorno (transparente)", type=["png"])

if base_file and contour_file:

    base = Image.open(base_file).convert("RGBA")
    contour_original = Image.open(contour_file).convert("RGBA")

    st.sidebar.header("Ajuste do contorno")

    escala = st.sidebar.slider("Escala", 0.1, 3.0, 1.0, 0.01)
    rotacao = st.sidebar.slider("Rotação", -180, 180, 0)
    dx = st.sidebar.slider("Translação X", -500, 500, 0)
    dy = st.sidebar.slider("Translação Y", -500, 500, 0)

    # -------------------
    # Transformar contorno
    # -------------------

    w, h = contour_original.size

    contour = contour_original.resize(
        (int(w*escala), int(h*escala)),
        Image.Resampling.LANCZOS
    )

    contour = contour.rotate(rotacao, expand=True)

    # -------------------
    # Canvas
    # -------------------

    canvas = Image.new("RGBA", base.size, (0,0,0,0))
    canvas.paste(contour, (dx, dy), contour)

    alpha = np.array(canvas.split()[3])

    mask_array = np.where(alpha > 0, 255, 0).astype(np.uint8)
    mask = Image.fromarray(mask_array)

    # -------------------
    # Recorte
    # -------------------

    resultado = base.copy()
    resultado.putalpha(mask)

    # -------------------
    # Binarização
    # -------------------

    threshold = st.sidebar.slider("Threshold binário", 0, 255, 120)

    gray = resultado.convert("L")
    gray_np = np.array(gray)

    binary_np = (gray_np > threshold).astype(np.uint8)

    # aplicar máscara do tronco
    trunk_mask = (mask_array > 0)
    binary_np_masked = binary_np * trunk_mask

    # -------------------
    # Cortar bounding box do tronco
    # -------------------

    ys, xs = np.where(trunk_mask)

    ymin, ymax = ys.min(), ys.max()
    xmin, xmax = xs.min(), xs.max()

    binary_crop = binary_np_masked[ymin:ymax, xmin:xmax]

    # imagem binária visual
    binary_rgba = np.zeros((binary_np.shape[0], binary_np.shape[1], 4), dtype=np.uint8)
    binary_rgba[:,:,0] = binary_np * 255
    binary_rgba[:,:,1] = binary_np * 255
    binary_rgba[:,:,2] = binary_np * 255
    binary_rgba[:,:,3] = mask_array

    binary_img = Image.fromarray(binary_rgba)

    # -------------------
    # Reescalonamento
    # -------------------

    st.sidebar.header("Resolução da matriz")

    res = st.sidebar.slider("Tamanho da matriz", 50, 500, 200)

    crop_img = Image.fromarray(binary_crop*255)

    binary_rescaled = crop_img.resize(
        (res, res),
        Image.Resampling.NEAREST
    )

    binary_rescaled_np = (np.array(binary_rescaled) > 0).astype(np.uint8)

    # -------------------
    # Visualização
    # -------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.subheader("Imagem original")
        st.image(base)

    with col2:
        st.subheader("Imagem recortada")
        st.image(resultado)

    with col3:
        st.subheader("Imagem binária")
        st.image(binary_img)

    with col4:
        st.subheader(f"Binária reescalada {res}x{res}")
        st.image(binary_rescaled_np*255)

    # -------------------
    # Download recortada
    # -------------------

    buffer1 = io.BytesIO()
    resultado.save(buffer1, format="PNG")
    buffer1.seek(0)

    st.download_button(
        "Baixar imagem recortada",
        buffer1,
        "tronco_recortado.png",
        "image/png"
    )

    # -------------------
    # Download binária
    # -------------------

    buffer2 = io.BytesIO()
    binary_img.save(buffer2, format="PNG")
    buffer2.seek(0)

    st.download_button(
        "Baixar imagem binária",
        buffer2,
        "tronco_binario.png",
        "image/png"
    )

    # -------------------
    # Download matriz
    # -------------------

    matriz_txt = "\n".join(
        " ".join(map(str,row))
        for row in binary_rescaled_np
    )

    st.download_button(
        "Baixar matriz binária (TXT)",
        matriz_txt,
        "tronco_binario_matriz.txt"
    )