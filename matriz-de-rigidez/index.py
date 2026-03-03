import streamlit as st
import pandas as pd
import numpy as np
import warnings
from poliedro import create_polyhedron_figure

# Ignorar FutureWarning do Pandas/NumPy no Streamlit
warnings.filterwarnings("ignore", category=FutureWarning)

mathematica_code = """
(* Definição de constantes e dimensões em mm *)
Lmenor = {L_MENOR_FIXO};
Htronco = {H_TRONCO_FIXO};
Hprisma = {H_PRISMA_FIXO};

(* Lmaior é forçado para ser a altura do prisma, para que as faces do prisma sejam quadradas *)
Lmaior = Hprisma;

(* Raio do Octógono (Circunraio R = L / (2 Sin[Pi/8])) *)
R[L_] := L / (2 Sin[Pi/8]);
Rmenor = R[Lmenor]; (* {poly_dims['R_menor']:.4f} mm *)
Rmaior = R[Lmaior]; (* {poly_dims['R_maior']:.4f} mm *)

(* Alturas Z dos 4 anéis de 8 vértices *)
Z1 = 0;
Z2 = Htronco; (* {H_TRONCO_FIXO:.1f} *)
Z3 = Htronco + Hprisma; (* {H_TRONCO_FIXO + H_PRISMA_FIXO:.1f} *)
Z4 = 2 Htronco + Hprisma; (* {poly_dims['Z4']:.1f} *)

(* Geração de coordenadas para um octógono de raio R no plano XY *)
Vcoord[R_, Z_] := Table[
    {{N[R Cos[phi]], N[R Sin[phi]], Z}},
    {{phi, N[Pi/8], N[2 Pi - Pi/8], N[Pi/4]}}
];

(* As 32 Coordenadas dos Vértices *)
vertices = Join[
    Vcoord[Rmenor, Z1],  (* V1 a V8: Base Menor, Z=0 *)
    Vcoord[Rmaior, Z2],  (* V9 a V16: Seção Maior Inferior, Z={H_TRONCO_FIXO:.1f} *)
    Vcoord[Rmaior, Z3],  (* V17 a V24: Seção Maior Superior, Z={H_TRONCO_FIXO + H_PRISMA_FIXO:.1f} *)
    Vcoord[Rmenor, Z4]   (* V25 a V32: Topo Menor, Z={poly_dims['Z4']:.1f} *)
];

(* Lista de Faces (2 Octogonais + 24 Quadrilaterais) *)
faces = Join[
    (* F1: Base Octogonal Menor (V1-V8) *)
    {{Range[8]}},
    (* F2: Topo Octogonal Menor (V25-V32) *)
    {{Range[25, 32]}},
    
    (* F3-F10: Tronco Inferior (V1-V8 para V9-V16) *)
    Table[{{i, i + 8, If[i < 8, i + 9, 9], If[i < 8, i + 1, 1]}}, {{i, 1, 8}}],
    (* F11-F18: Prisma Central (V9-V16 para V17-V24) - Retângulos *)
    Table[{{i + 8, i + 16, If[i < 8, i + 17, 17], If[i < 8, i + 9, 9]}}, {{i, 1, 8}}],
    (* F19-F26: Tronco Superior (V17-V24 para V25-V32) *)
    Table[{{i + 16, i + 24, If[i < 8, i + 25, 25], If[i < 8, i + 17, 17]}}, {{i, 1, 8}}]
];

(* Comando de Renderização do Poliedro no Mathematica *)
Polyhedron[vertices, faces,
    PlotLabel -> "Poliedro de 26 Faces (Tronco-Prisma-Tronco)",
    Boxed -> True,
    FaceGrids -> All
]
"""

# --- Configurações Iniciais do Streamlit ---
st.set_page_config(layout="wide", page_title="Calculadora de Propriedades Elásticas Editável e Diagnóstica")
st.title("🔬 Análise Interativa de Propriedades Elásticas de Madeira")
st.write("Carregue seu CSV contendo **Distância (cm)** e **Tempo (μs)**. A velocidade será calculada. Edite os dados e visualize os resultados no formato de sua preferência (Tabela ou Matriz LaTeX).")

L_MENOR_FIXO = 10.8  # Aresta da Base Menor
H_TRONCO_FIXO = 18.4  # Altura do Tronco de Pirâmide
H_PRISMA_FIXO = 25.0  # Altura do Prisma Central
BASE_COLOR = 'magenta'   # Cor uniforme

