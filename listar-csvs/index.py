import streamlit as st
from pathlib import Path
import psutil 
import pandas as pd # Necessário para criar o DataFrame com os ícones

# --- Mapeamento de Extensão para Ícone (Emoji) ---
ICON_MAP = {
    ".py": "🐍",    # Python
    ".ipynb": "📒", # Jupyter Notebook
    ".txt": "📄",   # Texto
    ".pdf": "📃",   # PDF
    ".docx": "📝",  # Documento Word
    ".xlsx": "📊",  # Excel
    ".csv": "📑",   # CSV
    ".jpg": "🖼️",  # Imagem
    ".png": "🖼️",  # Imagem
    ".html": "🌐",  # Web
    ".zip": "📦",   # Zip/Arquivo
    ".mp4": "🎬",  # Vídeo
    ".md": "📖",   # Markdown
    "default": "❓" # Padrão
}

# --- Configuração Inicial do Estado de Sessão ---

if 'historico' not in st.session_state:
    st.session_state.historico = [Path.cwd()] 
    
if 'indice_atual' not in st.session_state:
    st.session_state.indice_atual = 0

if 'unidade_selecionada' not in st.session_state: 
    st.session_state.unidade_selecionada = None 

# Obtém o caminho atual do histórico
caminho_atual = st.session_state.historico[st.session_state.indice_atual]

# --- Funções de Navegação de Histórico ---

def navegar_para_item(novo_caminho: Path):
    """Navega para um novo diretório, salva no histórico e atualiza o índice."""
    st.session_state.historico = st.session_state.historico[:st.session_state.indice_atual + 1]
    st.session_state.historico.append(novo_caminho)
    st.session_state.indice_atual += 1
    st.rerun()

def avancar_historico():
    """Avança um passo no histórico de navegação."""
    if st.session_state.indice_atual < len(st.session_state.historico) - 1:
        st.session_state.indice_atual += 1
        st.rerun()

def voltar_historico():
    """Volta um passo no histórico de navegação."""
    if st.session_state.indice_atual > 0:
        st.session_state.indice_atual -= 1
        st.rerun()

# --- Função para Obter Unidades ---
@st.cache_data
def obter_unidades_disco():
    """Retorna uma lista de pontos de montagem/letras de unidade raiz."""
    unidades = []
    
    # Adiciona a raiz do sistema de arquivos para Linux/macOS
    unidades.append("/")

    for part in psutil.disk_partitions():
        unidades.append(part.mountpoint)
        
    return sorted(list(set(unidades))) 

# --- Interface da Sidebar (Seleção de Unidade e Controles) ---

st.sidebar.header("1. Seleção de Unidade")

lista_unidades = obter_unidades_disco()
default_root = "C:\\" if Path("/").drive else "/"
default_index = 0

if lista_unidades:
    try:
        if default_root in lista_unidades:
             default_index = lista_unidades.index(default_root)
    except ValueError:
        pass
        
    unidade_selecionada_str = st.sidebar.selectbox(
        "Escolha a unidade de disco:",
        options=lista_unidades,
        index=default_index,
        key='unidade_selectbox',
    )
    
    if st.session_state.unidade_selecionada != unidade_selecionada_str:
        st.session_state.unidade_selecionada = unidade_selecionada_str
        st.session_state.historico = [Path(unidade_selecionada_str)]
        st.session_state.indice_atual = 0
        st.rerun()

else:
    st.sidebar.error("Não foi possível listar as unidades de disco.")
    st.stop()


st.sidebar.header("2. Controles de Navegação")

col_back, col_forward = st.sidebar.columns(2)

disable_back = st.session_state.indice_atual == 0
if col_back.button("⬅️ Voltar", disabled=disable_back, width="stretch"):
    voltar_historico()

disable_forward = st.session_state.indice_atual == len(st.session_state.historico) - 1
if col_forward.button("➡️ Avançar", disabled=disable_forward, width="stretch"):
    avancar_historico()
    
st.sidebar.markdown("---")

is_root = caminho_atual.resolve() == Path(st.session_state.unidade_selecionada).resolve()
if st.sidebar.button("⬆️ Subir um Nível (..)", disabled=is_root, width="stretch"):
    if not is_root:
        navegar_para_item(caminho_atual.parent) 

st.sidebar.markdown("---")


# --- Interface Principal (Listagem) ---

st.title("📂 Listador de Arquivos com Navegação Local")
st.info(f"Caminho Atual: `{caminho_atual.resolve()}`")

col_dir, col_list = st.columns([1, 1])
pastas_encontradas = []
arquivos_encontrados = []

try:
    for item in caminho_atual.iterdir():
        if item.name.startswith('.'):
            continue

        if item.is_dir():
            pastas_encontradas.append(item)
        elif item.is_file():
            arquivos_encontrados.append(item.name)
            
except PermissionError:
    st.error("Permissão Negada: Você não tem acesso a este diretório.")
except Exception as e:
    st.error(f"Erro ao ler o diretório: {e}")

# Exibe Pastas para Navegação (COM EXPANDER e SCROLL)
col_dir.subheader("1. Pastas para Avançar:")
with col_dir.expander("Pastas do Diretório Atual", expanded=True):
    
    st.markdown(
        """
        <style>
        .folder-container {
            max-height: 350px; 
            overflow-y: auto; 
            padding-right: 15px;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

    with st.container(height=350, border=False): 
        if pastas_encontradas:
            for pasta in sorted(pastas_encontradas, key=lambda p: p.name.lower()):
                if st.button(f"📁 {pasta.name}", key=f"dir_{pasta.name}", width="stretch"):
                    navegar_para_item(pasta) 
        else:
            st.write("Nenhuma subpasta encontrada neste nível.")

# Exibe Arquivos e Resultado CSV
col_list.subheader("2. Arquivos Encontrados:")
if arquivos_encontrados:
    
    # --- NOVO: Criando o DataFrame com Ícones ---
    dados_com_icones = []
    
    for nome_arquivo in arquivos_encontrados:
        extensao = Path(nome_arquivo).suffix.lower()
        icone = ICON_MAP.get(extensao, ICON_MAP["default"])
        
        dados_com_icones.append({
            "Ícone": icone,
            "Nome do Arquivo": nome_arquivo
        })

    df_arquivos_com_icones = pd.DataFrame(dados_com_icones)

    col_list.write(f"Total de **{len(arquivos_encontrados)}** arquivos neste diretório.")
    
    # Exibição do DataFrame
    st.dataframe(
        df_arquivos_com_icones,
        column_config={
            "Ícone": st.column_config.Column(width="small"),
            "Nome do Arquivo": st.column_config.Column(width="large")
        },
        hide_index=True,
        width="stretch",
    )
    # --- FIM NOVO: DataFrame com Ícones ---

    st.markdown("---")
    st.subheader("Resultado Final (Separado por Vírgula):")
    
    resultado_csv = ",".join(arquivos_encontrados)
    st.code(resultado_csv, language='text', height=100)

    # Botão de download
    st.download_button(
        label="Baixar CSV",
        data=resultado_csv,
        file_name=f'lista_{caminho_atual.name}.csv',
        mime='text/csv'
    )
else:
    col_list.write("Nenhum arquivo encontrado neste nível.")