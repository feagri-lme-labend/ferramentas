import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import warnings
import os

# --- Configuração do Layout ---
st.set_page_config(layout="wide")
st.title("🎯 Caçador de Linearidade Interativo: Análise Multi-Arquivo")
st.markdown("Selecione múltiplos arquivos, defina os limites de Y e escolha quais colunas representam X e Y.")

warnings.filterwarnings('ignore', category=UserWarning)

# --- 1. Funções de Carga e Otimização ---

DATA_DIR = "dados"
PERCENTUAIS_JANELA_X = [100, 80, 60, 40, 20]

@st.cache_data
def load_data_from_directory(dir_path):
    """Lê todos os arquivos CSV na pasta especificada."""
    if not os.path.exists(dir_path):
        st.error(f"O diretório '{dir_path}' não foi encontrado. Verifique se existe a pasta com os arquivos CSV.")
        st.stop()
        
    csv_files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
    dataframes = {}
    for file in csv_files:
        path = os.path.join(dir_path, file)
        try:
            dataframes[file] = pd.read_csv(path)
        except Exception as e:
            st.error(f"Erro ao carregar {file}: {e}")
    return dataframes


def find_best_linear_region(df_filtered, n_window, coluna_x, coluna_y):
    """
    Encontra a sub-região de N_WINDOW pontos com o maior R².
    Inclui o cálculo do erro padrão da inclinação (SE_B1).
    """
    best_r2 = -1
    best_start_index = 0
    best_intercept = 0
    best_slope = 0
    best_se_slope = 0  
    
    N_FILTRADO = len(df_filtered)
    if N_FILTRADO < 5:
        return None, None, None, None, None, None, None
    
    n_window = max(5, int(n_window))
    n_window = min(n_window, N_FILTRADO)
    
    X = df_filtered[coluna_x].values
    Y = df_filtered[coluna_y].values
    
    for i in range(N_FILTRADO - n_window + 1):
        x_window = X[i:i + n_window]
        y_window = Y[i:i + n_window]
        
        try:
            slope, intercept = np.polyfit(x_window, y_window, 1)
        except np.linalg.LinAlgError:
            continue
        
        if np.std(y_window) == 0 or np.std(x_window) == 0:
            r2 = 0.0
        else:
            r = np.corrcoef(x_window, y_window)[0, 1]
            r2 = np.clip(r**2, 0.0, 1.0)
        
        # Erro padrão da inclinação
        y_pred = slope * x_window + intercept
        residuals = y_window - y_pred
        n = len(x_window)
        if n > 2 and np.std(x_window) > 0:
            s2 = np.sum(residuals**2) / (n - 2)
            se_slope = np.sqrt(s2 / np.sum((x_window - np.mean(x_window))**2))
        else:
            se_slope = np.nan
        
        if r2 > best_r2:
            best_r2 = r2
            best_start_index = i
            best_intercept = intercept
            best_slope = slope
            best_se_slope = se_slope
    
    if best_r2 == -1:
        return None, None, None, None, None, None, None
    
    end_index = best_start_index + n_window - 1
    x_min_region = df_filtered.iloc[best_start_index][coluna_x]
    x_max_region = df_filtered.iloc[end_index][coluna_x]
    
    return best_r2, best_intercept, best_slope, best_se_slope, best_start_index, x_min_region, x_max_region


# --- 2. Interface do Usuário ---

dataframes = load_data_from_directory(DATA_DIR)
all_files = list(dataframes.keys())

st.sidebar.header("⚙️ Configurações de Análise")

selected_files_analysis = st.sidebar.multiselect(
    "1. Escolha os Arquivos CSV para ANÁLISE:",
    options=all_files,
    default=all_files 
)

if not selected_files_analysis:
    st.warning("Selecione pelo menos um arquivo para iniciar a análise.")
    st.stop()

base_file_for_plot = selected_files_analysis[0]
df_full_base = dataframes[base_file_for_plot]

# --- Escolha das Colunas de X e Y ---
st.sidebar.subheader("2. Escolha das Colunas de Análise")

colunas_disponiveis = list(df_full_base.columns)

