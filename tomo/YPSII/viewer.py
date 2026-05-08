import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

st.set_page_config(
    page_title="JSON Tree Viewer",
    layout="wide"
)

DATA_FILE = Path("data.json")


# ---------------------------------------------------------
# LOAD / SAVE
# ---------------------------------------------------------

def load_data():

    if not DATA_FILE.exists():

        data = {
            "trees": [],
            "scans": []
        }

        save_data(data)

    with open(DATA_FILE, "r", encoding="utf8") as f:
        return json.load(f)


def save_data(data):

    backup = DATA_FILE.with_suffix(".backup.json")

    if DATA_FILE.exists():
        shutil.copy(DATA_FILE, backup)

    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


data = load_data()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("🌳 Tree Database")

trees = data["trees"]

tree_labels = [
    f"{t['especie']} — {t['id_arvore']}"
    for t in trees
]

selected_tree_label = st.sidebar.selectbox(
    "Tree",
    tree_labels if tree_labels else ["No trees"]
)

selected_tree = None

for t in trees:

    label = f"{t['especie']} — {t['id_arvore']}"

    if label == selected_tree_label:
        selected_tree = t


# ---------------------------------------------------------
# CREATE TREE
# ---------------------------------------------------------

st.sidebar.markdown("### ➕ New tree")

with st.sidebar.form("new_tree"):

    especie = st.text_input("Specie")
    description = st.text_input("Description")
    condition = st.text_input("Condition")

    lat = st.number_input("Latitude", value=0.0)
    lon = st.number_input("Longitude", value=0.0)
    alt = st.number_input("Altitude (m)", value=0.0)

    submitted = st.form_submit_button("Create")

    if submitted:

        new_id = max([t["id_arvore"] for t in trees], default=0) + 1

        new_tree = {
            "id_arvore": new_id,
            "especie": especie,
            "description": description,
            "condition": condition,
            "location": {
                "latitude": lat,
                "longitude": lon,
                "altitude_m": alt
            }
        }

        data["trees"].append(new_tree)

        data["scans"].append({
            "id_arvore": new_id,
            "sections": []
        })

        save_data(data)

        st.rerun()


# ---------------------------------------------------------
# DELETE TREE
# ---------------------------------------------------------

if selected_tree:

    if st.sidebar.button("🗑 Delete tree"):

        data["trees"] = [
            t for t in data["trees"]
            if t["id_arvore"] != selected_tree["id_arvore"]
        ]

        data["scans"] = [
            s for s in data["scans"]
            if s["id_arvore"] != selected_tree["id_arvore"]
        ]

        save_data(data)

        st.rerun()


# ---------------------------------------------------------
# TREE INFO
# ---------------------------------------------------------

if selected_tree:

    st.header("🌳 Tree info")

    col1, col2 = st.columns(2)

    with col1:

        especie = st.text_input(
            "Specie",
            selected_tree["especie"]
        )

        description = st.text_input(
            "Description",
            selected_tree["description"]
        )

        condition = st.text_input(
            "Condition",
            selected_tree["condition"]
        )

    with col2:

        lat = st.number_input(
            "Latitude",
            value=float(selected_tree["location"]["latitude"])
        )

        lon = st.number_input(
            "Longitude",
            value=float(selected_tree["location"]["longitude"])
        )

        alt = st.number_input(
            "Altitude",
            value=float(selected_tree["location"]["altitude_m"])
        )

    if st.button("💾 Save tree info"):

        selected_tree["especie"] = especie
        selected_tree["description"] = description
        selected_tree["condition"] = condition

        selected_tree["location"] = {
            "latitude": lat,
            "longitude": lon,
            "altitude_m": alt
        }

        save_data(data)

        st.success("Saved")


# ---------------------------------------------------------
# SECTIONS
# ---------------------------------------------------------

scan = next(
    s for s in data["scans"]
    if s["id_arvore"] == selected_tree["id_arvore"]
)

sections = scan["sections"]

st.header("📊 Sections")


# ---------------------------------------------------------
# CREATE SECTION
# ---------------------------------------------------------

with st.form("new_section"):

    height = st.number_input("Height (cm)", value=50)

    submitted = st.form_submit_button("Add section")

    if submitted:

        new_section = {
            "height_cm": height,
            "acquisition_time": datetime.now().isoformat(),
            "transducers": [],
            "propagation_paths": []
        }

        sections.append(new_section)

        save_data(data)

        st.rerun()


# ---------------------------------------------------------
# SELECT SECTION
# ---------------------------------------------------------

if sections:

    section_labels = [
        f"{s['height_cm']} cm"
        for s in sections
    ]

    selected_section_label = st.selectbox(
        "Section",
        section_labels
    )

    section = next(
        s for s in sections
        if f"{s['height_cm']} cm" == selected_section_label
    )

else:

    st.info("No sections yet")
    st.stop()


# ---------------------------------------------------------
# TRANSDUCERS
# ---------------------------------------------------------

st.subheader("Transducers")

trans_df = pd.DataFrame(section["transducers"])

if trans_df.empty:

    trans_df = pd.DataFrame(
        columns=["id", "x", "y"]
    )

edited_trans = st.data_editor(
    trans_df,
    num_rows="dynamic",
    key=f"trans_{selected_tree['id_arvore']}_{section['height_cm']}"
)

if st.button("Save transducers"):

    section["transducers"] = edited_trans.to_dict("records")

    save_data(data)

    st.success("Saved")


# ---------------------------------------------------------
# PROPAGATION PATHS
# ---------------------------------------------------------

st.subheader("Propagation paths")

paths_df = pd.DataFrame(section["propagation_paths"])

if paths_df.empty:

    paths_df = pd.DataFrame(
        columns=["i", "j", "time"]
    )

edited_paths = st.data_editor(
    paths_df,
    num_rows="dynamic",
    key=f"paths_{selected_tree['id_arvore']}_{section['height_cm']}"
)

if st.button("Save paths"):

    section["propagation_paths"] = edited_paths.to_dict("records")

    save_data(data)

    st.success("Saved")