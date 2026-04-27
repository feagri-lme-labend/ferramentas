import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="ASTM D5764 Analyzer", layout="centered")

st.title("ASTM D5764 – Multi Test Analyzer")

# =============================
# SESSION STATE
# =============================

if "files" not in st.session_state:
    st.session_state["files"] = {}

# =============================
# UPLOAD
# =============================

uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state["files"]:

            df = pd.read_csv(file) if file.name.endswith("csv") else pd.read_excel(file)

            st.session_state["files"][file.name] = {
                "df": df,
                "yield_load": None,
                "yield_deformation": None,
                "diameter": 12.0,
                "slope": None,
                "r2": None
            }

# =============================
# FILE SELECT
# =============================

files = list(st.session_state["files"].keys())

if files:

    selected_file = st.sidebar.selectbox("Select test", files)

    data = st.session_state["files"][selected_file]
    df = data["df"]

    st.sidebar.header("Configuration")

    # =============================
    # COLUMNS
    # =============================

    x_col = st.sidebar.selectbox("Displacement column", df.columns)
    y_col = st.sidebar.selectbox("Load column", df.columns)
    time_col = st.sidebar.selectbox("Time column", df.columns)

    deformation = df[x_col].astype(float).values
    load = df[y_col].astype(float).values
    time = df[time_col].astype(float).values

    invert_x = st.sidebar.checkbox("Invert displacement")
    invert_y = st.sidebar.checkbox("Invert load")

    if invert_x:
        deformation = -deformation

    if invert_y:
        load = -load

    order = np.argsort(deformation)
    deformation = deformation[order]
    load = load[order]
    time = time[order]

    # =============================
    # TIME FILTER
    # =============================

    st.sidebar.header("Analysis filter")

    time_range = st.sidebar.slider(
        "Time interval",
        float(np.min(time)),
        float(np.max(time)),
        (float(np.min(time)), float(np.max(time)))
    )

    mask_time = (time >= time_range[0]) & (time <= time_range[1])

    deformation_f = deformation[mask_time]
    load_f = load[mask_time]

    if len(deformation_f) == 0:
        st.warning("No data after time filter")
        st.stop()

    # =============================
    # X FILTER
    # =============================

    st.sidebar.header("X filter")

    x_range = st.sidebar.slider(
        "Deformation range",
        float(np.min(deformation)),
        float(np.max(deformation)),
        (float(np.min(deformation)), float(np.max(deformation)))
    )

    mask_x = (
        (deformation_f >= x_range[0]) &
        (deformation_f <= x_range[1])
    )

    deformation_f = deformation_f[mask_x]
    load_f = load_f[mask_x]

    if len(deformation_f) == 0:
        st.warning("No data after X filter")
        st.stop()

    # =============================
    # LINEAR REGION
    # =============================

    lin_range = st.sidebar.slider(
        "Regression interval",
        float(np.min(deformation_f)),
        float(np.max(deformation_f)),
        (float(np.min(deformation_f)),
         float(np.min(deformation_f) + (np.max(deformation_f) - np.min(deformation_f)) * 0.3))
    )

    mask_lin = (
        (deformation_f >= lin_range[0]) &
        (deformation_f <= lin_range[1])
    )

    x_lin = deformation_f[mask_lin]
    y_lin = load_f[mask_lin]

    if len(x_lin) < 2:
        st.warning("Not enough points for regression")
        m, b, r2 = 0.0, 0.0, 0.0
    else:
        m, b = np.polyfit(x_lin, y_lin, 1)

        y_pred = m * x_lin + b

        ss_res = np.sum((y_lin - y_pred) ** 2)
        ss_tot = np.sum((y_lin - np.mean(y_lin)) ** 2)

        r2 = 1 - (ss_res / ss_tot if ss_tot != 0 else 0)

    # =============================
    # OFFSET
    # =============================

    diam_key = f"diameter_{selected_file}"

    if diam_key not in st.session_state:
        st.session_state[diam_key] = data.get("diameter", 12.0)

    diameter = st.sidebar.number_input(
        "Pin diameter",
        key=diam_key
    )

    data["diameter"] = st.session_state[diam_key]
    offset = 0.05 * diameter

    # =============================
    # INTERSECTION
    # =============================

    intersection_x = None
    intersection_y = None

    diff = load_f - (m * (deformation_f - offset) + b)

    order = np.argsort(deformation_f)
    x_sorted = deformation_f[order]
    diff_sorted = diff[order]

    sign_change = np.where(np.diff(np.sign(diff_sorted)))[0]

    if len(sign_change) > 0:

        i = sign_change[0]

        x1, x2 = x_sorted[i], x_sorted[i+1]
        y1, y2 = diff_sorted[i], diff_sorted[i+1]

        if y2 != y1:
            intersection_x = x1 - y1 * (x2 - x1) / (y2 - y1)

            intersection_y = np.interp(
                intersection_x,
                deformation_f,
                load_f
            )

            data["yield_load"] = float(intersection_y)
            data["yield_deformation"] = float(intersection_x)

    # =============================
    # SAVE REGRESSION + INPUTS
    # =============================

    data["slope"] = float(m)
    data["r2"] = float(r2)

    data["x_col"] = x_col
    data["y_col"] = y_col
    data["time_col"] = time_col

    data["invert_x"] = invert_x
    data["invert_y"] = invert_y

    data["time_range"] = time_range
    data["x_range"] = x_range
    data["linear_range"] = lin_range

    data["diameter"] = diameter
    data["offset"] = offset

    # =============================
    # PLOT
    # =============================

    st.subheader(f"Test: {selected_file}")

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.scatter(deformation, load, s=1, color="lightgray", label="Full dataset")
    ax.scatter(deformation_f, load_f, s=1, label="Filtered data")
    ax.scatter(x_lin, y_lin, s=5, color="orange", label="Linear region")

    x_line = np.linspace(np.min(deformation_f), np.max(deformation_f), 500)

    ax.plot(x_line, m * x_line + b, "--", label="Regression")
    ax.plot(x_line, m * (x_line - offset) + b, "--", label="Offset")

    if intersection_x is not None:
        ax.scatter(intersection_x, intersection_y, s=80, label="Yield")

    ax.set_xlim(np.min(deformation_f), np.max(deformation_f))
    ax.set_ylim(np.min(load_f), np.max(load_f))

    ax.set_xlabel("Deformation")
    ax.set_ylabel("Load")

    ax.legend(loc="lower right", fontsize=8)

    st.pyplot(fig)

# =============================
# GLOBAL RESULTS
# =============================

st.header("Global results")

rows = []

for name, data in st.session_state["files"].items():

    rows.append({
        "file": name,

        # inputs
        "x_col": data.get("x_col"),
        "y_col": data.get("y_col"),
        "time_col": data.get("time_col"),

        "invert_x": data.get("invert_x"),
        "invert_y": data.get("invert_y"),

        "time_range": data.get("time_range"),
        "x_range": data.get("x_range"),
        "linear_range": data.get("linear_range"),

        "diameter": data.get("diameter"),
        "offset": data.get("offset"),

        # outputs
        "slope": data.get("slope"),
        "r2": data.get("r2"),
        "yield_load": data.get("yield_load"),
        "yield_deformation": data.get("yield_deformation"),
    })

st.dataframe(pd.DataFrame(rows))