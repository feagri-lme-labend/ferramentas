import streamlit as st


def update_polygon_state(n_pontos, w, h, scale_img):

    # -------------------
    # INIT
    # -------------------
    if "pontos" not in st.session_state:
        st.session_state.pontos = [[w//2, h//2] for _ in range(n_pontos)]

    # -------------------
    # RESIZE ADJUST
    # -------------------
    if (
        "pontos" in st.session_state
        and scale_img != 1.0
        and "resize_applied" not in st.session_state
    ):

        novos_pontos = []

        for px, py in st.session_state.pontos:
            novo_x = int(px * scale_img)
            novo_y = int(py * scale_img)
            novos_pontos.append([novo_x, novo_y])

        st.session_state.pontos = novos_pontos
        st.session_state.resize_applied = True

    # -------------------
    # TRACK PREVIOUS N
    # -------------------
    if "n_pontos_prev" not in st.session_state:
        st.session_state.n_pontos_prev = n_pontos

    # -------------------
    # UPDATE IF N CHANGED
    # -------------------
    if st.session_state.n_pontos_prev != n_pontos:

        pontos_antigos = st.session_state.pontos

        if n_pontos > len(pontos_antigos):

            cx = sum(p[0] for p in pontos_antigos) / len(pontos_antigos)
            cy = sum(p[1] for p in pontos_antigos) / len(pontos_antigos)

            novos = []

            for _ in range(n_pontos - len(pontos_antigos)):
                novos.append([int(cx), int(cy)])

            st.session_state.pontos = pontos_antigos + novos

        else:
            st.session_state.pontos = pontos_antigos[:n_pontos]

        st.session_state.n_pontos_prev = n_pontos
  