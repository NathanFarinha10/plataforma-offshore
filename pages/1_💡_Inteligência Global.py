import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt
from fpdf import FPDF
import io
from datetime import datetime

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÕES DE CONSULTA AO BANCO ---
def get_paises():
    response = supabase.table('paises').select('id, nome, emoji_bandeira').execute()
    return {f"{item['nome']} {item['emoji_bandeira']}": item['id'] for item in response.data}

@st.cache_data(ttl=600)
def get_classes_de_ativos():
    response = supabase.table('classes_de_ativos').select('id, nome').execute()
    return {"--Selecione--": None, **{item['nome']: item['id'] for item in response.data}}

@st.cache_data(ttl=600)
def get_subclasses_de_ativos(classe_pai_id):
    if not classe_pai_id:
        return {"--Selecione--": None}
    response = supabase.table('subclasses_de_ativos').select('id, nome').eq('classe_pai_id', classe_pai_id).execute()
    return {"--Selecione--": None, **{item['nome']: item['id'] for item in response.data}}

@st.cache_data(ttl=600)
def get_temas():
    response = supabase.table('temas').select('id, nome').execute()
    return {"--Selecione--": None, **{item['nome']: item['id'] for item in response.data}}

# --- FUNÇÃO DE VISUALIZAÇÃO ---
def create_timeline_chart(data):
    """Cria um gráfico de timeline com a evolução das visões das gestoras."""
    if not data:
        return None

    df = pd.DataFrame(data)
    
    # Mapeia a visão para um valor numérico para o gráfico
    visao_map = {'Overweight': 1, 'Neutral': 0, 'Underweight': -1}
    df['visao_numerica'] = df['visao'].map(visao_map)
    
    # Extrai o nome da gestora do dicionário aninhado
    df['gestora_nome'] = df['gestoras'].apply(lambda x: x['nome'] if isinstance(x, dict) else 'N/A')
    
    # Converte a data para o formato correto
    df['data_publicacao'] = pd.to_datetime(df['data_publicacao'])

    # Cria o gráfico com Altair
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('data_publicacao:T', title='Data da Análise'),
        y=alt.Y('visao_numerica:Q', title='Visão', axis=alt.Axis(values=[-1, 0, 1], labelExpr="datum.value == 1 ? 'Overweight' : datum.value == 0 ? 'Neutral' : 'Underweight'")),
        color=alt.Color('gestora_nome:N', title='Gestora'),
        tooltip=['gestora_nome', 'data_publicacao', 'visao', 'titulo']
    ).interactive()
    
    return chart

def display_analises(analises):
    """Função reutilizável para exibir uma lista de análises."""
    if not analises:
        st.info("Nenhuma análise encontrada para os filtros selecionados.")
        return
    
    for analise in analises:
        nome_gestora = analise['gestoras']['nome'] if analise.get('gestoras') else "N/A"
        with st.expander(f"**{analise['titulo']}** (Visão: {nome_gestora})"):
            st.caption(f"Visão da Gestora: **{analise['visao']}**")
            st.write(f"**Resumo:** {analise['resumo']}")
            st.write(f"**Análise Completa:** {analise['texto_completo']}")

# --- NOVA FUNÇÃO: GERADOR DE PDF ---
# --- NOVA FUNÇÃO: VERSÃO DE TESTE PARA DIAGNÓSTICO ---
# --- FUNÇÃO DE PDF FINAL - VERSÃO ROBUSTA E À PROVA DE DADOS ---
def generate_pdf_report(selected_data):
    class PDF(FPDF):
        def header(self):
            self.set_font('DejaVu', 'B', 12)
            self.cell(0, 10, 'Relatório de Inteligência Global', 0, 1, 'C')
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font('DejaVu', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'I', 'DejaVuSans.ttf', uni=True)
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 24)
    pdf.cell(0, 20, 'Inteligência Global', 0, 1, 'C')
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 10, f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'C')
    pdf.ln(20)

    for section_title, analises in selected_data.items():
        if not analises: continue
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 16)
        pdf.multi_cell(0, 10, str(section_title), 0, 'L')
        pdf.ln(5)
        for analise in analises:
            nome_gestora = str(analise.get('gestoras', {}).get('nome', "N/A"))
            titulo = str(analise.get('titulo', 'Sem Título'))
            visao = str(analise.get('visao', 'N/A'))
            resumo = str(analise.get('resumo', ''))
            pdf.set_font('DejaVu', 'B', 12)
            pdf.multi_cell(0, 8, f"{titulo} (Fonte: {nome_gestora})")
            pdf.set_font('DejaVu', '', 11)
            pdf.cell(0, 8, f"Visão: {visao}", ln=1, align='L')
            pdf.multi_cell(0, 8, f"Resumo: {resumo}")
            pdf.ln(8)
            
    return pdf.output(dest='B')
        
