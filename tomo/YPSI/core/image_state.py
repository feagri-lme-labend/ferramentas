import streamlit as st
import hashlib


def reset_if_new_image(uploaded_file):

    file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()

    if st.session_state.get("current_image_hash") != file_hash:


        # limpar estruturas principais
        for k in ["pontos", "resize_applied", "pontos_comparacao"]:
            if k in st.session_state:
                del st.session_state[k]

        st.session_state.current_image_hash = file_hash