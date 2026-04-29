import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas


def polygon_canvas(img_np, h, w):

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#ff0000",
        background_image=Image.fromarray(img_np),
        #update_streamlit=True,
        height=h,
        width=w,
        drawing_mode="polygon",
        key="canvas",
    )

    # --- SINCRONIZAÇÃO COM SESSION STATE ---
    if canvas_result.json_data is not None:

        objs = canvas_result.json_data["objects"]


        if len(objs) > 0:

            path = objs[0].get("path", [])

            novos_pontos = []

            for p in path:
                if isinstance(p, list) and len(p) >= 3:
                    novos_pontos.append([int(p[1]), int(p[2])])

            if (
                len(novos_pontos) > 0
                and novos_pontos != st.session_state.get("pontos_comparacao")
            ):

                # atualizar pontos principais
                st.session_state.pontos = novos_pontos
                st.session_state.n_pontos = len(novos_pontos)

                # checkpoint
                st.session_state.pontos_comparacao = novos_pontos

                # sincronizar sliders
                for i, (x, y) in enumerate(novos_pontos):
                    st.session_state[f"x_{i}"] = x
                    st.session_state[f"y_{i}"] = y