poly_fig, poly_dims = create_polyhedron_figure(
    L_menor=L_MENOR_FIXO, 
    H_tronco=H_TRONCO_FIXO, 
    H_prisma=H_PRISMA_FIXO,
    base_color=BASE_COLOR
)

# Lista de todas as direções de velocidade necessárias (Base para o diagnóstico de dados)
DIRECOES_NECESSARIAS = [
    'LL', 'RR', 'TT',
    'LR', 'RL', 'LT', 'TL', 'RT', 'TR',
    'RL2', 'RT1', 'RT2', 'TL1', 'TL2'
]

# --- FUNDAMENTAÇÃO TEÓRICA (NOVA SEÇÃO COM TABELAS) ---
with st.expander("📚 Fundamentação Teórica do Cálculo Ortotrópico", expanded=False):
    st.markdown("""
    O cálculo das 9 Constantes Elásticas de um material ortotrópico (como a madeira) pelo método ultrassônico é baseado na solução das **Equações de Christoffel**, que relacionam a densidade ($\\rho$), a velocidade de propagação da onda ($V$) e os Coeficientes de Rigidez ($\\mathbf{C}_{ij}$). Os eixos de ortotropia são: Longitudinal ($X_1$), Radial ($X_2$) e Tangencial ($X_3$).
    """)

    # 3. Exibe o gráfico no Streamlit
    with st.expander("Script Wolfram", expanded=False):
        st.code(mathematica_code, language='wolfram')
    st.plotly_chart(poly_fig) 

    st.markdown("#### Relações do Método de Christoffel: Ondas Puras e Mistas")
    st.markdown("Esta tabela detalha as relações entre a direção de propagação ($X_i$), a polarização ($p_i$), e as expressões de velocidade para as ondas puras (Longitudinais $L$ e Transversais $T$) e mistas (Quase-Longitudinais $Q_L$ e Quase-Transversais $Q_T$).")

    # Tabela de Relações de Christoffel (FORNECIDA PELO USUÁRIO)
    data_christoffel = [
        {"Direção de Propagação": "$X_1$", "Componente Normal": "$n_1=1$", "Direção da polarização": "$X_1$", "Tipo": "$L$", "Velocidade": "$C_{11}=\\rho V_{11}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_2=0$", "Direção da polarização": "$X_2$", "Tipo": "$T$", "Velocidade": "$C_{66}=\\rho V_{66}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_3=0$", "Direção da polarização": "$X_3$", "Tipo": "$T$", "Velocidade": "$C_{55}=\\rho V_{55}^{2}$"},

        {"Direção de Propagação": "$X_2$", "Componente Normal": "$n_1=0$", "Direção da polarização": "$X_1$", "Tipo": "$T$", "Velocidade": "$C_{66}=\\rho V_{66}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_2=1$", "Direção da polarização": "$X_2$", "Tipo": "$L$", "Velocidade": "$C_{22}=\\rho V_{22}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_3=0$", "Direção da polarização": "$X_3$", "Tipo": "$T$", "Velocidade": "$C_{44}=\\rho V_{44}^{2}$"},

        {"Direção de Propagação": "$X_3$", "Componente Normal": "$n_1=0$", "Direção da polarização": "$X_1$", "Tipo": "$T$", "Velocidade": "$C_{55}=\\rho V_{55}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_2=0$", "Direção da polarização": "$X_2$", "Tipo": "$T$", "Velocidade": "$C_{44}=\\rho V_{44}^{2}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_3=1$", "Direção da polarização": "$X_3$", "Tipo": "$L$", "Velocidade": "$C_{33}=\\rho V_{33}^{2}$"},

        {"Direção de Propagação": "$X_1,X_2$", "Componente Normal": "$n_1,n_2$", 
        "Direção da polarização": "$\\dfrac{p_1}{p_2}=\\dfrac{\\Gamma_{12}}{\\rho V^2-\\Gamma_{11}}=\\dfrac{\\rho V^2-\\Gamma_{22}}{\\Gamma_{12}}$", 
        "Tipo": "$Q_L,Q_T$", 
        "Velocidade": "$2V_{Q_L,Q_T}^{2}\\rho=(\\Gamma_{11}+\\Gamma_{22})\\pm\\sqrt{(\\Gamma_{11}-\\Gamma_{22})^2+4\\Gamma_{12}^{2}}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_3=0$", "Direção da polarização": "$X_3$", "Tipo": "$T$", "Velocidade": "$\\rho V_T^2=\\Gamma_{33}$"},

        {"Direção de Propagação": "$X_1,X_3$", "Componente Normal": "$n_1,n_3$", 
        "Direção da polarização": "$\\dfrac{p_1}{p_3}=\\dfrac{\\Gamma_{13}}{\\rho V^2-\\Gamma_{11}}=\\dfrac{\\rho V^2-\\Gamma_{33}}{\\Gamma_{13}}$", 
        "Tipo": "$Q_L,Q_T$", 
        "Velocidade": "$2V_{Q_L,Q_T}^{2}\\rho=(\\Gamma_{11}+\\Gamma_{33})\\pm\\sqrt{(\\Gamma_{11}-\\Gamma_{33})^2+4\\Gamma_{13}^{2}}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_2=0$", "Direção da polarização": "$X_2$", "Tipo": "$T$", "Velocidade": "$\\rho V_T^2=\\Gamma_{22}$"},

        {"Direção de Propagação": "$X_2,X_3$", "Componente Normal": "$n_2,n_3$", 
        "Direção da polarização": "$\\dfrac{p_2}{p_3}=\\dfrac{\\Gamma_{23}}{\\rho V^2-\\Gamma_{22}}=\\dfrac{\\rho V^2-\\Gamma_{33}}{\\Gamma_{23}}$", 
        "Tipo": "$Q_L,Q_T$", 
        "Velocidade": "$2V_{Q_L,Q_T}^{2}\\rho=(\\Gamma_{22}+\\Gamma_{33})\\pm\\sqrt{(\\Gamma_{22}-\\Gamma_{33})^2+4\\Gamma_{23}^{2}}$"},
        {"Direção de Propagação": "", "Componente Normal": "$n_1=0$", "Direção da polarização": "$X_1$", "Tipo": "$T$", "Velocidade": "$\\rho V_T^2=\\Gamma_{11}$"},
    ]
    
    st.table(data_christoffel)
    
    data_christoffel = [
        {
            "": "$\\Gamma_{11} =$",
            "$n_{1}^{2}$": "$C_{11}$",
            "$n_{2}^{2}$": "$C_{66}$",
            "$n_{3}^{2}$": "$C_{55}$",
            "$2n_{2}n_{3}$": "$C_{56}$",
            "$2n_{1}n_{3}$": "$C_{15}$",
            "$2n_{1}n_{2}$": "$C_{16}$"
        },
        {
            "": "$\\Gamma_{22} =$",
            "$n_{1}^{2}$": "$C_{66}$",
            "$n_{2}^{2}$": "$C_{22}$",
            "$n_{3}^{2}$": "$C_{44}$",
            "$2n_{2}n_{3}$": "$C_{24}$",
            "$2n_{1}n_{3}$": "$C_{46}$",
            "$2n_{1}n_{2}$": "$C_{26}$"
        },
        {
            "": "$\\Gamma_{33} =$",
            "$n_{1}^{2}$": "$C_{55}$",
            "$n_{2}^{2}$": "$C_{44}$",
            "$n_{3}^{2}$": "$C_{33}$",
            "$2n_{2}n_{3}$": "$C_{34}$",
            "$2n_{1}n_{3}$": "$C_{35}$",
            "$2n_{1}n_{2}$": "$C_{45}$"
        },
        {
            "": "$\\Gamma_{12} =$",
            "$n_{1}^{2}$": "$C_{16}$",
            "$n_{2}^{2}$": "$C_{26}$",
            "$n_{3}^{2}$": "$C_{45}$",
            "$2n_{2}n_{3}$": "$\\dfrac{1}{2}(C_{25}+C_{46})$",
            "$2n_{1}n_{3}$": "$\\dfrac{1}{2}(C_{14}+C_{56})$",
            "$2n_{1}n_{2}$": "$\\dfrac{1}{2}(C_{12}+C_{66})$",
        },
        {
            "": "$\\Gamma_{13} =$",
            "$n_{1}^{2}$": "$C_{15}$",
            "$n_{2}^{2}$": "$C_{46}$",
            "$n_{3}^{2}$": "$C_{35}$",
            "$2n_{2}n_{3}$": "$\\dfrac{1}{2}(C_{36}+C_{45})$",
            "$2n_{1}n_{3}$": "$\\dfrac{1}{2}(C_{13}+C_{55})$",
            "$2n_{1}n_{2}$": "$\\dfrac{1}{2}(C_{14}+C_{56})$",
        },
        {
            "": "$\\Gamma_{23} =$",
            "$n_{1}^{2}$": "$C_{56}$",
            "$n_{2}^{2}$": "$C_{24}$",
            "$n_{3}^{2}$": "$C_{34}$",
            "$2n_{2}n_{3}$": "$\\dfrac{1}{2}(C_{23}+C_{44})$",
            "$2n_{1}n_{3}$": "$\\dfrac{1}{2}(C_{36}+C_{45})$",
            "$2n_{1}n_{2}$": "$\\dfrac{1}{2}(C_{25}+C_{46})$",
        }
    ]

    st.markdown(":material/search: Equações de Christoffel")
    st.table(data_christoffel)

    st.markdown("---")

    st.markdown("#### Coeficientes de Rigidez Derivados da Velocidade Pura")
    st.markdown("Os coeficientes da Matriz de Rigidez ($\\mathbf{C}_{ij}$) são obtidos diretamente das velocidades de ondas puras ($V_{ij}$), conforme o método de determinação dos termos $\\Gamma_{ij} =$ para ondas mistas:")
    
    # Tabela 4.38 Consolidada (simplificada a partir da anterior)
    teoria_data_438_simplificada = [
        {"Coeficiente": "$C_{11}$", "Expressão": r"$\rho V_{11}^{2}$", "Velocidade Medida": "$V_{LL}$"},
        {"Coeficiente": "$C_{22}$", "Expressão": r"$\rho V_{22}^{2}$", "Velocidade Medida": "$V_{RR}$"},
        {"Coeficiente": "$C_{33}$", "Expressão": r"$\rho V_{33}^{2}$", "Velocidade Medida": "$V_{TT}$"},
        {"Coeficiente": "$C_{44}$", "Expressão": r"$\rho V_{23}^{2}$", "Velocidade Medida": "$V_{RT}$"},
        {"Coeficiente": "$C_{55}$", "Expressão": r"$\rho V_{13}^{2}$", "Velocidade Medida": "$V_{LT}$"},
        {"Coeficiente": "$C_{66}$", "Expressão": r"$\rho V_{12}^{2}$", "Velocidade Medida": "$V_{LR}$"},
        {"Coeficiente": "$C_{12}$", "Expressão": r"$\dfrac{+\sqrt{(C_{11}n_{1}^{2}+C_{66}n_{2}^{2}-\rho V^{2})(C_{66}n_{1}^{2}+C_{22}n_{2}^{2}-\rho V^{2})}-C_{66}n_{1}n_{2}}{n_{1}n_{2}}$", "Velocidade Medida": "$(V_{Q_{L}})_{RL}$"},
        {"Coeficiente": "$C_{12}$", "Expressão": r"$\dfrac{-\sqrt{(C_{11}n_{1}^{2}+C_{66}n_{2}^{2}-\rho V^{2})(C_{66}n_{1}^{2}+C_{22}n_{2}^{2}-\rho V^{2})}-C_{66}n_{1}n_{2}}{n_{1}n_{2}}$", "Velocidade Medida": "$(V_{Q_{T}})_{RL}$"},
        {"Coeficiente": "$C_{13}$", "Expressão": r"$\dfrac{+\sqrt{(C_{11}n_{1}^{2}+C_{55}n_{3}^{2}-\rho V^{2})(C_{55}n_{1}^{2}+C_{33}n_{3}^{2}-\rho V^{2})}-C_{55}n_{1}n_{3}}{n_{1}n_{3}}$", "Velocidade Medida": "$(V_{Q_{L}})_{RT}$"},
        {"Coeficiente": "$C_{13}$", "Expressão": r"$\dfrac{-\sqrt{(C_{11}n_{1}^{2}+C_{55}n_{3}^{2}-\rho V^{2})(C_{55}n_{1}^{2}+C_{33}n_{3}^{2}-\rho V^{2})}-C_{55}n_{1}n_{3}}{n_{1}n_{3}}$", "Velocidade Medida": "$(V_{Q_{T}})_{RT}$"},
        {"Coeficiente": "$C_{23}$", "Expressão": r"$\dfrac{+\sqrt{(C_{22}n_{2}^{2}+C_{44}n_{3}^{2}-\rho V^{2})(C_{44}n_{2}^{2}+C_{33}n_{3}^{2}-\rho V^{2})}-C_{44}n_{2}n_{3}}{n_{2}n_{3}}$", "Velocidade Medida": "$(V_{Q_{L}})_{LT}$"},
        {"Coeficiente": "$C_{23}$", "Expressão": r"$\dfrac{-\sqrt{(C_{22}n_{2}^{2}+C_{44}n_{3}^{2}-\rho V^{2})(C_{44}n_{2}^{2}+C_{33}n_{3}^{2}-\rho V^{2})}-C_{44}n_{2}n_{3}}{n_{2}n_{3}}$", "Velocidade Medida": "$(V_{Q_{T}})_{LT}$"}

    ]
    st.table(teoria_data_438_simplificada)
    
    st.markdown("---")
    st.markdown("#### 3. Cálculo das Constantes Elásticas Fundamentais")
    st.markdown("Uma vez calculada a Matriz de Rigidez ($\\mathbf{C}_{ij}$), a Matriz de Flexibilidade ($\\mathbf{S}_{ij}$) é obtida pela sua inversa, e as 9 constantes elásticas são derivadas das seguintes relações:")
    
    st.latex(r"\mathbf{S}_{ij} = [\mathbf{C}_{ij}]^{-1}")
    st.latex(r"E_i = \frac{1}{S_{ii}}")
    st.latex(r"G_{ij} = \frac{1}{S_{kl}} \quad (\text{para } i, j=1, 2, 3 \text{ e } k, l=4, 5, 6)")
    st.latex(r"\nu_{ij} = -E_i \cdot S_{ij}")