coluna_x = st.sidebar.selectbox("Selecione a Coluna para X:", options=colunas_disponiveis, index=0)
coluna_y = st.sidebar.selectbox("Selecione a Coluna para Y:", options=colunas_disponiveis, index=1 if len(colunas_disponiveis) > 1 else 0)

# --- Validação: colunas devem ser numéricas ---
if not np.issubdtype(df_full_base[coluna_x].dtype, np.number):
    st.error(f"A coluna **{coluna_x}** não é numérica. Selecione outra coluna para X.")
    st.stop()

if not np.issubdtype(df_full_base[coluna_y].dtype, np.number):
    st.error(f"A coluna **{coluna_y}** não é numérica. Selecione outra coluna para Y.")
    st.stop()

# --- Filtro Vertical de Y ---
st.sidebar.subheader("3. Filtro Vertical (Eixo Y)")

y_range_perc = st.sidebar.slider(
    "Intervalo de Y (% do Y Máximo):",
    min_value=0, max_value=100,
    value=(10, 40), step=1
)
y_min_perc, y_max_perc = y_range_perc

if y_min_perc >= y_max_perc:
    st.sidebar.warning("O % Mínimo deve ser menor que o % Máximo.")
    st.stop()

# --- Seleção de gráfico ---
st.sidebar.subheader("4. Visualização Gráfica")
selected_file_plot = st.sidebar.selectbox("Escolha o Arquivo para GRÁFICO:", options=selected_files_analysis)
selected_janela_plot = st.sidebar.selectbox("Escolha a Janela X (%) para Visualizar:", options=[f"{p}%" for p in PERCENTUAIS_JANELA_X])


# --- 3. Execução da Otimização ---

all_results_list = []

st.header("Análise Consolidada dos Arquivos Selecionados")
st.markdown(f"*(Filtro Y percentual: **{y_min_perc}%** a **{y_max_perc}%**. Limites calculados com base no Y máximo de cada arquivo.)*")

with st.spinner("Processando Otimização de R² para todos os arquivos..."):
    for file_name in selected_files_analysis:
        df_current_full = dataframes[file_name]
        
        y_max_current = df_current_full[coluna_y].max()
        y_limite_min_current = y_max_current * (y_min_perc / 100)
        y_limite_max_current = y_max_current * (y_max_perc / 100)
        
        df_filtrado = df_current_full[
            (df_current_full[coluna_y] >= y_limite_min_current) &
            (df_current_full[coluna_y] <= y_limite_max_current)
        ].sort_values(by=coluna_x).reset_index(drop=True)
        
        N_FILTRADO = len(df_filtrado)
        N_TOTAL = len(df_current_full)
        
        if N_FILTRADO < 5:
            continue

        for percentual in PERCENTUAIS_JANELA_X:
            n_janela = max(5, int(N_FILTRADO * (percentual / 100)))
            
            max_r2, intercept, slope, se_slope, start_idx, x_min, x_max = find_best_linear_region(
                df_filtrado, n_janela, coluna_x, coluna_y
            )
            
            all_results_list.append({
                'Arquivo': file_name,
                'Qtd Total': N_TOTAL,
                'Qtd Filtrada': N_FILTRADO,
                'Y Mín (%)': f'{y_min_perc}%',
                'Y Máx (%)': f'{y_max_perc}%',
                'Janela X (%)': f'{percentual}%',
                'N Pontos Janela': n_janela,
                'R² Máx': max_r2,
                'B1 (Angular)': slope,
                'Erro Padrão B1': se_slope,
                'B0 (Linear)': intercept,
                'X Mín Região': x_min,
                'X Máx Região': x_max,
                'Y Mín Região': y_limite_min_current,
                'Y Máx Região': y_limite_max_current,
                'Y Máx Total': y_max_current,
                'Indice Inicial DF Filtrado': start_idx
            })

df_resultados_mestre = pd.DataFrame(all_results_list)

if df_resultados_mestre.empty:
    st.error("Nenhum resultado de otimização válido encontrado após a filtragem.")
    st.stop()

