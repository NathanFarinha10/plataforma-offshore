import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt

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
    st.write("Em breve...")

with tab_micro:
    st.header("🔬 Análise por Sub-Classe de Ativo")
    st.write("Em breve...")

with tab_thematic:
    st.header("🎨 Análise de Teses Temáticas")
    st.write("Em breve...")

with tab_report:
    st.header("📄 Gerador de Relatórios")
    st.write("Em breve...")
