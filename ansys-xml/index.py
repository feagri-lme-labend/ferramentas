import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página para ocupar a largura total
st.set_page_config(page_title="Ansys Material Dashboard", page_icon="🏗️", layout="wide")

class AnsysXMLConverter:
    def __init__(self):
        # Mapeamento fixo para manter consistência entre CSV e XML
        self.ortho_params = {
            "pa14": "E_x", "pa15": "E_y", "pa16": "E_z",
            "pa17": "Poisson_xy", "pa18": "Poisson_yz", "pa19": "Poisson_xz",
            "pa20": "G_xy", "pa21": "G_yz", "pa22": "G_xz"
        }
        
        # Mapeamento de versões comerciais para versões técnicas do XML
        self.version_map = {
            "2024 R1": "24.1.0.0",
            "2024 R2": "24.2.0.0",
            "2025 R1": "25.1.0.0",
            "2025 R2": "25.2.0.233"
        }

    def clean_numeric(self, value):
        """Trata o formato '7,85e+03' e remove aspas do Excel brasileiro."""
        if pd.isna(value) or value == "":
            return 0.0
        if isinstance(value, str):
            clean_val = value.replace('"', '').replace(',', '.').strip()
            try:
                return float(clean_val)
            except ValueError:
                return 0.0
        return float(value)

    def _get_xml_header(self, ui_version):
        """Gera o cabeçalho dinâmico baseado na versão selecionada."""
        tech_version = self.version_map.get(ui_version, "25.2.0.233")
        current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<EngineeringData version="{tech_version}" versiondate="{current_date}">\n'
            f'  <Notes>Gerado via Streamlit - Versão Ansys {ui_version} - Suporta Ortotropia</Notes>\n'
            '  <Materials>\n    <MatML_Doc>\n'
        )

    def _get_xml_footer(self):
        """Metadata robusto para evitar erros de 'Missing ParameterDetails'."""
        metadata = '      <Metadata>\n'
        metadata += '        <ParameterDetails id="pa0"><Name>Options Variable</Name><Unitless/></ParameterDetails>\n'
        metadata += '        <ParameterDetails id="pa1"><Name>Density</Name><Units name="Density"><Unit><Name>kg</Name></Unit><Unit power="-3"><Name>m</Name></Unit></Units></ParameterDetails>\n'
        metadata += '        <ParameterDetails id="pa2"><Name>Young\'s Modulus</Name><Units name="Stress"><Unit><Name>Pa</Name></Unit></Units></ParameterDetails>\n'
        metadata += '        <ParameterDetails id="pa3"><Name>Poisson\'s Ratio</Name><Unitless/></ParameterDetails>\n'
        
        # Parâmetros Ortotrópicos
        for i, axis in zip(range(14, 17), ["X", "Y", "Z"]):
            metadata += f'        <ParameterDetails id="pa{i}"><Name>Young\'s Modulus {axis} direction</Name><Units name="Stress"><Unit><Name>Pa</Name></Unit></Units></ParameterDetails>\n'
        for i, axis in zip(range(17, 20), ["XY", "YZ", "XZ"]):
            metadata += f'        <ParameterDetails id="pa{i}"><Name>Poisson\'s Ratio {axis}</Name><Unitless/></ParameterDetails>\n'
        for i, axis in zip(range(20, 23), ["XY", "YZ", "XZ"]):
            metadata += f'        <ParameterDetails id="pa{i}"><Name>Shear Modulus {axis}</Name><Units name="Stress"><Unit><Name>Pa</Name></Unit></Units></ParameterDetails>\n'
        
        metadata += '        <PropertyDetails id="pr0"><Name>Density</Name></PropertyDetails>\n'
        metadata += '        <PropertyDetails id="pr1"><Name>Elasticity</Name></PropertyDetails>\n'
        metadata += '      </Metadata>\n    </MatML_Doc>\n  </Materials>\n</EngineeringData>'
        return metadata

    def build_material_block(self, row):
        nome = str(row["Nome"])
        desc = str(row["Descrição"])
        tipo = str(row["Tipo"]).strip().capitalize()
        dens = self.clean_numeric(row["Densidade"])

        block = f'      <Material>\n        <BulkDetails>\n'
        block += f'          <Name>{nome}</Name>\n'
        block += f'          <Description>{desc}</Description>\n'
        block += '          <Class><Name>Composite</Name></Class>\n'

        # Propriedade Densidade
        block += '          <PropertyData property="pr0">\n'
        block += '            <Data format="string">-</Data>\n'
        block += '            <ParameterValue parameter="pa0" format="string"><Data>Interpolation Options</Data><Qualifier name="AlgorithmType">Linear Multivariate (Qhull)</Qualifier></ParameterValue>\n'
        block += f'            <ParameterValue parameter="pa1" format="float"><Data>{dens}</Data><Qualifier name="Variable Type">Dependent</Qualifier></ParameterValue>\n'
        block += '          </PropertyData>\n'

        # Propriedade Elasticidade
        block += '          <PropertyData property="pr1">\n'
        block += '            <Data format="string">-</Data>\n'
        block += f'            <Qualifier name="Behavior">{tipo}</Qualifier>\n'
        block += '            <ParameterValue parameter="pa0" format="string"><Data>Interpolation Options</Data></ParameterValue>\n'

        if tipo == "Isotropic":
            block += '            <Qualifier name="Derive from">Young\'s Modulus and Poisson\'s Ratio</Qualifier>\n'
            block += f'            <ParameterValue parameter="pa2" format="float"><Data>{self.clean_numeric(row["E_x"])}</Data><Qualifier name="Variable Type">Dependent</Qualifier></ParameterValue>\n'
            block += f'            <ParameterValue parameter="pa3" format="float"><Data>{self.clean_numeric(row["Poisson_xy"])}</Data><Qualifier name="Variable Type">Dependent</Qualifier></ParameterValue>\n'
        else:
            for pa_id, col in self.ortho_params.items():
                val = self.clean_numeric(row[col])
                block += f'            <ParameterValue parameter="{pa_id}" format="float"><Data>{val}</Data><Qualifier name="Variable Type">Dependent</Qualifier></ParameterValue>\n'
        
        block += '          </PropertyData>\n        </BulkDetails>\n      </Material>\n'
        return block

    def convert(self, df, ui_version):
        """Recebe a versão da interface e aplica no header."""
        xml_out = self._get_xml_header(ui_version)
        for _, row in df.iterrows():
            xml_out += self.build_material_block(row)
        xml_out += self._get_xml_footer()
        return xml_out

