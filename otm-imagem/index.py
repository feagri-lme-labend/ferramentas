import streamlit as st
from PIL import Image
import io
import zipfile
from datetime import datetime

st.set_page_config(layout="wide")

# -----------------------------
# Inicialização do session state
# -----------------------------
if "processed_images" not in st.session_state:
    st.session_state.processed_images = {}

if "stats" not in st.session_state:
    st.session_state.stats = {}

st.session_state.stats.setdefault("original_total", 0)
st.session_state.stats.setdefault("compressed_total", 0)
st.session_state.stats.setdefault("count", 0)

# -----------------------------
# Função de compressão
# -----------------------------
def compress_image(uploaded_file, quality):

    image = Image.open(uploaded_file).convert("RGB")

    original_bytes = uploaded_file.getvalue()
    original_size = len(original_bytes) / 1024

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True
    )

    compressed_bytes = buffer.getvalue()
    compressed_size = len(compressed_bytes) / 1024

    return {
        "original_image": image,
        "compressed_bytes": compressed_bytes,
        "original_size": original_size,
        "compressed_size": compressed_size
    }

# -----------------------------
# Interface
# -----------------------------
st.title("Otimizador de Imagens")

c1, c2 = st.columns([7, 1])
uploaded_files = c1.file_uploader(
    "Carregar imagens",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

c2.image(
    "https://img.freepik.com/fotos-gratis/close-up-de-uma-arara-escarlate-de-vista-lateral-close-up-da-cabeca-da-arara-scarlate_488145-3540.jpg?semt=ais_hybrid&w=740&q=80",

)

c1, c2, c3, c4 = st.columns([2, 1.75, 2.75, 1])
quality = c1.number_input(
    "Qualidade da compressão",
    10,
    95,
    25,
    step=5
)

process_button = c4.container(horizontal_alignment="right").button("Processar imagens")

# -----------------------------
# Processamento
# -----------------------------
if process_button and uploaded_files:

    processed = {}
    original_total = 0
    compressed_total = 0

    progress = st.progress(0)

    for i, file in enumerate(uploaded_files):

        result = compress_image(file, quality)

        processed[file.name] = result

        original_total += result["original_size"]
        compressed_total += result["compressed_size"]

        progress.progress((i + 1) / len(uploaded_files))

    st.session_state.processed_images = processed
    st.session_state.stats = {
        "original_total": original_total,
        "compressed_total": compressed_total,
        "count": len(processed)
    }

# -----------------------------
# Estatísticas gerais
# -----------------------------
if st.session_state.stats["count"] > 0:

    stats = st.session_state.stats

    reduction = 100 * (
        stats["original_total"] - stats["compressed_total"]
    ) / stats["original_total"]

    st.subheader("Estatísticas gerais")

    c1, c2, c3, c4, c5, c6 = st.columns([1, 1.375, 1.375, 1.375, 1.375, 1])

    c2.metric(
        "Imagens carregadas",
        stats["count"]
    )

    c3.metric(
        "Tamanho original",
        f"{stats['original_total']:.1f} KB"
    )

    c4.metric(
        "Tamanho comprimido",
        f"{stats['compressed_total']:.1f} KB"
    )

    c5.metric(
        "Redução",
        f"{reduction:.1f}%"
    )

# -----------------------------
# Visualização de imagem
# -----------------------------
if st.session_state.processed_images:

    st.subheader("Visualizar imagem específica")

    names = list(st.session_state.processed_images.keys())

    col1, col2, col3 = st.columns([1, 5.5, 1])
    selected = col2.selectbox(
        "Escolha a imagem",
        names
    )

    data = st.session_state.processed_images[selected]

    col1, col2, col3, col4 = st.columns([1, 2.75, 2.75, 1])

    with col2:
        st.image(
            data["original_image"],
            caption="Original",
            width="stretch"
        )

    with col3:
        st.image(
            data["compressed_bytes"],
            caption="Comprimida",
            width="stretch"
        )

    col1.markdown("**Detalhes da imagem**")

    original_size = data.get("original_size", 0)
    compressed_size = data.get("compressed_size", 0)

    reduction = 0
    if original_size > 0:
        reduction = 100 * (original_size - compressed_size) / original_size

    col1.metric(
        "Original",
        f"{original_size:.1f} KB"
    )

    col1.metric(
        "Comprimida",
        f"{compressed_size:.1f} KB"
    )

    col1.metric(
        "Redução",
        f"{reduction:.1f}%"
    )

# -----------------------------
# Gerar ZIP
# -----------------------------
if st.session_state.processed_images:

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as z:

        for name, data in st.session_state.processed_images.items():

            filename = name.rsplit(".", 1)[0] + ".jpg"

            z.writestr(
                filename,
                data["compressed_bytes"]
            )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"opt_{timestamp}.zip"

    col4.download_button(
        "Baixar imagens comprimidas",
        zip_buffer.getvalue(),
        file_name=zip_name,
        mime="application/zip"
    )