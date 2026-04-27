import streamlit as st
import numpy as np
from PIL import Image
import pandas as pd
import io
from scipy.ndimage import binary_dilation

st.set_page_config(
    layout="wide",
    page_title="YPS III",
    page_icon="https://static.vecteezy.com/system/resources/thumbnails/068/754/722/small/flowing-red-and-yellow-waves-create-a-warm-vibrant-abstract-background-free-vector.jpg"
)

st.title("Binary Segmentation Evaluation")

st.info("""
Upload the following images:

- **Ground Truth Binary Image**
- **Modeled Binary Image**
- **Hull Mask**

The evaluation will be performed **only inside the mask region**.
""")


# =========================================================
# FUNCTIONS
# =========================================================

def load_binary(file):
    """Load image and convert to binary numpy array"""
    img = Image.open(file).convert("L")
    arr = np.array(img)
    return (arr > 127).astype(np.uint8)


def resize_if_needed(img, target_shape):
    """Resize image if resolution differs"""
    if img.shape != target_shape:

        pil = Image.fromarray((img * 255).astype(np.uint8))

        pil = pil.resize(
            (target_shape[1], target_shape[0]),
            Image.NEAREST
        )

        img = (np.array(pil) > 127).astype(np.uint8)

    return img


# =========================================================
# CONFUSION MATRIX WITH SPATIAL TOLERANCE
# =========================================================

def confusion_components(real, model, mask, tolerance=0):
    """
    Compute TP, TN, FP, FN using optional spatial tolerance
    """

    if tolerance > 0:

        real_tol = binary_dilation(real, iterations=tolerance)
        model_tol = binary_dilation(model, iterations=tolerance)

    else:

        real_tol = real
        model_tol = model

    tp = ((model == 1) & (real_tol == 1) & (mask == 1))

    fn = ((real == 1) & (model_tol == 0) & (mask == 1))

    fp = ((model == 1) & (real_tol == 0) & (mask == 1))

    tn = ((real == 0) & (model == 0) & (mask == 1))

    return tp, tn, fp, fn


# =========================================================
# METRICS
# =========================================================

def compute_metrics(tp, tn, fp, fn):

    TP = np.sum(tp)
    TN = np.sum(tn)
    FP = np.sum(fp)
    FN = np.sum(fn)

    total = TP + TN + FP + FN

    accuracy = (TP + TN) / total if total else 0
    precision = TP / (TP + FP) if TP + FP else 0
    recall = TP / (TP + FN) if TP + FN else 0
    specificity = TN / (TN + FP) if TN + FP else 0

    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0

    dice = 2 * TP / (2 * TP + FP + FN) if (2 * TP + FP + FN) else 0

    iou = TP / (TP + FP + FN) if (TP + FP + FN) else 0

    balanced_accuracy = (recall + specificity) / 2

    denom = np.sqrt((TP+FP)*(TP+FN)*(TN+FP)*(TN+FN))

    mcc = ((TP*TN)-(FP*FN))/denom if denom else 0

    return {
        "TP":TP,
        "TN":TN,
        "FP":FP,
        "FN":FN,
        "Accuracy":accuracy,
        "Precision":precision,
        "Recall":recall,
        "Specificity":specificity,
        "F1-score":f1,
        "Dice":dice,
        "IoU":iou,
        "Balanced Accuracy":balanced_accuracy,
        "MCC":mcc
    }


# =========================================================
# ERROR MAP
# =========================================================

def create_error_map(tp, tn, fp, fn):

    h, w = tp.shape

    img = np.zeros((h, w, 3), dtype=np.uint8)

    img[tn] = [0, 0, 0]       # True Negative
    img[tp] = [0, 255, 0]     # True Positive
    img[fp] = [255, 0, 0]     # False Positive
    img[fn] = [0, 0, 255]     # False Negative

    return img


# =========================================================
# FILE UPLOAD
# =========================================================

real_file = st.sidebar.file_uploader(
    "Ground Truth Binary Image",
    type=["png", "jpg", "tif"]
)

model_file = st.sidebar.file_uploader(
    "Modeled Binary Image",
    type=["png", "jpg", "tif"]
)

mask_file = st.sidebar.file_uploader(
    "Hull Mask",
    type=["png", "jpg", "tif"]
)


# =========================================================
# SPATIAL TOLERANCE CONTROL
# =========================================================

tolerance = st.slider(
    "Edge tolerance (pixels)",
    0,
    5,
    1
)


# =========================================================
# PROCESSING
# =========================================================

if real_file and model_file and mask_file:

    real = load_binary(real_file)
    model = load_binary(model_file)
    mask = load_binary(mask_file)

    st.subheader("Resolution Check")

    st.write("Ground Truth:", real.shape)
    st.write("Modeled:", model.shape)
    st.write("Hull Mask:", mask.shape)

    if real.shape == model.shape == mask.shape:

        st.success("Resolutions are compatible")

    else:

        st.warning("Different resolutions detected. Resizing automatically")

        target = real.shape

        model = resize_if_needed(model, target)
        mask = resize_if_needed(mask, target)

    # =====================================================
    # DIFFERENCE MAP (DIAGNOSTIC)
    # =====================================================

    diff = np.abs(real.astype(int) - model.astype(int))

    col1, col2 = st.columns([1, 2])

    col1.subheader("Difference Map (Diagnostic)")

    col1.container(horizontal_alignment="center").image(
        diff * 255,
        caption="Absolute difference between ground truth and modeled binary image",
        width="stretch"
    )

    # =====================================================
    # CONFUSION MATRIX
    # =====================================================

    tp, tn, fp, fn = confusion_components(
        real,
        model,
        mask,
        tolerance
    )

    metrics = compute_metrics(tp, tn, fp, fn)

    metrics_df = pd.DataFrame(
        list(metrics.items()),
        columns=["Metric", "Value"]
    )

    col2.subheader("Evaluation Metrics")

    col2.dataframe(metrics_df)

    st.subheader("Confusion Matrix")

    matrix = pd.DataFrame(
        [[metrics["TN"], metrics["FP"]],
         [metrics["FN"], metrics["TP"]]],
        columns=["Predicted 0", "Predicted 1"],
        index=["Real 0", "Real 1"]
    )

    st.dataframe(matrix)

    # =====================================================
    # ERROR MAP
    # =====================================================

    st.subheader("Error Map")

    error_map = create_error_map(tp, tn, fp, fn)

    st.image(
        error_map,
        caption="""
        Green = TP | Black = TN | Red = FP | Blue = FN
        """
    )

    # =====================================================
    # IMAGE VISUALIZATION
    # =====================================================

    st.subheader("Loaded Images")

    col1, col2, col3 = st.columns(3)

    col1.image(real * 255, caption="Ground Truth")
    col2.image(model * 255, caption="Modeled")
    col3.image(mask * 255, caption="Hull Mask")

    # =====================================================
    # DOWNLOAD METRICS
    # =====================================================

    csv = metrics_df.to_csv(index=False).encode()

    st.download_button(
        "Download metrics (CSV)",
        csv,
        "segmentation_metrics.csv",
        "text/csv"
    )

    # =====================================================
    # DOWNLOAD ERROR MAP
    # =====================================================

    buf = io.BytesIO()

    Image.fromarray(error_map).save(buf, format="PNG")

    st.download_button(
        "Download error map",
        buf.getvalue(),
        "error_map.png",
        "image/png"
    )