# --- LAYOUT DA PÁGINA ---
st.set_page_config(page_title="Inteligência Global", page_icon="💡", layout="wide")
st.title("💡 Inteligência Global")
st.write("Visões e estratégias consolidadas para o investidor global.")
st.markdown("---")

# --- NAVEGAÇÃO INTERNA COM ABAS ---
tab_hub, tab_macro, tab_assets, tab_micro, tab_thematic, tab_report = st.tabs([
    "📍 Hub", "🌍 Macro View", "📊 Assets View", "🔬 MicroAssets View", "🎨 Thematic View", "📄 Research Report"
])

# --- ABA HUB ---
with tab_hub:
    st.header("📍 Hub de Inteligência")
    st.write("Em breve...")

# --- ABA MACRO VIEW ---
with tab_macro:
    st.header("🌍 Visão Macroeconômica por País")
    
    paises_map = get_paises()
    pais_selecionado_nome = st.selectbox(
        "Selecione um país ou região para analisar:",
        options=list(paises_map.keys())
    )

    if pais_selecionado_nome:
        pais_selecionado_id = paises_map[pais_selecionado_nome]

        # --- PAINEL DE INDICADORES ECONÔMICOS ---
        st.subheader("Painel de Indicadores")
        indicadores_response = supabase.table('indicadores_economicos').select('*').eq('pais_id', pais_selecionado_id).execute()
        
        if indicadores_response.data:
            cols = st.columns(4) # Cria 4 colunas para os métricos
            for i, indicador in enumerate(indicadores_response.data):
                col = cols[i % 4]
                with col:
                    st.metric(
                        label=indicador['nome_indicador'],
                        value=indicador['valor_atual'],
                        help=f"Referência: {indicador['data_referencia']}"
                    )
        else:
            st.info("Nenhum indicador econômico cadastrado para este país.")
        
        st.markdown("---")

        # --- PAINEL VISÃO BANCO CENTRAL ---
        st.subheader("Visão do Banco Central")
        bc_response = supabase.table('analises').select('*').eq('pais_id', pais_selecionado_id).eq('tipo_analise', 'Visão BC').order('data_publicacao', desc=True).limit(1).execute()

        if bc_response.data:
            analise_bc = bc_response.data[0]
            with st.container(border=True):
                st.write(f"**{analise_bc['titulo']}**")
                st.caption(f"Publicado em: {pd.to_datetime(analise_bc['data_publicacao']).strftime('%d/%m/%Y')}")
                st.write(analise_bc['texto_completo'])
        else:
            st.info("Nenhuma análise do Banco Central encontrada para este país.")

        st.markdown("---")

         # --- NOVO: PAINEL TIMELINE ---
        st.subheader("Timeline de Visões")
        # Busca dados apenas do tipo 'Macro' para a timeline
        timeline_response = supabase.table('analises').select(
            'data_publicacao, titulo, visao, gestoras(nome)'
        ).eq('pais_id', pais_selecionado_id).eq('tipo_analise', 'Macro').neq('visao', 'N/A').execute()

        if timeline_response.data:
            timeline_chart = create_timeline_chart(timeline_response.data)
            if timeline_chart:
                st.altair_chart(timeline_chart, use_container_width=True)
        else:
            st.info("Não há dados suficientes para gerar a timeline de visões para este país.")
        
        st.markdown("---")
        
        # --- PAINEL VISÃO DAS GESTORAS ---
        st.subheader("Visão das Gestoras")
        gestoras_response = supabase.table('analises').select('*, gestoras(nome)').eq('pais_id', pais_selecionado_id).eq('tipo_analise', 'Macro').execute()
        
        if gestoras_response.data:
            for analise in gestoras_response.data:
                nome_gestora = analise['gestoras']['nome'] if analise.get('gestoras') else "N/A"
                with st.expander(f"**{analise['titulo']}** (Visão: {nome_gestora})"):
                    st.caption(f"Visão da Gestora: **{analise['visao']}**")
                    st.write(f"**Resumo:** {analise['resumo']}")
                    st.write(f"**Análise Completa:** {analise['texto_completo']}")
        else:
            st.info("Nenhuma análise macro de gestoras encontrada para este país.")

        # --- NOVO: PAINEL TREND THESIS ---
        st.subheader("Teses de Investimento (Macro)")
        tese_response = supabase.table('analises').select('*, gestoras(nome)').eq('pais_id', pais_selecionado_id).eq('tipo_analise', 'Tese').execute()
        
        if tese_response.data:
            for tese in tese_response.data:
                nome_gestora = tese['gestoras']['nome'] if tese.get('gestoras') else "N/A"
                with st.container(border=True):
                    st.write(f"**{tese['titulo']}**")
                    st.caption(f"Fonte: {nome_gestora} | Publicado em: {pd.to_datetime(tese['data_publicacao']).strftime('%d/%m/%Y')}")
                    st.write(tese['texto_completo'])
        else:
            st.info("Nenhuma tese de investimento encontrada para este país.")