# --- Interface Streamlit ---

st.title("📊 Ansys Material Dashboard & XML Generator")
st.markdown("Converta planilhas em arquivos de engenharia para o Ansys Workbench/Autodyn.")

uploaded_file = st.file_uploader("Upload do arquivo CSV (Use codificação UTF-8)", type="csv")
ansys_version = st.selectbox("Versão do Ansys", ["2024 R1", "2024 R2", "2025 R1", "2025 R2"])

if uploaded_file:
    # 1. Leitura e Limpeza
    df = pd.read_csv(uploaded_file, encoding='utf-8')
    converter = AnsysXMLConverter()
    
    # Criar DF numérico para gráficos
    df_plot = df.copy()
    numeric_cols = ["Densidade", "E_x", "E_y", "E_z", "Poisson_xy", "G_xy", "G_yz", "G_xz"]
    for col in numeric_cols:
        if col in df_plot.columns:
            df_plot[col] = df_plot[col].apply(converter.clean_numeric)

    # 2. Métricas de Resumo
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Materiais", len(df))
    m2.metric("Densidade Média", f"{df_plot['Densidade'].mean():.1f} kg/m³")
    m3.metric("E_max (GPa)", f"{df_plot['E_x'].max()/1e9:.1f}")
    m4.metric("Ortotrópicos", len(df[df['Tipo'].str.contains('Orthotropic', na=False)]))

    # 3. Gráficos Comparativos
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🚀 Rigidez Específica (E vs ρ)")
        fig_ashby = px.scatter(df_plot, x="Densidade", y="E_x", text="Nome", color="Tipo",
                               log_y=True, template="plotly_dark",
                               labels={"E_x": "Módulo de Young (Pa)", "Densidade": "Densidade (kg/m³)"})
        st.plotly_chart(fig_ashby)

    with col_b:
        st.subheader("📐 Anisotropia Direcional")
        df_ortho = df_plot[df_plot['Tipo'].str.contains('Orthotropic', case=False, na=False)]
        
        if not df_ortho.empty:
            prop_choice = st.radio("Visualizar:", ["E (Young)", "G (Cisalhamento)"], horizontal=True)
            fig_polar = go.Figure()
            for _, row in df_ortho.iterrows():
                r_vals = [row['E_x'], row['E_y'], row['E_z'], row['E_x']] if "E" in prop_choice else [row['G_xy'], row['G_yz'], row['G_xz'], row['G_xy']]
                theta = ['X', 'Y', 'Z', 'X']
                fig_polar.add_trace(go.Scatterpolar(r=r_vals, theta=theta, fill='toself', name=row['Nome']))
            
            fig_polar.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=True, tickformat=".1e")))
            st.plotly_chart(fig_polar)
        else:
            st.info("Adicione materiais 'Orthotropic' para ver o gráfico polar.")

    # 4. Exportação
    st.divider()
    st.subheader("💾 Exportação de Dados")
    if st.button("🚀 Gerar XML para Ansys"):
        # Passando a variável ansys_version para a função convert
        final_xml = converter.convert(df, ansys_version)
        st.success(f"XML gerado com sucesso para Ansys {ansys_version}!")
        st.download_button(
            label="📥 Baixar arquivo .xml",
            data=final_xml.encode('utf-8'),
            file_name=f"EngineeringData_{ansys_version.replace(' ', '_')}.xml",
            mime="text/xml"
        )

# Rodapé Técnico
st.sidebar.title("Instruções")
st.sidebar.info("""
1. O CSV deve conter as colunas: **Nome, Descrição, Tipo, Densidade, E_x, E_y, E_z, Poisson_xy, Poisson_yz, Poisson_xz, G_xy, G_yz, G_xz**.
2. O separador deve ser **vírgula**.
3. No Ansys, importe via **Engineering Data Sources**.
""")