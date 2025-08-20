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

@st.cache_data(ttl=60)
def get_all_indicators():
    response = supabase.table('indicadores_economicos').select('id, nome_indicador, paises(nome)').order('nome_indicador').execute()
    return {"--- Criar Novo Indicador ---": None, **{f"{item['paises']['nome']} - {item['nome_indicador']}": item['id'] for item in response.data}}

@st.cache_data(ttl=60)
def get_full_indicator_details(indicator_id):
    if not indicator_id: return None
    response = supabase.table('indicadores_economicos').select('*').eq('id', indicator_id).single().execute()
    return response.data

@st.cache_data(ttl=60)
def get_all_themes():
    response = supabase.table('temas').select('id, nome').order('nome').execute()
    return {"--- Criar Novo Tema ---": None, **{item['nome']: item['id'] for item in response.data}}

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

    tab_analise, tab_indicadores, tab_temas, tab_alertas, tab_alocacoes = st.tabs([
        "Gerenciar Análises", "Gerenciar Indicadores", "Gerenciar Temas", 
        "Gerenciar Alertas", "Gerenciar Alocações"
    ])

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
        
        indicators_map = get_all_indicators()
        paises_map = get_all_data('paises')

        selected_indicator_label = st.selectbox(
            "Selecione um indicador para editar ou escolha 'Criar Novo Indicador'",
            options=list(indicators_map.keys()),
            key="indicator_select"
        )
        selected_indicator_id = indicators_map[selected_indicator_label]
        indicator_data = get_full_indicator_details(selected_indicator_id) if selected_indicator_id else {}

        with st.form("indicadores_form", clear_on_submit=False):
            def get_pais_index(pais_id):
                if not pais_id: return 0
                reverse_map = {v: k for k, v in paises_map.items()}
                key = reverse_map.get(pais_id)
                return list(paises_map.keys()).index(key) if key in paises_map else 0

            pais_nome = st.selectbox("País do Indicador", options=list(paises_map.keys()), index=get_pais_index(indicator_data.get('pais_id')))
            nome_indicador = st.text_input("Nome do Indicador", value=indicator_data.get('nome_indicador', ''))
            valor_atual = st.text_input("Valor Atual", value=indicator_data.get('valor_atual', ''))
            data_referencia = st.text_input("Data de Referência", value=indicator_data.get('data_referencia', ''))
            
            tendencia_options = ["N/A", "Estável 😐", "Alta ↗️", "Baixa ↘️"]
            tendencia_idx = tendencia_options.index(indicator_data.get('tendencia', "N/A")) if indicator_data.get('tendencia') in tendencia_options else 0
            tendencia = st.selectbox("Tendência", options=tendencia_options, index=tendencia_idx)
            
            submitted_indicador = st.form_submit_button("Salvar Indicador")
            if submitted_indicador:
                pais_id = paises_map[pais_nome]
                form_data = {
                    'pais_id': pais_id, 'nome_indicador': nome_indicador,
                    'valor_atual': valor_atual, 'data_referencia': data_referencia,
                    'tendencia': tendencia
                }
                try:
                    if selected_indicator_id:
                        supabase.table('indicadores_economicos').update(form_data).eq('id', selected_indicator_id).execute()
                        st.success(f"Indicador '{nome_indicador}' atualizado com sucesso!")
                    else:
                        supabase.table('indicadores_economicos').insert(form_data).execute()
                        st.success(f"Indicador '{nome_indicador}' criado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar indicador: {e}")
        
        if selected_indicator_id:
            if st.button(f"Apagar Indicador '{selected_indicator_label}'", type="primary"):
                try:
                    supabase.table('indicadores_economicos').delete().eq('id', selected_indicator_id).execute()
                    st.success("Indicador apagado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao apagar: {e}")

    with tab_temas:
        st.header("Gerenciar Temas de Investimento")
        
        themes_map = get_all_themes()
        selected_theme_name = st.selectbox(
            "Selecione um tema para editar ou escolha 'Criar Novo Tema'",
            options=list(themes_map.keys()),
            key="theme_select"
        )
        selected_theme_id = themes_map[selected_theme_name]

        with st.form("theme_form", clear_on_submit=False):
            nome_tema = st.text_input("Nome do Tema", value=selected_theme_name if selected_theme_id else "")
            submitted_theme = st.form_submit_button("Salvar Tema")

            if submitted_theme and nome_tema:
                try:
                    if selected_theme_id:
                        supabase.table('temas').update({'nome': nome_tema}).eq('id', selected_theme_id).execute()
                        st.success(f"Tema '{nome_tema}' atualizado com sucesso!")
                    else:
                        supabase.table('temas').insert({'nome': nome_tema}).execute()
                        st.success(f"Tema '{nome_tema}' criado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar tema: {e}")

        if selected_theme_id:
            if st.button(f"Apagar Tema '{selected_theme_name}'", type="primary"):
                try:
                    supabase.table('temas').delete().eq('id', selected_theme_id).execute()
                    st.success("Tema apagado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao apagar: {e}")

    with tab_alertas:
        st.header("Gerenciar Alertas para o Hub")
        st.info("Crie alertas que aparecerão em destaque na página principal do Hub.")

        with st.form("alertas_form", clear_on_submit=True):
            titulo = st.text_input("Título do Alerta")
            tipo_alerta = st.selectbox("Tipo de Alerta", options=['Mudança de Visão', 'Risco', 'Oportunidade', 'Notícia'])
            importancia = st.selectbox("Importância", options=['Alta', 'Média', 'Baixa'])
            descricao = st.text_area("Descrição (opcional)")
            
            submitted_alerta = st.form_submit_button("Salvar Alerta")
            if submitted_alerta:
                form_data = {
                    'titulo': titulo,
                    'tipo_alerta': tipo_alerta,
                    'importancia': importancia,
                    'descricao': descricao
                }
                try:
                    supabase.table('alertas').insert(form_data).execute()
                    st.success(f"Alerta '{titulo}' criado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar o alerta: {e}")
        
        # Adicionar aqui a funcionalidade de ver/editar/apagar alertas no futuro
    with tab_alocacoes:
        st.header("Gerenciar Alocações Modelo")
        st.info("Crie e edite as carteiras modelo que serão sugeridas aos utilizadores.")

        # Buscar perfis de risco
        perfis_response = supabase.table('perfis_de_risco').select('id, nome').execute()
        perfis_map = {p['nome']: p['id'] for p in perfis_response.data}
        
        selected_perfil_nome = st.selectbox("Selecione o Perfil de Risco para editar a alocação:", options=perfis_map.keys())
        selected_perfil_id = perfis_map[selected_perfil_nome]

        # Verifica se já existe uma alocação para este perfil
        response = supabase.table('alocacoes_modelo').select('*').eq('perfil_de_risco_id', selected_perfil_id).limit(1).execute()
        alocacao_existente = response.data[0] if response.data else None
        
        if alocacao_existente:
            st.write(f"Editando: **{alocacao_existente['nome_estrategia']}**")
            # Carrega componentes existentes
            componentes_existentes = supabase.table('componentes_alocacao').select('*').eq('alocacao_modelo_id', alocacao_existente['id']).execute().data
            df_componentes = pd.DataFrame(componentes_existentes)
        else:
            st.warning(f"Nenhuma alocação encontrada para o perfil '{selected_perfil_nome}'. Crie uma abaixo.")
            df_componentes = pd.DataFrame(columns=['nome_ativo', 'ticker_exemplo', 'percentual', 'justificativa'])

        with st.form("alocacao_form"):
            nome_estrategia = st.text_input("Nome da Estratégia", value=alocacao_existente['nome_estrategia'] if alocacao_existente else f"Alocação {selected_perfil_nome} Global")
            
            st.write("Componentes da Alocação:")
            
            # Usar o editor de dados do Streamlit para uma experiência de tabela
            edited_df = st.data_editor(df_componentes[['nome_ativo', 'ticker_exemplo', 'percentual', 'justificativa']], num_rows="dynamic", key="alocacao_editor")

            submitted = st.form_submit_button("Salvar Alocação")
            if submitted:
                total_percentual = edited_df['percentual'].astype(float).sum()
                if not (99.9 <= total_percentual <= 100.1):
                    st.error(f"A soma dos percentuais deve ser 100%. Soma atual: {total_percentual:.2f}%")
                else:
                    try:
                        # Se a alocação não existe, cria-a primeiro
                        if not alocacao_existente:
                            alocacao_existente = supabase.table('alocacoes_modelo').insert({
                                'perfil_de_risco_id': selected_perfil_id,
                                'nome_estrategia': nome_estrategia
                            }).execute().data[0]
                        
                        alocacao_id = alocacao_existente['id']
                        # Apaga os componentes antigos
                        supabase.table('componentes_alocacao').delete().eq('alocacao_modelo_id', alocacao_id).execute()
                        
                        # Insere os novos componentes
                        novos_componentes = edited_df.to_dict('records')
                        for comp in novos_componentes:
                            comp['alocacao_modelo_id'] = alocacao_id
                        
                        supabase.table('componentes_alocacao').insert(novos_componentes).execute()
                        st.success(f"Alocação para o perfil '{selected_perfil_nome}' salva com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar a alocação: {e}") 

elif password:
    st.error("Senha incorreta. Tente novamente.")