# --- OUTRAS ABAS (EM CONSTRUÇÃO) ---
with tab_assets:
    st.header("📊 Análise por Classe de Ativo")
    paises_map_assets = get_paises()
    classes_map_assets = get_classes_de_ativos()
    
    col1, col2 = st.columns(2)
    with col1:
        pais_selecionado_nome = st.selectbox("Selecione um país:", options=list(paises_map_assets.keys()), key="asset_pais")
    with col2:
        classe_selecionada_nome = st.selectbox("Selecione uma Classe de Ativo:", options=list(classes_map_assets.keys()), key="asset_classe")

    if pais_selecionado_nome and classe_selecionada_nome != "--Selecione--":
        pais_id = paises_map_assets[pais_selecionado_nome]
        classe_id = classes_map_assets[classe_selecionada_nome]

        response = supabase.table('analises').select('*, gestoras(nome)').eq('pais_id', pais_id).eq('classe_de_ativo_id', classe_id).in_('tipo_analise', ['Asset', 'Tese', 'Driver']).execute()
        
        st.markdown("---")
        display_analises(response.data)

# --- NOVA: ABA MICROASSETS VIEW ---
with tab_micro:
    st.header("🔬 Análise por Sub-Classe de Ativo")
    paises_map_micro = get_paises()
    classes_map_micro = get_classes_de_ativos()

    col1, col2, col3 = st.columns(3)
    with col1:
        pais_selecionado_nome_micro = st.selectbox("Selecione um país:", options=list(paises_map_micro.keys()), key="micro_pais")
    with col2:
        classe_selecionada_nome_micro = st.selectbox("Selecione uma Classe:", options=list(classes_map_micro.keys()), key="micro_classe")
    
    subclasses_map_micro = get_subclasses_de_ativos(classes_map_micro.get(classe_selecionada_nome_micro))
    with col3:
        subclasse_selecionada_nome_micro = st.selectbox("Selecione uma Sub-Classe:", options=list(subclasses_map_micro.keys()), key="micro_subclasse")

    if pais_selecionado_nome_micro and classe_selecionada_nome_micro != "--Selecione--" and subclasse_selecionada_nome_micro != "--Selecione--":
        pais_id = paises_map_micro[pais_selecionado_nome_micro]
        subclasse_id = subclasses_map_micro[subclasse_selecionada_nome_micro]

        response = supabase.table('analises').select('*, gestoras(nome)').eq('pais_id', pais_id).eq('subclasse_de_ativo_id', subclasse_id).in_('tipo_analise', ['MicroAsset', 'Tese', 'Driver']).execute()

        st.markdown("---")
        display_analises(response.data)

