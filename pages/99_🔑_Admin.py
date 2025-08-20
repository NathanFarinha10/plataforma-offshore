import streamlit as st
from supabase import create_client, Client
import pandas as pd 

# --- INICIALIZAÇÃO DA CONEXÃO ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÕES DE CONSULTA AO BANCO ---
@st.cache_data(ttl=600)
def get_gestoras():
    response = supabase.table('gestoras').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

@st.cache_data(ttl=600)
def get_paises():
    response = supabase.table('paises').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

@st.cache_data(ttl=600)
def get_classes_de_ativos():
    response = supabase.table('classes_de_ativos').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

@st.cache_data(ttl=600)
def get_subclasses_de_ativos(classe_pai_id):
    if not classe_pai_id:
        return {}
    response = supabase.table('subclasses_de_ativos').select('id, nome').eq('classe_pai_id', classe_pai_id).execute()
    return {item['nome']: item['id'] for item in response.data}

@st.cache_data(ttl=60)
def get_temas():
    response = supabase.table('temas').select('id, nome').execute()
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
    classes_map = get_classes_de_ativos()
    temas_map = get_temas()

    tab_analise, tab_indicadores, tab_temas = st.tabs(["Lançar Análise", "Gerenciar Indicadores", "Gerenciar Temas"])

    with tab_analise:
        st.header("Inserir Nova Análise")
        with st.form("nova_analise_form", clear_on_submit=True):
            titulo = st.text_input("Título da Análise")
            tipo_analise = st.selectbox("Tipo de Análise", options=["Macro", "Visão BC", "Tese", "Asset", "MicroAsset", "Thematic"])

            tema_id_final = None
            if tipo_analise == 'Thematic':
                tema_nome = st.selectbox("Selecione o Tema da Análise", options=list(temas_map.keys()))
                tema_id_final = temas_map.get(tema_nome)

            # --- CAMPOS DINÂMICOS ---
            pais_nome = st.selectbox("Selecione o País", options=["N/A"] + list(paises_map.keys()))
            classe_nome = st.selectbox("Selecione a Classe de Ativo (para 'Asset' ou 'MicroAsset')", options=["N/A"] + list(classes_map.keys()))
            
            subclasses_map = {}
            subclasse_id_final = None
            if classe_nome and classe_nome != "N/A":
                classe_id = classes_map.get(classe_nome)
                subclasses_map = get_subclasses_de_ativos(classe_id)
                subclasse_nome = st.selectbox("Selecione a Sub-Classe (para 'MicroAsset')", options=["N/A"] + list(subclasses_map.keys()))
                subclasse_id_final = subclasses_map.get(subclasse_nome)
            
            gestora_nome = st.selectbox("Selecione a Gestora", options=["N/A"] + list(gestoras_map.keys()))
            visao = st.selectbox("Visão", options=["Overweight", "Neutral", "Underweight", "N/A"])
            resumo = st.text_area("Resumo")
            texto_completo = st.text_area("Texto Completo da Análise", height=300)
            
            submitted = st.form_submit_button("Salvar Análise")
            if submitted:
                # Mapeia nomes para IDs
                pais_id = paises_map.get(pais_nome)
                gestora_id = gestoras_map.get(gestora_nome)
                classe_id_final = classes_map.get(classe_nome)
                
                nova_analise_data = {
                    'titulo': titulo, 'resumo': resumo, 'texto_completo': texto_completo,
                    'tipo_analise': tipo_analise, 'visao': visao, 'pais_id': pais_id,
                    'gestora_id': gestora_id, 'classe_de_ativo_id': classe_id_final,
                    'subclasse_de_ativo_id': subclasse_id_final,
                    'tema_id': tema_id_final
                }
                try:
                    supabase.table('analises').insert(nova_analise_data).execute()
                    st.success("Análise salva com sucesso!")
                    st.cache_data.clear() # Limpa o cache para recarregar os temas se um novo for adicionado
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

    with tab_temas:
        st.header("Gerenciar Temas de Investimento")
        with st.form("novo_tema_form", clear_on_submit=True):
            novo_tema = st.text_input("Nome do Novo Tema")
            submitted_tema = st.form_submit_button("Adicionar Tema")
            if submitted_tema and novo_tema:
                try:
                    supabase.table('temas').insert({'nome': novo_tema}).execute()
                    st.success(f"Tema '{novo_tema}' adicionado com sucesso!")
                    st.cache_data.clear() # Limpa o cache para que o novo tema apareça nos seletores
                except Exception as e:
                    st.error(f"Erro ao adicionar tema: {e}")
        
        st.markdown("---")
        st.write("Temas existentes:")
        st.dataframe(pd.DataFrame(list(temas_map.keys()), columns=["Tema"]))

elif password:
    st.error("Senha incorreta. Tente novamente.")
