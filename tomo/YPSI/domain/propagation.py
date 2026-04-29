import pandas as pd
import streamlit as st

def create_propagation_matrix(labels):

    mat = pd.DataFrame(0.0, index=labels, columns=labels)

    for i in range(len(labels)):
        mat.iloc[i, i] = None

    return mat

def ensure_propagation_matrix(labels):

    if "propagation_matrix" not in st.session_state:
        st.session_state["propagation_matrix"] = create_propagation_matrix(labels)

    elif list(st.session_state["propagation_matrix"].index) != labels:
        st.session_state["propagation_matrix"] = create_propagation_matrix(labels)

    return st.session_state["propagation_matrix"]

def extract_propagation_paths(sensor_ids, matrix):

    paths = []

    for i in range(len(sensor_ids)):
        for j in range(i + 1, len(sensor_ids)):

            val = matrix.iloc[j, i]

            if pd.notna(val):

                paths.append({
                    "i": sensor_ids[i],
                    "j": sensor_ids[j],
                    "time": float(val)
                })

    return paths