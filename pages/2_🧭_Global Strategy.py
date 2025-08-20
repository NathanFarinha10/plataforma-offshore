import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- INTERFACE ---
st.set_page_config(page_title="Global Strategy", page_icon="🧭", layout="wide")
st.title("🧭 Arquiteto de Estratégia Global")
st.write("Descubra uma alocação de ativos globais alinhada com os seus objetivos. Responda às perguntas abaixo para determinar o seu perfil.")

# --- QUESTIONÁRIO DE PERFIL DE RISCO ---
st.header("Questionário de Perfil de Risco")

pontuacao = 0
respostas = {}

q1 = st.radio(
    "1. Qual é o seu principal objetivo ao investir no exterior?",
    ["Preservação de capital com baixo risco", "Equilíbrio entre crescimento e segurança", "Maximizar o crescimento a longo prazo"],
    key="q1"
)
respostas['q1'] = q1
if q1 == "Equilíbrio entre crescimento e segurança": pontuacao += 5
elif q1 == "Maximizar o crescimento a longo prazo": pontuacao += 10

q2 = st.radio(
    "2. Por quanto tempo pretende manter os seus investimentos aplicados?",
    ["Menos de 3 anos", "Entre 3 e 10 anos", "Mais de 10 anos"],
    key="q2"
)
respostas['q2'] = q2
if q2 == "Entre 3 e 10 anos": pontuacao += 5
elif q2 == "Mais de 10 anos": pontuacao += 10

q3 = st.radio(
    "3. Imagine que o mercado global cai 20%. Como reagiria?",
    ["Venderia a maior parte dos meus ativos para evitar mais perdas.", "Manteria os investimentos, mas ficaria preocupado.", "Veria como uma oportunidade para comprar mais."],
    key="q3"
)
respostas['q3'] = q3
if q3 == "Manteria os investimentos, mas ficaria preocupado.": pontuacao += 5
elif q3 == "Veria como uma oportunidade para comprar mais.": pontuacao += 10

# --- LÓGICA DE APRESENTAÇÃO DO RESULTADO ---
if st.button("Descobrir Meu Perfil e Estratégia"):
    perfil_final = ""
    if pontuacao <= 10:
        perfil_final = "Conservador"
    elif 11 <= pontuacao <= 20:
        perfil_final = "Moderado"
    else:
        perfil_final = "Arrojado"

    st.header(f"Seu Perfil de Investidor: **{perfil_final}**")
    
    # Busca a alocação modelo para o perfil determinado
    perfil_id_response = supabase.table('perfis_de_risco').select('id').eq('nome', perfil_final).execute()
    
    if perfil_id_response.data:
        perfil_id = perfil_id_response.data[0]['id']
        alocacao_response = supabase.table('alocacoes_modelo').select('id, nome_estrategia').eq('perfil_de_risco_id', perfil_id).single().execute()
        
        if alocacao_response.data:
            alocacao = alocacao_response.data
            componentes_response = supabase.table('componentes_alocacao').select('*').eq('alocacao_modelo_id', alocacao['id']).execute()
            
            if componentes_response.data:
                df_componentes = pd.DataFrame(componentes_response.data)
                
                st.subheader(f"Estratégia de Alocação Sugerida: {alocacao['nome_estrategia']}")
                
                # Gráfico de Alocação
                fig = px.pie(df_componentes, values='percentual', names='nome_ativo', title='Distribuição da Carteira Modelo', hole=.3)
                st.plotly_chart(fig, use_container_width=True)

                # Detalhes da Alocação
                st.write("Componentes da Alocação:")
                for index, row in df_componentes.iterrows():
                    with st.expander(f"**{row['nome_ativo']} ({row['percentual']}%)** - Exemplo: {row['ticker_exemplo']}"):
                        st.write(row['justificativa'])
            else:
                st.warning("Ainda não foram definidos os componentes para esta alocação modelo.")
        else:
            st.error(f"Nenhuma estratégia de alocação foi encontrada para o perfil '{perfil_final}'. Por favor, contacte o administrador.")
    else:
        st.error("Perfil de risco não encontrado na base de dados.")