st.sidebar.markdown("---") # Separador visual

# --- Funções Auxiliares e de Cálculo ---

def to_latex_matrix(np_array, precision=2, is_flexibility=False):
    """
    Converte uma matriz numpy 6x6 em uma string de matriz LaTeX.
    """
    lines = []
    
    if is_flexibility:
        # Usa notação científica para a matriz de flexibilidade (valores tipicamente pequenos)
        formatter = lambda x: f'{x:.{precision}e}'.replace('e', r' \cdot 10^{').replace('+', '').replace('-', '{-}') + '}'
    else:
        # Usa notação de ponto flutuante para a matriz de rigidez
        formatter = lambda x: f'{x:.{precision}f}'
        
    for row in np_array:
        formatted_row = [formatter(val) for val in row]
        lines.append(' & '.join(formatted_row) + r' \\')
        
    latex_string = r'\begin{bmatrix}' + '\n' + '\n'.join(lines) + '\n' + r'\end{bmatrix}'
    return latex_string

def verificar_dados_amostra(df_amostra):
    """Verifica se todos os dados necessários para o cálculo ortotrópico estão presentes."""
    direcoes_presentes = set(df_amostra['Direção'].unique())
    faltando_direcoes = [d for d in DIRECOES_NECESSARIAS if d not in direcoes_presentes]
    
    # Verifica a consistência da densidade. Se for inconsistente, adiciona ao erro.
    if df_amostra['Densidade (kg/m³)'].nunique() != 1 and len(df_amostra) > 0:
        faltando_direcoes.append("Densidade (valor inconsistente)")
        
    return faltando_direcoes

