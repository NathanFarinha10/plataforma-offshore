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
# Adicionamos 'order' para que as listas apareçam sempre na mesma ordem
@st.cache_data(ttl=60)
def get_all_data(table_name):
    response = supabase.table(table_name).select('id, nome').order('nome').execute()
    return {item['nome']: item['id'] for item in response.data}

@st.cache_data(ttl=60)
def get_all_analyses():
    response = supabase.table('analises').select('id, titulo').order('titulo').execute()
    return {"--- Criar Nova Análise ---": None, **{item['titulo']: item['id'] for item in response.data}}

@st.cache_data(ttl=60)
def get_full_analysis_details(analysis_id):
    if not analysis_id:
        return None
    response = supabase.table('analises').select('*').eq('id', analysis_id).single().execute()
    return response.data

# --- INTERFACE DA PÁGINA ADMIN ---
st.set_page_config(page_title="Painel Admin", page_icon="🔑", layout="wide")
st.title("🔑 Painel de Administração")
st.markdown("---")

# --- SISTEMA DE AUTENTICAÇÃO ---
password = st.text_input("Digite a senha para acessar o painel", type="password")

if password == st.secrets["ADMIN_PASSWORD"]:
    st.success("Acesso liberado!")

    # Carrega os dados para os dropdowns
    gestoras_map = get_all_data('gestoras')
    paises_map = get_all_data('paises')
    classes_map = get_all_data('classes_de_ativos')
    temas_map = get_all_data('temas')
    analyses_map = get_all_analyses()

    tab_analise, tab_indicadores, tab_temas = st.tabs(["Gerenciar Análises", "Gerenciar Indicadores", "Gerenciar Temas"])

    with tab_analise:
        st.header("Gestão de Análises")

        selected_analysis_title = st.selectbox(
            "Selecione uma análise para editar ou escolha 'Criar Nova Análise'",
            options=list(analyses_map.keys())
        )
        
        selected_analysis_id = analyses_map[selected_analysis_title]
        
        # Carrega os dados da análise selecionada se houver uma
        analysis_data = get_full_analysis_details(selected_analysis_id) if selected_analysis_id else {}

        # Função para encontrar o índice de um valor num dicionário de mapeamento
        def get_index(value_id, data_map):
            if value_id is None: return 0
            try:
                # Cria um dicionário reverso de ID para Nome
                reverse_map = {v: k for k, v in data_map.items()}
                # Encontra a chave (nome) correspondente ao ID
                key = reverse_map.get(value_id)
                # Retorna o índice da chave na lista de opções
                return list(data_map.keys()).index(key)
            except (ValueError, KeyError):
                return 0 # Retorna 0 (primeira opção) se não encontrar

        with st.form("analysis_form"):
            titulo = st.text_input("Título da Análise", value=analysis_data.get('titulo', ''))
            
            # Preenche os seletores com os valores existentes
            tipo_analise = st.selectbox("Tipo de Análise", options=["Macro", "Visão BC", "Tese", "Asset", "MicroAsset", "Thematic"], index=["Macro", "Visão BC", "Tese", "Asset", "MicroAsset", "Thematic"].index(analysis_data.get('tipo_analise', 'Macro')))
            
            pais_idx = get_index(analysis_data.get('pais_id'), paises_map)
            pais_nome = st.selectbox("País", options=list(paises_map.keys()), index=pais_idx)
            
            gestora_idx = get_index(analysis_data.get('gestora_id'), gestoras_map)
            gestora_nome = st.selectbox("Gestora", options=list(gestoras_map.keys()), index=gestora_idx)
            
            # (Campos para classe, subclasse e tema seriam adicionados aqui com lógica similar)

            visao = st.selectbox("Visão", options=["Overweight", "Neutral", "Underweight", "N/A"], index=["Overweight", "Neutral", "Underweight", "N/A"].index(analysis_data.get('visao', 'N/A')))
            resumo = st.text_area("Resumo", value=analysis_data.get('resumo', ''))
            texto_completo = st.text_area("Texto Completo", value=analysis_data.get('texto_completo', ''), height=300)
            
            submitted = st.form_submit_button("Salvar")

            if submitted:
                form_data = {
                    'titulo': titulo, 'tipo_analise': tipo_analise, 'visao': visao,
                    'resumo': resumo, 'texto_completo': texto_completo,
                    'pais_id': paises_map.get(pais_nome),
                    'gestora_id': gestoras_map.get(gestora_nome)
                }
                
                try:
                    if selected_analysis_id: # Se um ID existe, é uma ATUALIZAÇÃO (UPDATE)
                        supabase.table('analises').update(form_data).eq('id', selected_analysis_id).execute()
                        st.success(f"Análise '{titulo}' atualizada com sucesso!")
                    else: # Se não há ID, é uma CRIAÇÃO (INSERT)
                        supabase.table('analises').insert(form_data).execute()
                        st.success(f"Análise '{titulo}' criada com sucesso!")
                    
                    st.cache_data.clear() # Limpa o cache para recarregar as listas
                    st.rerun() # Força a recarga da página para mostrar as atualizações
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        # --- SEÇÃO DE APAGAR ---
        if selected_analysis_id:
            st.markdown("---")
            st.subheader("⚠️ Zona de Perigo")
            if st.button(f"Apagar Análise '{selected_analysis_title}'", type="primary"):
                try:
                    supabase.table('analises').delete().eq('id', selected_analysis_id).execute()
                    st.success("Análise apagada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao apagar: {e}")

    with tab_indicadores:
        st.header("Gerenciar Indicadores Econômicos")
        st.info("Funcionalidade de Editar/Apagar para Indicadores em breve.")

    with tab_temas:
        st.header("Gerenciar Temas de Investimento")
        st.info("Funcionalidade de Editar/Apagar para Temas em breve.")

elif password:
    st.error("Senha incorreta. Tente novamente.")
