import streamlit as st
from supabase import create_client, Client

# --- INICIALIZAÇÃO DA CONEXÃO COM O SUPABASE ---
# (A mesma lógica que usamos no painel Admin)

@st.cache_resource
def init_connection() -> Client:
    """Inicializa e retorna o cliente do Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÕES DE CONSULTA AO BANCO ---

def get_paises():
    """Busca todos os países para popular o selectbox."""
    response = supabase.table('paises').select('id, nome, emoji_bandeira').execute()
    # Retorna um dicionário mapeando "Nome (Emoji)" para o ID do país
    return {f"{item['nome']} {item['emoji_bandeira']}": item['id'] for item in response.data}

# --- LAYOUT DA PÁGINA ---

st.set_page_config(page_title="Inteligência Global", page_icon="💡", layout="wide")
st.title("💡 Inteligência Global")
st.write("Visões e estratégias consolidadas para o investidor global.")
st.markdown("---")


# --- NAVEGAÇÃO INTERNA COM ABAS ---

tab_hub, tab_macro, tab_assets, tab_micro, tab_thematic, tab_report = st.tabs([
    "📍 Hub",
    "🌍 Macro View",
    "📊 Assets View",
    "🔬 MicroAssets View",
    "🎨 Thematic View",
    "📄 Research Report"
])


# --- ABA HUB (AINDA EM CONSTRUÇÃO) ---
with tab_hub:
    st.header("📍 Hub de Inteligência")
    st.write("Em breve: Um painel consolidado com os principais insights da plataforma.")


# --- ABA MACRO VIEW (NOSSO FOCO AGORA) ---
with tab_macro:
    st.header("🌍 Visão Macroeconômica por País")
    
    # Carrega o mapa de países
    paises_map = get_paises()
    
    # Cria o dropdown para o usuário selecionar o país
    pais_selecionado_nome = st.selectbox(
        "Selecione um país ou região para analisar:",
        options=list(paises_map.keys())
    )

    if pais_selecionado_nome:
        # Pega o ID do país correspondente ao nome selecionado
        pais_selecionado_id = paises_map[pais_selecionado_nome]

        # Faz a consulta ao banco de dados
        # Pede todas as colunas de 'analises' e o 'nome' da 'gestora' relacionada
        response = supabase.table('analises').select(
            '*, gestoras(nome)'
        ).eq(
            'pais_id', pais_selecionado_id
        ).eq(
            'tipo_analise', 'Macro'
        ).execute()
        
        # Verifica se a consulta retornou algum dado
        if response.data:
            st.write(f"Exibindo {len(response.data)} análise(s) macro para **{pais_selecionado_nome}**.")
            
            # Itera sobre cada análise encontrada e a exibe
            for analise in response.data:
                # O nome da gestora vem como uma lista de um dicionário, acessamos assim:
                nome_gestora = analise['gestoras']['nome'] if analise.get('gestoras') else "N/A"
                
                # Usamos um 'expander' para um layout limpo
                with st.expander(f"**{analise['titulo']}** (Visão: {nome_gestora})"):
                    st.caption(f"Visão da Gestora: **{analise['visao']}**")
                    st.subheader("Resumo da Análise")
                    st.write(analise['resumo'])
                    st.subheader("Análise Completa")
                    st.write(analise['texto_completo'])
                    st.caption(f"Publicado em: {analise['data_publicacao']}")
        else:
            # Mensagem para o caso de não haver análises para o país selecionado
            st.info(f"Nenhuma análise macro foi encontrada para **{pais_selecionado_nome}** no momento.")


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
