import streamlit as st
from supabase import create_client, Client

# --- INICIALIZAÇÃO DA CONEXÃO COM O SUPABASE ---

# Função para inicializar a conexão. Usa o cache do Streamlit para evitar reconectar a cada interação.
@st.cache_resource
def init_connection() -> Client:
    """Inicializa e retorna o cliente do Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Cria o cliente Supabase
supabase = init_connection()

# --- FUNÇÕES DE CONSULTA AO BANCO ---

def get_gestoras():
    """Busca todas as gestoras para popular o selectbox."""
    response = supabase.table('gestoras').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

def get_paises():
    """Busca todos os países para popular o selectbox."""
    response = supabase.table('paises').select('id, nome').execute()
    return {item['nome']: item['id'] for item in response.data}

# --- INTERFACE DA PÁGINA ADMIN ---

st.set_page_config(page_title="Painel Admin", page_icon="🔑", layout="wide")
st.title("🔑 Painel de Administração")
st.write("Área para inserção e gerenciamento de conteúdo da plataforma.")
st.markdown("---")

# --- SISTEMA DE AUTENTICAÇÃO SIMPLES ---

# Pede a senha ao usuário
password = st.text_input("Digite a senha para acessar o painel", type="password")

# Verifica se a senha está correta (comparando com o que está nos Secrets)
if password == st.secrets["ADMIN_PASSWORD"]:
    st.success("Acesso liberado!")

    # Carrega os dados para os dropdowns
    gestoras_map = get_gestoras()
    paises_map = get_paises()

    st.header("Inserir Nova Análise Macro")

    # Cria um formulário para a inserção de dados
    with st.form("nova_analise_form", clear_on_submit=True):
        # Campos do formulário
        titulo = st.text_input("Título da Análise")
        
        # Dropdowns para selecionar itens de outras tabelas
        gestora_nome = st.selectbox("Selecione a Gestora", options=list(gestoras_map.keys()))
        pais_nome = st.selectbox("Selecione o País", options=list(paises_map.keys()))
        
        visao = st.selectbox("Visão", options=["Overweight", "Neutral", "Underweight", "N/A"])
        tipo_analise = "Macro" # Por enquanto, fixo como "Macro"
        
        resumo = st.text_area("Resumo (aparecerá nas listagens)")
        texto_completo = st.text_area("Texto Completo da Análise", height=300)
        
        # Botão de envio do formulário
        submitted = st.form_submit_button("Salvar Análise")

        # Lógica a ser executada quando o botão for clicado
        if submitted:
            # Pega o ID correspondente ao nome selecionado nos dropdowns
            gestora_id = gestoras_map[gestora_nome]
            pais_id = paises_map[pais_nome]
            
            # Monta o objeto a ser inserido no banco
            nova_analise_data = {
                'titulo': titulo,
                'resumo': resumo,
                'texto_completo': texto_completo,
                'tipo_analise': tipo_analise,
                'visao': visao,
                'gestora_id': gestora_id,
                'pais_id': pais_id
            }
            
            # Tenta inserir os dados na tabela 'analises'
            try:
                response = supabase.table('analises').insert(nova_analise_data).execute()
                st.success("Análise salva com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar a análise: {e}")

elif password: # Se o usuário digitou algo, mas a senha está errada
    st.error("Senha incorreta. Tente novamente.")
