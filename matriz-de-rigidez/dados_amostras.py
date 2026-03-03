# ============================================================
# Arquivo: dados_amostras.py
# Contém o dicionário externo com todas as amostras em SI.
# Você pode editar livremente, adicionar novas amostras, etc.
# ============================================================

dados = {
    "Amostra1": {
        "massa": 85.52e-3,     # kg
        "volume": 1.5304e-4,     # m³

        "medidas": {
            # Direções principais
            "LL":  {"dist": 4.683e-2, "tempo": 10.97e-6},
            "RR":  {"dist": 4.650e-2, "tempo": 21.95e-6},
            "TT":  {"dist": 4.656e-2, "tempo": 26.09e-6},

            # Cisalhamentos nas direções principais
            "LR":  {"dist": 4.683e-2, "tempo": 36.69e-6},
            "LT":  {"dist": 4.683e-2, "tempo": 42.72e-6},
            "RL":  {"dist": 4.650e-2, "tempo": 38.35e-6},
            "RT":  {"dist": 4.650e-2, "tempo": 60.88e-6},
            "TL":  {"dist": 4.656e-2, "tempo": 41.76e-6},
            "TR":  {"dist": 4.656e-2, "tempo": 63.57e-6},

            # Direções oblíquas (ângulo definido no Streamlit)
            "LT1": {"dist": 4.397e-2, "tempo": 37.4e-6},
            "LT2": {"dist": 4.395e-2, "tempo": 37.13e-6},
            "RL1": {"dist": 4.406e-2, "tempo": 34.17e-6},
            "RL2": {"dist": 4.399e-2, "tempo": 34.44e-6},
            "RT1": {"dist": 4.395e-2, "tempo": 39.01e-6},
            "RT2": {"dist": 4.391e-2, "tempo": 39.85e-6}
        }
    },
    "Amostra2": {
        "massa": 85.52e-3,     # kg
        "volume": 1.5304e-4,     # m³

        "medidas": {
            # Direções principais
            "LL":  {"dist": 4.683e-2, "tempo": 10.97e-6},
            "RR":  {"dist": 4.650e-2, "tempo": 21.95e-6},
            "TT":  {"dist": 4.656e-2, "tempo": 26.09e-6},

            # Cisalhamentos nas direções principais
            "LR":  {"dist": 4.683e-2, "tempo": 36.69e-6},
            "LT":  {"dist": 4.683e-2, "tempo": 41.76e-6},
            "RL":  {"dist": 4.650e-2, "tempo": 36.69e-6},
            "RT":  {"dist": 4.650e-2, "tempo": 60.88e-6},
            "TL":  {"dist": 4.656e-2, "tempo": 41.76e-6},
            "TR":  {"dist": 4.656e-2, "tempo": 60.88e-6},

            # Direções oblíquas (ângulo definido no Streamlit)
            "LT1": {"dist": 4.397e-2, "tempo": 37.13e-6},
            "LT2": {"dist": 4.395e-2, "tempo": 37.13e-6},
            "RL1": {"dist": 4.406e-2, "tempo": 34.17e-6},
            "RL2": {"dist": 4.399e-2, "tempo": 34.17e-6},
            "RT1": {"dist": 4.395e-2, "tempo": 39.01e-6},
            "RT2": {"dist": 4.391e-2, "tempo": 39.01e-6}
        }
    },
}