def verificar_condicoes_de_ordem(C_matrix):
    """Verifica as condições de ordem esperadas para madeira ortotrópica."""
    C11, C22, C33 = C_matrix[0, 0], C_matrix[1, 1], C_matrix[2, 2]
    C44, C55, C66 = C_matrix[3, 3], C_matrix[4, 4], C_matrix[5, 5]
    C12, C13, C23 = C_matrix[0, 1], C_matrix[0, 2], C_matrix[1, 2]

    diagnostico_list = [
        {
            'Condição': r'$\mathbf{C}_{ii} \text{ (Normal)}$',
            'Regra Esperada': r'$C_{11} > C_{22} > C_{33}$',
            'Valor da Condição': f'{C11:.2f} > {C22:.2f} > {C33:.2f}',
            'Conformidade': '✅ Atendida' if (C11 > C22 and C22 > C33) else '❌ Não Atendida'
        },
        {
            'Condição': r'$\mathbf{C}_{ij} \text{ (Cisalhamento)}$',
            'Regra Esperada': r'$C_{44} < C_{55} < C_{66}$',
            'Valor da Condição': f'{C44:.2f} < {C55:.2f} < {C66:.2f}',
            'Conformidade': '✅ Atendida' if (C66 > C55 and C55 > C44) else '❌ Não Atendida'
        },
        {
            'Condição': r'$\mathbf{C}_{ij} \text{ (Mútua)}$',
            'Regra Esperada': r'$C_{12} > C_{13} > C_{23}$',
            'Valor da Condição': f'{C12:.2f} > {C13:.2f} > {C23:.2f}',
            'Conformidade': '✅ Atendida' if (C12 > C13 and C13 > C23) else '❌ Não Atendida'
        }
    ]
        
    return diagnostico_list