# --- 4. Exibição da Tabela ---
format_dict = {
    'R² Máx': '{:.4f}',
    'B1 (Angular)': '{:.4f}',
    'Erro Padrão B1': '{:.6f}',
    'B0 (Linear)': '{:.4f}',
    'X Mín Região': '{:.2f}',
    'X Máx Região': '{:.2f}',
    'Y Mín Região': '{:.2f}',
    'Y Máx Região': '{:.2f}',
    'Y Máx Total': '{:.2f}',
}

st.markdown("### 📊 Tabela de Resultados por Arquivo e Janela X")
st.dataframe(
    df_resultados_mestre.drop(columns=['Indice Inicial DF Filtrado']).style.format(format_dict),
    hide_index=True,
    width="stretch"
)

st.divider()

# --- 5. Gráfico Detalhado ---

st.header(f"Visualização Detalhada: {selected_file_plot} (Janela: {selected_janela_plot})")

df_plot_results = df_resultados_mestre[
    (df_resultados_mestre['Arquivo'] == selected_file_plot) &
    (df_resultados_mestre['Janela X (%)'] == selected_janela_plot)
]

if df_plot_results.empty or df_plot_results.iloc[0]['Qtd Filtrada'] < 5:
    st.warning(f"Não há resultados válidos para o arquivo **{selected_file_plot}** com a janela **{selected_janela_plot}**.")
    st.stop()

plot_result = df_plot_results.iloc[0].to_dict()
y_limite_min_plot = plot_result['Y Mín Região']
y_limite_max_plot = plot_result['Y Máx Região']

df_full_plot = dataframes[selected_file_plot]
df_filtrado_plot = df_full_plot[
    (df_full_plot[coluna_y] >= y_limite_min_plot) & 
    (df_full_plot[coluna_y] <= y_limite_max_plot)
].sort_values(by=coluna_x).reset_index(drop=True)

n_janela_plot = plot_result['N Pontos Janela']
max_r2_calc, intercept_calc, slope_calc, se_slope_calc, start_idx, x_min_calc, x_max_calc = find_best_linear_region(
    df_filtrado_plot, n_janela_plot, coluna_x, coluna_y
)

df_melhor_regiao = df_filtrado_plot.iloc[start_idx : start_idx + n_janela_plot]

fig = px.scatter(
    df_full_plot, 
    x=coluna_x, y=coluna_y,
    opacity=0.7,
    color_discrete_sequence=["#8bc1ff"], 
    title=f'Região Mais Linear Filtrada: R² = {plot_result["R² Máx"]:.4f}, SE(B1) = {plot_result["Erro Padrão B1"]:.6f}',
    labels={coluna_x: 'Variável X', coluna_y: 'Variável Y'}
)
fig.update_traces(marker_size=2.5)

fig.add_trace(
    go.Scatter(
        x=df_melhor_regiao[coluna_x],
        y=df_melhor_regiao[coluna_y],
        mode='markers',
        marker=dict(color='magenta', size=3, line=dict(width=1, color='magenta')),
        name=f'Região da Janela ({selected_janela_plot}, N={n_janela_plot})'
    )
)

X_range = np.array([plot_result['X Mín Região'], plot_result['X Máx Região']])
slope_plot = plot_result['B1 (Angular)']
intercept_plot = plot_result['B0 (Linear)']
Y_pred = slope_plot * X_range + intercept_plot

fig.add_trace(
    go.Scatter(
        x=X_range,
        y=Y_pred,
        mode='lines',
        line=dict(color='blue', width=3, dash='dash'),
        name=f'Reta Otimizada (Y ≈ {slope_plot:.3f}X + {intercept_plot:.3f})'
    )
)

fig.add_hrect(y0=y_limite_min_plot, y1=y_limite_max_plot, fillcolor="green", opacity=0.1, line_width=0)
fig.add_hline(y=y_limite_min_plot, line_dash="dash", line_color="green", line_width=2, opacity=.5)
fig.add_hline(y=y_limite_max_plot, line_dash="dash", line_color="green", line_width=2, opacity=.5)

st.plotly_chart(fig, config={"responsive": True})
