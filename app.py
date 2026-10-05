import os
import pandas as pd
import streamlit as st
import plotly.express as px

# Para la nube, usamos la API Key que configuraremos en los secretos de Streamlit
os.environ["OPENAI_API_KEY"] = "sk-fake-key" # Bypass para herramientas locales
os.environ["CREWAI_TOOLS_ALLOW_UNSAFE_PATHS"] = "true"
if "GROQ_API_KEY" not in os.environ and "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

from crewai import Agent, Task, Crew, Process
from crewai_tools import MDXSearchTool
from langchain_groq import ChatGroq

# ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
st.set_page_config(page_title="Pluxow & AD Partners AI Demos", page_icon="🚀", layout="wide")

# ---------------- SISTEMA DE LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔒 Acceso a la Plataforma PMO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Pluxow + Practical Thinking Group</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                if usuario == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = "Administrador"
                    st.rerun()
                elif usuario == "consultor" and password == "user123":
                    st.session_state.logged_in = True
                    st.session_state.role = "consultor"
                    st.session_state.username = "Consultor PMO"
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Intente nuevamente.")
        
        st.info("**Cuentas de prueba para la Demo:**\n\nDueño: `admin` / `admin123`\n\nEmpleado: `consultor` / `user123`")
    st.stop() 

# ---------------- MENÚ LATERAL ----------------
st.sidebar.title("🚀 Menú de Soluciones AI")
st.sidebar.success(f"👤 Bienvenido, **{st.session_state.username}**")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

st.sidebar.divider()
demo_seleccionada = st.sidebar.radio(
    "Seleccione el entorno:", 
    ["Demo 1: Asistente Normativas PMO", "Demo 2: Tablero Tracking Beneficios", "⚙️ Panel de Administración"]
)

# ---------------- MOTOR LLM (NUBE - GROQ) ----------------
@st.cache_resource
def iniciar_llm_nube():
    # Usamos el modelo ultrarrápido de Llama 3 en Groq
    return ChatGroq(model_name="llama3-70b-8192", temperature=0)

nube_llm = iniciar_llm_nube()

# ==========================================================
# DEMO 1: ASISTENTE RAG
# ==========================================================
if demo_seleccionada == "Demo 1: Asistente Normativas PMO":
    st.title("🤖 Asistente de Normativas PMO")
    
    # Ruta relativa para la nube
    md_path = "normativas_pmo_demo.md"

    @st.cache_resource
    def crear_agente_pmo():
        md_tool = MDXSearchTool(mdx=md_path) # Simplified tool setup for cloud
        return Agent(
            role='Especialista en Normativas PMO',
            goal='Responder dudas basándose exclusivamente en el documento Markdown.',
            backstory='Consultor experto. Siempre justificas tu respuesta extrayendo datos exactos.',
            tools=[md_tool], llm=nube_llm, verbose=True, allow_delegation=False
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ej: ¿Cuáles son los pasos para cerrar un proyecto?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Buscando en repositorios..."):
                agente = crear_agente_pmo()
                tarea = Task(description=f'Responde usando el documento Markdown: "{prompt}"', expected_output='Respuesta estructurada en viñetas.', agent=agente)
                resultado = str(Crew(agents=[agente], tasks=[tarea], process=Process.sequential).kickoff())
                st.markdown(resultado)
                st.session_state.messages.append({"role": "assistant", "content": resultado})

# ==========================================================
# DEMO 2: TABLERO INTELIGENTE
# ==========================================================
elif demo_seleccionada == "Demo 2: Tablero Tracking Beneficios":
    st.title("📊 Tablero de Control: KPIs y Estado RAG")
    
    # Ruta relativa para la nube
    csv_path = "proyectos_kpi.csv"
    
    try:
        df = pd.read_csv(csv_path)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Proyectos", len(df))
        m2.metric("Proyectos On Track", len(df[df['Estado_RAG'] == 'Green']))
        m3.metric("Proyectos en Riesgo", len(df[df['Estado_RAG'] == 'Amber']))
        m4.metric("Proyectos Críticos", len(df[df['Estado_RAG'] == 'Red']))
        
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            st.plotly_chart(px.pie(df, names='Estado_RAG', hole=0.4, title='Estado RAG', color='Estado_RAG', color_discrete_map={'Green':'#28a745', 'Amber':'#ffc107', 'Red':'#dc3545'}), use_container_width=True)
        with col_pie2:
            st.plotly_chart(px.pie(df, names='Nivel_Riesgo', hole=0.4, title='Nivel de Riesgo', color='Nivel_Riesgo', color_discrete_map={'Bajo':'#28a745', 'Medio':'#ffc107', 'Alto':'#dc3545'}), use_container_width=True)

        st.divider()

        if st.button("Generar Reporte Ejecutivo con IA 🧠", type="primary"):
            with st.spinner("El Analista Financiero IA está procesando los KPIs..."):
                datos_texto = df.to_markdown(index=False)
                
                analista_financiero = Agent(
                    role='Analista Senior de PMO y Riesgos',
                    goal='Analizar KPIs financieros y cruzar el estado RAG con niveles de riesgo.',
                    backstory='Auditor experto de AD Partners.',
                    llm=nube_llm, verbose=True, allow_delegation=False
                )
                tarea_analisis = Task(description=f"Analiza:\n\n{datos_texto}\n\nConcéntrate en proyectos 'Red' y 'Amber'.", expected_output="Un reporte ejecutivo estructurado.", agent=analista_financiero)
                reporte_final = str(Crew(agents=[analista_financiero], tasks=[tarea_analisis], process=Process.sequential).kickoff())
                
                st.success("Reporte generado.")
                st.info(reporte_final)

    except FileNotFoundError:
        st.error(f"No se encontró el archivo CSV en la nube.")

# ==========================================================
# PANEL DE ADMINISTRACIÓN
# ==========================================================
elif demo_seleccionada == "⚙️ Panel de Administración":
    st.title("⚙️ Gestión de Base de Conocimientos")
    if st.session_state.role != "admin":
        st.error("🚫 ACCESO DENEGADO")
    else:
        st.success("✅ Acceso Autorizado: Perfil Administrador")
        st.markdown("Función de subida de archivos deshabilitada en la versión Demo Cloud.")