@st.cache_data
def calcular_propriedades_elasticas(df_amostra, nome_amostra):
    
    # 1. Pré-cálculos e Constantes
    rho_kg_m3 = df_amostra['Densidade (kg/m³)'].iloc[0]
    rho = rho_kg_m3
    velocidades = df_amostra.set_index('Direção')['Velocidade (m/s)'].to_dict()
    fator_conversao = 1e-6 # Pa para MPa
    n1 = n2 = n3 = 0.7071067812 # cos(45) ou sin(45)
    n_quadrado = 0.5 # n1*n2

    # 2. Coeficientes Diagonais e de Cisalhamento (Ondas Puras)
    C11 = rho * (velocidades['LL']**2) * fator_conversao
    C22 = rho * (velocidades['RR']**2) * fator_conversao
    C33 = rho * (velocidades['TT']**2) * fator_conversao
    
    V6_puro = (velocidades['LR'] + velocidades['RL']) / 2
    V5_puro = (velocidades['LT'] + velocidades['TL']) / 2
    V4_puro = (velocidades['RT'] + velocidades['TR']) / 2
    
    C66 = rho * (V6_puro**2) * fator_conversao
    C55 = rho * (V5_puro**2) * fator_conversao
    C44 = rho * (V4_puro**2) * fator_conversao
    
    # 3. Coeficientes Fora da Diagonal (Ondas 45 graus)
    
    # C12 (Plano L-R)
    V_LR_45 = velocidades['RL2']
    rho_VLR_quadrado = rho * (V_LR_45**2) * fator_conversao
    I_12 = C11 * (n1**2) + C66 * (n2**2) - rho_VLR_quadrado
    II_12 = C66 * (n1**2) + C22 * (n2**2) - rho_VLR_quadrado 
    C12 = (np.sqrt(I_12 * II_12) / n_quadrado) - C66
    
    # C23 (Plano R-T)
    V_RT_45 = (velocidades['RT1'] + velocidades['RT2']) / 2
    rho_VRT_quadrado = rho * (V_RT_45**2) * fator_conversao
    I_23 = C22 * (n2**2) + C44 * (n3**2) - rho_VRT_quadrado # n2 e n3 para RT
    II_23 = C44 * (n2**2) + C33 * (n3**2) - rho_VRT_quadrado # n2 e n3 para RT
    C23 = (np.sqrt(I_23 * II_23) / n_quadrado) - C44

    # C13 (Plano L-T)
    V_LT_45 = (velocidades['TL1'] + velocidades['TL2']) / 2
    rho_VLT_quadrado = rho * (V_LT_45**2) * fator_conversao
    I_13 = C11 * (n1**2) + C55 * (n3**2) - rho_VLT_quadrado # n1 e n3 para LT
    II_13 = C55 * (n1**2) + C33 * (n3**2) - rho_VLT_quadrado # n1 e n3 para LT
    C13 = (np.sqrt(I_13 * II_13) / n_quadrado) - C55
    
    # 4. Matriz de Rigidez (C)
    C_matrix = np.array([
        [C11, C12, C13, 0.0, 0.0, 0.0],
        [C12, C22, C23, 0.0, 0.0, 0.0],
        [C13, C23, C33, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, C44, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, C55, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, C66]
    ])

    # 5. Matriz de Flexibilidade (S)
    S_matrix = np.linalg.inv(C_matrix)
    
    # 6. Constantes Elásticas (E, G, nu)
    S11, S12, S13 = S_matrix[0, 0], S_matrix[0, 1], S_matrix[0, 2]
    S22, S23 = S_matrix[1, 1], S_matrix[1, 2]
    S33 = S_matrix[2, 2]
    S44, S55, S66 = S_matrix[3, 3], S_matrix[4, 4], S_matrix[5, 5]

    EL = 1 / S11; ER = 1 / S22; ET = 1 / S33
    GLR = 1 / S66; GLT = 1 / S55; GRT = 1 / S44
    
    # Relações de Poisson: nu_ij = -E_i * S_ij
    nu_LR = -EL * S12; nu_LT = -EL * S13
    nu_RL = -ER * S12; nu_RT = -ER * S23
    nu_TL = -ET * S13; nu_TR = -ET * S23
    
    propriedades_list = [
        {"Constante": r'$E_L$', "Valor": f"{EL:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$E_R$', "Valor": f"{ER:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$E_T$', "Valor": f"{ET:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$G_{LR}$', "Valor": f"{GLR:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$G_{LT}$', "Valor": f"{GLT:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$G_{RT}$', "Valor": f"{GRT:.4f}", "Unidade": 'MPa'},
        {"Constante": r'$\nu_{LR}$', "Valor": f"{nu_LR:.4f}", "Unidade": '-'},
        {"Constante": r'$\nu_{LT}$', "Valor": f"{nu_LT:.4f}", "Unidade": '-'},
        {"Constante": r'$\nu_{RL}$', "Valor": f"{nu_RL:.4f}", "Unidade": '-'},
        {"Constante": r'$\nu_{RT}$', "Valor": f"{nu_RT:.4f}", "Unidade": '-'},
        {"Constante": r'$\nu_{TL}$', "Valor": f"{nu_TL:.4f}", "Unidade": '-'},
        {"Constante": r'$\nu_{TR}$', "Valor": f"{nu_TR:.4f}", "Unidade": '-'}
    ]
    
    df_rigidez = pd.DataFrame(C_matrix, index=['C1', 'C2', 'C3', 'C4', 'C5', 'C6'], columns=['C1', 'C2', 'C3', 'C4', 'C5', 'C6'])
    df_flexibilidade = pd.DataFrame(S_matrix, index=['S1', 'S2', 'S3', 'S4', 'S5', 'S6'], columns=['S1', 'S2', 'S3', 'S4', 'S5', 'S6'])
    
    diagnostico_list = verificar_condicoes_de_ordem(C_matrix)

    return propriedades_list, df_rigidez, df_flexibilidade, diagnostico_list, C_matrix, S_matrix

# --- SEÇÃO PRINCIPAL DO STREAMLIT (FLUXO DINÂMICO) ---

uploaded_file = st.sidebar.file_uploader("0. Arraste e solte o arquivo CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Carregar o CSV
        df_completo = pd.read_csv(uploaded_file, decimal=',', sep=',')
        colunas_esperadas = ['Amostra', 'Densidade (kg/m³)', 'Direção', 'Distância (cm)', 'Tempo (μs)']
        df_completo = df_completo[[col for col in colunas_esperadas if col in df_completo.columns]].copy()
        
        # Converte para numérico
        for col in ['Densidade (kg/m³)', 'Distância (cm)', 'Tempo (μs)']:
            df_completo[col] = pd.to_numeric(df_completo[col], errors='coerce')
        
        # Cria um DataFrame base no state, para persistir edições entre abas
        if 'data_state' not in st.session_state:
            st.session_state.data_state = df_completo
            
        todas_amostras = sorted(st.session_state.data_state['Amostra'].unique())
        
        st.sidebar.markdown("---")
        # Seletor de amostras para filtrar quais abas serão criadas
        amostras_para_exibir = st.sidebar.multiselect(
            "1. Selecione as Amostras para Visualização/Edição:",
            options=todas_amostras,
            default=todas_amostras
        )
        use_latex = st.sidebar.checkbox("Visualizar Matrizes em formato LaTeX", value=False)
        
        if not amostras_para_exibir:
            st.warning("Por favor, selecione pelo menos uma amostra para análise.")
            st.stop()
            
        st.header(f"2. Análise Instantânea por Amostra ({len(amostras_para_exibir)} Amostra(s))")
        tabs = st.tabs(amostras_para_exibir)

        # Loop principal para criar as abas dinâmicas
        for i, amostra in enumerate(amostras_para_exibir):
            
            # DataFrame original da amostra no estado
            df_amostra_original = st.session_state.data_state[st.session_state.data_state['Amostra'] == amostra].copy()
            
            with tabs[i]:
                
                # Layout de colunas para o fluxo de edição/visualização
                col_editor, col_resultados = st.columns([1.5, 1])

                with col_editor:
                    st.markdown("##### 2.1 Edite Distância e Tempo (μs)")
                    
                    # O data_editor opera apenas nos dados desta amostra
                    df_editado_tab = st.data_editor(
                        df_amostra_original,
                        key=f"editor_{amostra}",
                        num_rows="dynamic", 
                        use_container_width=True,
                        column_config={
                            "Distância (cm)": st.column_config.NumberColumn(format="%.3f"),
                            "Tempo (μs)": st.column_config.NumberColumn(format="%.2f"),
                            "Densidade (kg/m³)": st.column_config.NumberColumn(format="%.2f"),
                            "Amostra": st.column_config.TextColumn(disabled=True),
                            "Direção": st.column_config.TextColumn(disabled=False),
                        }
                    )
                    
                # Processamento dos dados editados
                df_processar = df_editado_tab.copy()
                df_processar.dropna(subset=['Densidade (kg/m³)', 'Distância (cm)', 'Tempo (μs)'], inplace=True)
                
                # Recálculo da Velocidade
                df_processar['Velocidade (m/s)'] = (df_processar['Distância (cm)'] / df_processar['Tempo (μs)']) * 10000

                # Atualiza o estado da sessão com os dados editados
                # Remove as linhas antigas da amostra e adiciona as novas
                st.session_state.data_state = st.session_state.data_state[st.session_state.data_state['Amostra'] != amostra]
                st.session_state.data_state = pd.concat([st.session_state.data_state, df_editado_tab], ignore_index=True)


                with col_resultados:
                    st.markdown("##### 2.2 Resultados Instantâneos (MPa)")

                    if faltando := verificar_dados_amostra(df_processar):
                        st.error("⚠️ Dados insuficientes. Edite e complete.")
                        st.info(f"Faltando Direções/Dados: {', '.join(faltando)}")
                        continue 

                    try:
                        resultados = calcular_propriedades_elasticas(df_processar, amostra)
                        propriedades_list, df_rigidez, df_flexibilidade, diagnostico_list, C_matrix, S_matrix = resultados

                        st.success("Cálculo Ok. Ajuste um valor para recálculo.")
                        
                        # Tabela de Propriedades ao lado
                        st.table(propriedades_list)
                            
                    except np.linalg.LinAlgError:
                        st.error("Erro: Matriz de Rigidez Singular. Dados de velocidade ou densidade irrealistas.")
                    except ValueError as ve:
                        st.error(f"Erro de dados: {ve}")
                    except Exception as e:
                        st.error(f"Erro inesperado: {e}")
                
                # --- Visualização de Matrizes e Diagnóstico (Abaixo do Fluxo Principal) ---
                st.markdown("---")
                
                # Relatório de Diagnóstico
                if 'diagnostico_list' in locals():
                    with st.expander("Diagnóstico de Conformidade da Rigidez", expanded=False):
                         st.markdown("**Verificação das Condições de Ordem da Madeira:**")
                         st.table(diagnostico_list)

                # Matrizes de Rigidez e Flexibilidade
                if 'C_matrix' in locals():
                    st.markdown("##### 2.3 Matrizes de Rigidez e Flexibilidade")
                    
                    col_C_matriz, col_S_matriz = st.columns(2)
                    
                    with col_C_matriz:
                         if use_latex:
                             latex_C_code = r"\mathbf{C}_{ij} \text{ [MPa]} = " + to_latex_matrix(C_matrix, precision=2)
                             st.markdown("###### Matriz de Rigidez ($C_{ij}$) [MPa]")
                             st.latex(latex_C_code)
                         else:
                             st.markdown("###### Matriz de Rigidez ($C_{ij}$) [MPa]")
                             st.dataframe(df_rigidez.style.format(precision=2), use_container_width=True)

                    with col_S_matriz:
                        if use_latex:
                            latex_S_code = r"\mathbf{S}_{ij} \text{ [MPa}^{-1}\text{]} = " + to_latex_matrix(S_matrix, precision=2, is_flexibility=True)
                            st.markdown("###### Matriz de Flexibilidade ($S_{ij}$) [$MPa^{-1}$]")
                            st.latex(latex_S_code)
                        else:
                            st.markdown("###### Matriz de Flexibilidade ($S_{ij}$) [$MPa^{-1}$]")
                            st.dataframe(df_flexibilidade.style.format('{:.2e}'), use_container_width=True)
                            
    except Exception as e:
        st.error("Erro fatal ao carregar ou processar o arquivo CSV. Verifique se as colunas e o separador decimal (vírgula ',') estão corretos.")
        st.exception(e)