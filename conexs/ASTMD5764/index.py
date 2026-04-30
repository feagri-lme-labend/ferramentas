import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="ASTM D5764 Analyzer", 
    layout="wide",
    page_icon="./icon.png"
)

def downsample(x, y, fraction=.2):
    n = len(x)

    if n < 1000:
        return x, y

    step = max(int(1 / fraction), 1)

    idx = np.arange(0, n, step)

    return x[idx], y[idx]


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

            st.success(f"✅ Loaded: {file.name}")

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

    time_key = f"time_range_{selected_file}"

    if time_key not in st.session_state:
        st.session_state[time_key] = data.get(
            "time_range",
            (float(np.min(time)), float(np.max(time)))
        )

    time_range = st.sidebar.slider(
        "Time interval",
        float(np.min(time)),
        float(np.max(time)),
        key=time_key
    )

    data["time_range"] = time_range

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

    x_key = f"x_range_{selected_file}"

    if x_key not in st.session_state:
        st.session_state[x_key] = data.get(
            "x_range",
            (float(np.min(deformation)), float(np.max(deformation)))
        )

    x_range = st.sidebar.slider(
        "Deformation range",
        float(np.min(deformation)),
        float(np.max(deformation)),
        key=x_key
    )

    data["x_range"] = x_range

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

    lin_key = f"linear_range_{selected_file}"

    default_lin = (
        float(np.min(deformation_f)),
        float(np.min(deformation_f) +
            (np.max(deformation_f) - np.min(deformation_f)) * 0.3)
    )

    if lin_key not in st.session_state:
        st.session_state[lin_key] = data.get("linear_range", default_lin)

    lin_range = st.sidebar.slider(
        "Regression interval",
        float(np.min(deformation_f)),
        float(np.max(deformation_f)),
        key=lin_key
    )

    data["linear_range"] = lin_range

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

    deformation_plot, load_plot = downsample(deformation, load)
    deformation_f_plot, load_f_plot = downsample(deformation_f, load_f)
    x_lin_plot, y_lin_plot = downsample(x_lin, y_lin)

    st.subheader(f"Test: {selected_file}")

    fig = go.Figure()

    # Full dataset
    fig.add_trace(
        go.Scatter(
            x=deformation_plot,
            y=load_plot,
            mode="markers",
            marker=dict(size=3, color="lightgray"),
            name="Full dataset"
        )
    )

    # Filtered data
    fig.add_trace(
        go.Scatter(
            x=deformation_f_plot,
            y=load_f_plot,
            mode="markers",
            marker=dict(size=3),
            name="Filtered data"
        )
    )

    # Linear region
    fig.add_trace(
        go.Scatter(
            x=x_lin_plot,
            y=y_lin_plot,
            mode="markers",
            marker=dict(size=6, color="orange"),
            name="Linear region"
        )
    )

    # Lines
    x_line = np.linspace(np.min(deformation_f), np.max(deformation_f), 500)

    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=m * x_line + b,
            mode="lines",
            line=dict(dash="dash"),
            name="Regression"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=m * (x_line - offset) + b,
            mode="lines",
            line=dict(dash="dash"),
            name="Offset"
        )
    )

    # Yield point
    if intersection_x is not None:
        fig.add_trace(
            go.Scatter(
                x=[intersection_x],
                y=[intersection_y],
                mode="markers",
                marker=dict(size=12, color="red"),
                name="Yield"
            )
        )

    # Layout
    fig.update_layout(
        xaxis_title=x_col,
        yaxis_title=y_col,
        height=500,
        legend=dict(
            x=1,
            y=0,
            xanchor="right",
            yanchor="bottom"
        )
    )

    fig.update_xaxes(range=[np.min(deformation_f), np.max(deformation_f)])
    fig.update_yaxes(range=[np.min(load_f), np.max(load_f)])

    st.plotly_chart(fig, width="stretch")

    # =============================
    # GLOBAL RESULTS
    # =============================

    st.header("Global results")

    rows = []

    for name, data in st.session_state["files"].items():

        rows.append({
            "file": name,

            # columns used
            "x_col": data.get("x_col"),
            "y_col": data.get("y_col"),
            "time_col": data.get("time_col"),

            # inversion flags
            "invert_x": data.get("invert_x"),
            "invert_y": data.get("invert_y"),

            # time filter
            "time_min": data.get("time_range")[0] if data.get("time_range") else None,
            "time_max": data.get("time_range")[1] if data.get("time_range") else None,

            # deformation filter
            "x_min": data.get("x_range")[0] if data.get("x_range") else None,
            "x_max": data.get("x_range")[1] if data.get("x_range") else None,

            # regression region
            "linear_min": data.get("linear_range")[0] if data.get("linear_range") else None,
            "linear_max": data.get("linear_range")[1] if data.get("linear_range") else None,

            # geometry
            "diameter": data.get("diameter"),
            "offset": data.get("offset"),

            # regression results
            "slope": data.get("slope"),
            "r2": data.get("r2"),

            # yield results
            "yield_load": data.get("yield_load"),
            "yield_deformation": data.get("yield_deformation"),
        })

    st.dataframe(pd.DataFrame(rows))
else:
    st.info("📂 Upload one or more CSV or Excel files to start the analysis.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.markdown("### ASTM D5764 Analyzer")

        st.markdown(
            """
            This tool helps analyze **bearing tests** by automatically computing:

            - Linear regression of the elastic region  
            - Offset method for **yield load detection**  
            - Interactive filtering of time and deformation  
            - Visualization of full and filtered datasets  

            Upload one or more experimental files to begin.
            """
        )

        st.markdown("---")

        st.markdown("#### Accepted formats")

        st.markdown(
            """
            - **CSV**

            Each file should contain columns representing:
            - **Time**
            - **Displacement**
            - **Load**

            **CSV formatting requirements:**

            - Columns must be separated by **commas ( , )**
            - Decimal numbers must use **dot notation ( . )**

            Example:

            ```
            Time,Displacement,Load
            0.00,0.000,0.00
            0.01,0.002,15.32
            0.02,0.004,31.87
            ```
            """
        )

        st.markdown("---")

        st.markdown("#### Quick tips")

        st.markdown(
            """
            • Use the **time filter** to remove machine stabilization regions  
            • Adjust the **linear regression interval** to capture the elastic slope  
            • The **offset line (0.05D)** is used to detect the yield load automatically  
            • Multiple tests can be analyzed simultaneously
            """
        )

        st.markdown("---")

        VIDEO_URL = "https://www.youtube.com/watch?v=2zcTKhohtJg"

        st.video(
            VIDEO_URL,
            autoplay=True,
            muted=True,
            loop=True
        )