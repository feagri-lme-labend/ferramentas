# index2.py
#
# Versão final revisada do app Streamlit:
# - Heatmaps removidos
# - Matriz S mostrada também em LaTeX (convenção L, R, T)
# - Aba "JSON" renomeada para "Dict" e exibe um dict Python com números (floats)
# - Validações exibem emojis: ☑️ para ok e ⛔ para fail
# - Recarregamento automático de dados_amostras.py
# - Validação RÍGIDA por amostra: se faltar qualquer chave obrigatória na amostra selecionada,
#   o cálculo daquela amostra é bloqueado (mensagem) — outras amostras permanecem disponíveis.
# - Exportador global (uma linha por amostra) usando o ângulo atual do slider.
#
ORIGINAL_FILE = "/mnt/data/index1.py"

import streamlit as st
import numpy as np
import pandas as pd
import importlib
import io
import base64
from typing import Tuple, Optional, Dict, List

st.set_page_config(page_title="Matriz de Rigidez — Final", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    .stApp { font-family: "Inter", sans-serif; }
    .kpibox { background: linear-gradient(90deg,#ffffff,#f7fbff); padding:10px; border-radius:8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Utilitários
# ---------------------------
def sci_str(x):
    try:
        return f"{float(x):.6e}"
    except Exception:
        return str(x)

def float_or_nan(s):
    try:
        return float(s)
    except Exception:
        return float('nan')

def download_link_bytes(content: bytes, filename: str, label: str):
    b64 = base64.b64encode(content).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{label}</a>'
    return href

# ---------------------------
# Núcleo de cálculo (mantém a sua lógica)
# ---------------------------
def processar_amostra(dados_amostra, angulo_rad):
    massa = dados_amostra["massa"]
    volume = dados_amostra["volume"]
    rho = massa / volume

    medidas = dados_amostra["medidas"]
    vel = {k: medidas[k]["dist"] / medidas[k]["tempo"] for k in medidas}

    # médias iguais ao index1 original
    V_LL = vel["LL"]
    V_RR = vel["RR"]
    V_TT = vel["TT"]
    V_LR = (vel["LR"] + vel["RL"]) / 2
    V_LT = (vel["LT"] + vel["TL"]) / 2
    V_RT = (vel["RT"] + vel["TR"]) / 2
    V_12a = (vel["RL1"] + vel["RL2"]) / 2
    V_13a = (vel["LT1"] + vel["LT2"]) / 2
    V_23a = (vel["RT1"] + vel["RT2"]) / 2

    # diagonais
    C11 = rho * V_LL**2
    C22 = rho * V_RR**2
    C33 = rho * V_TT**2
    C44 = rho * V_RT**2
    C55 = rho * V_LT**2
    C66 = rho * V_LR**2

    n1 = np.sin(angulo_rad)
    n2 = np.cos(angulo_rad)
    n3 = np.cos(angulo_rad)

    # off-diagonais (mesma equação)
    C12 = (
        np.sqrt(
            (C11*n1**2 + C66*n2**2 - rho*V_12a**2) *
            (C66*n1**2 + C22*n2**2 - rho*V_12a**2)
        ) - C66*n1*n2
    ) / (n1*n2)

    C13 = (
        np.sqrt(
            (C11*n1**2 + C55*n3**2 - rho*V_13a**2) *
            (C55*n1**2 + C33*n3**2 - rho*V_13a**2)
        ) - C55*n1*n3
    ) / (n1*n3)

    C23 = (
        np.sqrt(
            (C22*n2**2 + C44*n3**2 - rho*V_23a**2) *
            (C44*n2**2 + C33*n3**2 - rho*V_23a**2)
        ) - C44*n2*n3
    ) / (n2*n3)

    C = np.array([
        [C11, C12, C13, 0,   0,   0],
        [C12, C22, C23, 0,   0,   0],
        [C13, C23, C33, 0,   0,   0],
        [0,   0,   0,   C44, 0,   0],
        [0,   0,   0,   0,   C55, 0],
        [0,   0,   0,   0,   0,   C66]
    ])

    S = np.linalg.inv(C)

    E = { "L": 1.0/S[0,0], "R": 1.0/S[1,1], "T": 1.0/S[2,2] }
    G = { "RT": 1.0/S[3,3], "LT": 1.0/S[4,4], "LR": 1.0/S[5,5] }
    nu = {
        "LR": -S[0,1]/S[0,0], "LT": -S[0,2]/S[0,0],
        "RL": -S[1,0]/S[1,1], "TL": -S[2,0]/S[2,2],
        "RT": -S[1,2]/S[1,1], "TR": -S[1,2]/S[2,2]
    }

    # return numeric values (floats) for E, G, nu and formatted strings for display in tables where needed
    return {
        "rho": rho,
        "vel": vel,   # floats
        "C": C,
        "S": S,
        "E": E,
        "G": G,
        "nu": nu
    }

# ---------------------------
# Verificação de tempos (reciprocidade e simetria)
# ---------------------------
def verificar_tempos(medidas, limite_alerta=0.10, limite_aviso=0.05):
    """
    Verifica pares de tempos (simetria e reciprocidade) e retorna
    uma lista de tuplas (nome_a, nome_b, erro_relativo, mensagem).
    - medidas: dicionário medidas (cada entrada tem 'dist' e 'tempo')
    - limite_alerta: diferença relativa acima da qual é considerado erro (ex: 0.10 = 10%)
    - limite_aviso: diferença relativa acima da qual é aviso (ex: 0.05 = 5%)
    """

    # pares: (nome1, nome2)
    pares = [
        ("RL1", "RL2"),
        ("LT1", "LT2"),
        ("RT1", "RT2"),
        ("LR", "RL"),
        ("LT", "TL"),
        ("RT", "TR"),
    ]

    mensagens = []

    for a, b in pares:
        if a in medidas and b in medidas:
            t1 = medidas[a].get("tempo", None)
            t2 = medidas[b].get("tempo", None)

            # se qualquer um for None ou não numérico, pula
            try:
                if t1 is None or t2 is None:
                    continue
                t1f = float(t1)
                t2f = float(t2)
            except Exception:
                continue

            # evita divisão por zero
            denom = max(abs(t1f), abs(t2f))
            if denom == 0:
                continue

            erro = abs(t1f - t2f) / denom

            if erro > limite_alerta:
                mensagens.append(
                    (a, b, erro, f"❌ Diferença grande entre {a} ({t1f}) e {b} ({t2f}): erro = {erro*100:.1f}%")
                )
            elif erro > limite_aviso:
                mensagens.append(
                    (a, b, erro, f"⚠️ Diferença moderada entre {a} ({t1f}) e {b} ({t2f}): erro = {erro*100:.1f}%")
                )
            else:
                mensagens.append(
                    (a, b, erro, f"✔️ {a} e {b} coerentes (erro = {erro*100:.1f}%)")
                )

    return mensagens

# ---------------------------
# Função de validação rígida (por amostra) usada tanto na seleção quanto na exportação
# ---------------------------
def validar_amostra_rigida(dados_amostra: dict) -> List[str]:
    """
    Valida a presença de chaves obrigatórias em uma amostra.
    Retorna uma lista de strings com mensagens de erro (vazia se OK).
    """
    erros = []
    if not isinstance(dados_amostra, dict):
        return ["A amostra não é um dicionário válido."]

    chaves_obrigatorias_top = ["massa", "volume", "medidas"]

    chaves_medidas_obrig = [
        "LL","RR","TT",
        "LR","RL","LT","TL","RT","TR",
        "RL1","RL2","LT1","LT2","RT1","RT2"
    ]

    # topo
    for ch in chaves_obrigatorias_top:
        if ch not in dados_amostra:
            erros.append(f"Falta a chave obrigatória: '{ch}'.")

    if "medidas" not in dados_amostra or not isinstance(dados_amostra["medidas"], dict):
        erros.append("Bloco 'medidas' ausente ou inválido.")
        return erros

    medidas = dados_amostra["medidas"]

    # chaves faltantes
    faltando = [k for k in chaves_medidas_obrig if k not in medidas]
    if faltando:
        erros.append("Faltam as seguintes medidas obrigatórias: " + ", ".join(faltando))

    # valida dist/tempo
    for nome in medidas:
        bloco = medidas[nome]
        if not isinstance(bloco, dict):
            erros.append(f"A medida '{nome}' deveria ser um dicionário com 'dist' e 'tempo'.")
            continue

        if "dist" not in bloco or "tempo" not in bloco:
            erros.append(f"A medida '{nome}' está incompleta (precisa ter 'dist' e 'tempo').")
            continue

        try:
            float(bloco["dist"])
            float(bloco["tempo"])
        except Exception:
            erros.append(f"Valores não numéricos em '{nome}': dist={bloco.get('dist')} tempo={bloco.get('tempo')}.")

    return erros

# ---------------------------
# Carregamento automático do arquivo dados_amostras.py
# ---------------------------
try:
    importlib.invalidate_caches()
    dados_mod = importlib.import_module("dados_amostras")
    importlib.reload(dados_mod)
    dados = dados_mod.dados
except Exception as e:
    st.error(f"Erro ao carregar 'dados_amostras.py': {e}")
    st.stop()

# ---------------------------
# Sidebar (controles)
# ---------------------------
with st.sidebar:
    st.markdown("### ⚙️ $\\text{Controles}$")
    st.markdown("---")

    amostras = list(dados.keys())
    if not amostras:
        st.error("Nenhuma amostra encontrada em dados_amostras.py")
        st.stop()

    # selectbox: uma amostra por vez
    amostra_sel = st.selectbox("$\\text{Escolha a amostra}$", amostras, index=0)

    angulo = st.slider("$\\text{Ângulo oblíquo (°)}$", 0.0, 90.0, 45.0)

    st.markdown("---")
    show_equations = st.checkbox("Mostrar equações", value=False)

    st.markdown("---")
    # (opcional) sliders para limites de verificação de tempos
    limite_aviso = st.slider("Limiar aviso (%)", 0.0, 20.0, 5.0) / 100.0
    limite_alerta = st.slider("Limiar erro (%)", 0.0, 50.0, 10.0) / 100.0
    st.caption("Defina os limites relativos para emissão de aviso/erro na verificação de tempos.")

    st.markdown("---")
    if st.button("Exportar resultados (CSV)"):
        export_request = True
    else:
        export_request = False

# ---------------------------
# Processar amostra selecionada (validação RÍGIDA por amostra)
# ---------------------------
angulo_rad = np.deg2rad(angulo)
dados_sel = dados[amostra_sel]

# Validação RÍGIDA por amostra:
erros = validar_amostra_rigida(dados_sel)

# Se houver erros, bloqueamos somente a amostra atual com mensagem clara
if erros:
    st.error(f"❌ A amostra **{amostra_sel}** está incompleta ou inválida:\n\n" + "\n".join("- " + e for e in erros))
    st.stop()

# Se passou na validação rígida, processamos
R = processar_amostra(dados_sel, angulo_rad)

# ---------------------------
# Preparar tabelas e números para validação
# ---------------------------
C = R["C"]
S = R["S"]

# Extract scalar C values
C11 = float(C[0,0]); C22 = float(C[1,1]); C33 = float(C[2,2])
C44 = float(C[3,3]); C55 = float(C[4,4]); C66 = float(C[5,5])
C12 = float(C[0,1]); C13 = float(C[0,2]); C23 = float(C[1,2])

# Validation checks (user-specified monotonic order constraints)
valid_C11_gt = C11 > C22 > C33
valid_C44_lt = C44 < C55 < C66
valid_C12_gt   = C12 > C13 > C23

# Also check basic positivity
basic_positive = all(v > 0 for v in [C11, C22, C33, C44, C55, C66])

# Check principal minors (informational)
minor12 = C11 * C22 - C12**2
minor13 = C11 * C33 - C13**2
minor23 = C22 * C33 - C23**2


# ---------------------------
# Layout principal
# ---------------------------
st.markdown("# 📐 $\\text{Matriz de Rigidez}$")

# top KPI row
col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
col1.metric("$E_{L}$ (GPa)", f"{R['E']['L']:.3e}")
col2.metric("$E_{R}$ (GPa)", f"{R['E']['R']:.3e}")
col3.metric("$E_{T}$ (GPa)", f"{R['E']['T']:.3e}")
col4.metric("$\\rho$ (kg/m³)", f"{R['rho']:.3f}")
col5.metric("$G_{LR}$ (GPa)", f"{R['G']['LR']:.3e}")

st.markdown("---")

# Tabs
tab_vel, tab_C, tab_S, tab_props, tab_dict = st.tabs(["$\\text{Velocidades}$","$\\text{Matriz C}$","$\\text{Matriz S}$","$\\text{Propriedades}$","$\\text{Dict}$"])

# ---------- Velocidades ----------
with tab_vel:
    st.markdown("$\\text{Velocidades (m/s)}$")
    df_vel = pd.DataFrame.from_dict(R["vel"], orient="index", columns=["Velocidade (m/s)"])
    # show with scientific format
    st.dataframe(df_vel.style.format("{:.6e}"), width="stretch")

    # --- Verificação de tempos ---
    st.markdown("### ⏱️ Validação dos Tempos (Simetria e Reciprocidade)")

    try:
        avisos = verificar_tempos(dados_sel["medidas"], limite_alerta=limite_alerta, limite_aviso=limite_aviso)
    except Exception:
        avisos = []

    # Construção da tabela consolidada
    linhas = []

    for a, b, erro, msg in avisos:
        # Determinar status
        if "❌" in msg:
            status = "ERRO"
        elif "⚠️" in msg:
            status = "AVISO"
        else:
            status = "OK"

        linhas.append({
            "Par": f"{a} – {b}",
            "Erro relativo (%)": round(erro * 100, 3),
            "Status": status,
            "Mensagem": msg
        })

    if not linhas:
        st.info("Nenhum par válido de tempos encontrado para validação.")
    else:
        df_valid = pd.DataFrame(linhas)
        # Ordenar: ERRO → AVISO → OK
        df_valid["ord"] = df_valid["Status"].map({"ERRO": 0, "AVISO": 1, "OK": 2})
        df_valid = df_valid.sort_values("ord").drop(columns="ord")

        st.dataframe(df_valid, width="stretch")


# ---------- Matriz C ----------
with tab_C:
    st.markdown("$\\text{Matriz C (Pa)}$")
    df_C = pd.DataFrame(C,
                        columns=["σ_L","σ_R","σ_T","τ_RT","τ_LT","τ_LR"],
                        index=["ε_L","ε_R","ε_T","γ_RT","γ_LT","γ_LR"])
    st.dataframe(df_C.style.format("{:.6e}"), width="stretch")

    # Validations summary for C with emojis
    st.markdown("###### $\\text{Validações (ordenamentos requeridos)}$")
    cols = st.columns(3)
    cols[0].markdown("$C_{11} > C_{22} > C_{33}$: " + f"{'☑️' if valid_C11_gt else '⛔'}")
    cols[1].write("$C_{44} < C_{55} < C_{66}$: " + f"{'☑️' if valid_C44_lt else '⛔'}")
    cols[2].write("$C_{12} > C_{13} > C_{23}$: " + f"{'☑️' if valid_C12_gt else '⛔'}")

    # Basic positivity
    if not basic_positive:
        st.error("Algumas componentes diagonais Cii não são positivas — verificar medições.")
    else:
        st.success("Componentes diagonais Cii positivas.")

    if show_equations:
        st.markdown("###### $\\text{Equações usadas para C (origem)}$")
        st.latex(r"""
        C_{11} = \rho V_{LL}^2,\quad
        C_{22} = \rho V_{RR}^2,\quad
        C_{33} = \rho V_{TT}^2
        """)
        st.latex(r"""
        C_{44} = \rho V_{RT}^2,\quad
        C_{55} = \rho V_{LT}^2,\quad
        C_{66} = \rho V_{LR}^2
        """)
        st.latex(r"""
        C_{12} = \frac{\sqrt{(C_{11}n_1^2 + C_{66}n_2^2 - \rho V_{12}^2)(C_{66}n_1^2 + C_{22}n_2^2 - \rho V_{12}^2)} - C_{66}n_1 n_2}{n_1 n_2}
        """)
        st.latex(r" \text{(equivalente para } C_{13}\text{ e } C_{23}\text{)}")

# ---------- Matriz S ----------
with tab_S:
    st.markdown("$S = C^{-1}\\,\\text{(Pa⁻¹)}$")
    df_S = pd.DataFrame(S,
                        columns=["σ_L","σ_R","σ_T","τ_RT","τ_LT","τ_LR"],
                        index=["ε_L","ε_R","ε_T","γ_RT","γ_LT","γ_LR"])
    st.dataframe(df_S.style.format("{:.6e}"), width="stretch")

    # Show S in LaTeX using the L,R,T convention provided by the user
    if show_equations:
        st.markdown("### Matriz de Flexibilidade S em função das propriedades (L,R,T)")
        st.latex(r"""
        \mathbf{S}= 
        \begin{bmatrix}
        \dfrac{1}{E_{L}} & -\dfrac{\nu_{RL}}{E_{R}} & -\dfrac{\nu_{TL}}{E_{T}} & 0 & 0 & 0 \\[8pt]
        -\dfrac{\nu_{LR}}{E_{L}} & \dfrac{1}{E_{R}} & -\dfrac{\nu_{TR}}{E_{T}} & 0 & 0 & 0 \\[8pt]
        -\dfrac{\nu_{LT}}{E_{L}} & -\dfrac{\nu_{RT}}{E_{R}} & \dfrac{1}{E_{T}} & 0 & 0 & 0 \\[8pt]
        0 & 0 & 0 & \dfrac{1}{G_{RT}} & 0 & 0 \\[8pt]
        0 & 0 & 0 & 0 & \dfrac{1}{G_{LT}} & 0 \\[8pt]
        0 & 0 & 0 & 0 & 0 & \dfrac{1}{G_{LR}}
        \end{bmatrix}
        """)

# ---------- Propriedades ----------
with tab_props:
    st.markdown("#### $\\text{Propriedades mecânicas}$")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("###### $\\text{Módulos de Young (Pa)}$")
        dfE = pd.DataFrame({k:[v] for k,v in R["E"].items()}).T.rename(columns={0:"E (Pa)"})
        st.table(dfE.style.format("{:.6e}"))
        st.markdown("###### $\\text{Módulos de Cisalhamento (Pa)}$")
        dfG = pd.DataFrame({k:[v] for k,v in R["G"].items()}).T.rename(columns={0:"G (Pa)"})
        st.table(dfG.style.format("{:.6e}"))
    with colB:
        st.markdown("###### $\\text{Coeficientes de Poisson}$")
        dfnu = pd.DataFrame({k:[v] for k,v in R["nu"].items()}).T.rename(columns={0:"ν"})
        st.table(dfnu.style.format("{:.6e}"))
        st.markdown("$\\text{Densidade}\\,(\\text{kg/m}^{3}):\\,$" + f"{R['rho']:.6e}")

    # Validations results with emojis
    st.markdown("### $\\text{Resultado das validações de rigidez}$")
    valrows = {
        "$C_{11} > C_{22} > C_{33}$": "☑️" if valid_C11_gt else "⛔",
        "$C_{44} < C_{55} < C_{66}$": "☑️" if valid_C44_lt else "⛔",
        "$C_{12} > C_{13} > C_{23}$": "☑️" if valid_C12_gt else "⛔",
        "$C_{ii} > 0\\,\\text{(diagonais)}$": "☑️" if basic_positive else "⛔",
    }
    df_val = pd.DataFrame.from_dict(valrows, orient="index", columns=["Resultado"])
    st.table(df_val)

# ---------- Dict tab (Python dict with numeric values) ----------
with tab_dict:
    st.markdown("#### $\\text{Dicionário com propriedades (valores numéricos)}$")
    # Build numeric dict
    dict_out = {
        "rho": R["rho"],
        "E": {"L": R["E"]["L"], "R": R["E"]["R"], "T": R["E"]["T"]},
        "G": {"RT": R["G"]["RT"], "LT": R["G"]["LT"], "LR": R["G"]["LR"]},
        "nu": {"LR": R["nu"]["LR"], "LT": R["nu"]["LT"], "RL": R["nu"]["RL"],
               "TL": R["nu"]["TL"], "RT": R["nu"]["RT"], "TR": R["nu"]["TR"]}
    }

    # Display as a python code block but with numeric literals (not strings)
    resultado_python = "resultado = {\n"
    resultado_python += f"    'rho': {dict_out['rho']:.6e},\n"
    resultado_python += "    'E': {\n"
    resultado_python += f"        'L': {dict_out['E']['L']:.6e}, 'R': {dict_out['E']['R']:.6e}, 'T': {dict_out['E']['T']:.6e}\n"
    resultado_python += "    },\n"
    resultado_python += "    'G': {\n"
    resultado_python += f"        'RT': {dict_out['G']['RT']:.6e}, 'LT': {dict_out['G']['LT']:.6e}, 'LR': {dict_out['G']['LR']:.6e}\n"
    resultado_python += "    },\n"
    resultado_python += "    'nu': {\n"
    resultado_python += f"        'LR': {dict_out['nu']['LR']:.6e}, 'LT': {dict_out['nu']['LT']:.6e}, 'RL': {dict_out['nu']['RL']:.6e},\n"
    resultado_python += f"        'TL': {dict_out['nu']['TL']:.6e}, 'RT': {dict_out['nu']['RT']:.6e}, 'TR': {dict_out['nu']['TR']:.6e}\n"
    resultado_python += "    }\n"
    resultado_python += "}\n"

    st.code(resultado_python, language="python")

# ---------------------------
# EXPORTADOR GLOBAL (UMA LINHA POR AMOSTRA, USANDO ANGULO ATUAL)
# ---------------------------
def safe_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

def montar_linha_completa(nome_amostra: str, dados_amostra: dict, angulo_rad: float, limite_aviso: float, limite_alerta: float):
    """
    Gera uma linha completa para o CSV. Se amostra inválida, inclui validation_errors e validacao_ok=False.
    """
    linha = {}
    linha["amostra"] = nome_amostra

    # validar amostra
    erros = validar_amostra_rigida(dados_amostra)
    if erros:
        # preenche campos básicos e devolve o erro na linha
        linha["validacao_ok"] = False
        linha["validation_errors"] = " | ".join(erros)
        # ainda incluo massa/volume se existirem
        linha["massa"] = safe_float(dados_amostra.get("massa", np.nan))
        linha["volume"] = safe_float(dados_amostra.get("volume", np.nan))
        linha["rho"] = np.nan
        # preencher tempos/distâncias se possível
        medidas = dados_amostra.get("medidas", {}) if isinstance(dados_amostra, dict) else {}
        for chave in medidas:
            md = medidas.get(chave, {})
            linha[f"t_{chave}"] = md.get("tempo", np.nan)
            linha[f"d_{chave}"] = md.get("dist", np.nan)
        # preencher colunas padrões com NaN (C,S,E,G,nu,vel etc)
        # We'll fill them later uniformly when building df, but here just return.
        return linha

    # se validou OK
    linha["validacao_ok"] = True
    linha["validation_errors"] = ""

    # massa/volume/rho
    linha["massa"] = safe_float(dados_amostra["massa"])
    linha["volume"] = safe_float(dados_amostra["volume"])
    try:
        linha["rho"] = float(dados_amostra["massa"]) / float(dados_amostra["volume"])
    except Exception:
        linha["rho"] = np.nan

    # tempos/distâncias brutos
    medidas = dados_amostra["medidas"]
    for chave, md in medidas.items():
        linha[f"t_{chave}"] = md.get("tempo", np.nan)
        linha[f"d_{chave}"] = md.get("dist", np.nan)

    # tenta processar a amostra com o ângulo fornecido
    try:
        resultados = processar_amostra(dados_amostra, angulo_rad)
    except Exception as e:
        # erro no processamento (p.ex. raiz negativa), marcar como inválida mas incluir mensagem
        linha["validacao_ok"] = False
        linha["validation_errors"] = f"Erro no processamento: {e}"
        return linha

    vel = resultados.get("vel", {})
    # Velocidades
    for k, v in vel.items():
        linha[f"V_{k}"] = safe_float(v)

    # Médias internas
    def safe_avg_names(a, b):
        return (vel.get(a, np.nan) + vel.get(b, np.nan)) / 2 if (a in vel and b in vel) else np.nan

    linha["V_66"] = safe_avg_names("LR", "RL")
    linha["V_55"] = safe_avg_names("LT", "TL")
    linha["V_44"] = safe_avg_names("RT", "TR")
    linha["V_12"] = safe_avg_names("RL1", "RL2")
    linha["V_13"] = safe_avg_names("LT1", "LT2")
    linha["V_23"] = safe_avg_names("RT1", "RT2")

    # Matriz C
    C = resultados.get("C", None)
    if C is not None:
        for i in range(6):
            for j in range(6):
                linha[f"C{i+1}{j+1}"] = safe_float(C[i, j])
    else:
        for i in range(6):
            for j in range(6):
                linha[f"C{i+1}{j+1}"] = np.nan

    # Matriz S
    S = resultados.get("S", None)
    if S is not None:
        for i in range(6):
            for j in range(6):
                linha[f"S{i+1}{j+1}"] = safe_float(S[i, j])
    else:
        for i in range(6):
            for j in range(6):
                linha[f"S{i+1}{j+1}"] = np.nan

    # Propriedades E,G,nu
    E = resultados.get("E", {})
    for k in ("L", "R", "T"):
        linha[f"E_{k}"] = safe_float(E.get(k, np.nan))

    G = resultados.get("G", {})
    for k in ("RT", "LT", "LR"):
        linha[f"G_{k}"] = safe_float(G.get(k, np.nan))

    nu = resultados.get("nu", {})
    for k in ("LR","LT","RL","TL","RT","TR"):
        linha[f"nu_{k}"] = safe_float(nu.get(k, np.nan))

    # Erros relativos dos pares de tempos (usar mesma função verificar_tempos)
    avisos = verificar_tempos(medidas, limite_alerta=limite_alerta, limite_aviso=limite_aviso)
    pares_esperados = [
        ("RL1", "RL2"),
        ("LT1", "LT2"),
        ("RT1", "RT2"),
        ("LR", "RL"),
        ("LT", "TL"),
        ("RT", "TR"),
    ]
    # inicializa com NaN
    for a, b in pares_esperados:
        linha[f"erro_{a}_{b}"] = np.nan

    for a, b, erro, msg in avisos:
        linha[f"erro_{a}_{b}"] = safe_float(erro)

    return linha

if export_request:
    lista = []
    # percorre todas as amostras e monta linha
    for nome_amostra, dados_amostra in dados.items():
        try:
            linha = montar_linha_completa(nome_amostra, dados_amostra, angulo_rad, limite_aviso, limite_alerta)
            lista.append(linha)
        except Exception as e:
            # Em caso extremo, adicionar linha com erro
            lista.append({
                "amostra": nome_amostra,
                "validacao_ok": False,
                "validation_errors": f"Erro inesperado durante export: {e}"
            })

    if not lista:
        st.error("Nenhuma amostra pôde ser exportada.")
    else:
        df_export = pd.DataFrame(lista)
        # Garantir colunas ordenadas (amostra, validacao_ok, validation_errors, massa, volume, rho, ...)
        # Construir lista de colunas padrão para melhor legibilidade
        cols_order = ["amostra", "validacao_ok", "validation_errors", "massa", "volume", "rho"]
        # tempos/distâncias
        # reunir todas chaves t_*/d_* presentes no df
        others = [c for c in df_export.columns if c not in cols_order]
        cols_final = cols_order + sorted(others)
        df_export = df_export.reindex(columns=cols_final)
        b = df_export.to_csv(index=False).encode("utf-8")
        st.markdown(download_link_bytes(b, "amostras_completas.csv", "📥 Download — CSV Completo"), unsafe_allow_html=True)

st.markdown("---")
