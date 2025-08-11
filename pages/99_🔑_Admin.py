import streamlit as st
from supabase import create_client, Client

# --- INICIALIZAÇÃO DA CONEXÃO ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÕES DE CONSULTA AO BANCO ---
def get_gestoras():
    response = supabase.table('gestoras').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

def get_paises():
    response = supabase.table('paises').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

# --- INTERFACE DA PÁGINA ADMIN ---
st.set_page_config(page_title="Painel Admin", page_icon="🔑", layout="wide")
st.title("🔑 Painel de Administração")
st.write("Área para inserção e gerenciamento de conteúdo da plataforma.")
st.markdown("---")

# --- SISTEMA DE AUTENTICAÇÃO ---
password = st.text_input("Digite a senha para acessar o painel", type="password")

if password == st.secrets["ADMIN_PASSWORD"]:
    st.success("Acesso liberado!")

    # Carrega os dados para os dropdowns
    gestoras_map = get_gestoras()
    paises_map = get_paises()

    # Separa os formulários em abas para melhor organização
    tab_analise, tab_indicadores = st.tabs(["Lançar Análise", "Gerenciar Indicadores"])

    with tab_analise:
        st.header("Inserir Nova Análise")
        with st.form("nova_analise_form", clear_on_submit=True):
            titulo = st.text_input("Título da Análise")
            
            # Tipos de análise agora incluem 'Visão BC'
            tipo_analise = st.selectbox("Tipo de Análise", options=["Macro", "Visão BC", "Asset", "Driver", "Tese"])
            
            gestora_nome = st.selectbox("Selecione a Gestora (deixe em branco para Visão BC)", options=["N/A"] + list(gestoras_map.keys()))
            pais_nome = st.selectbox("Selecione o País", options=list(paises_map.keys()))
            visao = st.selectbox("Visão", options=["Overweight", "Neutral", "Underweight", "N/A"])
            
            resumo = st.text_area("Resumo")
            texto_completo = st.text_area("Texto Completo da Análise", height=300)
            
            submitted = st.form_submit_button("Salvar Análise")
            if submitted:
                gestora_id = gestoras_map.get(gestora_nome) # .get() para não dar erro se for "N/A"
                pais_id = paises_map[pais_nome]
                
                nova_analise_data = {
                    'titulo': titulo, 'resumo': resumo, 'texto_completo': texto_completo,
                    'tipo_analise': tipo_analise, 'visao': visao,
                    'gestora_id': gestora_id, 'pais_id': pais_id
                }
                try:
                    supabase.table('analises').insert(nova_analise_data).execute()
                    st.success("Análise salva com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar a análise: {e}")

    with tab_indicadores:
        st.header("Gerenciar Indicadores Econômicos")
        with st.form("indicadores_form", clear_on_submit=True):
            pais_indicador_nome = st.selectbox("País do Indicador", options=list(paises_map.keys()))
            nome_indicador = st.text_input("Nome do Indicador (Ex: Inflação (CPI))")
            valor_atual = st.text_input("Valor Atual (Ex: 5.2%)")
            data_referencia = st.text_input("Data de Referência (Ex: Jul/2025)")
            tendencia = st.selectbox("Tendência", options=["Estável 😐", "Alta ↗️", "Baixa ↘️", "N/A"])
            
            submitted_indicador = st.form_submit_button("Salvar Indicador")
            if submitted_indicador:
                pais_id = paises_map[pais_indicador_nome]
                
                indicador_data = {
                    'pais_id': pais_id, 'nome_indicador': nome_indicador,
                    'valor_atual': valor_atual, 'data_referencia': data_referencia,
                    'tendencia': tendencia.split(" ")[0] # Salva apenas a palavra
                }
                try:
                    # 'upsert' atualiza se o indicador já existir para o país, ou cria um novo.
                    supabase.table('indicadores_economicos').upsert(indicador_data).execute()
                    st.success(f"Indicador '{nome_indicador}' salvo para {pais_indicador_nome}!")
                except Exception as e:
                    st.error(f"Erro ao salvar indicador: {e}")

elif password:
    st.error("Senha incorreta. Tente novamente.")