with tab_thematic:
    st.header("🎨 Análise de Teses Temáticas")
    temas_map = get_temas()
    
    tema_selecionado_nome = st.selectbox(
        "Selecione um tema para explorar as análises:",
        options=list(temas_map.keys()),
        key="tema_select"
    )

    if tema_selecionado_nome and tema_selecionado_nome != "--Selecione--":
        tema_id = temas_map[tema_selecionado_nome]
        
        response = supabase.table('analises').select(
            '*, gestoras(nome)'
        ).eq(
            'tema_id', tema_id
        ).eq(
            'tipo_analise', 'Thematic'
        ).execute()

        st.markdown("---")
        display_analises(response.data)

with tab_report:
    st.header("📄 Gerador de Relatórios Personalizados")
    st.write("Selecione as análises que deseja incluir no seu relatório em PDF.")
    
    paises_map = get_paises()
    classes_map = get_classes_de_ativos()
    temas_map = get_temas()

    selected_paises = st.multiselect("Análises Macro por País:", options=list(paises_map.keys()))
    selected_classes = st.multiselect("Análises por Classe de Ativo (geral):", options=[k for k in classes_map.keys() if k != '--Selecione--'])
    selected_temas = st.multiselect("Análises Temáticas:", options=[k for k in temas_map.keys() if k != '--Selecione--'])
    
    if st.button("Gerar Relatório"):
        with st.spinner("Compilando seu relatório..."):
            report_data = {}
            st.session_state.pdf_report = None # Limpa o relatório anterior
            
            # --- INÍCIO DO BLOCO DE DEPURAÇÃO ---
            st.markdown("---")
            st.subheader("🕵️ Informação de Depuração")

            # Depuração de dados macro
            if selected_paises:
                pais_ids = [paises_map[p] for p in selected_paises]
                st.write(f"Buscando análises 'Macro' para IDs de país: `{pais_ids}`")
                macro_response = supabase.table('analises').select('*, gestoras(nome)').in_('pais_id', pais_ids).eq('tipo_analise', 'Macro').execute()
                st.write(f"Encontradas {len(macro_response.data)} análises 'Macro'.")
                if macro_response.data:
                    report_data['Analises Macroeconomicas'] = macro_response.data
            
            # Depuração de dados de classes de ativos
            if selected_classes:
                classe_ids = [classes_map[c] for c in selected_classes]
                st.write(f"Buscando análises 'Asset' para IDs de classe: `{classe_ids}`")
                asset_response = supabase.table('analises').select('*, gestoras(nome)').in_('classe_de_ativo_id', classe_ids).eq('tipo_analise', 'Asset').execute()
                st.write(f"Encontradas {len(asset_response.data)} análises 'Asset'.")
                if asset_response.data:
                    report_data['Analises por Classe de Ativo'] = asset_response.data

            # Depuração de dados de temas
            if selected_temas:
                tema_ids = [temas_map[t] for t in selected_temas]
                st.write(f"Buscando análises 'Thematic' para IDs de tema: `{tema_ids}`")
                thematic_response = supabase.table('analises').select('*, gestoras(nome)').in_('tema_id', tema_ids).eq('tipo_analise', 'Thematic').execute()
                st.write(f"Encontradas {len(thematic_response.data)} análises 'Thematic'.")
                if thematic_response.data:
                    report_data['Analises Tematicas'] = thematic_response.data
            
            st.write("Conteúdo final a ser enviado para o PDF:")
            st.json(report_data) # Mostra o dicionário de dados completo
            st.markdown("---")
            # --- FIM DO BLOCO DE DEPURAÇÃO ---

            pdf_output = generate_pdf_report(report_data)

            if pdf_output:
                st.session_state.pdf_report = bytes(pdf_output)
            else:
                st.error("Ocorreu um erro ao gerar o PDF. Por favor, tente novamente.")

    if 'pdf_report' in st.session_state and st.session_state.pdf_report:
        st.download_button(
            label="Clique para Baixar o PDF",
            data=st.session_state.pdf_report,
            file_name=f"Relatorio_Inteligencia_Global_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
